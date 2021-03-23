from django.db.models import Avg, Max, Min, Q, Sum
from django.db.models.functions import Coalesce

from delivery.models import Courier, Invoice, InvoiceOrder, Order

COURIER_LOAD_CAPACITY = {
    Courier.CourierType.FOOT: 10,
    Courier.CourierType.BIKE: 15,
    Courier.CourierType.CAR: 50,
}

PAY_RATE = 500

PAY_COEFFICIENTS = {
    Courier.CourierType.FOOT: 2,
    Courier.CourierType.BIKE: 5,
    Courier.CourierType.CAR: 9,
}


def knapsack(max_weight, order_weight, num_orders):
    memorize = [[0 for _ in range(max_weight + 1)] for _ in
                range(num_orders + 1)]
    for i in range(num_orders + 1):
        for w in range(max_weight + 1):
            if i == 0 or w == 0:
                memorize[i][w] = 0
            elif order_weight[i - 1] <= w:
                memorize[i][w] = max(
                    order_weight[i - 1] + memorize[i - 1][
                        w - order_weight[i - 1]],
                    memorize[i - 1][w])
            else:
                memorize[i][w] = memorize[i - 1][w]
    return memorize


def get_orders_for_delivery(orders, max_weight):
    knapsack_weight = max_weight * 100
    num_orders = len(orders)
    weights = [int(order.weight * 100) for order in orders]
    memorize = knapsack(knapsack_weight, weights, num_orders)

    pack_orders = []
    w, i, total_weight = knapsack_weight, num_orders, 0
    result = memorize[num_orders][knapsack_weight]
    while i > 0 and result > 0:
        if result != memorize[i - 1][w]:
            pack_orders.append(orders[i - 1])
            result -= weights[i - 1]
            w -= weights[i - 1]
        i -= 1
    return pack_orders


def get_available_orders(courier):
    """ Вернуть запрос на все недоставленные, подходящие курьеру, заказы.

    !!! выборка содержит как свои так и чужие заказы, нужен доп. фильтр.
    """
    working_hours = courier.working_hours.values('begin', 'end')
    working_hours_limit = Q()
    for interval in working_hours:
        working_hours_limit = (
            working_hours_limit |
            Q(delivery_hours__begin__range=(
                interval['begin'], interval['end'] - 1)) |
            Q(delivery_hours__end__range=(
                interval['begin'] + 1, interval['end']))
        )

    return Order.objects.filter(invoice_orders__complete_time__isnull=True,
                                region__in=courier.regions.all(),
                                weight__lte=COURIER_LOAD_CAPACITY[
                                    courier.courier_type],
                                ).filter(working_hours_limit)


def get_active_invoice_orders(courier):
    """ Вернуть все назначенные курьеру, но недоставленные заказы."""
    return InvoiceOrder.objects.filter(invoice__courier=courier,
                                       complete_time__isnull=True)


def get_assign_not_available_orders(courier):
    """Вернуть заказы которые курьер не сможет доставить."""
    # Получим доступные на текущий момент недоставленные заказы курьера
    invoice_orders = get_active_invoice_orders(courier)
    orders = get_available_orders(courier).filter(
        invoice_orders__in=invoice_orders)
    if not orders.exists():
        return False
    # Если общий вес доступных заказов превышает грузоподъемность по текущему
    # типу, то надо выбрать из них комбинацию с максимальным весом
    weight = orders.aggregate(sum_weight=Sum('weight'))['sum_weight']
    max_weight = COURIER_LOAD_CAPACITY[courier.courier_type]
    if (weight > max_weight):
        orders = get_orders_for_delivery(
            orders, COURIER_LOAD_CAPACITY[courier.courier_type])
    unavailable_orders = invoice_orders.exclude(order__in=orders)
    return unavailable_orders


def delete_unavailable_orders(courier):
    unavailable_orders = get_assign_not_available_orders(courier)
    if unavailable_orders:
        unavailable_orders.delete()


def assign_orders(courier):
    """Назначить подходящие заказы курьеру с максимально возможным весом не
    превышающим его грузоподьемность.
    """
    available_orders = get_available_orders(courier).filter(
        invoices__isnull=True)
    if not available_orders:
        return []
    delivery_orders = get_orders_for_delivery(
        available_orders, COURIER_LOAD_CAPACITY[courier.courier_type])
    expected_reward = PAY_RATE * PAY_COEFFICIENTS[courier.courier_type]
    invoice = Invoice.objects.create(courier=courier,
                                     expected_reward=expected_reward)
    invoice.orders.set(delivery_orders)
    return invoice


def get_active_invoice(courier):
    """Если развоз не завершен - вернуть недоставленные заказы по накладной,
    иначе назначить новые и вернуть их список.

    Заметки: возврат неисполненных заказов обеспечивает идемпотентность вызова.
    """
    active_invoice = Invoice.objects.filter(
        courier=courier, invoice_orders__complete_time__isnull=True)
    if active_invoice:
        return active_invoice[0]
    return assign_orders(courier)


def complete_order(invoice_order, complete_time):
    """Проставить время завершения, если заказ активный и вернуть id заказа."""
    if not invoice_order.complete_time:
        last_delivery_time = InvoiceOrder.objects.filter(
            invoice_id=invoice_order.invoice_id
        ).aggregate(time=Max('complete_time'))['time']
        if not last_delivery_time:
            last_delivery_time = invoice_order.invoice.assign_time
        delivery_time = (complete_time - last_delivery_time
                         ).total_seconds()
        invoice_order.complete_time = complete_time
        invoice_order.delivery_time = delivery_time
        invoice_order.save()
    return invoice_order.order_id


def get_courier_rating(courier):
    is_complete_deliveries = Courier.objects.filter(
        invoices__invoice_orders__complete_time__isnull=False).exists()
    if not is_complete_deliveries:
        return None
    min_average_duration = (
        Order.objects
        .filter(invoice_orders__delivery_time__isnull=False,
                invoices__courier=courier)
        .values('region_id')
        .annotate(td=Avg('invoice_orders__delivery_time'))
        .aggregate(time=Min('td')))['time']
    return round((3600 - min(min_average_duration, 3600)) / 3600 * 5, 2)


def get_courier_earning(courier):
    return (
        Invoice.objects
        .filter(courier=courier)
        .exclude(invoice_orders__complete_time__isnull=True)
        .distinct()
        .aggregate(sum=Coalesce(Sum('expected_reward'), 0))['sum']
    )
