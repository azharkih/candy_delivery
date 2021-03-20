from dateutil.parser import parse
from django.db.models import F
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from candy_delivery.settings import IS_NEW_REGIONS_AND_TIME_INTERVALS_AVAILABLE
from delivery import services
from delivery.models import Courier, InvoiceOrder, Order
from delivery.serializers import (CourierRelationsSerializer,
                                  CourierSerializer, OrderRelationsSerializer,
                                  OrderSerializer)
from delivery.utils import serialize_invoice


class CourierViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     GenericViewSet):
    queryset = Courier.objects.all()
    serializer_class = CourierSerializer

    def _add_new_regions_and_intervals(self, data):
        # Если допускаются еще незарегистрированные регионы и интервалы времени
        # перед созданием курьера добавим их в базу
        if IS_NEW_REGIONS_AND_TIME_INTERVALS_AVAILABLE:
            for item in data:
                serializer_relations = CourierRelationsSerializer(data=item)
                if serializer_relations.is_valid():
                    serializer_relations.save()

    def create(self, request, *args, **kwargs):
        self._add_new_regions_and_intervals(request.data.get('data'))
        serializer = self.get_serializer(
            data=request.data.get('data'), many=True)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'couriers': serializer.data},
                        status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        self._add_new_regions_and_intervals([request.data])

        return super().update(request, *args, **kwargs)


class OrderViewSet(mixins.CreateModelMixin, GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        if IS_NEW_REGIONS_AND_TIME_INTERVALS_AVAILABLE:
            for item in request.data.get('data'):
                serializer_relations = OrderRelationsSerializer(data=item)
                if serializer_relations.is_valid():
                    serializer_relations.save()

        serializer = self.get_serializer(
            data=request.data.get('data'), many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'orders': serializer.data},
                        status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def assign(self, request):
        try:
            courier = Courier.objects.get(
                courier_id=request.data['courier_id'])
        except:
            return Response({'error': 'Курьер не найден'},
                            status=status.HTTP_400_BAD_REQUEST)
        active_invoice = services.get_active_invoice(courier)
        context = serialize_invoice(active_invoice)
        return Response(context, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def complete(self, request):
        try:
            invoiceorder = InvoiceOrder.objects.get(
                order_id=request.data['order_id'],
                invoice__courier_id=request.data['courier_id'])
        except:
            return Response(
                {'error': 'Заказ не найден или назначен другому курьеру'},
                status=status.HTTP_400_BAD_REQUEST
            )
        complete_time = parse(request.data.get('complete_time'))
        if not complete_time:
            return Response(
                {'error': 'Не передано время доставки'},
                status=status.HTTP_400_BAD_REQUEST
            )
        completed_order = services.complete_order(invoiceorder, complete_time)
        return Response({'order_id': completed_order},
                        status=status.HTTP_200_OK)
