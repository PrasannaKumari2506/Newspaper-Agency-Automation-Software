from django.shortcuts import render, get_object_or_404, redirect  # ADD 'render' HERE
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.db.models import Count, Sum, Q, Avg
from django.views.decorators.csrf import csrf_exempt
from datetime import date, timedelta, datetime
import json
from django.contrib.auth import authenticate, login, logout  # ADD THESE IMPORTS
from django.http import JsonResponse,HttpResponse
from decimal import Decimal
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
import io
from datetime import datetime
from .models import *
from .forms import *
import logging
from .decorators import manager_required
from .decorators import manager_required, clerk_required, delivery_required, customer_required
from .services import NotificationService

logger = logging.getLogger(__name__)


def home(request):
    publications = Publication.objects.filter(is_available=True)[:8]
    return render(request, 'naas/home.html', {'publications': publications})

def customer_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None and hasattr(user, 'customer'):
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                return redirect('customer_dashboard')
            else:
                messages.error(request, 'Invalid customer credentials.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'naas/customer_login.html', {'form': form})

def customer_register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('customer_login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'naas/customer_register.html', {'form': form})

def employee_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None and hasattr(user, 'employee'):
                login(request, user)
                employee = user.employee
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                
                if employee.position == 'manager':
                    return redirect('manager_dashboard')
                elif employee.position == 'clerk':
                    return redirect('clerk_dashboard')
                elif employee.position == 'delivery':
                    return redirect('delivery_dashboard')
            else:
                messages.error(request, 'Invalid employee credentials.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'naas/employee_login.html', {'form': form})

def custom_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')

# Decorators for role-based access
def customer_required(function):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'customer'):
            return function(request, *args, **kwargs)
        messages.error(request, 'Please login as customer to access this page.')
        return redirect('customer_login')
    return wrapper

def manager_required(function):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'employee') and request.user.employee.position == 'manager':
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Manager privileges required.')
        return redirect('employee_login')
    return wrapper

def clerk_required(function):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'employee') and request.user.employee.position == 'clerk':
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Clerk privileges required.')
        return redirect('employee_login')
    return wrapper

def delivery_required(function):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'employee') and request.user.employee.position == 'delivery':
            return function(request, *args, **kwargs)
        messages.error(request, 'Access denied. Delivery person privileges required.')
        return redirect('employee_login')
    return wrapper

# Dashboard Views
@customer_required
def customer_dashboard(request):
    customer = request.user.customer
    subscriptions = Subscription.objects.filter(customer=customer).order_by('-created_at')
    payments = Payment.objects.filter(subscription__customer=customer).order_by('-payment_date')[:10]
    recent_deliveries = Delivery.objects.filter(subscription__customer=customer).order_by('-delivery_date')[:10]
    complaints = Complaint.objects.filter(customer=customer).order_by('-created_at')[:5]
    
    active_subscriptions = Subscription.objects.filter(
        customer=customer, 
        status='active'
    ).select_related('publication')
    
    # Get subscriptions with pause requests for display

    subscriptions_with_requests = Subscription.objects.filter(
        customer=customer,
        pause_status__in=['pending', 'approved', 'rejected']
    )
    my_complaints = Complaint.objects.filter(
        customer=customer
    ).order_by('-created_at')[:10]

    # Calculate stats
    total_deliveries_this_month = Delivery.objects.filter(
        subscription__customer=customer,
        delivery_date__month=date.today().month,
        delivery_date__year=date.today().year
    ).count()
    
    monthly_cost = sum(sub.publication.monthly_price for sub in active_subscriptions)
    
    upcoming_payment = Payment.objects.filter(
        subscription__customer=customer,
        payment_status='pending',
        due_date__gte=date.today()
    ).order_by('due_date').first()
    
    days_until_next_bill = (upcoming_payment.due_date - date.today()).days if upcoming_payment else 0
    
    current_balance = Payment.objects.filter(
        subscription__customer=customer,
        payment_status='pending'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'customer': customer,
        'my_complaints': my_complaints,

        'subscriptions': subscriptions,
        'active_subscriptions': active_subscriptions,
        'subscriptions_with_requests': subscriptions_with_requests,
        'payments': payments,
        'recent_deliveries': recent_deliveries,
        'complaints': complaints,
        'total_deliveries_this_month': total_deliveries_this_month,
        'monthly_cost': monthly_cost,
        'days_until_next_bill': days_until_next_bill,
        'current_balance': current_balance,
        'upcoming_payment': upcoming_payment,
    }
    return render(request, 'naas/customer_dashboard.html', context)

@manager_required
def manager_dashboard(request):
    manager = request.user.employee
    
    # Statistics
    total_customers = Customer.objects.count()
    total_subscriptions = Subscription.objects.filter(status='active').count()
    total_employees = Employee.objects.filter(is_active=True).count()
    total_delivery_persons = Employee.objects.filter(position='delivery', is_active=True).count()
    
    # Revenue stats
    monthly_revenue = Payment.objects.filter(
        payment_status='completed',
        payment_date__month=date.today().month,
        payment_date__year=date.today().year
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    expiring_subscriptions = Subscription.objects.filter(
        end_date__lte=date.today() + timedelta(days=7),
        status='active'
    ).count()
    
    pending_complaints = Complaint.objects.filter(status='open').count()
    pending_commissions = Commission.objects.filter(status='pending').count()
    
    # Recent activities
    recent_subscriptions = Subscription.objects.select_related('customer__user', 'publication').order_by('-created_at')[:10]
    recent_payments = Payment.objects.select_related('subscription__customer__user').filter(payment_status='completed').order_by('-payment_date')[:5]
    
    # Delivery data
    delivery_persons = Employee.objects.filter(position='delivery', is_active=True).select_related('user')
    
    # Get pending deliveries for today and future dates
    today = date.today()
    pending_deliveries = Delivery.objects.filter(
        delivery_status='pending',
        delivery_date__gte=today
    ).select_related(
        'subscription__customer__user', 
        'subscription__publication',
        'delivery_person__user'
    ).order_by('delivery_date')[:50]

    publications = Publication.objects.all().order_by('type', 'title')
    
    # Calculate some stats for publications
    publication_stats = {
        'total_publications': publications.count(),
        'active_publications': publications.filter(is_available=True).count(),
        'newspapers': publications.filter(type='newspaper').count(),
        'magazines': publications.filter(type='magazine').count(),
    }
    
    # Calculate today's deliveries count for each delivery person
    delivery_persons_with_counts = []
    for person in delivery_persons:
        todays_deliveries_count = Delivery.objects.filter(
            delivery_person=person,
            delivery_date=today,
            delivery_status='pending'
        ).count()
        delivery_persons_with_counts.append({
            'person': person,
            'todays_deliveries_count': todays_deliveries_count
        })
    
    # Handle delivery assignment form
    delivery_form = DeliveryAssignmentForm()
    if request.method == 'POST' and 'create_delivery' in request.POST:
        delivery_form = DeliveryAssignmentForm(request.POST)
        if delivery_form.is_valid():
            delivery = delivery_form.save(commit=False)
            delivery.delivery_status = 'pending'  # Set default status
            delivery.save()
            messages.success(request, f'Delivery scheduled successfully for {delivery.subscription.customer.user.get_full_name()}!')
            return redirect('manager_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    
    # Get active subscriptions for the form
    active_subscriptions = Subscription.objects.filter(status='active').select_related('customer__user', 'publication')
    
    commissions = Commission.objects.select_related(
        'delivery_person__user'
    ).all().order_by('-period_end_date', '-created_at')
    
    # Simple commission stats
    commission_stats = {
        'pending_commissions': commissions.filter(status='pending').count(),
        'approved_commissions': commissions.filter(status='approved').count(),
        'paid_commissions': commissions.filter(status='paid').count(),
        'total_pending_amount': commissions.filter(status='pending').aggregate(
            total=Sum('commission_amount')
        )['total'] or Decimal('0.00'),
        'total_approved_amount': commissions.filter(status='approved').aggregate(
            total=Sum('commission_amount')
        )['total'] or Decimal('0.00'),
        'total_paid_amount': commissions.filter(status='paid').aggregate(
            total=Sum('commission_amount')
        )['total'] or Decimal('0.00'),
    }
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    
    # Payment Collection Report Data
    payment_collection_data = Payment.objects.filter(
        payment_date__gte=thirty_days_ago
    ).values('payment_date').annotate(
        total_amount=Sum('amount'),
        payment_count=Count('payment_id')
    ).order_by('payment_date')
    
    # Calculate payment totals
    payment_totals = {
        'total_collected': sum(item['total_amount'] for item in payment_collection_data if item['total_amount']),
        'total_days': len(payment_collection_data),
        'total_payments': sum(item['payment_count'] for item in payment_collection_data if item['payment_count']),
    }
    
    # Commission Summary Report Data
    commission_summary_data = Commission.objects.values(
        'delivery_person__user__first_name', 
        'delivery_person__user__last_name'
    ).annotate(
        total_commission=Sum('commission_amount'),
        pending_commission=Sum('commission_amount', filter=Q(status='pending')),
        approved_commission=Sum('commission_amount', filter=Q(status='approved')),
        paid_commission=Sum('commission_amount', filter=Q(status='paid')),
        commission_count=Count('commission_id')
    ).order_by('delivery_person__user__first_name')
    
    # Calculate commission totals
    commission_totals = {
        'total_commission': sum(item['total_commission'] or 0 for item in commission_summary_data),
        'total_pending': sum(item['pending_commission'] or 0 for item in commission_summary_data),
        'total_approved': sum(item['approved_commission'] or 0 for item in commission_summary_data),
        'total_paid': sum(item['paid_commission'] or 0 for item in commission_summary_data),
        'total_records': sum(item['commission_count'] or 0 for item in commission_summary_data),
    }
    
    # Subscription Analytics Report Data - FIXED VERSION
    subscription_analytics_data = Subscription.objects.values(
        'publication__title',
        'publication__type'
    ).annotate(
        total_subscriptions=Count('subscription_id'),
        active_subscriptions=Count('subscription_id', filter=Q(status='active')),
        paused_subscriptions=Count('subscription_id', filter=Q(status='paused')),
        cancelled_subscriptions=Count('subscription_id', filter=Q(status='cancelled'))
    ).order_by('-total_subscriptions')
    
    # Calculate subscription totals and add active rates
    for item in subscription_analytics_data:
        if item['total_subscriptions'] > 0:
            item['active_rate'] = round((item['active_subscriptions'] / item['total_subscriptions']) * 100, 1)
        else:
            item['active_rate'] = 0
    
    subscription_totals = {
        'total_subscriptions': sum(item['total_subscriptions'] for item in subscription_analytics_data),
        'total_active': sum(item['active_subscriptions'] for item in subscription_analytics_data),
        'total_paused': sum(item['paused_subscriptions'] for item in subscription_analytics_data),
        'total_cancelled': sum(item['cancelled_subscriptions'] for item in subscription_analytics_data),
    }

    today = date.today()
    
    # Get customers for targeting
    customers = Customer.objects.filter(is_active=True).select_related('user')
    
    # Get recent notifications
    recent_notifications = Notification.objects.select_related('user').order_by('-sent_date')[:10]
    
    # Notification statistics
    notification_stats = {
        'total_sent': Notification.objects.count(),
        'sent_today': Notification.objects.filter(sent_date__date=today).count(),
        'unread_count': Notification.objects.filter(status='sent').count(),
        'payment_reminders': Notification.objects.filter(type='payment_reminder').count(),
    }
    
    # Get customers with overdue payments for targeting - FIXED QUERY
    customers_with_overdue = Customer.objects.filter(
        subscription__payment__payment_status='overdue'
    ).distinct().select_related('user')
    
    # Get customers with expiring subscriptions - FIXED QUERY
    customers_expiring_soon = Customer.objects.filter(
        subscription__end_date__lte=today + timedelta(days=7),
        subscription__status='active'
    ).distinct().select_related('user')


    context = {
        'user': request.user,
        'manager': manager,
        'total_customers': total_customers,
        'total_subscriptions': total_subscriptions,
        'total_employees': total_employees,
        'total_delivery_persons': total_delivery_persons,
        'monthly_revenue': monthly_revenue,
        'expiring_subscriptions': expiring_subscriptions,
        'pending_complaints': pending_complaints,
        'pending_commissions': pending_commissions,
        'recent_subscriptions': recent_subscriptions,
        'recent_payments': recent_payments,
        'delivery_persons': delivery_persons,
        'delivery_persons_with_counts': delivery_persons_with_counts,
        'pending_deliveries': pending_deliveries,
        'active_subscriptions': active_subscriptions,
        'publications': publications,
        'commissions': commissions,
        'commission_stats': commission_stats,
        'publication_stats': publication_stats,
        'delivery_form': delivery_form,
        'today': today.strftime('%Y-%m-%d'),
        'payment_collection_data': list(payment_collection_data),
        'payment_totals': payment_totals,
        'commission_summary_data': list(commission_summary_data),
        'commission_totals': commission_totals,
        'subscription_analytics_data': list(subscription_analytics_data),
        'subscription_totals': subscription_totals,        
        'today': today,
        'thirty_days_ago': thirty_days_ago,
        'customers': customers,
        'customers_with_overdue': customers_with_overdue,
        'customers_expiring_soon': customers_expiring_soon,
        'recent_notifications': recent_notifications,
        'notification_stats': notification_stats,

    }
    return render(request, 'naas/manager_dashboard.html', context)

@clerk_required
def clerk_dashboard(request):
    clerk = request.user.employee

    # Get pending payments
    pending_payments = Payment.objects.filter(payment_status='pending').select_related('subscription__customer__user')[:10]
    overdue_payments = Payment.objects.filter(payment_status='overdue')

    # Get open complaints
    open_complaints = Complaint.objects.filter(
        status='open'
    ).select_related('customer__user').order_by('created_at')
    
    # Get recently resolved complaints
    resolved_complaints = Complaint.objects.filter(
        status__in=['resolved', 'closed']
    ).select_related('customer__user', 'resolved_by__user').order_by('-updated_at')[:10]
    
    pending_pause_requests = Subscription.objects.filter(
        pause_status='pending',
        status='active'
    ).select_related('customer__user', 'publication').order_by('pause_requested_at')
    
    # Get currently active pauses
    today = date.today()
    active_pauses = Subscription.objects.filter(
        pause_status='approved',
        status='paused',
        pause_start_date__lte=today,
        pause_end_date__gte=today
    ).select_related('customer__user', 'publication')

    # Get paused subscriptions
    paused_subscriptions = Subscription.objects.filter(status='paused').select_related('customer__user', 'publication')[:10]
    
    active_subscribers = Subscription.objects.filter(status='active').count()

    # Today's stats
    today = date.today()
    today_payments = Payment.objects.filter(payment_date=today, payment_status='completed').count()
    today_complaints = Complaint.objects.filter(created_at__date=today).count()
    
    # Get completed payments for receipts - ADD THIS
    completed_payments = Payment.objects.filter(
        payment_status='completed'
    ).select_related(
        'subscription__customer__user', 
        'subscription__publication'
    ).order_by('-payment_date')[:20]

    pending_pause_requests = Subscription.objects.filter(
        pause_status='pending',
        status='active'
    ).select_related(
        'customer__user',
        'publication'
    ).order_by('pause_requested_at')
    


    # Get currently active pauses
    
    active_pauses = Subscription.objects.filter(
        pause_status='approved',
        status='paused',
        pause_start_date__lte=today,
        pause_end_date__gte=today
    ).select_related(
        'customer__user',
        'publication'
    )
    
    
    # Get all active customers and publications for the subscription form
    customers = Customer.objects.filter(is_active=True).select_related('user')
    publications = Publication.objects.filter(is_available=True)
    
    # Calculate dates for the form
    today_str = today.strftime('%Y-%m-%d')
    one_year_from_now = (today + timedelta(days=365)).strftime('%Y-%m-%d')
    
    # Calculate monthly revenue
    monthly_revenue = Payment.objects.filter(
        payment_date__month=today.month,
        payment_date__year=today.year,
        payment_status='completed'
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    context = {
        'user': request.user,
        'clerk': clerk,
        'pending_payments': pending_payments,
        'open_complaints': open_complaints,
        'resolved_complaints': resolved_complaints,
        'pending_pause_requests': pending_pause_requests,
        'active_pauses': active_pauses,
        'overdue_payments': overdue_payments,
        'paused_subscriptions': paused_subscriptions,
        'today_payments': today_payments,
        'today_complaints': today_complaints,
        'total_subscribers': active_subscribers,
        'monthly_revenue': monthly_revenue,
        'customers': customers,
        'publications': publications,
        'today': today_str,
        'one_year_from_now': one_year_from_now,
        'completed_payments': completed_payments,  # Add this line
        'subscriptions': Subscription.objects.all().select_related('customer__user', 'publication')[:50],
        'active_subscriptions': Subscription.objects.filter(status='active').select_related('customer__user', 'publication'),
        'recent_payments': Payment.objects.all().select_related('subscription__customer__user')[:10],
        'pending_pause_requests': pending_pause_requests,
        'active_pauses': active_pauses,
    }
    return render(request, 'naas/clerk_dashboard.html', context)

@delivery_required
def delivery_dashboard(request):
    delivery_person = request.user.employee
    
    # Today's deliveries
    today_deliveries = Delivery.objects.filter(
        delivery_person=delivery_person,
        delivery_date=date.today()
    ).select_related('subscription__customer__user', 'subscription__publication')
    
    completed_deliveries = today_deliveries.filter(delivery_status='completed').count()
    pending_deliveries = today_deliveries.filter(delivery_status='pending').count()
    
    # This month's stats
    month_start = date.today().replace(day=1)
    monthly_deliveries = Delivery.objects.filter(
        delivery_person=delivery_person,
        delivery_date__gte=month_start
    ).count()
    
    # Commission calculations for current month
    monthly_completed_deliveries = Delivery.objects.filter(
        delivery_person=delivery_person,
        delivery_date__gte=month_start,
        delivery_status='completed'
    )
    
    total_bill_amount = Decimal('0.00')
    for delivery in monthly_completed_deliveries:
        total_bill_amount += delivery.subscription.publication.monthly_price
    
    potential_commission = total_bill_amount * Decimal('0.025')
    
    # Commission history (last 6 months)
    commission_history = Commission.objects.filter(
        delivery_person=delivery_person
    ).order_by('-period_end_date')[:12]  # Last 12 commission records
    
    # Commission summary stats
    total_approved_commission = Commission.objects.filter(
        delivery_person=delivery_person,
        status='approved'
    ).aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')
    
    total_pending_commission = Commission.objects.filter(
        delivery_person=delivery_person,
        status='pending'
    ).aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')
    
    total_paid_commission = Commission.objects.filter(
        delivery_person=delivery_person,
        status='paid'
    ).aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')
    
    context = {
        'delivery_person': delivery_person,
        'today_deliveries': today_deliveries,
        'completed_deliveries': completed_deliveries,
        'pending_deliveries': pending_deliveries,
        'monthly_deliveries': monthly_deliveries,
        'potential_commission': potential_commission,
        'total_bill_amount': total_bill_amount,
        'commission_history': commission_history,
        'total_approved_commission': total_approved_commission,
        'total_pending_commission': total_pending_commission,
        'total_paid_commission': total_paid_commission,
        'month_start': month_start,
    }
    return render(request, 'naas/delivery_dashboard.html', context)

# Subscription Management
@customer_required
def subscribe(request):
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.customer = request.user.customer
            subscription.status = 'active'
            subscription.save()
            
            # Create initial payment
            due_date = date.today() + timedelta(days=30)
            Payment.objects.create(
                subscription=subscription,
                amount=subscription.publication.monthly_price,
                payment_date=date.today(),
                payment_method='cash',
                payment_status='pending',
                due_date=due_date
            )
            
            messages.success(request, f'Successfully subscribed to {subscription.publication.title}!')
            return redirect('customer_dashboard')
    else:
        form = SubscriptionForm()
    
    publications = Publication.objects.filter(is_available=True)
    return render(request, 'naas/subscribe.html', {'form': form, 'publications': publications})

@customer_required
def manage_subscription(request, subscription_id):
    subscription = get_object_or_404(Subscription, subscription_id=subscription_id, customer=request.user.customer)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'pause':
            subscription.status = 'paused'
            subscription.save()
            messages.success(request, 'Subscription paused successfully.')
        elif action == 'resume':
            subscription.status = 'active'
            subscription.save()
            messages.success(request, 'Subscription resumed successfully.')
        elif action == 'cancel':
            subscription.status = 'cancelled'
            subscription.save()
            messages.success(request, 'Subscription cancelled successfully.')
        
        return redirect('customer_dashboard')
    
    return render(request, 'naas/manage_subscription.html', {'subscription': subscription})

# Payment Management
@clerk_required
def record_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.payment_status = 'completed'
            payment.payment_date = date.today()
            payment.save()
            
            messages.success(request, f'Payment of ${payment.amount} recorded successfully!')
            return redirect('clerk_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentForm()
    
    pending_payments = Payment.objects.filter(payment_status='pending').select_related('subscription__customer__user')
    return render(request, 'naas/record_payment.html', {'form': form, 'pending_payments': pending_payments})

@customer_required
def make_payment(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id, subscription__customer=request.user.customer)
    
    if request.method == 'POST':
        payment.payment_status = 'completed'
        payment.payment_date = date.today()
        payment.payment_method = 'card'
        payment.save()
        
        messages.success(request, f'Payment of ${payment.amount} completed successfully!')
        return redirect('customer_dashboard')
    
    return render(request, 'naas/make_payment.html', {'payment': payment})

# Complaint Management
@customer_required
def submit_complaint(request):
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.customer = request.user.customer
            complaint.save()
            
            messages.success(request, 'Complaint submitted successfully! We will get back to you soon.')
            return redirect('customer_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ComplaintForm()
    
    return render(request, 'naas/submit_complaint.html', {'form': form})

@clerk_required
def resolve_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    
    if request.method == 'POST':
        resolution_notes = request.POST.get('resolution_notes')
        complaint.status = 'resolved'
        complaint.resolved_by = request.user.employee
        complaint.resolution_notes = resolution_notes
        complaint.save()
        
        messages.success(request, 'Complaint marked as resolved!')
        return redirect('clerk_dashboard')
    
    return render(request, 'naas/resolve_complaint.html', {'complaint': complaint})

# Delivery Management
@delivery_required
def mark_delivery_completed(request, delivery_id):
    delivery = get_object_or_404(Delivery, delivery_id=delivery_id, delivery_person=request.user.employee)
    
    if request.method == 'POST':
        delivery.delivery_status = 'completed'
        delivery.delivery_time = datetime.now().time()
        delivery.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Delivery marked as completed!'})
        else:
            messages.success(request, 'Delivery marked as completed!')
    
    return redirect('delivery_dashboard')

@delivery_required
def report_issue(request, delivery_id):
    delivery = get_object_or_404(Delivery, delivery_id=delivery_id, delivery_person=request.user.employee)
    
    if request.method == 'POST':
        form = IssueReportForm(request.POST)
        if form.is_valid():
            issue_report = form.save(commit=False)
            issue_report.delivery = delivery
            issue_report.reported_by = request.user.employee
            issue_report.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Issue reported successfully!'})
            else:
                messages.success(request, 'Issue reported successfully!')
                return redirect('delivery_dashboard')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = IssueReportForm()
    
    return render(request, 'naas/report_issue.html', {
        'form': form,
        'delivery': delivery
    })


# API Views for AJAX calls
@customer_required
def customer_dashboard_stats(request):
    customer = request.user.customer
    
    stats = {
        'active_subscriptions': Subscription.objects.filter(customer=customer, status='active').count(),
        'deliveries_this_month': Delivery.objects.filter(
            subscription__customer=customer,
            delivery_date__month=date.today().month,
            delivery_date__year=date.today().year
        ).count(),
        'monthly_cost': float(sum(
            sub.publication.monthly_price 
            for sub in Subscription.objects.filter(customer=customer, status='active')
        )),
        'current_balance': float(Payment.objects.filter(
            subscription__customer=customer,
            payment_status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0),
    }
    
    return JsonResponse(stats)

@customer_required
def refresh_subscriptions(request):
    customer = request.user.customer
    subscriptions = Subscription.objects.filter(customer=customer).order_by('-created_at')
    
    data = {
        'subscriptions': [
            {
                'id': str(sub.subscription_id),
                'publication_name': sub.publication.title,
                'start_date': sub.start_date.strftime('%Y-%m-%d'),
                'end_date': sub.end_date.strftime('%Y-%m-%d'),
                'monthly_price': float(sub.publication.monthly_price),
                'status': sub.status,
            }
            for sub in subscriptions
        ]
    }
    
    return JsonResponse(data)

@customer_required
def refresh_payments(request):
    customer = request.user.customer
    payments = Payment.objects.filter(subscription__customer=customer).order_by('-payment_date')[:10]
    
    data = {
        'payments': [
            {
                'billing_date': payment.payment_date.strftime('%Y-%m-%d'),
                'amount': float(payment.amount),
                'due_date': payment.due_date.strftime('%Y-%m-%d'),
                'status': payment.payment_status,
                'receipt_number': payment.receipt_number,
            }
            for payment in payments
        ]
    }
    
    return JsonResponse(data)

@customer_required
def pause_delivery(request):
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')

        # Assuming customer is logged in
        customer = request.user.customer
        subscription = Subscription.objects.filter(customer=customer, status='active').first()

        if subscription:
            PauseRequest.objects.create(
                customer=customer,
                subscription=subscription,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
            )
            messages.success(request, 'Your request has been sent to the clerk for approval.')
        else:
            messages.error(request, 'No active subscription found.')

    return redirect('customer_dashboard')


# Manager specific views
@manager_required
def manage_employees(request):
    employees = Employee.objects.select_related('user').all()
    return render(request, 'naas/manage_employees.html', {'employees': employees})

@manager_required
def generate_reports(request):
    report_type = request.GET.get('type', 'subscriptions')
    
    if report_type == 'subscriptions':
        data = Subscription.objects.values('publication__title').annotate(
            count=Count('subscription_id'),
            total_revenue=Sum('publication__monthly_price')
        )
    elif report_type == 'payments':
        data = Payment.objects.filter(payment_status='completed').extra(
            {'month': "strftime('%Y-%m', payment_date)"}
        ).values('month').annotate(
            total_amount=Sum('amount'),
            payment_count=Count('payment_id')
        )
    elif report_type == 'deliveries':
        data = Delivery.objects.extra(
            {'date': "delivery_date"}
        ).values('date').annotate(
            completed=Count('delivery_id', filter=Q(delivery_status='completed')),
            total=Count('delivery_id')
        )
    
    return render(request, 'naas/reports.html', {'report_type': report_type, 'data': data})

# Data initialization view (for demo purposes)
def initialize_sample_data(request):
    if not request.user.is_superuser:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Create sample publications
    publications_data = [
        {'title': 'The Daily Times', 'type': 'newspaper', 'monthly_price': 30.00, 'frequency': 'daily', 'publisher': 'Times Media'},
        {'title': 'Business Chronicle', 'type': 'newspaper', 'monthly_price': 45.00, 'frequency': 'daily', 'publisher': 'Business Press'},
        {'title': 'Sunday Herald', 'type': 'newspaper', 'monthly_price': 20.00, 'frequency': 'weekly', 'publisher': 'Herald Group'},
        {'title': 'Tech Magazine', 'type': 'magazine', 'monthly_price': 25.00, 'frequency': 'monthly', 'publisher': 'Tech Media'},
        {'title': 'Sports Weekly', 'type': 'magazine', 'monthly_price': 35.00, 'frequency': 'weekly', 'publisher': 'Sports Network'},
    ]
    
    for pub_data in publications_data:
        Publication.objects.get_or_create(
            title=pub_data['title'],
            defaults=pub_data
        )
    
    messages.success(request, 'Sample data initialized successfully!')
    return redirect('admin:index')



#clerk
@clerk_required
def pause_subscription(request):
    if request.method == 'POST':
        subscription_id = request.POST.get('subscription')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')
        
        try:
            subscription = Subscription.objects.get(subscription_id=subscription_id)
            subscription.status = 'paused'
            subscription.save()
            
            messages.success(request, f'Subscription for {subscription.customer.user.get_full_name()} has been paused successfully.')
        except Subscription.DoesNotExist:
            messages.error(request, 'Subscription not found.')
        
        return redirect('clerk_dashboard')
    
    return redirect('clerk_dashboard')

@clerk_required
def resume_subscription(request, subscription_id):
    try:
        subscription = Subscription.objects.get(subscription_id=subscription_id)
        subscription.status = 'active'
        subscription.save()
        
        messages.success(request, f'Subscription for {subscription.customer.user.get_full_name()} has been resumed successfully.')
    except Subscription.DoesNotExist:
        messages.error(request, 'Subscription not found.')
    
    return redirect('clerk_dashboard')

@clerk_required
def record_payment(request):
    if request.method == 'POST':
        subscription_id = request.POST.get('subscription')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        due_date = request.POST.get('due_date')
        
        try:
            subscription = Subscription.objects.get(subscription_id=subscription_id)
            
            payment = Payment(
                subscription=subscription,
                amount=amount,
                payment_method=payment_method,
                due_date=due_date,
                payment_status='completed'
            )
            payment.save()
            
            messages.success(request, f'Payment of ${amount} recorded successfully for {subscription.customer.user.get_full_name()}.')
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')
        
        return redirect('clerk_dashboard')
    
    return redirect('clerk_dashboard')

@clerk_required
def resolve_complaint(request, complaint_id):
    if request.method == 'POST':
        resolution_notes = request.POST.get('resolution_notes')
        
        try:
            complaint = Complaint.objects.get(id=complaint_id)
            complaint.status = 'resolved'
            complaint.resolution_notes = resolution_notes
            complaint.resolved_at = timezone.now()
            complaint.resolved_by = request.user
            complaint.save()
            
            messages.success(request, 'Complaint resolved successfully.')
        except Complaint.DoesNotExist:
            messages.error(request, 'Complaint not found.')
        
        return redirect('clerk_dashboard')
    
    return redirect('clerk_dashboard')

@clerk_required
def add_subscription(request):
    if request.method == 'POST':
        try:
            customer_id = request.POST.get('customer')
            publication_id = request.POST.get('publication')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            delivery_address = request.POST.get('delivery_address')
            quantity = int(request.POST.get('quantity', 1))
            payment_plan = request.POST.get('payment_plan', 'monthly')
            
            print(f"Customer ID: {customer_id}")  # Debug
            print(f"Publication ID: {publication_id}")  # Debug
            
            # Get customer and publication objects
            customer = Customer.objects.get(customer_id=customer_id)
            publication = Publication.objects.get(publication_id=publication_id)
            
            # Create the subscription
            subscription = Subscription.objects.create(
                customer=customer,
                publication=publication,
                start_date=start_date,
                end_date=end_date,
                delivery_address=delivery_address,
                quantity=quantity,
                status='active'
            )
            
            # Create initial payment if requested
            if request.POST.get('create_initial_payment'):
                # Calculate amount based on publication price and payment plan
                amount = publication.monthly_price
                
                if payment_plan == 'quarterly':
                    amount = publication.monthly_price * 3
                elif payment_plan == 'yearly':
                    amount = publication.monthly_price * 12
                
                Payment.objects.create(
                    subscription=subscription,
                    amount=amount,
                    payment_method='cash',  # Default method
                    payment_status='pending',
                    due_date=start_date
                )
            
            messages.success(request, f'Subscription created successfully for {customer.user.get_full_name()}')
            
        except Customer.DoesNotExist:
            messages.error(request, 'Selected customer does not exist')
            print(f"Customer with ID {customer_id} not found")  # Debug
        except Publication.DoesNotExist:
            messages.error(request, 'Selected publication does not exist')
            print(f"Publication with ID {publication_id} not found")  # Debug
        except Exception as e:
            messages.error(request, f'Error creating subscription: {str(e)}')
            print(f"Error: {str(e)}")  # Debug
            import traceback
            traceback.print_exc()  # This will print the full traceback
    
    return redirect('clerk_dashboard')


def download_receipt(request, payment_id):
    try:
        # Convert string to UUID if needed
        if isinstance(payment_id, str):
            payment_id = uuid.UUID(payment_id)
            
        payment = Payment.objects.select_related(
            'subscription__customer__user', 
            'subscription__publication'
        ).get(payment_id=payment_id)
        
        # Create buffer for PDF
        buffer = io.BytesIO()
        
        # Create PDF
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Set up receipt content
        y = height - inch
        
        # Header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(inch, y, "NEWSEXPRESS - PAYMENT RECEIPT")
        y -= 0.5 * inch
        
        # Receipt info
        p.setFont("Helvetica", 10)
        p.drawString(inch, y, f"Receipt Number: {payment.receipt_number}")
        y -= 0.25 * inch
        p.drawString(inch, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        y -= 0.5 * inch
        
        # Customer Information
        p.setFont("Helvetica-Bold", 12)
        p.drawString(inch, y, "Customer Information:")
        y -= 0.25 * inch
        p.setFont("Helvetica", 10)
        customer_name = payment.subscription.customer.user.get_full_name()
        p.drawString(inch, y, f"Name: {customer_name}")
        y -= 0.25 * inch
        p.drawString(inch, y, f"Email: {payment.subscription.customer.user.email}")
        y -= 0.5 * inch
        
        # Payment Details
        p.setFont("Helvetica-Bold", 12)
        p.drawString(inch, y, "Payment Details:")
        y -= 0.25 * inch
        p.setFont("Helvetica", 10)
        p.drawString(inch, y, f"Publication: {payment.subscription.publication.title}")
        y -= 0.25 * inch
        p.drawString(inch, y, f"Amount: ${payment.amount}")
        y -= 0.25 * inch
        p.drawString(inch, y, f"Payment Method: {payment.payment_method.title()}")
        y -= 0.25 * inch
        p.drawString(inch, y, f"Payment Date: {payment.payment_date.strftime('%Y-%m-%d')}")
        y -= 0.25 * inch
        p.drawString(inch, y, f"Status: {payment.payment_status.title()}")
        
        # Footer
        p.setFont("Helvetica-Oblique", 8)
        p.drawString(inch, 0.75 * inch, "Thank you for your business!")
        p.drawString(inch, 0.5 * inch, "This is a computer-generated receipt.")
        
        # Save PDF
        p.showPage()
        p.save()
        
        # Get the value of the BytesIO buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        # Create HttpResponse
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{payment.receipt_number}.pdf"'
        response['Content-Length'] = len(pdf)
        response.write(pdf)
        
        return response
        
    except Payment.DoesNotExist:
        messages.error(request, "Payment not found")
        return redirect('clerk_dashboard')
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")  # Check your console for this error
        messages.error(request, f"Error generating receipt: {str(e)}")
        return redirect('clerk_dashboard')

@customer_required
def request_pause(request):
    if request.method == 'POST':
        try:
            subscription_id = request.POST.get('subscription')
            pause_start_date = request.POST.get('pause_start_date')
            pause_end_date = request.POST.get('pause_end_date')
            pause_reason = request.POST.get('pause_reason')
            pause_notes = request.POST.get('pause_notes', '')
            
            # Validate dates
            start_date_obj = datetime.strptime(pause_start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(pause_end_date, '%Y-%m-%d').date()
            today = date.today()
            
            if start_date_obj <= today:
                messages.error(request, "Pause start date must be in the future")
                return redirect('customer_dashboard')
            
            if start_date_obj >= end_date_obj:
                messages.error(request, "End date must be after start date")
                return redirect('customer_dashboard')
            
            # Check if pause period is reasonable
            pause_days = (end_date_obj - start_date_obj).days
            if pause_days < 3:
                messages.error(request, "Minimum pause period is 3 days")
                return redirect('customer_dashboard')
            if pause_days > 30:
                messages.error(request, "Maximum pause period is 30 days")
                return redirect('customer_dashboard')
            
            # Get subscription and verify it belongs to customer and is active
            subscription = Subscription.objects.get(
                subscription_id=subscription_id,
                customer=request.user.customer,
                status='active'
            )
            
            # Check if subscription already has a pending request
            if subscription.pause_status == 'pending':
                messages.error(request, "You already have a pending pause request for this subscription")
                return redirect('customer_dashboard')
            
            # Update subscription with pause request
            subscription.pause_status = 'pending'
            subscription.pause_start_date = start_date_obj
            subscription.pause_end_date = end_date_obj
            subscription.pause_reason = pause_reason
            subscription.pause_notes = pause_notes
            subscription.pause_requested_at = timezone.now()
            subscription.save()
            
            messages.success(request, "Pause request submitted successfully! It will be processed within 24-48 hours.")
            
        except Subscription.DoesNotExist:
            messages.error(request, "Invalid subscription selected")
        except Exception as e:
            messages.error(request, f"Error submitting pause request: {str(e)}")
    
    return redirect('customer_dashboard')

@clerk_required
def approve_pause_request(request, subscription_id):
    try:
        subscription = Subscription.objects.get(
            subscription_id=subscription_id,
            pause_status='pending',
            status='active'
        )
        
        # Calculate pause duration and extend subscription end date
        pause_duration = (subscription.pause_end_date - subscription.pause_start_date).days
        new_end_date = subscription.end_date + timedelta(days=pause_duration)
        
        # Update subscription
        subscription.pause_status = 'approved'
        subscription.status = 'paused'
        subscription.end_date = new_end_date
        subscription.pause_processed_at = timezone.now()
        subscription.pause_processed_by = request.user.employee
        subscription.save()
        
        messages.success(request, f"Pause request approved for {subscription.customer.user.get_full_name}")
        
    except Subscription.DoesNotExist:
        messages.error(request, "Pause request not found or already processed")
    
    return redirect('clerk_dashboard')

@clerk_required
def reject_pause_request(request, subscription_id):
    try:
        subscription = Subscription.objects.get(
            subscription_id=subscription_id,
            pause_status='pending'
        )
        
        # Update subscription - reset pause fields but keep history
        subscription.pause_status = 'rejected'
        subscription.pause_processed_at = timezone.now()
        subscription.pause_processed_by = request.user.employee
        subscription.save()
        
        messages.success(request, f"Pause request rejected for {subscription.customer.user.get_full_name}")
        
    except Subscription.DoesNotExist:
        messages.error(request, "Pause request not found or already processed")
    
    return redirect('clerk_dashboard')


@customer_required
def submit_complaint(request):
    if request.method == 'POST':
        try:
            subject = request.POST.get('subject')
            description = request.POST.get('description')
            
            # Create complaint
            complaint = Complaint.objects.create(
                customer=request.user.customer,
                subject=subject,
                description=description,
                status='open'
            )
            
            messages.success(request, "Your complaint has been submitted successfully! We'll get back to you soon.")
            
        except Exception as e:
            messages.error(request, f"Error submitting complaint: {str(e)}")
    
    return redirect('customer_dashboard')

@clerk_required
def resolve_complaint(request, complaint_id):
    if request.method == 'POST':
        try:
            resolution_notes = request.POST.get('resolution_notes')
            
            complaint = Complaint.objects.get(
                complaint_id=complaint_id,
                status='open'
            )
            
            # Update complaint
            complaint.status = 'resolved'
            complaint.resolution_notes = resolution_notes
            complaint.resolved_by = request.user.employee
            complaint.save()
            
            messages.success(request, f"Complaint resolved successfully for {complaint.customer.user.get_full_name}")
            
        except Complaint.DoesNotExist:
            messages.error(request, "Complaint not found or already resolved")
        except Exception as e:
            messages.error(request, f"Error resolving complaint: {str(e)}")
    
    return redirect('clerk_dashboard')


#manager
@manager_required
def all_subscriptions(request):
    """View to display all subscriptions for manager"""
    subscriptions = Subscription.objects.select_related(
        'customer__user', 
        'publication'
    ).order_by('-created_at')
    
    # Filter parameters
    status_filter = request.GET.get('status', '')
    if status_filter:
        subscriptions = subscriptions.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        subscriptions = subscriptions.filter(
            Q(customer__user__first_name__icontains=search_query) |
            Q(customer__user__last_name__icontains=search_query) |
            Q(publication__title__icontains=search_query) |
            Q(delivery_address__icontains=search_query)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(subscriptions, 20)  # 20 subscriptions per page
    
    try:
        subscriptions_page = paginator.page(page)
    except PageNotAnInteger:
        subscriptions_page = paginator.page(1)
    except EmptyPage:
        subscriptions_page = paginator.page(paginator.num_pages)
    
    # Statistics for the page
    total_subscriptions = subscriptions.count()
    active_subscriptions = subscriptions.filter(status='active').count()
    paused_subscriptions = subscriptions.filter(status='paused').count()
    cancelled_subscriptions = subscriptions.filter(status='cancelled').count()
    
    context = {
        'subscriptions': subscriptions_page,
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'paused_subscriptions': paused_subscriptions,
        'cancelled_subscriptions': cancelled_subscriptions,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'naas/all_subscriptions.html', context)

@manager_required
@csrf_exempt
def assign_delivery_person(request):
    if request.method == 'POST':
        try:
            # Check if it's JSON data or form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
            
            delivery_id = data.get('delivery_id')
            delivery_person_id = data.get('delivery_person_id')
            delivery_date = data.get('delivery_date')
            
            print(f"Received data: delivery_id={delivery_id}, delivery_person_id={delivery_person_id}, delivery_date={delivery_date}")  # Debug
            
            # Validate required fields
            if not delivery_id:
                return JsonResponse({'success': False, 'error': 'Delivery ID is required'})
            
            if not delivery_person_id:
                return JsonResponse({'success': False, 'error': 'Delivery person is required'})
            
            # Get delivery and delivery person
            try:
                delivery = Delivery.objects.get(delivery_id=delivery_id)
                delivery_person = Employee.objects.get(employee_id=delivery_person_id, position='delivery')
            except Delivery.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Delivery not found'})
            except Employee.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Delivery person not found or not a delivery employee'})
            
            # Update delivery
            delivery.delivery_person = delivery_person
            if delivery_date:
                try:
                    delivery.delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid date format'})
            
            delivery.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Delivery assigned to {delivery_person.user.get_full_name()} successfully!',
                'delivery_person_name': delivery_person.user.get_full_name()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            print(f"Error in assign_delivery_person: {str(e)}")  # Debug
            return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@manager_required
@csrf_exempt
def add_publication(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['title', 'type', 'monthly_price', 'frequency', 'publisher']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({'success': False, 'error': f'{field.replace("_", " ").title()} is required'})
            
            # Create publication
            publication = Publication(
                title=data['title'],
                type=data['type'],
                monthly_price=Decimal(data['monthly_price']),
                frequency=data['frequency'],
                publisher=data['publisher'],
                description=data.get('description', ''),
                image_url=data.get('image_url', ''),
                is_available=data.get('is_available', True)
            )
            publication.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Publication "{publication.title}" added successfully!',
                'publication_id': publication.publication_id
            })
            
        except Exception as e:
            logger.error(f"Error adding publication: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@manager_required
@csrf_exempt
def toggle_publication_availability(request, publication_id):
    if request.method == 'POST':
        try:
            publication = get_object_or_404(Publication, publication_id=publication_id)
            data = json.loads(request.body)
            new_status = data.get('is_available', not publication.is_available)
            
            publication.is_available = new_status
            publication.save()
            
            status_text = "activated" if new_status else "deactivated"
            return JsonResponse({
                'success': True,
                'message': f'Publication "{publication.title}" {status_text} successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@manager_required
@csrf_exempt
def delete_publication(request, publication_id):
    if request.method == 'DELETE':
        try:
            publication = get_object_or_404(Publication, publication_id=publication_id)
            
            # Check if publication has active subscriptions
            active_subscriptions = Subscription.objects.filter(
                publication=publication, 
                status='active'
            ).exists()
            
            if active_subscriptions:
                return JsonResponse({
                    'success': False, 
                    'error': 'Cannot delete publication with active subscriptions'
                })
            
            publication_title = publication.title
            publication.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Publication "{publication_title}" deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

""" @manager_required
@csrf_exempt
def generate_commissions(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            period_end_date = data.get('period_end_date', date.today().isoformat())
            
            # Calculate period (typically monthly)
            try:
                period_end = datetime.strptime(period_end_date, '%Y-%m-%d').date()
                period_start = period_end.replace(day=1)  # Start of month
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'})
            
            # Get all active delivery persons
            delivery_persons = Employee.objects.filter(position='delivery', is_active=True)
            
            commissions_created = 0
            commissions_updated = 0
            commission_details = []
            
            for person in delivery_persons:
                # Get completed deliveries for this period
                deliveries = Delivery.objects.filter(
                    delivery_person=person,
                    delivery_date__range=[period_start, period_end],
                    delivery_status='completed'
                )
                
                total_deliveries = deliveries.count()
                
                if total_deliveries > 0:
                    # Calculate commission (example: $2 per delivery)
                    commission_rate = Decimal('2.00')
                    commission_amount = total_deliveries * commission_rate
                    
                    # Create or update commission record
                    commission, created = Commission.objects.get_or_create(
                        delivery_person=person,
                        period_start_date=period_start,
                        period_end_date=period_end,
                        defaults={
                            'total_deliveries': total_deliveries,
                            'commission_amount': commission_amount,
                            'status': 'pending'
                        }
                    )
                    
                    if not created:
                        # Update existing commission
                        commission.total_deliveries = total_deliveries
                        commission.commission_amount = commission_amount
                        commission.status = 'pending'  # Reset status for new calculation
                        commission.save()
                        commissions_updated += 1
                    else:
                        commissions_created += 1
                    
                    commission_details.append({
                        'delivery_person': person.user.get_full_name(),
                        'deliveries': total_deliveries,
                        'amount': float(commission_amount),
                        'created': created
                    })
            
            return JsonResponse({
                'success': True,
                'message': f'Commissions generated! {commissions_created} created, {commissions_updated} updated for {len(delivery_persons)} delivery persons.',
                'commissions_created': commissions_created,
                'commissions_updated': commissions_updated,
                'total_delivery_persons': len(delivery_persons),
                'period': f'{period_start} to {period_end}',
                'details': commission_details
            })
            
        except Exception as e:
            logger.error(f"Error generating commissions: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
 """
@manager_required
@csrf_exempt
def update_commission_status(request, commission_id):
    if request.method == 'POST':
        try:
            commission = get_object_or_404(Commission, commission_id=commission_id)
            data = json.loads(request.body)
            new_status = data.get('status')
            
            valid_statuses = ['pending', 'approved', 'paid', 'rejected']
            if new_status not in valid_statuses:
                return JsonResponse({'success': False, 'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'})
            
            # Store old status for message
            old_status = commission.status
            commission.status = new_status
            commission.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Commission status updated from {old_status} to {new_status} successfully!',
                'commission_id': str(commission_id),
                'delivery_person': commission.delivery_person.user.get_full_name(),
                'old_status': old_status,
                'new_status': new_status,
                'amount': float(commission.commission_amount)
            })
            
        except Commission.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Commission not found'})
        except Exception as e:
            logger.error(f"Error updating commission status: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@manager_required
@csrf_exempt
def update_commission_status(request, commission_id):
    if request.method == 'POST':
        try:
            commission = get_object_or_404(Commission, commission_id=commission_id)
            data = json.loads(request.body)
            new_status = data.get('status')
            
            if new_status not in ['pending', 'approved', 'paid', 'rejected']:
                return JsonResponse({'success': False, 'error': 'Invalid status'})
            
            commission.status = new_status
            commission.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Commission status updated to {new_status} successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@manager_required
def download_report_pdf(request, report_type):
    try:
        # Validate report type
        valid_report_types = ['payment', 'commission', 'subscription']
        if report_type not in valid_report_types:
            return JsonResponse({'success': False, 'error': 'Invalid report type'})

        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()
        
        # Create the PDF object
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        today = date.today()
        report_title = f"NewsExpress - {report_type.replace('_', ' ').title()} Report"
        
        # Add title
        title = Paragraph(report_title, styles['Heading1'])
        story.append(title)
        story.append(Paragraph(f"Generated on: {today}", styles['Normal']))
        story.append(Paragraph("<br/>", styles['Normal']))
        
        if report_type == 'payment':
            # Payment Collection Report Data
            thirty_days_ago = today - timedelta(days=30)
            payment_data = Payment.objects.filter(
                payment_date__gte=thirty_days_ago
            ).values('payment_date').annotate(
                total_amount=Sum('amount'),
                payment_count=Count('payment_id')
            ).order_by('payment_date')
            
            # Create table data
            table_data = [['Date', 'Total Amount', 'Number of Payments', 'Average Payment']]
            
            for payment_day in payment_data:
                avg_payment = payment_day['total_amount'] / payment_day['payment_count'] if payment_day['payment_count'] > 0 else 0
                table_data.append([
                    payment_day['payment_date'].strftime('%Y-%m-%d'),
                    f"${payment_day['total_amount']:.2f}",
                    str(payment_day['payment_count']),
                    f"${avg_payment:.2f}"
                ])
            
        elif report_type == 'commission':
            # Commission Summary Report Data
            commission_data = Commission.objects.values(
                'delivery_person__user__first_name', 
                'delivery_person__user__last_name'
            ).annotate(
                total_commission=Sum('commission_amount'),
                pending_commission=Sum('commission_amount', filter=Q(status='pending')),
                approved_commission=Sum('commission_amount', filter=Q(status='approved')),
                paid_commission=Sum('commission_amount', filter=Q(status='paid')),
                commission_count=Count('commission_id')
            ).order_by('delivery_person__user__first_name')
            
            table_data = [['Delivery Person', 'Total Commission', 'Pending', 'Approved', 'Paid', 'Records']]
            
            for commission in commission_data:
                table_data.append([
                    f"{commission['delivery_person__user__first_name']} {commission['delivery_person__user__last_name']}",
                    f"${commission['total_commission'] or 0:.2f}",
                    f"${commission['pending_commission'] or 0:.2f}",
                    f"${commission['approved_commission'] or 0:.2f}",
                    f"${commission['paid_commission'] or 0:.2f}",
                    str(commission['commission_count'] or 0)
                ])
            
        elif report_type == 'subscription':
            # Subscription Analytics Report Data
            subscription_data = Subscription.objects.values(
                'publication__title',
                'publication__type'
            ).annotate(
                total_subscriptions=Count('subscription_id'),
                active_subscriptions=Count('subscription_id', filter=Q(status='active')),
                paused_subscriptions=Count('subscription_id', filter=Q(status='paused')),
                cancelled_subscriptions=Count('subscription_id', filter=Q(status='cancelled'))
            ).order_by('-total_subscriptions')
            
            table_data = [['Publication', 'Type', 'Total', 'Active', 'Paused', 'Cancelled', 'Active Rate']]
            
            for subscription in subscription_data:
                active_rate = (subscription['active_subscriptions'] / subscription['total_subscriptions'] * 100) if subscription['total_subscriptions'] > 0 else 0
                table_data.append([
                    subscription['publication__title'],
                    subscription['publication__type'],
                    str(subscription['total_subscriptions']),
                    str(subscription['active_subscriptions']),
                    str(subscription['paused_subscriptions']),
                    str(subscription['cancelled_subscriptions']),
                    f"{active_rate:.1f}%"
                ])
        
        # Create table
        if len(table_data) > 1:
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No data available for the selected report.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF value from buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        # Create HTTP response with PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{today}.pdf"'
        response['Content-Length'] = len(pdf)
        response.write(pdf)
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating PDF report: {str(e)}")
        
        # Return JSON error for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
        # Return simple error message for direct requests
        return HttpResponse(f"Error generating report: {str(e)}", status=500)
""" @manager_required
@csrf_exempt
def delete_delivery(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            delivery_id = data.get('delivery_id')
            
            if not delivery_id:
                return JsonResponse({'success': False, 'error': 'Delivery ID is required'})
            
            delivery = get_object_or_404(Delivery, delivery_id=delivery_id)
            customer_name = delivery.subscription.customer.user.get_full_name()
            delivery.delete()
            
            return JsonResponse({
                'success': True, 
                'message': f'Delivery for {customer_name} deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
 """

@manager_required
@csrf_exempt
def send_notification(request):
    if request.method == 'POST':
        try:
            # Parse JSON data
            data = json.loads(request.body)
            notification_type = data.get('notification_type')
            target_audience = data.get('target_audience')
            subject = data.get('subject')
            message = data.get('message')
            specific_customers = data.get('specific_customers', [])
            channels = data.get('channels', ['in_app'])  # Default to in-app only
            
            print(f"Received notification request: {notification_type}, {target_audience}, channels: {channels}")
            
            # Validate required fields
            if not all([notification_type, target_audience, subject, message]):
                return JsonResponse({
                    'success': False, 
                    'error': 'All fields (notification_type, target_audience, subject, message) are required'
                })
            
            if not channels:
                return JsonResponse({
                    'success': False,
                    'error': 'At least one delivery channel must be selected'
                })
            
            # Get target customers based on audience selection
            if target_audience == 'all_customers':
                customers = Customer.objects.filter(is_active=True)
            elif target_audience == 'overdue_payments':
                customers = Customer.objects.filter(
                    subscription__payment__payment_status='overdue'
                ).distinct()
            elif target_audience == 'expiring_subscriptions':
                customers = Customer.objects.filter(
                    subscription__end_date__lte=date.today() + timedelta(days=7),
                    subscription__status='active'
                ).distinct()
            elif target_audience == 'specific_customers':
                if not specific_customers:
                    return JsonResponse({
                        'success': False, 
                        'error': 'No specific customers selected'
                    })
                customers = Customer.objects.filter(
                    customer_id__in=specific_customers
                )
            else:
                return JsonResponse({
                    'success': False, 
                    'error': 'Invalid target audience'
                })
            
            # Convert to list to avoid multiple database queries
            customers_list = list(customers)
            
            if not customers_list:
                return JsonResponse({
                    'success': False, 
                    'error': 'No customers found for the selected audience'
                })
            
            print(f"Found {len(customers_list)} customers to notify")
            
            # Send notifications using the service
            results = {
                'total_customers': len(customers_list),
                'successful': 0,
                'failed': 0,
                'details': []
            }
            
            # Create notifications for each customer
            for customer in customers_list:
                try:
                    # Create notification record
                    notification = Notification.objects.create(
                        user=customer.user,
                        type=notification_type,
                        subject=subject,
                        message=message,
                        status='sent'
                    )
                    
                    # Here you would integrate with actual email/SMS services
                    # For now, we'll just create the notification record
                    
                    results['successful'] += 1
                    results['details'].append({
                        'customer': customer.user.get_full_name(),
                        'status': 'sent',
                        'channels': channels
                    })
                    
                    print(f"Notification created for {customer.user.get_full_name()}")
                    
                except Exception as e:
                    results['failed'] += 1
                    results['details'].append({
                        'customer': customer.user.get_full_name() if customer.user else 'Unknown',
                        'status': 'failed',
                        'error': str(e)
                    })
                    print(f"Failed to create notification for {customer.user.get_full_name()}: {str(e)}")
            
            # Log the notification campaign
            logger.info(f"Notification campaign completed: {results['successful']} successful, {results['failed']} failed")
            
            return JsonResponse({
                'success': True,
                'message': f'Notifications sent successfully! {results["successful"]} delivered, {results["failed"]} failed',
                'recipient_count': results['total_customers'],
                'successful_count': results['successful'],
                'failed_count': results['failed'],
                'details': results['details'][:10]  # Return first 10 details to avoid large response
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False, 
                'error': 'Invalid JSON data'
            })
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False, 
        'error': 'Invalid request method'
    })


@manager_required
def manage_employees(request):
    """View for managing employees"""
    employees = Employee.objects.select_related('user').all()
    context = {
        'employees': employees
    }
    return render(request, 'naas/manage_employees.html', context)

@manager_required
def generate_reports(request):
    """View for generating reports"""
    context = {
        'report_types': ['payment', 'commission', 'subscription', 'employee']
    }
    return render(request, 'naas/generate_reports.html', context)

@clerk_required
def download_receipt(request, payment_id):
    """Download payment receipt"""
    payment = get_object_or_404(Payment, payment_id=payment_id)
    # Implement receipt download logic
    return JsonResponse({'success': True, 'message': 'Receipt download functionality'})

# Add other missing view functions as needed

def upload_image(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'upload.html', {'form': form})

def product_list(request):
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products})

def home(request):
    context = {
        'hero_image_url': 'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80',
        'publications': Publication.objects.filter(is_available=True)[:8]  # Show only 8 publications
    }
    return render(request, 'naas/home.html', context)

from django.utils import timezone
from django.db.models import Q

def assign_deliveries_view(request):
    today = timezone.now().date()
    
    # Get unassigned deliveries for today and future dates
    unassigned_deliveries = Delivery.objects.filter(
        delivery_person__isnull=True,
        delivery_date__gte=today,
        delivery_status='pending'
    ).select_related(
        'subscription__customer__user',
        'subscription__publication'
    )
    
    # Get delivery persons
    delivery_persons = Employee.objects.filter(position='delivery')
    
    # Get today's deliveries count for each delivery person
    delivery_persons_with_counts = []
    for person in delivery_persons:
        todays_deliveries_count = Delivery.objects.filter(
            delivery_person=person,
            delivery_date=today
        ).count()
        delivery_persons_with_counts.append({
            'person': person,
            'todays_deliveries_count': todays_deliveries_count
        })
    
    context = {
        'unassigned_deliveries': unassigned_deliveries,
        'delivery_persons': delivery_persons,
        'delivery_persons_with_counts': delivery_persons_with_counts,
        'today': today,
    }
    
    return render(request, 'your_template.html', context)


@csrf_exempt
def bulk_create_deliveries(request):
    try:
        data = json.loads(request.body)
        subscription_ids = data.get('subscription_ids', [])
        delivery_person_id = data.get('delivery_person_id')
        delivery_date = data.get('delivery_date')
        
        if not subscription_ids or not delivery_person_id:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        delivery_person = Employee.objects.get(employee_id=delivery_person_id, position='delivery')
        deliveries_created = []
        
        for subscription_id in subscription_ids:
            subscription = Subscription.objects.get(subscription_id=subscription_id, status='active')
            
            # Check if delivery already exists for this date
            existing_delivery = Delivery.objects.filter(
                subscription=subscription,
                delivery_date=delivery_date
            ).first()
            
            if not existing_delivery:
                delivery = Delivery.objects.create(
                    subscription=subscription,
                    delivery_person=delivery_person,
                    delivery_date=delivery_date,
                    delivery_status='pending'
                )
                deliveries_created.append(delivery.delivery_id)
        
        return JsonResponse({
            'success': True, 
            'message': f'Created {len(deliveries_created)} deliveries',
            'deliveries_created': len(deliveries_created)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def assign_deliveries_view(request):
    today = timezone.now().date()

    unassigned = Delivery.objects.filter(
        delivery_person__isnull=True,
        delivery_date=today,
        delivery_status='pending'
    ).select_related(
        'subscription__customer__user',
        'subscription__publication'
    )

    delivery_boys = Employee.objects.filter(position='delivery')

    workload = []
    for boy in delivery_boys:
        workload.append({
            "person": boy,
            "todays_deliveries_count": Delivery.objects.filter(
                delivery_person=boy,
                delivery_date=today
            ).count()
        })

    if request.method == "POST":
        assigned = 0

        for key, val in request.POST.items():
            if key.startswith("delivery_person_") and val:
                delivery_id = key.replace("delivery_person_", "")
                try:
                    delivery = Delivery.objects.get(
                        delivery_id=delivery_id,
                        delivery_person__isnull=True
                    )
                    boy = Employee.objects.get(employee_id=val, position='delivery')
                    delivery.delivery_person = boy
                    delivery.save()
                    assigned += 1
                except:
                    pass

        if assigned:
            messages.success(request, f"{assigned} deliveries assigned.")
        else:
            messages.warning(request, "Nothing assigned.")

        return redirect("assign_deliveries")

    context = {
        "unassigned_deliveries": unassigned,
        "delivery_persons": delivery_boys,
        "delivery_persons_with_counts": workload,
        "today": today,
    }
    return render(request, "assign_deliveries.html", context)
def manager_delivery_status_view(request):
    today = timezone.now().date()

    deliveries = Delivery.objects.filter(
        delivery_date=today
    ).select_related(
        "subscription__customer__user",
        "subscription__publication",
        "delivery_person__user"
    )

    if request.method == "POST":
        delivery_id = request.POST.get("delivery_id")
        new_status = request.POST.get("delivery_status")

        try:
            d = Delivery.objects.get(delivery_id=delivery_id)
            d.delivery_status = new_status
            d.save()
            messages.success(request, "Delivery status updated.")
        except:
            messages.error(request, "Could not update.")

        return redirect("manager_delivery_status")

    context = {
        "deliveries": deliveries,
        "today": today
    }
    return render(request, "manager_delivery_status.html", context)
