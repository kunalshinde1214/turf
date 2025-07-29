from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from .models import User, UserProfile
from .forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm


class UserRegistrationView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()

        # Create user profile
        UserProfile.objects.create(user=user)

        # Send welcome email
        try:
            send_mail(
                'Welcome to TurfBooking!',
                f'Hi {user.first_name}, welcome to our turf booking platform!',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=True,
            )
        except:
            pass

        messages.success(self.request, 'Account created successfully! Please log in.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')

            # Redirect to next page or dashboard
            next_page = request.GET.get('next', 'core:dashboard')
            return redirect(next_page)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:home')


class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'

    def get_object(self):
        return self.request.user


@login_required
def update_profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user.profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'accounts/update_profile.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:login')

    return render(request, 'accounts/change_password.html')


@csrf_exempt
@login_required
def upload_profile_picture(request):
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        user = request.user
        user.profile_picture = request.FILES['profile_picture']
        user.save()

        return JsonResponse({
            'success': True,
            'image_url': user.profile_picture.url
        })

    return JsonResponse({'success': False})


@login_required
def user_dashboard(request):
    user = request.user
    recent_bookings = user.bookings.all()[:5]

    context = {
        'user': user,
        'recent_bookings': recent_bookings,
        'total_bookings': user.bookings.count(),
        'pending_bookings': user.bookings.filter(status='pending').count(),
        'confirmed_bookings': user.bookings.filter(status='confirmed').count(),
    }

    if user.user_type == 'owner':
        context.update({
            'owned_turfs': user.owned_turfs.all(),
            'total_turfs': user.owned_turfs.count(),
            'active_turfs': user.owned_turfs.filter(status='active').count(),
        })

    return render(request, 'accounts/dashboard.html', context)