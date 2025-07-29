from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from PIL import Image
import os

User = get_user_model()


class TurfCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # Font Awesome icon class

    class Meta:
        verbose_name_plural = "Turf Categories"

    def __str__(self):
        return self.name


class Turf(models.Model):
    SURFACE_TYPES = (
        ('grass', 'Natural Grass'),
        ('artificial', 'Artificial Turf'),
        ('concrete', 'Concrete'),
        ('clay', 'Clay'),
    )

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_turfs')
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(TurfCategory, on_delete=models.CASCADE, related_name='turfs')

    # Location Details
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # Turf Details
    surface_type = models.CharField(max_length=20, choices=SURFACE_TYPES)
    length = models.PositiveIntegerField(help_text="Length in meters")
    width = models.PositiveIntegerField(help_text="Width in meters")
    capacity = models.PositiveIntegerField()

    # Pricing
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    weekend_price_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)

    # Features
    features = models.JSONField(default=list, blank=True)  # ['parking', 'washroom', 'lighting', etc.]

    # Images
    main_image = models.ImageField(upload_to='turf_images/', blank=True, null=True)

    # Status and Ratings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_bookings = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.city}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.main_image:
            img = Image.open(self.main_image.path)
            if img.height > 800 or img.width > 800:
                output_size = (800, 800)
                img.thumbnail(output_size)
                img.save(self.main_image.path)

    @property
    def area(self):
        return self.length * self.width

    def get_weekend_price(self):
        return self.price_per_hour * self.weekend_price_multiplier


class TurfImage(models.Model):
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='turf_images/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.turf.name} - Image {self.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.image.path)
        if img.height > 800 or img.width > 800:
            output_size = (800, 800)
            img.thumbnail(output_size)
            img.save(self.image.path)


class TurfAvailability(models.Model):
    DAYS_OF_WEEK = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ['turf', 'day_of_week']

    def __str__(self):
        return f"{self.turf.name} - {self.get_day_of_week_display()}"


class TurfReview(models.Model):
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['turf', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.turf.name} - {self.rating} stars by {self.user.username}"