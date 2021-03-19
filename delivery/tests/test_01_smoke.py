from django.db.models import QuerySet
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import Courier, Invoice, Order, Region


class SmokeTests(APITestCase):
    class TestEndPoint:
        def __init__(self, endpoint_name: str, allowed_methods: list,
                     test_data: dict = None,
                     test_instance: QuerySet = None) -> None:
            self.endpoint_name = endpoint_name
            self.allowed_methods = allowed_methods
            self.test_data = test_data
            self.test_instance = test_instance

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.METHODS_FOR_TEST = ['GET', 'POST', 'PATCH', 'DELETE']

        data_couriers = {'data': [
            {'courier_id': 1, 'courier_type': 'foot', 'regions': [1],
             'working_hours': ["00:00-00:01"]}]}
        data_orders = {'data': [{'order_id': 1, 'weight': 1, 'region': 1,
                                 'delivery_hours': ["00:00-00:01"]}]}
        region = Region.objects.create(code=1)
        courier = Courier.objects.create(courier_id=2, courier_type='foot')
        order = Order.objects.create(order_id=2, weight=1, region=region)
        Invoice.objects.create(courier=courier, expected_reward =0).orders.set([order])
        data_assign = {'courier_id': courier.courier_id}
        data_complete = {'courier_id': courier.courier_id,
                         'order_id': order.order_id}

        cls.testcase = list()
        cls.testcase.append(cls.TestEndPoint(
            'couriers-list', ['POST'], test_data=data_couriers))
        cls.testcase.append(cls.TestEndPoint(
            'couriers-detail', ['GET', 'PATCH'], test_instance=courier))
        cls.testcase.append(cls.TestEndPoint(
            'orders-list', ['POST'], test_data=data_orders))
        cls.testcase.append(cls.TestEndPoint(
            'orders-assign', ['POST'], test_data=data_assign))
        cls.testcase.append(cls.TestEndPoint(
            'orders-complete', ['POST'], test_data=data_complete))

    @classmethod
    def _get_url(cls, endpoint):
        if 'detail' in endpoint.endpoint_name:
            return reverse(endpoint.endpoint_name,
                           kwargs={'pk': endpoint.test_instance.pk})
        return reverse(endpoint.endpoint_name)

    def test_allowed_methods(self):
        for endpoint in SmokeTests.testcase:
            url = SmokeTests._get_url(endpoint)
            for method in SmokeTests.METHODS_FOR_TEST:
                response = getattr(self.client, method.lower())(
                    url, data=endpoint.test_data, format='json')
                if method in endpoint.allowed_methods:
                    self.assertTrue(
                        status.is_success(response.status_code),
                        f'Запрос с методом {method} на "{url}" не прошел, хотя'
                        f' ожидается')
                    print(f'+ {method:10} {url:40} allowded  -- OK')
                else:
                    self.assertEqual(
                        response.status_code,
                        status.HTTP_405_METHOD_NOT_ALLOWED,
                        f'Для "{url}" запрос с методом {method} должен быть '
                        f'недоступен')
                    print(f'- {method:10} {url:40} forbidden -- ОК')


