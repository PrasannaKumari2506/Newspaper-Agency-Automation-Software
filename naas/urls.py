from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.home, name='home'),
    path('customer-login/', views.customer_login, name='customer_login'),
    path('customer-register/', views.customer_register, name='customer_register'),
    path('employee-login/', views.employee_login, name='employee_login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Dashboards
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('manager/dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('clerk/dashboard/', views.clerk_dashboard, name='clerk_dashboard'),
    path('delivery/dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    
    # Customer Actions
    path('subscribe/', views.subscribe, name='subscribe'),
    path('manage-subscription/<uuid:subscription_id>/', views.manage_subscription, name='manage_subscription'),
    path('make-payment/<uuid:payment_id>/', views.make_payment, name='make_payment'),
    path('submit-complaint/', views.submit_complaint, name='submit_complaint'),
    path('pause-delivery/', views.pause_delivery, name='pause_delivery'),
    
    # Clerk Actions
    path('record-payment/', views.record_payment, name='record_payment'),
    path('resolve-complaint/<uuid:complaint_id>/', views.resolve_complaint, name='resolve_complaint'),
    
    # Delivery Actions
    path('mark-delivery-completed/<uuid:delivery_id>/', views.mark_delivery_completed, name='mark_delivery_completed'),
    path('report-issue/<uuid:delivery_id>/', views.report_issue, name='report_issue'),
    
    # Manager Actions
    path('manage-employees/', views.manage_employees, name='manage_employees'),
    path('generate-reports/', views.generate_reports, name='generate_reports'),
    
    # API endpoints
    path('api/customer/dashboard-stats/', views.customer_dashboard_stats, name='customer_dashboard_stats'),
    path('api/customer/refresh-subscriptions/', views.refresh_subscriptions, name='refresh_subscriptions'),
    path('api/customer/refresh-payments/', views.refresh_payments, name='refresh_payments'),
    
    # Admin utilities
    path('initialize-sample-data/', views.initialize_sample_data, name='initialize_sample_data'),

    # Delivery
    path('pause-subscription/', views.pause_subscription, name='pause_subscription'),
    path('resume-subscription/<uuid:subscription_id>/', views.resume_subscription, name='resume_subscription'),
    path('record-payment/', views.record_payment, name='record_payment'),
    path('resolve-complaint/<int:complaint_id>/', views.resolve_complaint, name='resolve_complaint'),
    path('add-subscription/', views.add_subscription, name='add_subscription'),

    # Clerk
    path('clerk/subscription/add/', views.add_subscription, name='add_subscription'),
    path('clerk/receipt/<uuid:payment_id>/download/', views.download_receipt, name='download_receipt'),
    path('clerk/receipt/<str:payment_id>/', views.download_receipt, name='download_receipt'),


    # Pause newspaper
    path('customer/pause/request/', views.request_pause, name='request_pause'),
    path('clerk/pause/<uuid:subscription_id>/approve/', views.approve_pause_request, name='approve_pause_request'),
    path('clerk/pause/<uuid:subscription_id>/reject/', views.reject_pause_request, name='reject_pause_request'),

    # Complaints
    path('customer/complaint/submit/', views.submit_complaint, name='submit_complaint'),
    path('clerk/complaint/<uuid:complaint_id>/resolve/', views.resolve_complaint, name='resolve_complaint'),

    # Manager Dashboard URLs
    path('manager/subscriptions/', views.all_subscriptions, name='all_subscriptions'),
    path('manager/add-publication/', views.add_publication, name='add_publication'),
    path('manager/assign-delivery-person/', views.assign_delivery_person, name='assign_delivery_person'),
   # path('manager/delete-delivery/', views.delete_delivery, name='delete_delivery'),
    path('manager/send-notification/', views.send_notification, name='send_notification'),

    path('manager/delivery/', views.manager_delivery_status_view, name='manage_delivery'),    
    # Publication Management
    path('manager/publications/add/', views.add_publication, name='add_publication'),
    path('manager/publications/<uuid:publication_id>/toggle-availability/', views.toggle_publication_availability, name='toggle_publication_availability'),
    path('manager/publications/<uuid:publication_id>/delete/', views.delete_publication, name='delete_publication'),
    
    # Commission Management
    #path('manager/commissions/generate/', views.generate_commissions, name='generate_commissions'),
    path('manager/commissions/<uuid:commission_id>/update-status/', views.update_commission_status, name='update_commission_status'),
    
    # Reports
    path('manager/reports/download/<str:report_type>/', views.download_report_pdf, name='download_report_pdf'),

    #Notifications
    path('manager/notifications/send/', views.send_notification, name='send_notification'),

]