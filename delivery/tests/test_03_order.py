# 'orders-complete'
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import Courier, Order, TimeInterval
from delivery.tests.test_fixtures import create_test_case_full


class OrdersTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_test_case_full()

    def test_valid_data_create_orders(self):
        url = reverse('orders-list')
        data = {
            'data': [{'order_id': 1, 'weight': 0.20, 'region': 12,
                      'delivery_hours': ['09:00-18:00']},
                     {'order_id': 2, 'weight': 5, 'region': 1,
                      'delivery_hours': ['09:00-18:00']},
                     {'order_id': 3, 'weight': 0.01, 'region': 22,
                      'delivery_hours': ['09:00-12:00', '16:00-21:59']}]}

        count_orders = Order.objects.count()
        response = self.client.post(url, data, format='json')

        # Проверяем корректность ответа
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_list = [{'id': x['order_id']} for x in data['data']]
        self.assertListEqual(response.data.get('orders'), created_list,
                             'Проверьте что ответ содержит корректный список '
                             'созданных заказов')
        # Проверяем данные в базе
        equal_data = data['data'][0]
        new_order = Order.objects.get(order_id=equal_data['order_id'])
        self.assertEqual(Order.objects.count(), count_orders + 3,
                         'Проверьте что все записи заказов пишутся в базу')
        self.assertTrue(new_order, 'Проверьте что переданный идентификатор '
                                   'заказа пишется в базу')
        self.assertEqual(float(new_order.weight), equal_data['weight'],
                         'Проверьте что вес заказа корректно пишется в базу')
        self.assertEqual(new_order.region.code, equal_data['region'],
                         'Проверьте что переданный регион корректно '
                         'пишется в базу')
        self.assertListEqual(
            list(new_order.delivery_hours.values()),
            list(TimeInterval.objects.filter(
                name__in=equal_data['delivery_hours']).values()),
            'Проверьте что переданные интервалы корректно пишутся в базу')

    def test_not_valid_data_create_orders(self):
        url = reverse('orders-list')
        count_orders = Order.objects.count()

        wrong_data = {
            'data': [
                {'order_id': 1, 'weight': 0.20, 'region': 12,
                 'delivery_hours': ['09:00-18:00']},
                {}
            ]
        }
        response = self.client.post(url, wrong_data, format='json')

        # Проверяем корректность ответа
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Проверяем, что ответ имеет правильную структуру, есть проверка на
        # отсутствие обязательных полей и что в ответ не попадают данные по
        # валидному заказу.

        right_answer = {
            'validation errors': {
                'orders': [
                    {'order_id': None,
                     'errors': {'order_id': ['This field is required.'],
                                'weight': ['This field is required.'],
                                'region': ['This field is required.'],
                                'delivery_hours': [
                                    'This field is required.']}}]}}
        self.assertEqual(
            json.loads(response.content), right_answer,
            'Проверьте что ответ имеет имеет правильную структуру, есть '
            'проверка на отсутствие обязательных полей и что в ответ не '
            'попадают данные по валидному заказу')

        # Проверяем, что при получении неописанного поля - возвращается ошибка

        wrong_data = {'order_id': 1, 'undescribed_field': 'test',
                      'weight': 0.20, 'region': 12, 'delivery_hours':
                          ['09:00-18:00']}

        wrong_data = {'data': [
            {'order_id': 1, 'undescribed_field': 'test', 'weight': 0.20,
             'region': 12, 'delivery_hours': ['09:00-18:00']}]}

        response = self.client.post(url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        unknown_fields = json.loads(response.content)[
            'validation errors']['orders'][0]['errors']['unknown_fields']
        self.assertTrue('undescribed_field' in unknown_fields,
                        'Проверьте, что при наличии в запросе неописанных '
                        'полей возвращается ошибка валидации')

        # Проверяем что при  невалидных значений в полях - возвращается ошибка
        wrong_data = {
            'data': [
                {'order_id': 'ddd', 'weight': 'очень легкий',
                 'region': 'Moscow', 'delivery_hours': ['1:35-14:05']},
                {'order_id': -1, 'weight': 0,
                 'region': -1, 'delivery_hours': '11:35-14:05'},
                {'order_id': 1, 'weight': 50.01,
                 'region': 1, 'delivery_hours': ['11:61-14:05']}
            ]
        }

        response = self.client.post(url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = json.loads(response.content)[
            'validation errors']['orders'][0]['errors']
        errors_2 = json.loads(response.content)[
            'validation errors']['orders'][1]['errors']
        errors_3 = json.loads(response.content)[
            'validation errors']['orders'][2]['errors']
        # Проверки 'order_id'
        self.assertTrue(
            'A valid integer is required.' in errors['order_id'],
            'Проверьте, что при передаче строки в качестве значения '
            '"order_id" возвращается соответствующая ошибка')
        self.assertTrue(
            'Ensure this value is greater than or equal to 0.'
            in errors_2['order_id'],
            'Проверьте, что при передаче любого значения "order_id" '
            'отличного от положительного целого числа возвращается '
            'соответствующая ошибка')
        # Проверки 'weight'
        self.assertTrue(
            'A valid number is required.' in errors['weight'],
            'Проверьте, что при передаче некорректного значения "weight"'
            ' возвращается соответствующая ошибка')
        self.assertTrue(
            'Недопустимый вес заказа' in errors_2['weight'],
            'Проверьте, что при передаче веса меньше 0.01 возвращается ошибка')
        self.assertTrue(
            'Недопустимый вес заказа' in errors_3['weight'],
            'Проверьте, что при передаче веса больше 50 возвращается ошибка')
        # Проверки 'region'

        self.assertTrue(
            'Incorrect type. Expected pk value, received str.'
            in errors['region'],
            'Проверьте, что проверяется что код региона это целочисленное '
            'значение')
        self.assertTrue(
            'Invalid pk "-1" - object does not exist.'
            in errors_2['region'],
            'Проверьте, что проверяется ввод отрицательных кодов региона')
        # Проверки 'delivery_hours'
        self.assertTrue(
            'Invalid pk "1:35-14:05" - object does not exist.'
            in errors['delivery_hours'],
            'Проверьте, что проверяется что интервалы имеют соответствующую '
            'структуру')
        self.assertTrue(
            'Expected a list of items but got type "str".'
            in errors_2['delivery_hours'],
            'Проверьте, что проверяется передача значения в списке')
        self.assertTrue(
            'Invalid pk "11:61-14:05" - object does not exist.'
            in errors_3['delivery_hours'],
            'Проверьте, что строковые значения времени валидны')

        # Проверяем, что ни валидная, ни невалидная не записались в базу
        self.assertEqual(Order.objects.count(), count_orders,
                         'Проверьте что при наличии невалидных данных в базе '
                         'не создаются записи')

    def test_valid_data_assign_orders(self):
        url = reverse('orders-assign')
        data = {'courier_id': 100}
        response = self.client.post(url, data, format='json')
        # Проверяем корректность ответа
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        # Проверяем структуру ответа.
        # Проверяем, что заказы назначены на максимально возможную сумму.
        # Проверяем идемпотентность.
        # Проверяем, что другому курьеру не назначены заказы первого.
        # Проверяем, что доставленные заказы текущего развоза исключаются,
        # а время остается тоже.
        # Проверяем, что если для курьера нет доступных заказов - возвращается
        # пустой список, время не возвращается.

    # self.assertEqual(1, 2, 'Тест не написан')

# def test_assign_orders_that_will_fail(self):
#     self.assertEqual(1, 2, 'Тест не написан')
#
# def test_complete_order_that_will_pass(self):
#     self.assertEqual(1, 2, 'Тест не написан')
#
# def test_complete_order_that_will_fail(self):
#     self.assertEqual(1, 2, 'Тест не написан')
