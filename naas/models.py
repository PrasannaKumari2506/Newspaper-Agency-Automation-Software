from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('clerk', 'Clerk'),
        ('manager', 'Manager'),
        ('delivery', 'Delivery Person'),
    )
    
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fix reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='naas_user_set',  # Add related_name
        related_query_name='naas_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='naas_user_set',  # Add related_name
        related_query_name='naas_user',
    )
    
    class Meta:
        db_table = 'user'
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

class Customer(models.Model):
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    registration_date = models.DateField(auto_now_add=True)
    subscription_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'customer'
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"
    
    def save(self, *args, **kwargs):
        if not self.subscription_count:
            self.subscription_count = self.subscription_set.filter(status='active').count()
        super().save(*args, **kwargs)

class Employee(models.Model):
    POSITION_CHOICES = (
        ('clerk', 'Clerk'),
        ('manager', 'Manager'),
        ('delivery', 'Delivery Person'),
    )
    
    employee_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hire_date = models.DateField(default=timezone.now)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    is_active = models.BooleanField(default=True)
    zone = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        db_table = 'employee'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_position_display()}"

class Publication(models.Model):
    TYPE_CHOICES = (
        ('newspaper', 'Newspaper'),
        ('magazine', 'Magazine'),
    )
    
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )
    
    publication_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    publisher = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'publication'
    
    def __str__(self):
        return self.title

class Subscription(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )
    
    PAUSE_STATUS_CHOICES = (
        ('no_request', 'No Request'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    REASON_CHOICES = (
        ('vacation', 'Vacation'),
        ('financial', 'Financial Hardship'),
        ('delivery_issues', 'Delivery Issues'),
        ('other', 'Other'),
    )
    
    subscription_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    delivery_address = models.TextField()
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Pause request fields
    pause_status = models.CharField(max_length=20, choices=PAUSE_STATUS_CHOICES, default='no_request')
    pause_start_date = models.DateField(null=True, blank=True)
    pause_end_date = models.DateField(null=True, blank=True)
    pause_reason = models.CharField(max_length=50, choices=REASON_CHOICES, blank=True)
    pause_notes = models.TextField(blank=True)
    pause_requested_at = models.DateTimeField(null=True, blank=True)
    pause_processed_at = models.DateTimeField(null=True, blank=True)
    pause_processed_by = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'subscription'
    
    def __str__(self):
        return f"{self.customer.user.username} - {self.publication.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.customer.subscription_count = self.customer.subscription_set.filter(status='active').count()
        self.customer.save()
    
    @property
    def has_pending_pause_request(self):
        return self.pause_status == 'pending'
    
    @property
    def pause_duration_days(self):
        if self.pause_start_date and self.pause_end_date:
            return (self.pause_end_date - self.pause_start_date).days
        return 0
    
    @property
    def is_pause_active(self):
        """Check if the subscription is currently in paused state"""
        today = date.today()
        return (self.status == 'paused' and 
                self.pause_start_date and 
                self.pause_end_date and
                self.pause_start_date <= today <= self.pause_end_date)

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('overdue','Overdue'),
    )
    
    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    due_date = models.DateField()
    receipt_number = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta:
        db_table = 'payment'

    def save(self, *args, **kwargs):
        # Auto-generate receipt number
        if not self.receipt_number:
            self.receipt_number = f"RCP{str(self.payment_id)[:8].upper()}"
        
        # Automatically mark overdue payments
        if self.payment_status == 'pending' and self.due_date < date.today():
            self.payment_status = 'overdue'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Payment {self.receipt_number} - ${self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCP{str(self.payment_id)[:8].upper()}"
        super().save(*args, **kwargs)

class Delivery(models.Model):
    DELIVERY_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
        ('delayed', 'Delayed'),
        ('failed', 'Failed'),
    )
    
    delivery_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    delivery_person = models.ForeignKey(Employee, on_delete=models.CASCADE, limit_choices_to={'position': 'delivery'})
    delivery_date = models.DateField()
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='pending')
    delivery_time = models.TimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'delivery'
    
    def __str__(self):
        return f"Delivery {self.delivery_date} - {self.subscription}"

class DeliverySchedule(models.Model):
    schedule_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery_person = models.ForeignKey(Employee, on_delete=models.CASCADE, limit_choices_to={'position': 'delivery'})
    delivery_date = models.DateField()
    area = models.CharField(max_length=100)
    assigned_subscriptions_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'delivery_schedule'
    
    def __str__(self):
        return f"Schedule {self.delivery_date} - {self.delivery_person.user.get_full_name()}"

class Commission(models.Model):
    COMMISSION_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    )
    
    commission_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery_person = models.ForeignKey(Employee, on_delete=models.CASCADE, limit_choices_to={'position': 'delivery'})
    period_start_date = models.DateField()
    period_end_date = models.DateField()
    total_deliveries = models.IntegerField(default=0)
    total_collections = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=COMMISSION_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'commission'
    
    def __str__(self):
        return f"Commission {self.period_start_date} to {self.period_end_date} - {self.delivery_person}"

class IssueReport(models.Model):
    ISSUE_TYPE_CHOICES = (
        ('wrong_address', 'Wrong Address'),
        ('customer_unavailable', 'Customer Unavailable'),
        ('damaged_copy', 'Damaged Copy'),
        ('delivery_issue', 'Delivery Issue'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    issue_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE)
    reported_by = models.ForeignKey(Employee, on_delete=models.CASCADE)
    issue_type = models.CharField(max_length=30, choices=ISSUE_TYPE_CHOICES)
    description = models.TextField()
    report_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'issue_report'
    
    def __str__(self):
        return f"Issue {self.issue_id} - {self.issue_type}"

class Complaint(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    complaint_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'position__in': ['clerk', 'manager']})
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'complaint'
    
    def __str__(self):
        return f"Complaint: {self.subject} - {self.customer}"

class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ('payment_reminder', 'Payment Reminder'),
        ('renewal', 'Renewal'),
        ('status_update', 'Status Update'),
        ('delivery_update', 'Delivery Update'),
        ('general', 'General'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    )
    
    CHANNEL_CHOICES = (
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('all', 'All Channels'),
    )
    
    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255, default='NewsExpress Notification')  # Added subject field
    message = models.TextField()
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='in_app')
    sent_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    read_date = models.DateTimeField(null=True, blank=True)
    related_object_id = models.UUIDField(null=True, blank=True)
    
    class Meta:
        db_table = 'notification'
        ordering = ['-sent_date']
    
    def __str__(self):
        return f"Notification {self.notification_id} - {self.user.username}"



class Product(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='products/')
    description = models.TextField()
    
    def __str__(self):
        return self.name
