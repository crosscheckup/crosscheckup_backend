
from rest_framework import serializers

from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    assigned_admin_id = serializers.IntegerField(source='assigned_admin.id', read_only=True)
    assigned_engineer_id = serializers.IntegerField(source='assigned_engineer.id', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 'city', 'status', 'created',
            'assigned_admin_id', 'assigned_engineer_id',
        ]
        read_only_fields = ['id', 'status', 'created', 'assigned_admin_id', 'assigned_engineer_id']

    def validate_phone(self, value):
        value = value.strip()
        if len(value) < 7:
            raise serializers.ValidationError('Enter a valid phone number.')
        return value
