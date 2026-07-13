
from rest_framework import serializers
 
from .models import Booking
 
 
class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'city', 'status', 'created']
        read_only_fields = ['id', 'status', 'created']
 
    def validate_phone(self, value):
        value = value.strip()
        if len(value) < 7:
            raise serializers.ValidationError('Enter a valid phone number.')
        return value
 