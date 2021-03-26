from dateutil.parser import parse
from django.db.models import F
from rest_framework import serializers

from delivery import services
from .models import Courier, InvoiceOrder, Order, Region
from .services import delete_unavailable_orders
from .utils import add_regions, add_time_intervals
from .validators import check_unknown_fields, interval_list_validator


class CourierRelationsSerializer(serializers.Serializer):
    """ Класс CourierRelationsSerializer описывает сериализатор связанных полей
    модели курьера.

    Родительский класс -- serializers.ModelSerializer.
    Переопределенные методы -- create.

    Дополнительные атрибуты класса
    --------
    regions : [int]
        районы работы курьера
    working_hours : [str]
        часы работы курьера.

    Методы класса:
    ________
    validate_delivery_hours
        Выполняет дополнительную валидация поля delivery_hours.
    """
    regions = serializers.ListSerializer(
        child=serializers.IntegerField(min_value=1), required=False)
    working_hours = serializers.ListSerializer(
        child=serializers.CharField(max_length=11, min_length=11),
        required=False)

    def validate_working_hours(self, value):
        return interval_list_validator(value)

    def create(self, validated_data, **kwargs):
        region_codes = validated_data.get('regions')
        if region_codes:
            add_regions(region_codes)
        working_hours = validated_data.get('working_hours')
        if working_hours:
            add_time_intervals(working_hours)
        return validated_data


class OrderRelationsSerializer(serializers.Serializer):
    """ Класс OrderRelationsSerializer описывает сериализатор связанных полей
    модели заказа.

    Родительский класс -- serializers.ModelSerializer.
    Переопределенные методы -- create.

    Дополнительные атрибуты класса
    --------
    region : int
        регион доставки заказа
    delivery_hours : [str]
        интервалы получения заказа

    Методы класса:
    ________
    validate_delivery_hours
        Выполняет дополнительную валидация поля delivery_hours
    """
    region = serializers.IntegerField(min_value=1)
    delivery_hours = serializers.ListSerializer(
        child=serializers.CharField(max_length=11, min_length=11))

    def validate_delivery_hours(self, value):
        return interval_list_validator(value)

    def create(self, validated_data, **kwargs):
        Region.objects.get_or_create(code=validated_data['region'])
        delivery_hours = validated_data.get('delivery_hours')
        add_time_intervals(delivery_hours)
        return validated_data


class CourierSerializer(serializers.ModelSerializer):
    """ Класс CourierSerializer описывает сериализатор модели курьера.

    Родительский класс -- serializers.ModelSerializer.
    Переопределенные методы -- run_validation, update, to_representation.

    Дополнительные атрибуты класса
    --------
    rating : Decimal
        Рейтинг курьера
    earnings : Decimal
        Заработок курьера

    Методы класса:
    ________
    validate_courier_id
        Выполняет дополнительную валидация поля courier_id
    get_rating
        Получает значение для поля rating
    get_earnings
        Получает значение для поля earnings
    """
    rating = serializers.SerializerMethodField()
    earnings = serializers.SerializerMethodField()

    class Meta:
        model = Courier
        fields = ['courier_id', 'courier_type', 'regions', 'working_hours',
                  'rating', 'earnings', ]

    def validate_courier_id(self, value):
        if (self.context['request'].method == 'PATCH'
                and self.initial_data.get('courier_id')):
            raise serializers.ValidationError('Поле недоступно для изменения')
        return value

    def get_rating(self, instance):
        return services.get_courier_rating(instance)

    def get_earnings(self, instance):
        return services.get_courier_earning(instance)

    def run_validation(self, data=serializers.empty):
        check_unknown_fields(self.fields, data)
        return super().run_validation(data)

    def update(self, instance, validated_data):
        courier = super().update(instance, validated_data)
        delete_unavailable_orders(courier)
        return courier

    def to_representation(self, instance):
        # При post-запросе возвращаем только идентификаторы курьеров
        if self.context['request'].method == 'POST':
            value_id = instance.get('courier_id') if isinstance(
                instance, dict) else instance.courier_id
            return {'id': value_id}
        # Если доставок у курьера не было, поле с рейтингом исключаем
        result = super().to_representation(instance)
        if result.get('rating') is None:
            result.pop('rating')
        return result


class OrderSerializer(serializers.ModelSerializer):
    """ Класс OrderSerializer описывает сериализатор модели заказа.

    Родительский класс -- serializers.ModelSerializer.
    Переопределенные методы -- run_validation, to_representation.
    """

    class Meta:
        model = Order
        fields = ['order_id', 'weight', 'region', 'delivery_hours', ]

    def run_validation(self, data=serializers.empty):
        check_unknown_fields(self.fields, data)
        return super().run_validation(data)

    def to_representation(self, instance):
        # При post-запросе возвращаем только идентификаторы заказов
        if self.context['request'].method == 'POST':
            value_id = instance.get('order_id') if isinstance(
                instance, dict) else instance.order_id
            return {'id': value_id}
        return super().to_representation(instance)


def serialize_assign_order(data):
    """ Проверить данные курьера и вернуть данные по его активному развозу."""

    try:
        courier = Courier.objects.get(
            courier_id=data['courier_id'])
    except Courier.DoesNotExist:
        return {'error': 'Курьер не найден'}
    active_invoice = services.get_active_invoice(courier)
    context = {'orders': []}
    if active_invoice:
        context['orders'] = Order.objects.filter(
            invoices=active_invoice,
            invoice_orders__complete_time__isnull=True
        ).values(id=F('order_id'))
        context['assign_time'] = active_invoice.assign_time
    return context


def serialize_complete_order(data):
    """ Проверить данные завершенного заказа."""

    try:
        invoice_order = InvoiceOrder.objects.get(
            order_id=data['order_id'],
            invoice__courier_id=data['courier_id'])
    except InvoiceOrder.DoesNotExist:
        return {'error': 'Заказ не найден или назначен другому курьеру'}
    complete_time = data.get('complete_time')
    if not complete_time:
        return {'error': 'Не передано время доставки'}
    complete_time = parse(complete_time)
    completed_order = services.complete_order(invoice_order, complete_time)
    return {'order_id': completed_order}
