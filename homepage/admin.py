from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone', 'city', 'status', 'created']
    list_filter = ['status', 'city', 'created']
    search_fields = ['first_name', 'last_name', 'email', 'phone']