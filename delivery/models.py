from django.db import models
from django.utils.translation import gettext_lazy as _

from delivery.validators import interval_validator, weight_validator


class Region(models.Model):
    """Класс Region используется для описания модели районов доставки.

    Родительский класс -- models.Model.

    Атрибуты класса
    --------
                                            PK <-- Order, Courier
    code : models.PositiveIntegerField()
        числовой код района.
    """
    code = models.PositiveIntegerField(
        primary_key=True,
        verbose_name='Код района',
    )


class TimeInterval(models.Model):
    """Класс TimeInterval используется для описания модели интервалов времени.

    Родительский класс -- models.Model.

    Атрибуты класса
    --------
                                            PK <-- Order, Courier
    name : models.CharField()
        Имя интервала в формате 'HH:MM-HH:MM'
    begin : models.PositiveIntegerField()
        Начало интервала в минутах от 00:00
    end : models.PositiveIntegerField()
        Конец интервала в минутах от 00:00.

    Методы класса
    --------
    __str__() -- возвращает строковое представление модели.
    save() -- вычисляет значения полей begin и end и сохраняет все изменения в
        БД.
    """
    name = models.CharField(
        primary_key=True,
        verbose_name='Интервал(HH:MM-HH:MM)',
        max_length=11,
        validators=[interval_validator]
    )
    begin = models.PositiveIntegerField(
        verbose_name='Начало интервала в минутах'
    )
    end = models.PositiveIntegerField(
        verbose_name='Конец интервала в минутах'
    )

    def __str__(self) -> str:
        """Вернуть строковое представление в виде имени интервала."""

        return self.name

    def save(self, *args, **kwargs) -> None:
        """Вычислить значения полей begin и end и сохранить все изменения в БД.
        """

        self.begin, self.end = interval_validator(self.name)
        super().save(*args, **kwargs)


class Courier(models.Model):
    """Класс Courier используется для описания модели курьера.

    Родительский класс -- models.Model.

    Атрибуты класса
    --------
                                                 PK <-- Invoice
    courier_id : models.PositiveIntegerField()
        идентификатор курьера
    courier_type : models.CharField()
        тип курьера
    regions : models.ManyToManyField()          FK --> Region
        регионы в которых работает курьер
    working_hours = models.ManyToManyField()    FK --> TimeInterval
        интервалы времени в которых работает курьер

    Методы класса
    --------
    __str__() -- возвращает строковое представление модели.
    """

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
        """Вернуть строковое представление в виде типа и идентификатора
        курьера."""
        return f'{self.courier_type} - {self.courier_id}'


class Order(models.Model):
    """Класс Order используется для описания модели заказа.

    Родительский класс -- models.Model.

    Атрибуты класса
    --------
                                                PK <-- InvoiceOrder
    order_id : models.PositiveIntegerField()
        идентификатор заказа
    weight : models.DecimalField()
        вес заказа
    region : models.ForeignKey()                FK --> Region
        регион доставки заказа
    delivery_hours = models.ManyToManyField()   FK --> TimeInterval
        интервалы времени в которые удобно принять заказ.

    Методы класса
    --------
    __str__() -- возвращает строковое представление модели.
    """
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

    def __str__(self) -> str:
        """Вернуть строковое представление в виде идентификатора заказа."""
        return f'order_id: {self.order_id}'


class Invoice(models.Model):
    """Класс Invoice используется для описания модели задания на развоз.

    Родительский класс -- models.Model.

    Атрибуты класса
    --------
                                            PK <-- InvoiceOrder
    courier : models.ForeignKey()           FK --> Courier
        курьер назначенный на развоз
    assign_time : models.DateTimeField()
        время формирования развоза
    orders : models.ManyToManyField()       FK --> Order
        заказы включенные в развоз
    expected_reward = models.PositiveIntegerField()
        ожидаемая вознаграждение курьеру за развоз.
    """
    courier = models.ForeignKey(
        Courier,
        related_name='invoices',
        verbose_name='Назначенный курьер',
        on_delete=models.CASCADE,
        db_index=True,
    )
    assign_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время выдачи курьеру',
    )
    orders = models.ManyToManyField(
        Order,
        through='InvoiceOrder',
        related_name='invoices',
        verbose_name='Заказы',
        db_index=True,
    )
    expected_reward = models.PositiveIntegerField(
        null=False,
        verbose_name='Ожидаемое вознаграждение',
    )


class InvoiceOrder(models.Model):
    """Класс InvoiceOrder используется для описания модели детализации развоза.

    Родительский класс -- models.Model.

    Атрибуты класса
    --------
    invoice : models.ForeignKey()           FK --> Invoice
        идентификатор развоза
    order : models.ForeignKey()             FK --> Order
        заказ
    complete_time : models.DateTimeField()
        время завершения заказа
    delivery_time : models.PositiveIntegerField()
        время доставки заказа в секундах.
    """
    invoice = models.ForeignKey(
        Invoice,
        related_name='invoice_orders',
        on_delete=models.CASCADE,
    )
    order = models.ForeignKey(
        Order,
        related_name='invoice_orders',
        on_delete=models.CASCADE
    )
    complete_time = models.DateTimeField(
        null=True,
        verbose_name='Время завершения заказа',
    )
    delivery_time = models.PositiveIntegerField(
        null=True,
        verbose_name='Время доставки в секундах',
    )
