from django.db import models
from django.utils.translation import gettext_lazy as _

from delivery.validators import interval_validator, weight_validator


class Region(models.Model):
    code = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='Код района',
    )


class TimeInterval(models.Model):
    name = models.CharField(
        verbose_name='Интервал(HH:MM-HH:MM)',
        max_length=11,
        db_index=True,
        validators=[interval_validator]
    )
    begin = models.PositiveSmallIntegerField(
        verbose_name='Начало интервала'
    )
    end = models.PositiveSmallIntegerField(
        verbose_name='Конец интервала'
    )

    def __str__(self):
        return self.name

    @staticmethod
    def parse_name(name):
        begin = int(name[:2]) * 60 + int(name[3:5])
        end = int(name[6:8]) * 60 + int(name[9:11])
        return begin, end

    def save(self, *args, **kwargs):
        self.begin, self.end = TimeInterval.parse_name(self.name)
        super().save(*args, **kwargs)


class Courier(models.Model):
    """Класс для описания модели..."""

    class CourierType(models.TextChoices):
        """Класс CourierType используется для определения допустимых
        типов курьеров."""

        FOOT = 'foot', _('Пеший')
        BIKE = 'bike', _('Велокурьер')
        CAR = 'car', _('Курьер на автомобиле')

    courier_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='Идентификатор курьера',
    )

    courier_type = models.CharField(
        max_length=4,
        choices=CourierType.choices,
        verbose_name='Тип курьера',
    )

    regions = models.ManyToManyField(
        Region,
        related_name='couriers',
        verbose_name='Районы доставки',
        db_index=True,
    )
    working_hours = models.ManyToManyField(
        TimeInterval,
        related_name='couriers',
        verbose_name='Часы работы',
        db_index=True,
    )

    def __str__(self) -> str:
        return f'{self.courier_type} - {self.courier_id}'


class Order(models.Model):
    """    """
    order_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='Идентификатор заказа',
    )

    weight = models.DecimalField(
        validators=[weight_validator],
        max_digits=4, decimal_places=2
    )
    region = models.ForeignKey(
        Region,
        related_name='orders',
        verbose_name='Район заказа',
        on_delete=models.PROTECT,
        db_index=True,
    )
    delivery_hours = models.ManyToManyField(
        TimeInterval,
        related_name='orders',
        verbose_name='Часы работы',
        db_index=True,
    )
    complete_time = models.DateTimeField(
        null=True,
        verbose_name='Время завершения заказа',
    )

    def __str__(self) -> str:
        return f'order_id: {self.order_id}'


class Invoice(models.Model):
    courier = models.ForeignKey(
        Courier,
        related_name='invoices',
        verbose_name='Назначенный курьер',
        on_delete=models.CASCADE,
        db_index=True,
    )
    assigned_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время выдачи курьеру',
    )
    orders = models.ManyToManyField(
        Order,
        related_name='invoices',
        verbose_name='Заказы',
        db_index=True,
    )
