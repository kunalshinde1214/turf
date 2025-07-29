from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from turfs.models import Turf, TurfCategory
from bookings.models import Booking
from accounts.models import User


def home(request):
    """Home page with featured turfs and statistics"""
    featured_turfs = Turf.objects.filter(
        status='active'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-avg_rating', '-review_count')[:6]

    # Statistics
    total_turfs = Turf.objects.filter(status='active').count()
    total_bookings = Booking.objects.filter(status='confirmed').count()
    total_users = User.objects.filter(is_active=True).count()
    categories = TurfCategory.objects.all()

    context = {
        'featured_turfs': featured_turfs,
        'total_turfs': total_turfs,
        'total_bookings': total_bookings,
        'total_users': total_users,
        'categories': categories,
    }

    return render(request, 'core/home.html', context)


@login_required
def dashboard(request):
    """User dashboard with personalized content"""
    user = request.user

    # Recent bookings
    recent_bookings = user.bookings.all().order_by('-created_at')[:5]

    # Upcoming bookings
    upcoming_bookings = user.bookings.filter(
        booking_date__gte=timezone.now().date(),
        status='confirmed'
    ).order_by('booking_date', 'start_time')[:3]

    # Statistics
    total_bookings = user.bookings.count()
    confirmed_bookings = user.bookings.filter(status='confirmed').count()
    cancelled_bookings = user.bookings.filter(status='cancelled').count()
    total_spent = sum(
        booking.total_amount for booking in user.bookings.filter(payment_status='paid')
    )

    # For turf owners
    owner_stats = {}
    if user.user_type == 'owner':
        owned_turfs = user.owned_turfs.all()
        owner_stats = {
            'total_turfs': owned_turfs.count(),
            'active_turfs': owned_turfs.filter(status='active').count(),
            'total_revenue': sum(
                booking.total_amount
                for turf in owned_turfs
                for booking in turf.bookings.filter(payment_status='paid')
            ),
            'recent_bookings': Booking.objects.filter(
                turf__owner=user
            ).order_by('-created_at')[:5]
        }

    context = {
        'recent_bookings': recent_bookings,
        'upcoming_bookings': upcoming_bookings,
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'total_spent': total_spent,
        'owner_stats': owner_stats,
    }

    return render(request, 'core/dashboard.html', context)


def search_suggestions(request):
    """AJAX endpoint for search suggestions"""
    query = request.GET.get('q', '')
    suggestions = []

    if len(query) >= 2:
        # Turf name suggestions
        turf_names = Turf.objects.filter(
            name__icontains=query,
            status='active'
        ).values_list('name', flat=True)[:5]

        # City suggestions
        cities = Turf.objects.filter(
            city__icontains=query,
            status='active'
        ).values_list('city', flat=True).distinct()[:3]

        suggestions = list(turf_names) + list(cities)

    return JsonResponse({'suggestions': suggestions})


def about(request):
    """About page"""
    return render(request, 'core/about.html')


def contact(request):
    """Contact page"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Here you would typically send an email or save to database
        # For now, just show a success message
        messages.success(request, 'Thank you for your message. We will get back to you soon!')
        return redirect('core:contact')

    return render(request, 'core/contact.html')


def custom_404(request, exception):
    """Custom 404 error page"""
    return render(request, 'errors/404.html', status=404)


def custom_500(request):
    """Custom 500 error page"""
    return render(request, 'errors/500.html', status=500)