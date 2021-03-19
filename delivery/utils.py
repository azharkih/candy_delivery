from django.db import models
from django.db.models import F, Func
from rest_framework.views import exception_handler

from delivery.models import Order, Region, TimeInterval


def custom_exception_handler(exc, context):
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
    regions = [Region(code=x) for x in region_codes]
    Region.objects.bulk_create(regions, ignore_conflicts=True)
    return regions


def add_time_intervals(time_interval):
    time_interval = [TimeInterval(name=name, begin=begin, end=end)
                     for name, begin, end in time_interval]
    TimeInterval.objects.bulk_create(time_interval, ignore_conflicts=True)
    return time_interval

def serialize_invoice(active_invoice):
    context = {'orders': []}
    if active_invoice:
        context['orders'] = Order.objects.filter(
            invoices=active_invoice).values(id=F('order_id'))
        context['assign_time'] = active_invoice.assign_time
    return context

class Epoch(Func):
    template = 'EXTRACT(epoch FROM %(expressions)s)::INTEGER'
    output_field = models.IntegerField()
