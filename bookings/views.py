from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from datetime import datetime, timedelta
import razorpay
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

from .models import Booking, Payment, BookingCancellation
from .forms import BookingForm
from turfs.models import Turf


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'bookings/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 10

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')


class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = 'bookings/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)


@login_required
def create_booking(request, turf_id):
    turf = get_object_or_404(Turf, id=turf_id, status='active')

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking_date = form.cleaned_data['booking_date']
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']

            # Check if slot is available
            existing_booking = Booking.objects.filter(
                turf=turf,
                booking_date=booking_date,
                start_time=start_time,
                end_time=end_time,
                status__in=['confirmed', 'pending']
            ).exists()

            if existing_booking:
                messages.error(request, 'This time slot is already booked.')
                return redirect('turfs:detail', pk=turf_id)

            # Calculate duration and pricing
            start_datetime = datetime.combine(booking_date, start_time)
            end_datetime = datetime.combine(booking_date, end_time)
            duration = (end_datetime - start_datetime).total_seconds() / 3600

            base_price = turf.price_per_hour * duration
            tax_amount = base_price * 0.18  # 18% GST
            total_amount = base_price + tax_amount

            # Create booking
            booking = form.save(commit=False)
            booking.user = request.user
            booking.turf = turf
            booking.duration_hours = duration
            booking.base_price = base_price
            booking.tax_amount = tax_amount
            booking.total_amount = total_amount
            booking.save()

            # Create Razorpay order
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            razorpay_order = client.order.create({
                'amount': int(total_amount * 100),  # Amount in paise
                'currency': 'INR',
                'receipt': str(booking.booking_id),
                'payment_capture': 1
            })

            booking.razorpay_order_id = razorpay_order['id']
            booking.save()

            context = {
                'booking': booking,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': int(total_amount * 100),
            }

            return render(request, 'bookings/payment.html', context)
    else:
        form = BookingForm()

    return render(request, 'bookings/create_booking.html', {
        'form': form,
        'turf': turf
    })


@csrf_exempt
@login_required
def payment_success(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')

        # Verify payment signature
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            # Update booking
            booking = get_object_or_404(Booking, razorpay_order_id=razorpay_order_id)
            booking.razorpay_payment_id = razorpay_payment_id
            booking.razorpay_signature = razorpay_signature
            booking.payment_status = 'paid'
            booking.status = 'confirmed'
            booking.confirmed_at = timezone.now()
            booking.save()

            # Create payment record
            Payment.objects.create(
                booking=booking,
                payment_method='razorpay',
                amount=booking.total_amount,
                transaction_id=razorpay_payment_id,
                is_successful=True
            )

            # Send confirmation email
            try:
                send_mail(
                    'Booking Confirmed - TurfBooking',
                    f'Your booking for {booking.turf.name} on {booking.booking_date} has been confirmed.',
                    settings.EMAIL_HOST_USER,
                    [booking.user.email],
                    fail_silently=True,
                )
            except:
                pass

            return JsonResponse({'success': True})

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'success': False, 'error': 'Payment verification failed'})

    return JsonResponse({'success': False})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if not booking.can_cancel:
        messages.error(request, 'This booking cannot be cancelled.')
        return redirect('bookings:detail', pk=booking_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'user_request')
        description = request.POST.get('description', '')

        # Cancel booking
        booking.cancel_booking()

        # Create cancellation record
        BookingCancellation.objects.create(
            booking=booking,
            reason=reason,
            description=description,
            cancelled_by=request.user,
            refund_amount=booking.total_amount * 0.8  # 80% refund
        )

        messages.success(request, 'Booking cancelled successfully. Refund will be processed within 5-7 business days.')
        return redirect('bookings:list')

    return render(request, 'bookings/cancel_booking.html', {'booking': booking})


@login_required
def download_booking_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph("BOOKING RECEIPT", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 20))

    # Booking details
    booking_data = [
        ['Booking ID:', str(booking.booking_id)],
        ['Turf Name:', booking.turf.name],
        ['Date:', booking.booking_date.strftime('%d %B %Y')],
        ['Time:', f"{booking.start_time} - {booking.end_time}"],
        ['Duration:', f"{booking.duration_hours} hours"],
        ['Base Price:', f"₹{booking.base_price}"],
        ['Tax (18%):', f"₹{booking.tax_amount}"],
        ['Total Amount:', f"₹{booking.total_amount}"],
        ['Status:', booking.get_status_display()],
        ['Payment Status:', booking.get_payment_status_display()],
    ]

    table = Table(booking_data, colWidths=[2 * 72, 4 * 72])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(table)
    doc.build(story)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="booking_receipt_{booking.booking_id}.pdf"'

    return response


@login_required
def booking_analytics(request):
    """Generate booking analytics and reports"""
    user = request.user

    # Get date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)  # Last 30 days

    bookings = Booking.objects.filter(
        user=user,
        created_at__date__range=[start_date, end_date]
    )

    # Analytics data
    total_bookings = bookings.count()
    total_spent = sum(booking.total_amount for booking in bookings if booking.payment_status == 'paid')
    confirmed_bookings = bookings.filter(status='confirmed').count()
    cancelled_bookings = bookings.filter(status='cancelled').count()

    # Monthly breakdown
    monthly_data = {}
    for booking in bookings:
        month_key = booking.created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {'count': 0, 'amount': 0}
        monthly_data[month_key]['count'] += 1
        if booking.payment_status == 'paid':
            monthly_data[month_key]['amount'] += float(booking.total_amount)

    context = {
        'total_bookings': total_bookings,
        'total_spent': total_spent,
        'confirmed_bookings': confirmed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'monthly_data': monthly_data,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'bookings/analytics.html', context)


@login_required
def generate_booking_report(request):
    """Generate PDF report of user's bookings"""
    user = request.user
    bookings = Booking.objects.filter(user=user).order_by('-created_at')[:50]  # Last 50 bookings

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph(f"BOOKING REPORT - {user.get_full_name()}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 20))

    # Summary
    total_bookings = bookings.count()
    total_spent = sum(b.total_amount for b in bookings if b.payment_status == 'paid')

    summary_data = [
        ['Total Bookings:', str(total_bookings)],
        ['Total Amount Spent:', f"₹{total_spent}"],
        ['Report Generated:', timezone.now().strftime('%d %B %Y, %I:%M %p')],
    ]

    summary_table = Table(summary_data, colWidths=[2 * 72, 3 * 72])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 30))

    # Bookings table
    if bookings:
        booking_data = [['Date', 'Turf', 'Time', 'Amount', 'Status']]

        for booking in bookings:
            booking_data.append([
                booking.booking_date.strftime('%d/%m/%Y'),
                booking.turf.name[:20] + '...' if len(booking.turf.name) > 20 else booking.turf.name,
                f"{booking.start_time}-{booking.end_time}",
                f"₹{booking.total_amount}",
                booking.get_status_display()
            ])

        booking_table = Table(booking_data, colWidths=[1 * 72, 2.5 * 72, 1.5 * 72, 1 * 72, 1 * 72])
        booking_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))

        story.append(booking_table)

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="booking_report_{user.username}.pdf"'

    return response