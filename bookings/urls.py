from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.BookingListView.as_view(), name='list'),
    path('<int:pk>/', views.BookingDetailView.as_view(), name='detail'),
    path('create/<int:turf_id>/', views.create_booking, name='create'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('<int:booking_id>/cancel/', views.cancel_booking, name='cancel'),
    path('<int:booking_id>/receipt/', views.download_booking_receipt, name='download_receipt'),
    path('analytics/', views.booking_analytics, name='analytics'),
    path('report/', views.generate_booking_report, name='generate_report'),
]