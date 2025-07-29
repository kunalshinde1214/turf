from django.contrib import admin
from .models import TurfCategory, Turf, TurfImage, TurfAvailability, TurfReview


@admin.register(TurfCategory)
class TurfCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'icon')
    search_fields = ('name',)


class TurfImageInline(admin.TabularInline):
    model = TurfImage
    extra = 1


class TurfAvailabilityInline(admin.TabularInline):
    model = TurfAvailability
    extra = 7  # One for each day of the week


@admin.register(Turf)
class TurfAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'city', 'category', 'price_per_hour', 'status', 'average_rating', 'created_at')
    list_filter = ('status', 'category', 'surface_type', 'city', 'created_at')
    search_fields = ('name', 'owner__username', 'city', 'address')
    ordering = ('-created_at',)
    readonly_fields = ('average_rating', 'total_bookings', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'name', 'description', 'category', 'status')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'pincode', 'latitude', 'longitude')
        }),
        ('Turf Details', {
            'fields': ('surface_type', 'length', 'width', 'capacity', 'features', 'main_image')
        }),
        ('Pricing', {
            'fields': ('price_per_hour', 'weekend_price_multiplier')
        }),
        ('Statistics', {
            'fields': ('average_rating', 'total_bookings'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [TurfImageInline, TurfAvailabilityInline]


@admin.register(TurfReview)
class TurfReviewAdmin(admin.ModelAdmin):
    list_display = ('turf', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('turf__name', 'user__username', 'comment')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)