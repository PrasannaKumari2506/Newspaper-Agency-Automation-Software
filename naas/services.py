import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import Notification, Customer
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_email_notification(customer, subject, message):
        """Send email notification to customer"""
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer.user.email],
                fail_silently=False,
                html_message=render_to_string('naas/email_notification.html', {
                    'customer_name': customer.user.get_full_name(),
                    'subject': subject,
                    'message': message,
                })
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {customer.user.email}: {str(e)}")
            return False

    @staticmethod
    def send_sms_notification(customer, message):
        """Send SMS notification to customer (placeholder implementation)"""
        # In a real implementation, integrate with SMS service like Twilio
        try:
            # For now, just log that SMS would be sent
            logger.info(f"SMS would be sent to {customer.user.get_full_name()}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {customer.user.get_full_name()}: {str(e)}")
            return False

    @staticmethod
    def send_in_app_notification(customer, subject, message, notification_type):
        """Create in-app notification"""
        try:
            notification = Notification.objects.create(
                user=customer.user,
                subject=subject,
                message=message,
                type=notification_type,
                channel='in_app',
                status='sent'
            )
            return notification
        except Exception as e:
            logger.error(f"Failed to create in-app notification: {str(e)}")
            return None

    @staticmethod
    def send_notification_to_customer(customer, subject, message, notification_type, channels=['in_app']):
        """Send notification through specified channels"""
        results = {
            'in_app': False,
            'email': False,
            'sms': False
        }
        
        try:
            # Send through each requested channel
            if 'in_app' in channels:
                notification = NotificationService.send_in_app_notification(customer, subject, message, notification_type)
                results['in_app'] = notification is not None
            
            if 'email' in channels:
                results['email'] = NotificationService.send_email_notification(customer, subject, message)
            
            if 'sms' in channels:
                results['sms'] = NotificationService.send_sms_notification(customer, message)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to send notification to {customer.user.email}: {str(e)}")
            return results

    @staticmethod
    def send_bulk_notifications(customers, subject, message, notification_type, channels=['in_app']):
        """Send notifications to multiple customers"""
        results = {
            'total_customers': len(customers),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        for customer in customers:
            try:
                channel_results = NotificationService.send_notification_to_customer(
                    customer, subject, message, notification_type, channels
                )
                
                # Consider it successful if at least one channel worked
                success = any(channel_results.values())
                
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                
                results['details'].append({
                    'customer': customer.user.get_full_name(),
                    'email': customer.user.email,
                    'channels': channel_results,
                    'success': success
                })
                
            except Exception as e:
                logger.error(f"Failed to send notification to {customer.user.email}: {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    'customer': customer.user.get_full_name(),
                    'email': customer.user.email,
                    'error': str(e),
                    'success': False
                })
        
        return results