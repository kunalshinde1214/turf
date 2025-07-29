from django.contrib import admin
from .models import Booking, Payment, BookingCancellation, BookingTimeSlot


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
    'booking_id', 'user', 'turf', 'booking_date', 'start_time', 'end_time', 'status', 'payment_status', 'total_amount')
    list_filter = ('status', 'payment_status', 'booking_date', 'created_at')
    search_fields = ('booking_id', 'user__username', 'turf__name', 'contact_number')
    ordering = ('-created_at',)
    readonly_fields = ('booking_id', 'duration_hours', 'created_at', 'updated_at', 'confirmed_at', 'cancelled_at')

    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_id', 'user', 'turf', 'booking_date', 'start_time', 'end_time', 'duration_hours')
        }),
        ('Contact & Requests', {
            'fields': ('contact_number', 'special_requests')
        }),
        ('Pricing', {
            'fields': ('base_price', 'discount_amount', 'tax_amount', 'total_amount')
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Payment Details', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'payment_method', 'amount', 'transaction_id', 'is_successful', 'payment_date')
    list_filter = ('payment_method', 'is_successful', 'payment_date')
    search_fields = ('booking__booking_id', 'transaction_id')
    ordering = ('-payment_date',)
    readonly_fields = ('payment_date',)


@admin.register(BookingCancellation)
class BookingCancellationAdmin(admin.ModelAdmin):
    list_display = ('booking', 'reason', 'cancelled_by', 'refund_amount', 'refund_processed', 'cancelled_at')
    list_filter = ('reason', 'refund_processed', 'cancelled_at')
    search_fields = ('booking__booking_id', 'cancelled_by__username')
    ordering = ('-cancelled_at',)
    readonly_fields = ('cancelled_at',)


@admin.register(BookingTimeSlot)
class BookingTimeSlotAdmin(admin.ModelAdmin):
    list_display = ('turf', 'date', 'start_time', 'end_time', 'price', 'is_available')
    list_filter = ('is_available', 'date', 'turf')
    search_fields = ('turf__name',)
    ordering = ('date', 'start_time')