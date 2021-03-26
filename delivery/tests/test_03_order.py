import json
from datetime import timedelta

from dateutil.parser import parse
from django.db.models import F, Q, Sum
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import Courier, InvoiceOrder, Order, TimeInterval
from delivery.services import complete_order, get_active_invoice
from delivery.tests.test_fixtures import create_test_case_full


class OrdersTests(APITestCase):
    """Класс OrdersTests предназначен для теста обработчиков на эндпоинтах
    связанных с заказами."""

    @classmethod
    def setUpClass(cls):
        """Произвести настройки перед проведением всех тестов."""

        super().setUpClass()
        create_test_case_full()

    def test_valid_data_create_orders(self):
        """Проверить обработку запроса POST /orders с валидными данными.

        Проверки:
        __________
        * При валидной структуре json на входе получаем статус ответа 201
        * На выходе получаем json c корректной структурой
        * Проверка, что все данные запроса сохраняются в базе
        """
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
        self.assertListEqual(
            response.data.get('orders'), created_list,
            'Проверьте что ответ содержит корректный список созданных заказов')
        # Проверяем данные в базе
        equal_data = data['data'][0]
        new_order = Order.objects.get(order_id=equal_data['order_id'])
        self.assertEqual(
            Order.objects.count(), count_orders + 3,
            'Проверьте что все записи заказов пишутся в базу')
        self.assertTrue(
            new_order,
            'Проверьте что переданный идентификатор заказа пишется в базу')
        self.assertEqual(
            float(new_order.weight), equal_data['weight'],
            'Проверьте что вес заказа корректно пишется в базу')
        self.assertEqual(
            new_order.region.code, equal_data['region'],
            'Проверьте что переданный регион корректно пишется в базу')
        self.assertListEqual(
            list(new_order.delivery_hours.values()),
            list(TimeInterval.objects.filter(
                name__in=equal_data['delivery_hours']).values()),
            'Проверьте что переданные интервалы корректно пишутся в базу')

    def test_not_valid_data_create_orders(self):
        """Проверить обработку запроса POST /orders с невалидными данными.

        Проверки:
        __________
        * При невалидной структуре json на входе получаем статус ответа 400
        * На выходе получаем json c корректной структурой
        * Есть проверка на обязательные поля
        * При получении неописанного поля -- возвращается ошибка
        * Валидация входных данных
        * При запросе с невалидными данными в базу ничего не пишется.
        """
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
        self.assertTrue(
            'undescribed_field' in unknown_fields,
            'Проверьте, что при наличии в запросе неописанных полей '
            'возвращается ошибка валидации')

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
        self.assertEqual(
            Order.objects.count(), count_orders,
            'Проверьте что при наличии невалидных данных в базе не создаются '
            'записи')

    def test_valid_data_assign_orders(self):
        """Проверить обработку запроса POST /orders/assign с валидными данными.

        Проверки:
        __________
        * При валидной структуре json на входе получаем статус ответа 200
        * Корректность структуры ответа, для курьера с активным развозом, с
          завершенным развозом с доступными заказами и их отсутствием
        * Проверяем, что заказы назначены c максимально возможной комбинацией
          весов и не превышают грузоподъемность курьера.
        * Обработчик идемпотентен
        * Доставленные заказы текущего развоза исключаются, а время остается
          тоже.
        """
        url = reverse('orders-assign')
        courier_100 = Courier.objects.get(courier_id=100)
        courier_101 = Courier.objects.get(courier_id=101)
        courier_102 = Courier.objects.get(courier_id=102)
        courier_103 = Courier.objects.get(courier_id=103)
        response = {}
        for courier_id in range(100, 104):
            data = {'courier_id': courier_id}
            response[courier_id] = self.client.post(url, data, format='json')
            self.assertEqual(response[courier_id].status_code,
                             status.HTTP_200_OK)
        courier_100_orders = Order.objects.filter(
            invoices__courier=courier_100)
        courier_101_orders = Order.objects.filter(
            invoices__courier=courier_101)
        courier_102_orders = Order.objects.filter(
            invoices__courier=courier_102)
        courier_103_orders = Order.objects.filter(
            invoices__courier=courier_103)

        # Проверяем структуру ответа.
        content_100 = json.loads(response[100].content)
        content_103 = json.loads(response[103].content)
        self.assertTrue(
            len(content_100) == 2,
            'Ответ при назначении заказа должен содержать 2 поля')
        self.assertListEqual(
            content_100.get('orders'),
            list(courier_100_orders.values(id=F('order_id'))),
            'Поле c заказами должно содержать список назначенных заказов')
        time_delta_order_assign = (
            timezone.now() -
            parse(content_100.get('assign_time'))).total_seconds()
        self.assertTrue(
            time_delta_order_assign < 1,
            'Разница между текущим временем и временем принятия заказа в '
            'ответе не должна превышать 1 секунды')

        # Проверяем, что если для курьера нет доступных заказов - возвращается
        # пустой список, время не возвращается.
        self.assertTrue(
            len(content_103) == 1,
            'Ответ при отсутствии доступных заказов должен содержать 1 поле')
        self.assertListEqual(
            content_103.get('orders'), [],
            'При отсутствии доступных заказов в ответ должен передаваться '
            'пустой список')

        # Проверяем, что заказы назначены c максимально возможным весом.
        # По тест-кейсу веса должны быть равны: 14.18 11 45.5 None
        courier_100_sum_orders = float(courier_100_orders.aggregate(
            sum=Sum('weight'))['sum'])
        courier_101_sum_orders = float(courier_101_orders.aggregate(
            sum=Sum('weight'))['sum'])
        courier_102_sum_orders = float(courier_102_orders.aggregate(
            sum=Sum('weight'))['sum'])
        courier_103_sum_orders = courier_103_orders.aggregate(
            sum=Sum('weight'))['sum']
        self.assertEqual(
            courier_100_sum_orders, 14.18,
            'Проверьте, что заказы назначаются корректно')
        self.assertEqual(
            courier_101_sum_orders, 11,
            'Проверьте, что заказы назначаются корректно')
        self.assertEqual(
            courier_102_sum_orders, 45.5,
            'Проверьте, что заказы назначаются корректно')
        self.assertEqual(
            courier_103_sum_orders, None,
            'Проверьте, что заказы назначаются корректно')

        # Проверяем идемпотентность.
        data = {'courier_id': 100}
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            content_100, json.loads(response.content),
            'Проверьте, что обработчик идемпотентен')

        # Проверяем, что другому курьеру не назначены заказы первого.
        self.assertFalse(
            courier_101_orders in courier_100_orders,
            'Проверьте, что заказы выданные первому курьеру не назначены '
            'второму')

        # Проверяем, что доставленные заказы текущего развоза исключаются,
        # а время остается тоже.
        order_for_complete = courier_100_orders.all()[0]
        invoice_order = InvoiceOrder.objects.get(order=order_for_complete)
        complete_time = timezone.now()
        complete_order(invoice_order, complete_time)
        data = {'courier_id': 100}
        response = self.client.post(url, data, format='json')

        content = json.loads(response.content)
        self.assertFalse(
            {'id': order_for_complete.order_id} in content.get('orders'),
            'Проверьте, что доставленные заказы исключаются из ответа.')
        self.assertEqual(
            content.get('assign_time', 0), content_100.get('assign_time', 1),
            'Проверьте, что при возврате недоставленных заказов время развоза'
            ' неизменно.')

    def test_not_valid_data_assign_orders(self):
        """Проверить обработку запроса POST /orders/assign с невалидными
        данными.

        Проверки:
        __________
        * При невалидной структуре json на входе получаем статус ответа 400
        """
        url = reverse('orders-assign')
        wrong_data = {'courier_id': 999}
        response = self.client.post(url, wrong_data, format='json')

        # Проверяем корректность ответа
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_data_complete_order(self):
        """Проверить обработку запроса POST /orders/complete с валидными
        данными.

        Проверки:
        __________
        * При валидной структуре json на входе получаем статус ответа 200
        * Корректность структуры ответа
        * Обработчик идемпотентен
        * Время завершения заказа устанавливется верно и корректно считается
          время доставки.
        """
        url = reverse('orders-complete')
        courier = Courier.objects.first()
        get_active_invoice(courier)
        order_1 = Order.objects.filter(
            invoice_orders__complete_time__isnull=True,
            invoices__courier=courier).first()
        complete_time_1 = timezone.now() + timedelta(minutes=11)
        complete_time_2 = complete_time_1 + timedelta(minutes=9)

        data = {'courier_id': courier.courier_id,
                'order_id': order_1.order_id,
                'complete_time': complete_time_1
                }
        # Проверяем корректность и структуру ответа.
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)

        self.assertEqual(
            content.get('order_id'), order_1.order_id,
            'Проверьте, что ответ содержит идентификатор завершенного заказа.')

        # Проверяем идемпотентность обработчика
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            content, json.loads(response.content),
            'Проверьте, что обработчик идемпотентен.')

        # Проверяем, что у заказа проставилось время завершения и посчиталось
        # время доставки в секундах.
        invoice_order_1 = InvoiceOrder.objects.get(order=order_1)
        self.assertEqual(
            invoice_order_1.complete_time, complete_time_1,
            'Проверьте, что в базе сохраняется время доставки.')

        self.assertEqual(
            invoice_order_1.delivery_time, 660,
            'Проверьте, что время доставки первого заказа из развоза считается'
            ' корректно.')

        # Завершаем следующий заказ и проверяем что время доставки считается
        # с момента доставки предыдущего заказа

        invoice_order_2 = InvoiceOrder.objects.filter(
            ~Q(order=order_1)).first()
        complete_order(invoice_order_2, complete_time_2)

        self.assertEqual(
            invoice_order_2.delivery_time, 540,
            'Проверьте, что время доставки второго заказа из развоза считается'
            ' корректно.')

    def test_not_valid_data_complete_order(self):
        """Проверить обработку запроса POST /orders/complete с невалидными
        данными.

        Проверки:
        __________
        * Если заказ не найден возвращается ошибка 400
        * Если заказ назначен на другого курьера возвращается ошибка 400
        * Если заказ не назначен возвращается ошибка 400
        """
        url = reverse('orders-complete')
        courier_1 = Courier.objects.first()
        courier_2 = Courier.objects.last()
        invoice_2 = get_active_invoice(courier_2)

        # В случае если заказ не найден возвращается ошибка 400
        data = {'courier_id': courier_1.courier_id,
                'order_id': 9999,
                'complete_time': timezone.now()
                }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # В случае если заказ назначен на другого курьера возвращается
        # ошибка 400
        data = {'courier_id': courier_1.courier_id,
                'order_id': invoice_2.orders.first().order_id,
                'complete_time': timezone.now()
                }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # В случае если заказ не назначен возвращается ошибка 400
        data = {'courier_id': courier_1.courier_id,
                'order_id': Order.objects.filter(
                    invoices__isnull=True).first().order_id,
                'complete_time': timezone.now()
                }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
