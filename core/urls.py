from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]