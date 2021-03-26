from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from delivery.models import Region, TimeInterval


def custom_exception_handler(exc, context):
    """Подготовить и вернуть Responce, содержащий описание ошибок, возникших
    при обработке исключений."""

    response = exception_handler(exc, context)

    if response is not None:
        customized_response = {'validation errors': {}}
        request_data = context.get('view').request.data
        if request_data.get('data'):
            request_data = request_data['data']
        if isinstance(request_data, list):
            basename = context.get('view').basename
            pk_name = context.get('view').queryset.model._meta.pk.attname
            customized_response['validation errors'][basename] = []
            for key, value in enumerate(response.data):
                if value:
                    error = {}
                    error[pk_name] = request_data[key].get(pk_name)
                    error['errors'] = value
                    customized_response[
                        'validation errors'][basename].append(error)
        else:
            customized_response['validation errors'] = response.data
        response.data = customized_response
    return response


def add_regions(region_codes):
    """Создать записи регионов в БД по переданному списку кодов."""

    regions = [Region(code=x) for x in region_codes]
    Region.objects.bulk_create(regions, ignore_conflicts=True)
    return regions


def add_time_intervals(time_interval):
    """Создать записи интервалов времени в БД по переданному списку."""

    time_interval = [TimeInterval(name=name, begin=begin, end=end)
                     for name, begin, end in time_interval]
    TimeInterval.objects.bulk_create(time_interval, ignore_conflicts=True)
    return time_interval


def response_200_or_400(context):
    """Вернуть ответ со статусом 200 или 400 в зависимости от контекста."""
    if context.get('error'):
        return Response(context, status=status.HTTP_400_BAD_REQUEST)
    return Response(context, status=status.HTTP_200_OK)
