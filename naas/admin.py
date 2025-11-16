from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Customer, Employee, Publication, Subscription, 
    Payment, DeliverySchedule, Delivery, Commission, 
    IssueReport, Notification
)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'phone', 'is_active', 'created_at')
    list_filter = ('user_type', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'phone')
    fieldsets = UserAdmin.fieldsets + (
        ('NAAS Information', {
            'fields': ('user_type', 'phone', 'address')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'registration_date', 'subscription_count', 'is_active')
    list_filter = ('is_active', 'registration_date')
    search_fields = ('user__username', 'user__email', 'user__phone')
    readonly_fields = ('registration_date',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'position', 'hire_date', 'salary', 'is_active')
    list_filter = ('position', 'is_active', 'hire_date')
    search_fields = ('user__username', 'employee_id', 'user__email')
    readonly_fields = ('employee_id',)

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'monthly_price', 'frequency', 'publisher', 'is_available')
    list_filter = ('type', 'frequency', 'is_available')
    search_fields = ('title', 'publisher', 'description')
    list_editable = ('monthly_price', 'is_available')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('subscription_id', 'customer', 'publication', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'start_date', 'end_date', 'publication__type')
    search_fields = ('customer__user__username', 'publication__title')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'start_date'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'subscription', 'amount', 'payment_method', 'payment_status', 'payment_date', 'due_date')
    list_filter = ('payment_method', 'payment_status', 'payment_date')
    search_fields = ('receipt_number', 'subscription__customer__user__username')
    readonly_fields = ('payment_date',)
    date_hierarchy = 'payment_date'

@admin.register(DeliverySchedule)
class DeliveryScheduleAdmin(admin.ModelAdmin):
    list_display = ('schedule_id', 'delivery_person', 'delivery_date', 'area', 'assigned_subscriptions_count')
    list_filter = ('delivery_date', 'area')
    search_fields = ('delivery_person__user__username', 'area')
    date_hierarchy = 'delivery_date'

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('delivery_id', 'subscription', 'delivery_person', 'delivery_date', 'delivery_status', 'delivery_time')
    list_filter = ('delivery_status', 'delivery_date', 'delivery_person')
    search_fields = ('subscription__customer__user__username', 'subscription__publication__title')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'delivery_date'

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('commission_id', 'delivery_person', 'period_start_date', 'period_end_date', 'commission_amount', 'status')
    list_filter = ('status', 'period_start_date', 'period_end_date')
    search_fields = ('delivery_person__user__username',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'period_start_date'

@admin.register(IssueReport)
class IssueReportAdmin(admin.ModelAdmin):
    list_display = ('issue_id', 'delivery', 'reported_by', 'issue_type', 'status', 'report_date')
    list_filter = ('issue_type', 'status', 'report_date')
    search_fields = ('delivery__subscription__customer__user__username', 'description')
    readonly_fields = ('report_date',)
    date_hierarchy = 'report_date'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('notification_id', 'user', 'type', 'status', 'sent_date')
    list_filter = ('type', 'status', 'sent_date')
    search_fields = ('user__username', 'message')
    readonly_fields = ('sent_date', 'read_date')
    date_hierarchy = 'sent_date'

# Custom admin site configuration - KEEP THIS ONLY IN admin.py
admin.site.site_header = "Newspaper Agency Automation System"
admin.site.site_title = "NAAS Admin Portal"
admin.site.index_title = "Welcome to Newspaper Agency Automation System"