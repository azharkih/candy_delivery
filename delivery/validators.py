from datetime import datetime as dt

from django.core.exceptions import ValidationError


def interval_validator(value):
    try:
        value = value.split('-')
        for time in value:
            dt.strptime(time, '%H:%M')
    except:
        raise ValidationError(
            'Значение не является интервалом времени в формате "HH:MM-HH:MM"'
        )


def weight_validator(value):
    if not (0.01 <= value <= 50):
        raise ValidationError('Недопустимый вес заказа')
