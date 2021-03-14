from rest_framework import serializers

from delivery import services
from .models import Courier, Order, Region, TimeInterval


class CourierSerializer(serializers.ModelSerializer):
    regions = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(),
        many=True)
    working_hours = serializers.SlugRelatedField(
        queryset=TimeInterval.objects.all(),
        many=True,
        slug_field='name'
    )
    rating = serializers.SerializerMethodField()
    earnings = serializers.SerializerMethodField()

    class Meta:
        model = Courier
        fields = ['courier_id', 'courier_type', 'regions', 'working_hours',
                  'rating', 'earnings', ]

    def get_rating(self, instance):
        return services.get_courier_rating(instance)

    def get_earnings(self, instance):
        return services.get_courier_earning(instance)

    def run_validation(self, data=serializers.empty):
        if data is not serializers.empty:
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                errors = [f for f in unknown_fields]
                raise serializers.ValidationError({
                    'unknown_fields': errors,
                })
            regions = data.get('regions')
            if regions:
                for code in regions:
                    Region.objects.get_or_create(code=code)
            working_hours = data.get('working_hours')
            if working_hours:
                for interval in working_hours:
                    TimeInterval.objects.get_or_create(name=interval)
        return super().run_validation(data)

    def to_representation(self, instance):
        if self.context['request'].method == 'POST':
            value_id = instance.get('courier_id') if isinstance(
                instance, dict) else instance.courier_id
            return {'id': value_id}
        return super().to_representation(instance)


class OrderSerializer(serializers.ModelSerializer):
    delivery_hours = serializers.SlugRelatedField(
        queryset=TimeInterval.objects.all(),
        many=True,
        slug_field='name'
    )

    class Meta:
        model = Order
        fields = ['order_id', 'weight', 'region', 'delivery_hours', ]

    def run_validation(self, data=serializers.empty):
        if data is not serializers.empty:
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError("dont send extra fields")
            regions = data.get('regions')
            if regions:
                for code in regions:
                    Region.objects.get_or_create(code=code)
            delivery_hours = data.get('delivery_hours')
            if delivery_hours:
                for interval in delivery_hours:
                    TimeInterval.objects.get_or_create(name=interval)
        return super().run_validation(data)

    def to_representation(self, instance):
        if self.context['request'].method == 'POST':
            value_id = instance.get('order_id') if isinstance(
                instance, dict) else instance.order_id
            return {'id': value_id}
        return super().to_representation(instance)


class OrderRepr(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['order_id']
