from delivery.models import Courier, Order, Region, TimeInterval


#
# def create_test_case():
#     region_1 = Region.objects.create(code=123)
#     working_hours_1 = TimeInterval.objects.create(name='09:00-18:00')
#     courier_1 = Courier.objects.create(courier_id=1, courier_type='foot')
#     courier_1.regions.set([region_1])
#     courier_1.working_hours.set([working_hours_1])
#     return {'courier_1': courier_1}

def create_test_case_full():
    working_hours = ['11:35-14:05', '09:00-11:00']
    courier_regions = [100, 101, 102]
    other_regions = [110, 111]
    delivery_hours_in = ['10:00-11:36', '12:00-13:00', '14:04-15:00',
                         '08:00-09:01', '09:00-11:00', '10:59-11:35']
    delivery_hours_out = ['06:00-07:00', '11:20-11:35', '14:05-16:35',
                          '18:00-22:00']
    heavy_weights = [2, 3, 7.5, 9, 9, 11, 29]

    for name in (working_hours + delivery_hours_in + delivery_hours_out):
        TimeInterval.objects.get_or_create(name=name)
    for code in (courier_regions + other_regions):
        Region.objects.get_or_create(code=code)

    courier = Courier.objects.create(courier_id=100, courier_type='bike')
    courier.regions.add(*courier_regions)
    courier.working_hours.add(*working_hours)
    other_courier = Courier.objects.create(courier_id=101, courier_type='bike')
    other_courier.regions.add(*courier_regions)
    other_courier.working_hours.add(*working_hours)

    order_id = 100

    for region in courier_regions + other_regions:
        for interval in delivery_hours_in + delivery_hours_out:
            Order.objects.create(
                order_id=order_id, weight=0.01,
                region_id=region).delivery_hours.add(interval)
            order_id += 1

    for weight in heavy_weights:
        Order.objects.create(
            order_id=order_id, weight=weight,
            region_id=courier_regions[0]).delivery_hours.add(working_hours[0])
        order_id += 1

