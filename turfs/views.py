from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import Turf, TurfCategory, TurfAvailability, TurfReview, TurfImage
from .forms import TurfForm, TurfReviewForm, TurfSearchForm
from bookings.models import Booking, BookingTimeSlot


class TurfListView(ListView):
    model = Turf
    template_name = 'turfs/turf_list.html'
    context_object_name = 'turfs'
    paginate_by = 12

    def get_queryset(self):
        queryset = Turf.objects.filter(status='active').annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )

        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(address__icontains=search_query)
            )

        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__id=category)

        # Filter by city
        city = self.request.GET.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)

        # Filter by price range
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price_per_hour__gte=min_price)
        if max_price:
            queryset = queryset.filter(price_per_hour__lte=max_price)

        # Sort options
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price_per_hour')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price_per_hour')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-avg_rating')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('name')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = TurfCategory.objects.all()
        context['search_form'] = TurfSearchForm(self.request.GET)
        context['cities'] = Turf.objects.values_list('city', flat=True).distinct()
        return context


class TurfDetailView(DetailView):
    model = Turf
    template_name = 'turfs/turf_detail.html'
    context_object_name = 'turf'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        turf = self.get_object()

        # Get reviews
        reviews = turf.reviews.all()[:10]
        context['reviews'] = reviews
        context['review_form'] = TurfReviewForm()

        # Get availability for next 7 days
        today = timezone.now().date()
        availability_data = []

        for i in range(7):
            date = today + timedelta(days=i)
            day_availability = TurfAvailability.objects.filter(
                turf=turf,
                day_of_week=date.weekday(),
                is_available=True
            ).first()

            if day_availability:
                # Generate time slots
                time_slots = self.generate_time_slots(turf, date, day_availability)
                availability_data.append({
                    'date': date,
                    'day_name': date.strftime('%A'),
                    'slots': time_slots
                })

        context['availability'] = availability_data
        context['images'] = turf.images.all()

        return context

    def generate_time_slots(self, turf, date, availability):
        slots = []
        current_time = availability.opening_time
        slot_duration = timedelta(hours=1)  # 1-hour slots

        while current_time < availability.closing_time:
            end_time = (datetime.combine(date, current_time) + slot_duration).time()
            if end_time > availability.closing_time:
                break

            # Check if slot is already booked
            is_booked = Booking.objects.filter(
                turf=turf,
                booking_date=date,
                start_time=current_time,
                status__in=['confirmed', 'pending']
            ).exists()

            slots.append({
                'start_time': current_time,
                'end_time': end_time,
                'is_available': not is_booked,
                'price': turf.price_per_hour
            })

            current_time = end_time

        return slots


class TurfCreateView(LoginRequiredMixin, CreateView):
    model = Turf
    form_class = TurfForm
    template_name = 'turfs/turf_create.html'
    success_url = reverse_lazy('accounts:dashboard')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Turf created successfully!')
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type not in ['owner', 'admin']:
            messages.error(request, 'You need to be a turf owner to create turfs.')
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)


class TurfUpdateView(LoginRequiredMixin, UpdateView):
    model = Turf
    form_class = TurfForm
    template_name = 'turfs/turf_update.html'

    def get_success_url(self):
        return reverse_lazy('turfs:detail', kwargs={'pk': self.object.pk})

    def dispatch(self, request, *args, **kwargs):
        turf = self.get_object()
        if request.user != turf.owner and request.user.user_type != 'admin':
            messages.error(request, 'You can only edit your own turfs.')
            return redirect('turfs:detail', pk=turf.pk)
        return super().dispatch(request, *args, **kwargs)


@login_required
def add_review(request, turf_id):
    turf = get_object_or_404(Turf, id=turf_id)

    if request.method == 'POST':
        form = TurfReviewForm(request.POST)
        if form.is_valid():
            # Check if user has already reviewed this turf
            existing_review = TurfReview.objects.filter(turf=turf, user=request.user).first()
            if existing_review:
                messages.error(request, 'You have already reviewed this turf.')
            else:
                review = form.save(commit=False)
                review.turf = turf
                review.user = request.user
                review.save()

                # Update turf average rating
                avg_rating = turf.reviews.aggregate(Avg('rating'))['rating__avg']
                turf.average_rating = avg_rating or 0
                turf.save()

                messages.success(request, 'Review added successfully!')

    return redirect('turfs:detail', pk=turf_id)


def search_turfs(request):
    """Advanced search with custom SQL for better performance"""
    query = request.GET.get('q', '')
    city = request.GET.get('city', '')
    category = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')

    # Custom SQL query for complex search
    from django.db import connection

    sql = """
    SELECT t.*, tc.name as category_name, 
           AVG(tr.rating) as avg_rating,
           COUNT(tr.id) as review_count
    FROM turfs_turf t
    LEFT JOIN turfs_turfcategory tc ON t.category_id = tc.id
    LEFT JOIN turfs_turfreview tr ON t.id = tr.turf_id
    WHERE t.status = 'active'
    """

    params = []

    if query:
        sql += " AND (t.name ILIKE %s OR t.description ILIKE %s OR t.city ILIKE %s)"
        params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])

    if city:
        sql += " AND t.city ILIKE %s"
        params.append(f'%{city}%')

    if category:
        sql += " AND t.category_id = %s"
        params.append(category)

    if min_price:
        sql += " AND t.price_per_hour >= %s"
        params.append(min_price)

    if max_price:
        sql += " AND t.price_per_hour <= %s"
        params.append(max_price)

    sql += " GROUP BY t.id, tc.name ORDER BY t.name"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        results = cursor.fetchall()

    # Convert results to dict format
    turfs_data = []
    for row in results:
        turfs_data.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'city': row[3],
            'price_per_hour': row[4],
            'category_name': row[-3],
            'avg_rating': row[-2] or 0,
            'review_count': row[-1] or 0,
        })

    return JsonResponse({'turfs': turfs_data})


@login_required
def check_availability(request, turf_id):
    turf = get_object_or_404(Turf, id=turf_id)
    date_str = request.GET.get('date')

    if not date_str:
        return JsonResponse({'error': 'Date is required'})

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'})

    # Get availability for the day
    day_availability = TurfAvailability.objects.filter(
        turf=turf,
        day_of_week=date.weekday(),
        is_available=True
    ).first()

    if not day_availability:
        return JsonResponse({'available_slots': []})

    # Generate available time slots
    slots = []
    current_time = day_availability.opening_time
    slot_duration = timedelta(hours=1)

    while current_time < day_availability.closing_time:
        end_time = (datetime.combine(date, current_time) + slot_duration).time()
        if end_time > day_availability.closing_time:
            break

        # Check if slot is booked
        is_booked = Booking.objects.filter(
            turf=turf,
            booking_date=date,
            start_time=current_time,
            status__in=['confirmed', 'pending']
        ).exists()

        if not is_booked:
            slots.append({
                'start_time': current_time.strftime('%H:%M'),
                'end_time': end_time.strftime('%H:%M'),
                'price': float(turf.price_per_hour)
            })

        current_time = end_time

    return JsonResponse({'available_slots': slots})