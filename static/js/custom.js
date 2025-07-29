// Custom JavaScript for TurfBooking

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new window.bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new window.bootstrap.Popover(popoverTriggerEl);
    });

    // Search suggestions
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        let searchTimeout;
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'search-suggestions';
        searchInput.parentNode.style.position = 'relative';
        searchInput.parentNode.appendChild(suggestionsContainer);

        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length >= 2) {
                searchTimeout = setTimeout(() => {
                    fetchSearchSuggestions(query, suggestionsContainer);
                }, 300);
            } else {
                suggestionsContainer.innerHTML = '';
                suggestionsContainer.style.display = 'none';
            }
        });

        // Hide suggestions when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                suggestionsContainer.style.display = 'none';
            }
        });
    }

    // Time slot selection
    const timeSlots = document.querySelectorAll('.time-slot.available');
    timeSlots.forEach(slot => {
        slot.addEventListener('click', function() {
            // Remove previous selection
            document.querySelectorAll('.time-slot.selected').forEach(s => {
                s.classList.remove('selected');
            });

            // Add selection to clicked slot
            this.classList.add('selected');

            // Update form fields if they exist
            const startTime = this.dataset.startTime;
            const endTime = this.dataset.endTime;
            const price = this.dataset.price;

            const startTimeInput = document.querySelector('input[name="start_time"]');
            const endTimeInput = document.querySelector('input[name="end_time"]');

            if (startTimeInput) startTimeInput.value = startTime;
            if (endTimeInput) endTimeInput.value = endTime;

            // Update booking summary
            updateBookingSummary(startTime, endTime, price);
        });
    });

    // Image gallery
    const galleryImages = document.querySelectorAll('.turf-gallery img');
    galleryImages.forEach(img => {
        img.addEventListener('click', function() {
            openImageModal(this.src, this.alt);
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Auto-hide alerts
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            const bsAlert = new window.bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Loading states for buttons
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.form && this.form.checkValidity()) {
                showLoadingState(this);
            }
        });
    });

    // Date picker restrictions
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        const today = new Date().toISOString().split('T')[0];
        input.setAttribute('min', today);
    });

    // Price range slider
    const priceRangeInputs = document.querySelectorAll('input[type="range"]');
    priceRangeInputs.forEach(input => {
        input.addEventListener('input', function() {
            const output = document.querySelector(`output[for="${this.id}"]`);
            if (output) {
                output.textContent = `₹${this.value}`;
            }
        });
    });
});

// Search suggestions function
function fetchSearchSuggestions(query, container) {
    fetch(`/search-suggestions/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            container.innerHTML = '';

            if (data.suggestions && data.suggestions.length > 0) {
                data.suggestions.forEach(suggestion => {
                    const item = document.createElement('div');
                    item.className = 'search-suggestion-item';
                    item.textContent = suggestion;
                    item.addEventListener('click', function() {
                        document.querySelector('input[name="search"]').value = suggestion;
                        container.style.display = 'none';
                    });
                    container.appendChild(item);
                });
                container.style.display = 'block';
            } else {
                container.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error fetching suggestions:', error);
            container.style.display = 'none';
        });
}

// Update booking summary
function updateBookingSummary(startTime, endTime, price) {
    const summaryContainer = document.querySelector('.booking-summary');
    if (!summaryContainer) return;

    const duration = calculateDuration(startTime, endTime);
    const basePrice = parseFloat(price) * duration;
    const tax = basePrice * 0.18;
    const total = basePrice + tax;

    summaryContainer.innerHTML = `
        <h5>Booking Summary</h5>
        <div class="row">
            <div class="col-6">Time:</div>
            <div class="col-6">${startTime} - ${endTime}</div>
        </div>
        <div class="row">
            <div class="col-6">Duration:</div>
            <div class="col-6">${duration} hour(s)</div>
        </div>
        <div class="row">
            <div class="col-6">Base Price:</div>
            <div class="col-6">₹${basePrice.toFixed(2)}</div>
        </div>
        <div class="row">
            <div class="col-6">Tax (18%):</div>
            <div class="col-6">₹${tax.toFixed(2)}</div>
        </div>
        <hr>
        <div class="row fw-bold">
            <div class="col-6">Total:</div>
            <div class="col-6">₹${total.toFixed(2)}</div>
        </div>
    `;
}

// Calculate duration between two times
function calculateDuration(startTime, endTime) {
    const start = new Date(`2000-01-01 ${startTime}`);
    const end = new Date(`2000-01-01 ${endTime}`);
    return (end - start) / (1000 * 60 * 60); // Convert to hours
}

// Open image modal
function openImageModal(src, alt) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${alt}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <img src="${src}" alt="${alt}" class="img-fluid">
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    const bsModal = new window.bootstrap.Modal(modal);
    bsModal.show();

    modal.addEventListener('hidden.bs.modal', function() {
        document.body.removeChild(modal);
    });
}

// Show loading state for buttons
function showLoadingState(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="loading-spinner"></span> Loading...';
    button.disabled = true;

    // Reset after 10 seconds as fallback
    setTimeout(function() {
        button.innerHTML = originalText;
        button.disabled = false;
    }, 10000);
}

// Availability checker
function checkAvailability(turfId, date) {
    if (!date) return;

    fetch(`/turfs/${turfId}/availability/?date=${date}`)
        .then(response => response.json())
        .then(data => {
            updateAvailabilityDisplay(data.available_slots);
        })
        .catch(error => {
            console.error('Error checking availability:', error);
        });
}

// Update availability display
function updateAvailabilityDisplay(slots) {
    const container = document.querySelector('.availability-slots');
    if (!container) return;

    container.innerHTML = '';

    if (slots.length === 0) {
        container.innerHTML = '<p class="text-muted">No available slots for this date.</p>';
        return;
    }

    slots.forEach(slot => {
        const slotElement = document.createElement('div');
        slotElement.className = 'time-slot available';
        slotElement.dataset.startTime = slot.start_time;
        slotElement.dataset.endTime = slot.end_time;
        slotElement.dataset.price = slot.price;
        slotElement.innerHTML = `
            <div>${slot.start_time} - ${slot.end_time}</div>
            <small>₹${slot.price}</small>
        `;

        slotElement.addEventListener('click', function() {
            document.querySelectorAll('.time-slot.selected').forEach(s => {
                s.classList.remove('selected');
            });
            this.classList.add('selected');
            updateBookingSummary(slot.start_time, slot.end_time, slot.price);
        });

        container.appendChild(slotElement);
    });
}

// Razorpay payment integration
function initializeRazorpay(options) {
    const rzp = new window.Razorpay({
        key: options.key,
        amount: options.amount,
        currency: 'INR',
        order_id: options.order_id,
        name: 'TurfBooking',
        description: 'Turf Booking Payment',
        image: '/static/images/logo.png',
        handler: function(response) {
            // Send payment details to server
            fetch('/bookings/payment-success/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    razorpay_payment_id: response.razorpay_payment_id,
                    razorpay_order_id: response.razorpay_order_id,
                    razorpay_signature: response.razorpay_signature
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/bookings/';
                } else {
                    alert('Payment verification failed. Please contact support.');
                }
            });
        },
        prefill: {
            name: options.user_name,
            email: options.user_email,
            contact: options.user_phone
        },
        theme: {
            color: '#2c5530'
        }
    });

    rzp.open();
}

// Get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Lazy loading for images
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

// Service Worker registration for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(error) {
                console.log('ServiceWorker registration failed');
            });
    });
}