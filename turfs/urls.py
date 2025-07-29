from django.urls import path
from . import views

app_name = 'turfs'

urlpatterns = [
    path('', views.TurfListView.as_view(), name='list'),
    path('<int:pk>/', views.TurfDetailView.as_view(), name='detail'),
    path('create/', views.TurfCreateView.as_view(), name='create'),
    path('<int:pk>/update/', views.TurfUpdateView.as_view(), name='update'),
    path('<int:turf_id>/review/', views.add_review, name='add_review'),
    path('search/', views.search_turfs, name='search'),
    path('<int:turf_id>/availability/', views.check_availability, name='check_availability'),
]