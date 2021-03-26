import time

from django.core.exceptions import ValidationError
from rest_framework import serializers


def hh_mm_to_minutes(str_hh_mm):
    """Перевести строку формата 'HH:MM' во время."""
    minutes = time.strptime(str_hh_mm, '%H:%M')
    return minutes.tm_hour * 60 + minutes.tm_min


def interval_validator(value):
    """Проверить является ли строка интервалом времени в формате 'HH:MM-HH:MM'
    и вернуть времена начала и конца периода."""
    try:
        value = value.split('-')
        begin = hh_mm_to_minutes(value[0])
        end = hh_mm_to_minutes(value[1])
    except ValueError:
        raise serializers.ValidationError(
            'Значение не является интервалом времени в формате "HH:MM-HH:MM"'
        )
    return begin, end


def interval_list_validator(interval_list):
    """Проверить список интервалов и вернуть список кортежей с валидным
    интервалом и временами начала и конца интервала."""

    new_list = []
    for interval in interval_list:
        begin, end = interval_validator(interval)
        new_list.append((interval, begin, end))
    return new_list


def weight_validator(value):
    """Проверить, что вес соответствует нормам сервиса."""

    if not (0 < value <= 50):
        raise ValidationError('Недопустимый вес заказа')


def check_unknown_fields(fields, data):
    """Проверить, что в сериализуемый контент не содержит необъявленных
    полей."""

    if data is not serializers.empty:
        unknown_fields = set(data) - set(fields)
        if unknown_fields:
            errors = [f for f in unknown_fields]
            raise serializers.ValidationError({
                'unknown_fields': errors,
            })
