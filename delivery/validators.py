import time

from django.core.exceptions import ValidationError
from rest_framework import serializers


def hh_mm_to_minutes(str_hh_mm):
    minutes = time.strptime(str_hh_mm, '%H:%M')
    return minutes.tm_hour * 60 + minutes.tm_min


def interval_validator(value):
    try:
        value = value.split('-')
        begin = hh_mm_to_minutes(value[0])
        end = hh_mm_to_minutes(value[1])
    except:
        raise serializers.ValidationError(
            'Значение не является интервалом времени в формате "HH:MM-HH:MM"'
        )
    return begin, end


def interval_list_validator(interval_list):
    new_list = []
    for interval in interval_list:
        begin, end = interval_validator(interval)
        new_list.append((interval, begin, end))
    return new_list


def weight_validator(value):
    if not (0 < value <= 50):
        raise ValidationError('Недопустимый вес заказа')


def check_unknown_fields(fields, data):
    if data is not serializers.empty:
        unknown_fields = set(data) - set(fields)
        if unknown_fields:
            errors = [f for f in unknown_fields]
            raise serializers.ValidationError({
                'unknown_fields': errors,
            })

def region_code_validator(region_code):
    if isinstance(region_code, int) and region_code > 0:
        return region_code
    raise serializers.ValidationError(
            'Коды регионов должны быть целыми положительными числами')

def region_list_validator(region_list):
    if isinstance(region_list, list):
        return [region_code_validator(code) for code in region_list]
    raise serializers.ValidationError(f'{region_list} не является списком кодов регионов')
