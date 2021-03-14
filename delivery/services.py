from django.db.models import Avg, ExpressionWrapper, F, \
    Q, TimeField
from django.utils import timezone

from delivery.models import Courier, Invoice, Order

COURIER_LOAD_CAPACITY = {
    Courier.CourierType.FOOT: 10,
    Courier.CourierType.BIKE: 15,
    Courier.CourierType.CAR: 50,
}

WAGE_RATE = 500

PAY_COEFFICIENTS = {
    Courier.CourierType.FOOT: 2,
    Courier.CourierType.BIKE: 5,
    Courier.CourierType.CAR: 9,
}


def get_available_orders(courier):
    """ Вернуть все подходящие курьеру заказы.

    Заметки: время работы курьера может начаться за минуту до окончания времени
    доставки. По условию, такой заказ доступен для курьера, но приняв такой
    заказ курьер вряд ли сможет его доставить в заданное время. Возможно
    стоит предусмотреть гэп.
    """
    working_hours = courier.working_hours.values('begin', 'end')
    working_hours_limit = Q()
    for interval in working_hours:
        working_hours_limit = (
            working_hours_limit |
            Q(delivery_hours__begin__range=(
                interval['begin'], interval['end'])) |
            Q(delivery_hours__end__range=(
                interval['begin'], interval['end']))
        )
    return Order.objects.filter(
        complete_time__isnull=True,
        region__in=courier.regions.all(),
        weight__lte=COURIER_LOAD_CAPACITY[courier.courier_type],
    ).filter(working_hours_limit)


def assign_orders(courier):
    """Назначить максимально возможное по общему весу количество подходящих
    курьеру заказов и вернуть их список.

    Заметки: по условию задачи необходимо назначить максимальное количество
    подходящих заказов, т.е. назначаем заказы начиная с наименьшего по весу
    пока помещается в "рюкзак". В реальности для повышения качества работы
    сервиса стоит оптимизировать загрузку с учетом приоритетов:
    - долго висящих не назначенных заказов;
    - доставки внутри одного района;
    - максимальной загрузки "рюкзака";
    - с загрузкой самого тяжелого из доступных данному типу курьера.
    """
    available_orders = get_available_orders(courier).order_by('weight')
    if not available_orders:
        return []
    delivery_orders = []
    bag_weight = 0
    for order in available_orders:
        bag_weight += order.weight
        if bag_weight > COURIER_LOAD_CAPACITY[courier.courier_type]:
            break
        delivery_orders.append(order.order_id)
    invoice = Invoice.objects.create(courier=courier)
    invoice.orders.set(delivery_orders)
    return invoice.orders.values(id=F('order_id')).order_by('id')


def get_active_orders(courier):
    """Если развоз не завершен - вернуть все заказы по накладной, иначе
    назначить новые и вернуть их список.

    Заметки: возврат неисполненных заказов обеспечивает идемпотентность вызова.
    """

    active_invoice = courier.invoices.filter(
        orders__complete_time__isnull=True)
    invoice_orders = Order.objects.filter(invoices__in=active_invoice)
    if active_invoice:
        return invoice_orders.values(id=F('order_id')).order_by('id')
    return assign_orders(courier)


def complete_order(order):
    """Проставить время завершения, если заказ активный и вернуть id заказа."""

    if not order.complete_time:
        order.complete_time = timezone.now()
        order.save()
    return order.order_id


def get_courier_rating(courier):
    delta = ExpressionWrapper(
        F('complete_time') - F('invoices__assigned_time'), TimeField())
    order = (Order.objects
             .filter(complete_time__isnull=False, invoices__courier=courier)
             .values('region_id')
             .annotate(td=Avg(delta))
             )
    min_average_time = int(
        min(order, key=lambda i: i['td'])['td'].total_seconds())
    return round((3600 - min(min_average_time, 3600)) / 3600 * 5, 2)


def get_courier_earning(courier):
    count_invoices = courier.invoices.count()
    return count_invoices * WAGE_RATE * PAY_COEFFICIENTS[courier.courier_type]
