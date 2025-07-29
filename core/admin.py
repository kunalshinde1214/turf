from django.contrib import admin

# Core app doesn't have models, but we can customize the admin site here
admin.site.site_header = "TurfBooking Administration"
admin.site.site_title = "TurfBooking Admin"
admin.site.index_title = "Welcome to TurfBooking Administration"