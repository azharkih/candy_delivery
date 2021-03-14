from django.urls import include, path
from rest_framework.routers import DefaultRouter

from delivery.views import CourierViewSet, OrderViewSet

router = DefaultRouter()
router.register('couriers', CourierViewSet, basename='couriers')
router.register('orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls))
]
