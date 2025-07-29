from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    # Basic Information
    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    turf = models.ForeignKey('turfs.Turf', on_delete=models.CASCADE, related_name='bookings')

    # Booking Details
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_hours = models.DecimalField(max_digits=4, decimal_places=2)

    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Additional Information
    special_requests = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=15)

    # Payment Information
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['turf', 'booking_date', 'start_time', 'end_time']

    def __str__(self):
        return f"Booking {self.booking_id} - {self.turf.name} on {self.booking_date}"

    def save(self, *args, **kwargs):
        if not self.duration_hours:
            # Calculate duration in hours
            start_datetime = timezone.datetime.combine(self.booking_date, self.start_time)
            end_datetime = timezone.datetime.combine(self.booking_date, self.end_time)
            duration = end_datetime - start_datetime
            self.duration_hours = Decimal(str(duration.total_seconds() / 3600))

        if not self.base_price:
            self.base_price = self.turf.price_per_hour * self.duration_hours

        if not self.total_amount:
            self.total_amount = self.base_price - self.discount_amount + self.tax_amount

        super().save(*args, **kwargs)

    @property
    def is_past_booking(self):
        booking_datetime = timezone.datetime.combine(self.booking_date, self.end_time)
        return timezone.now() > timezone.make_aware(booking_datetime)

    @property
    def can_cancel(self):
        if self.status in ['cancelled', 'completed', 'refunded']:
            return False

        booking_datetime = timezone.datetime.combine(self.booking_date, self.start_time)
        time_until_booking = timezone.make_aware(booking_datetime) - timezone.now()

        # Can cancel if booking is more than 2 hours away
        return time_until_booking.total_seconds() > 7200

    def confirm_booking(self):
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save()

    def cancel_booking(self):
        if self.can_cancel:
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            self.save()
            return True
        return False


class BookingTimeSlot(models.Model):
    turf = models.ForeignKey('turfs.Turf', on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['turf', 'date', 'start_time', 'end_time']
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.turf.name} - {self.date} {self.start_time}-{self.end_time}"

    @property
    def is_booked(self):
        return Booking.objects.filter(
            turf=self.turf,
            booking_date=self.date,
            start_time=self.start_time,
            end_time=self.end_time,
            status__in=['confirmed', 'pending']
        ).exists()


class Payment(models.Model):
    PAYMENT_METHODS = (
        ('razorpay', 'Razorpay'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=False)
    failure_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payment for {self.booking.booking_id} - ₹{self.amount}"


class BookingCancellation(models.Model):
    CANCELLATION_REASONS = (
        ('user_request', 'User Request'),
        ('weather', 'Weather Conditions'),
        ('maintenance', 'Turf Maintenance'),
        ('emergency', 'Emergency'),
        ('other', 'Other'),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='cancellation')
    reason = models.CharField(max_length=20, choices=CANCELLATION_REASONS)
    description = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.CASCADE)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_processed = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation for {self.booking.booking_id}"