from django.db.models import QuerySet
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import Courier, Invoice, Order, Region


class SmokeTests(APITestCase):
    """Класс SmokeTests предназначен для дымного теста всех эндпоинтов.

    При запросе с разрешенными методами для эндпоинта ответ должен возвращать
    один из статусов 2ХХ, для неразрешенных -- 4ХХ.
    """

    class TestEndPoint:
        """Класс SmokeTests предназначен для создания базового тест-кейса.

        Параметры экземпляра:
        _________
        endpoint_name: str
            имя эндпоинта
        allowed_methods: list
            разрешенные методы эндпоинта
        test_data: dict = None
            тело запроса
        test_instance: QuerySet = None
            объект для проверки запросов детали.
        """

        def __init__(self, endpoint_name: str, allowed_methods: list,
                     test_data: dict = None,
                     test_instance: QuerySet = None) -> None:
            self.endpoint_name = endpoint_name
            self.allowed_methods = allowed_methods
            self.test_data = test_data
            self.test_instance = test_instance

    @classmethod
    def setUpClass(cls):
        """Произвести настройки перед проведением всех тестов.

        Для настройки тестов необходимо определить:
        METHODS_FOR_TEST : list(str)
            Список методов которые проверяются на каждом эндпоинте.
        testcase : list(TestEndPoint)
            список базовых тест-кейсов.
        """

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
        Invoice.objects.create(courier=courier, expected_reward=0).orders.set(
            [order])
        data_assign = {'courier_id': courier.courier_id}
        data_complete = {'courier_id': courier.courier_id,
                         'order_id': order.order_id,
                         'complete_time': timezone.now()}

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
    def _get_url(cls, testcase):
        """Вернуть url по имени эндпоинта.

        эндпоинты детали должны содержать в названии слово 'detail'
        """

        if 'detail' in testcase.endpoint_name:
            return reverse(testcase.endpoint_name,
                           kwargs={'pk': testcase.test_instance.pk})
        return reverse(testcase.endpoint_name)

    def test_allowed_methods(self):
        """Проверить статусы ответов на запросы с разрешенными и неразрешенными
        методами.
        """

        for testcase in SmokeTests.testcase:
            url = SmokeTests._get_url(testcase)
            for method in SmokeTests.METHODS_FOR_TEST:
                response = getattr(self.client, method.lower())(
                    url, data=testcase.test_data, format='json')
                if method in testcase.allowed_methods:
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
                    print(f'- {method:10} {url:40} forbidden -- OK')
