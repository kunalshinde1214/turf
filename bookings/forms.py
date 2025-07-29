from django import forms
from .models import Booking
from django.utils import timezone
from datetime import datetime, time


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['booking_date', 'start_time', 'end_time', 'contact_number', 'special_requests']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set minimum date to today
        self.fields['booking_date'].widget = forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': timezone.now().date().isoformat()
        })

        self.fields['start_time'].widget = forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })

        self.fields['end_time'].widget = forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })

        self.fields['contact_number'].widget = forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+91 98765 43210'
        })

        self.fields['special_requests'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any special requirements or requests...'
        })
        self.fields['special_requests'].required = False

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if booking_date and booking_date < timezone.now().date():
            raise forms.ValidationError("Booking date cannot be in the past.")

        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError("End time must be after start time.")

            # Check minimum booking duration (1 hour)
            start_datetime = datetime.combine(booking_date or timezone.now().date(), start_time)
            end_datetime = datetime.combine(booking_date or timezone.now().date(), end_time)
            duration = (end_datetime - start_datetime).total_seconds() / 3600

            if duration < 1:
                raise forms.ValidationError("Minimum booking duration is 1 hour.")

            if duration > 8:
                raise forms.ValidationError("Maximum booking duration is 8 hours.")

        return cleaned_data


class BookingSearchForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    status = forms.ChoiceField(
        choices = [('', 'All Status')] + list(Booking.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    turf_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by turf name...'
        })
    )