import json
import random
from datetime import timedelta

from django.db.models import Sum
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from delivery.models import Courier, InvoiceOrder, Order, Region, TimeInterval
from delivery.services import (COURIER_LOAD_CAPACITY, PAY_COEFFICIENTS,
                               assign_orders, complete_order)
from delivery.tests.test_fixtures import create_test_case_full


class CourierTests(APITestCase):
    """Класс CourierTests предназначен для теста обработчиков на эндпоинтах
    связанных с данными о курьерах."""

    @classmethod
    def setUpClass(cls):
        """Произвести настройки перед проведением всех тестов."""

        super().setUpClass()
        create_test_case_full()

    def test_valid_data_create_couriers(self):
        """Проверить обработку запроса POST /couriers с валидными данными.

        Проверки:
        __________
        * При валидной структуре json на входе получаем статус ответа 201
        * На выходе получаем json c корректной структурой
        * Проверка, что все данные запроса сохраняются в базе
        """
        url = reverse('couriers-list')
        data = {
            'data': [
                {'courier_id': 11, 'courier_type': 'foot',
                 'regions': [1, 12, 22],
                 'working_hours': ['11:35-14:05', '09:00-11:00']},
                {'courier_id': 12, 'courier_type': 'bike', 'regions': [22],
                 'working_hours': ['09:00-18:00']},
                {'courier_id': 13, 'courier_type': 'car',
                 'regions': [12, 22, 23, 33], 'working_hours': ['09:00-18:00']}
            ]
        }
        count_couriers = Courier.objects.count()
        response = self.client.post(url, data, format='json')

        # Проверяем корректность ответа
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_list = [{'id': x['courier_id']} for x in data['data']]
        self.assertListEqual(
            response.data.get('couriers'), created_list,
            'Проверьте что ответ содержит список созданных курьеров')

        # Проверяем данные в базе
        equal_data = data['data'][0]
        new_courier = Courier.objects.get(courier_id=equal_data['courier_id'])
        self.assertEqual(
            Courier.objects.count(), count_couriers + 3,
            'Проверьте что все записи курьеров пишутся в базу')
        self.assertTrue(
            new_courier,
            'Проверьте что переданный идентификатор курьера пишется в базу')
        self.assertEqual(
            new_courier.courier_type, equal_data['courier_type'],
            'Проверьте что тип курьера корректно пишется в базу')
        self.assertListEqual(
            list(new_courier.regions.values()),
            list(Region.objects.filter(
                code__in=equal_data['regions']).values()),
            'Проверьте что переданные регионы корректно пишутся в базу')
        self.assertListEqual(
            list(new_courier.working_hours.values()),
            list(TimeInterval.objects.filter(
                name__in=equal_data['working_hours']).values()),
            'Проверьте что переданные интервалы корректно пишутся в базу')

    def test_not_valid_data_create_couriers(self):
        """Проверить обработку запроса POST /couriers с невалидными данными.

        Проверки:
        __________
        * При невалидной структуре json на входе получаем статус ответа 400
        * На выходе получаем json c корректной структурой
        * Есть проверка на обязательные поля
        * При получении неописанного поля -- возвращается ошибка
        * Валидация входных данных
        * При запросе с невалидными данными в базу ничего не пишется.
        """
        url = reverse('couriers-list')
        count_couriers = Courier.objects.count()
        wrong_data = {
            'data': [
                {'courier_id': 11, 'courier_type': 'foot',
                 'regions': [1, 12, 22],
                 'working_hours': ['11:35-14:05', '09:00-11:00']},
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
                'couriers': [
                    {'courier_id': None,
                     'errors': {'courier_id': ['This field is required.'],
                                'courier_type': ['This field is required.'],
                                'regions': ['This field is required.'],
                                'working_hours': ['This field is required.']
                                }}]}}
        self.assertEqual(
            json.loads(response.content), right_answer,
            'Проверьте что ответ имеет имеет правильную структуру, есть '
            'проверка на отсутствие обязательных полей и что в ответ не '
            'попадают данные по валидному заказу')

        # Проверяем, что при получении неописанного поля - возвращается ошибка
        wrong_data = {
            'data': [
                {'courier_id': 11, 'undescribed_field': 'test',
                 'courier_type': 'foot', 'regions': [1, 12, 22],
                 'working_hours': ['11:35-14:05', '09:00-11:00']}
            ]
        }
        response = self.client.post(url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        unknown_fields = json.loads(response.content)[
            'validation errors']['couriers'][0]['errors']['unknown_fields']
        self.assertTrue(
            'undescribed_field' in unknown_fields,
            'Проверьте, что при наличии в запросе неописанных полей '
            'возвращается ошибка валидации')

        # Проверяем что при  невалидных значений в полях - возвращается ошибка
        wrong_data = {
            'data': [
                {'courier_id': 'ddd', 'courier_type': 'foo',
                 'regions': ['Moscow'],
                 'working_hours': ['1:35-14:05']},
                {'courier_id': -1, 'courier_type': 2,
                 'regions': 1,
                 'working_hours': '11:35-14:05'},
                {'courier_id': 1, 'courier_type': 'bike',
                 'regions': [1],
                 'working_hours': ['11:61-14:05']}
            ]
        }
        response = self.client.post(url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = json.loads(response.content)[
            'validation errors']['couriers'][0]['errors']
        errors_2 = json.loads(response.content)[
            'validation errors']['couriers'][1]['errors']
        errors_3 = json.loads(response.content)[
            'validation errors']['couriers'][2]['errors']
        # Проверки 'courier_id'
        self.assertTrue(
            'A valid integer is required.' in errors['courier_id'],
            'Проверьте, что при передаче строки в качестве значения '
            '"courier_id" возвращается соответствующая ошибка')
        self.assertTrue(
            'Ensure this value is greater than or equal to 0.'
            in errors_2['courier_id'],
            'Проверьте, что при передаче любого значения "courier_id" '
            'отличного от положительного целого числа возвращается '
            'соответствующая ошибка')
        # Проверки 'courier_type'
        self.assertTrue(
            '"foo" is not a valid choice.' in errors['courier_type'],
            'Проверьте, что при передаче некорректного значения "courier_type"'
            ' возвращается соответствующая ошибка')
        self.assertTrue(
            '"2" is not a valid choice.' in errors_2['courier_type'],
            'Проверьте, что при передаче некорректного значения "courier_type"'
            ' возвращается соответствующая ошибка')
        # Проверки 'regions'
        self.assertTrue(
            'Incorrect type. Expected pk value, received str.'
            in errors['regions'], 'Проверьте, что проверяется что код региона '
                                  'это целочисленное значение')
        self.assertTrue(
            'Expected a list of items but got type "int".'
            in errors_2['regions'],
            'Проверьте, что проверяется передача значения в списке')

        # Проверки 'working_hours'
        self.assertTrue(
            'Invalid pk "1:35-14:05" - object does not exist.'
            in errors['working_hours'],
            'Проверьте, что проверяется что интервалы имеют соответствующую '
            'структуру')
        self.assertTrue(
            'Expected a list of items but got type "str".'
            in errors_2['working_hours'],
            'Проверьте, что проверяется передача значения в списке')
        self.assertTrue(
            'Invalid pk "11:61-14:05" - object does not exist.'
            in errors_3['working_hours'],
            'Проверьте, что строковые значения времени валидны')

        # Проверяем, что ни валидная, ни невалидная не записались в базу
        self.assertEqual(
            Courier.objects.count(), count_couriers,
            'Проверьте что при наличии невалидных данных в базе '
            'не создаются записи')

    def test_valid_data_patch_couriers(self):
        """Проверить обработку запроса PATCH /couriers с валидными данными.

        Проверки:
        __________
        * При валидной структуре json на входе получаем статус ответа 200
        * Доступны для редактирования поля courier_type, regions, working_hours
          в любой комбинации.
        * На выходе получаем json c корректной структурой
        * Все данные запроса сохраняются в базе
        * После изменения курьера снялись заказы которые он не может доставить
        """
        courier = Courier.objects.get(courier_id=100)
        assign_orders(courier)
        new_working_hours = ['11:35-14:05', '06:00-06:30']
        new_courier_regions = [100, 101]
        new_type = 'foot'
        url = reverse('couriers-detail', kwargs={'pk': courier.courier_id})
        # Проверка доступности изменения каждого поля в отдельности.
        data = {'courier_type': new_type}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_200_OK,
            'Проверьте, что поле courier_type доступно для изменения')

        data = {'regions': new_courier_regions}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_200_OK,
            'Проверьте, что поле regions доступно для изменения')

        data = {'working_hours': new_working_hours}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_200_OK,
            'Проверьте, что поле working_hours доступно для изменения')

        patched_courier = Courier.objects.get(courier_id=courier.courier_id)

        # Проверим что все изменения попали в базу
        self.assertEqual(
            patched_courier.courier_type, new_type,
            'Проверьте, что при patch запросе меняется тип курьера')
        self.assertListEqual(
            list(patched_courier.regions.values()),
            list(Region.objects.filter(
                code__in=new_courier_regions).values()),
            'Проверьте, что при patch запросе меняются районы курьера')
        self.assertListEqual(
            list(patched_courier.working_hours.values()),
            list(TimeInterval.objects.filter(
                name__in=new_working_hours).values()),
            'Проверьте, что при patch запросе меняются интервалы работы'
            'курьера')

        # Проверим, что после изменения курьера снялись заказы которые он не
        # может доставить
        patched_courier_orders = Order.objects.filter(
            invoices__courier=patched_courier,
            invoice_orders__complete_time__isnull=True)
        total_weight_orders = patched_courier_orders.aggregate(
            sum_weight=Sum('weight'))['sum_weight']
        self.assertTrue(
            total_weight_orders <= COURIER_LOAD_CAPACITY[
                patched_courier.courier_type],
            'Проверьте, что при patch запросе c изменением типа курьера '
            'снимаются заказы превышающие его актуальную грузоподъемность')
        excess_orders = patched_courier_orders.exclude(
            region__in=patched_courier.regions.all()).exclude(
            delivery_hours__in=patched_courier.working_hours.all())
        self.assertFalse(
            excess_orders.exists(),
            'Проверьте, что при patch запросе c изменением регионов и времен '
            'снимаются заказы которые курьер не сможет доставить')

    def test_not_valid_data_patch_courier(self):
        """Проверить обработку запроса PATCH /couriers с невалидными данными.

        Проверки:
        __________
        * Поле courier_id заблокировано от изменений
        * При получении неописанного поля -- возвращается ошибка
        * Валидация входных данных.
        """
        courier = Courier.objects.first()
        url = reverse('couriers-detail', kwargs={'pk': courier.courier_id})
        # Проверка, что поле courier_id заблокировано от изменений
        wrong_data = {'courier_id': 11}
        response = self.client.patch(url, wrong_data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST,
            'Проверьте, что поле courier_id заблокировано от изменений')

        # Проверяем, что при получении неописанного поля - возвращается ошибка
        wrong_data = {'undescribed_field': 'test', 'courier_type': 'foot'}
        response = self.client.patch(url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        unknown_fields = json.loads(response.content)[
            'validation errors'].get('unknown_fields')
        self.assertTrue(
            'undescribed_field' in unknown_fields,
            'Проверьте, что при наличии в запросе неописанных полей '
            'возвращается ошибка валидации')

        # Проверяем что при  невалидных значений в полях - возвращается ошибка
        wrong_data = {'courier_type': 'foo', 'regions': ['Moscow'],
                      'working_hours': ['1:35-14:05']}
        response = self.client.patch(url, wrong_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = json.loads(response.content)['validation errors']
        self.assertTrue(
            '"foo" is not a valid choice.' in errors['courier_type'],
            'Проверьте, что при передаче некорректного значения "courier_type"'
            ' возвращается соответствующая ошибка')
        self.assertTrue(
            'Incorrect type. Expected pk value, received str.'
            in errors['regions'], 'Проверьте, что проверяется что код региона '
                                  'это целочисленное значение')
        self.assertTrue(
            'Invalid pk "1:35-14:05" - object does not exist.'
            in errors['working_hours'],
            'Проверьте, что проверяется что интервалы имеют соответствующую '
            'структуру')

    def test_get_courier(self):
        """Проверить обработку запроса GET /courier/$courier_id.

        Проверки:
        __________
        * При отправке запроса на эндпоинт с id существующего курьера получаем
        ответ со статусом 200.
        * Структура ответа для курьера не совершившего ни одной доставки
        * Структура ответа для курьера с завершенными доставками
        * Корректность расчета рейтинга
        * Корректность расчета заработка
        * Корректность расчета заработка при смене типа курьера в середине
        развоза.
        """

        courier = Courier.objects.get(courier_id=100)
        url = reverse('couriers-detail', kwargs={'pk': courier.courier_id})

        active_invoice = assign_orders(courier)
        active_invoice_positions = InvoiceOrder.objects.filter(
            invoice=active_invoice)
        complete_time = active_invoice.assign_time

        fields_for_newbie = ['courier_id', 'courier_type', 'regions',
                             'working_hours', 'earnings']

        response = self.client.get(url)
        # Проверяем корректность ответа
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Проверка структуры ответа для курьера не совершившего ни одной
        # доставки
        content = json.loads(response.content)
        self.assertTrue(
            len(content) == len(fields_for_newbie),
            'Ответ на запрос для курьера не доставившего ни одного заказа '
            f'должен содержать следующие поля: {fields_for_newbie}')
        for field in fields_for_newbie:
            self.assertTrue(
                field in content,
                f'Ответ на запрос для курьера не доставившего ни одного заказа'
                f' должен содержать поле {field}')

        # Проверка расчета рейтинга.
        # Заработок должен увеличиться только по завершению развоза.
        # При смене типа курьера сумма заработка за развоз должна остаться
        # неизменной
        earning = PAY_COEFFICIENTS[courier.courier_type] * 500
        courier.courier_type = 'car'
        courier.save()
        results = {}
        count_orders = len(active_invoice_positions)
        for invoice_position in active_invoice_positions:
            region = invoice_position.order.region_id
            results.setdefault(region, [])

            delivery_time = random.randint(100, 500)
            complete_time += timedelta(seconds=delivery_time)
            complete_order(invoice_position, complete_time)
            results[region].append(delivery_time)

            average_time_delivery = {}
            for key, value in results.items():
                avg_td = sum(value) / len(value)
                average_time_delivery[key] = avg_td

            t = min(average_time_delivery.values())
            rating = round(((60 * 60 - min(t, 60 * 60)) / (60 * 60) * 5), 2)

            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = json.loads(response.content)
            self.assertEqual(
                content['rating'], rating,
                'Рейтинг считается неверно')
            count_orders -= 1
            if count_orders == 0:
                self.assertEqual(
                    content['earnings'], earning,
                    'Заработок считается неверно')
            else:
                self.assertEqual(
                    content['earnings'], 0,
                    'Заработок должен прибавляться только по завершенным '
                    'развозам')
