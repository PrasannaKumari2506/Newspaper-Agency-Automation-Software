import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from ..models import Notification

logger = logging.getLogger(__name__)

class NotificationService:
    
    @staticmethod
    def send_bulk_notifications(customers, subject, message, notification_type, channels=['in_app']):
        """
        Send notifications to multiple customers through specified channels
        """
        results = {
            'total_customers': len(customers),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        for customer in customers:
            try:
                # Send through each channel
                for channel in channels:
                    if channel == 'in_app':
                        success = NotificationService._send_in_app_notification(
                            customer.user, subject, message, notification_type
                        )
                    elif channel == 'email':
                        success = NotificationService._send_email_notification(
                            customer, subject, message
                        )
                    elif channel == 'sms':
                        success = NotificationService._send_sms_notification(
                            customer, subject, message
                        )
                    
                    if success:
                        results['successful'] += 1
                        results['details'].append({
                            'customer': customer.user.get_full_name(),
                            'channel': channel,
                            'status': 'success'
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'customer': customer.user.get_full_name(),
                            'channel': channel,
                            'status': 'failed'
                        })
                        
            except Exception as e:
                logger.error(f"Error sending notification to {customer.user.get_full_name()}: {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    'customer': customer.user.get_full_name(),
                    'channel': 'all',
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def _send_in_app_notification(user, subject, message, notification_type):
        """
        Send in-app notification
        """
        try:
            notification = Notification.objects.create(
                user=user,
                type=notification_type,
                subject=subject,
                message=message,
                status='sent'
            )
            return True
        except Exception as e:
            logger.error(f"Error creating in-app notification: {str(e)}")
            return False
    
    @staticmethod
    def _send_email_notification(customer, subject, message):
        """
        Send email notification
        """
        try:
            if not customer.user.email:
                return False
                
            html_message = render_to_string('naas/email_notification.html', {
                'customer_name': customer.user.get_full_name(),
                'subject': subject,
                'message': message
            })
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer.user.email],
                html_message=html_message,
                fail_silently=False
            )
            return True
        except Exception as e:
            logger.error(f"Error sending email to {customer.user.email}: {str(e)}")
            return False
    
    @staticmethod
    def _send_sms_notification(customer, subject, message):
        """
        Send SMS notification (placeholder - integrate with SMS service)
        """
        # This is a placeholder for SMS integration
        # You would integrate with services like Twilio, AWS SNS, etc.
        try:
            # Check if customer has phone number
            if not hasattr(customer, 'phone_number') or not customer.phone_number:
                return False
                
            # Implement SMS sending logic here
            # For now, just log and return True for simulation
            logger.info(f"SMS would be sent to {customer.phone_number}: {subject} - {message}")
            return True
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False