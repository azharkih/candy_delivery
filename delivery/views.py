from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from delivery.models import Courier, Order
from delivery.serializers import (CourierSerializer, OrderSerializer)
from delivery import services
from delivery.utils import get_error_objects


class CourierViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     GenericViewSet):
    queryset = Courier.objects.all()
    serializer_class = CourierSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data['data'], many=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'couriers': serializer.data},
                            status=status.HTTP_201_CREATED)
        invalid_objects = get_error_objects(serializer)
        return Response({'validation_error': {'couriers': invalid_objects}},
                        status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(mixins.CreateModelMixin, GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data['data'], many=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'orders': serializer.data},
                            status=status.HTTP_201_CREATED)
        invalid_objects = get_error_objects(serializer)
        return Response({'validation_error': {'orders': invalid_objects}},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def assign(self, request):
        try:
            courier = Courier.objects.get(
                courier_id=request.data['courier_id'])
        except:
            return Response({'error': 'Курьер не найден'},
                            status=status.HTTP_400_BAD_REQUEST)
        active_orders = services.get_active_orders(courier)
        return Response({'orders': active_orders}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def complete(self, request):
        try:
            order = Order.objects.get(
                order_id=request.data['order_id'],
                invoices__courier__courier_id=request.data['courier_id'])
        except:
            return Response(
                {'error': 'Заказ не найден или назначен другому курьеру'},
                status=status.HTTP_400_BAD_REQUEST
            )
        completed_order = services.complete_order(order)
        return Response({'order_id': completed_order},
                        status=status.HTTP_200_OK)
