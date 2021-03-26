from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from candy_delivery.settings import IS_NEW_REGIONS_AND_TIME_INTERVALS_AVAILABLE
from delivery.models import Courier, Order
from delivery.serializers import (CourierRelationsSerializer,
                                  CourierSerializer, OrderRelationsSerializer,
                                  OrderSerializer, serialize_assign_order,
                                  serialize_complete_order)
from delivery.utils import response_200_or_400


class CourierViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     GenericViewSet):
    """Класс CourierViewSet предназначен для обработки допустимых событий
    на эндпоинтах couriers/."""

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
    """Класс OrderViewSet предназначен для обработки допустимых событий
    на эндпоинтах orders/."""

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
        context = serialize_assign_order(request.data)
        return response_200_or_400(context)

    @action(detail=False, methods=['post'])
    def complete(self, request):
        context = serialize_complete_order(request.data)
        return response_200_or_400(context)
