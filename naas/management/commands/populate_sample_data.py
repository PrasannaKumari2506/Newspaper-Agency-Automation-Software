from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from naas.models import *
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Populate database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Populating sample data...')
        
        # Create publications
        publications = [
            {
                'title': 'The Daily Times',
                'type': 'newspaper',
                'monthly_price': 30.00,
                'frequency': 'daily',
                'publisher': 'Times Media',
                'description': 'Your daily dose of news and updates'
            },
            {
                'title': 'Business Chronicle',
                'type': 'newspaper', 
                'monthly_price': 45.00,
                'frequency': 'daily',
                'publisher': 'Business Press',
                'description': 'Business news and market analysis'
            },
            {
                'title': 'Sunday Herald',
                'type': 'newspaper',
                'monthly_price': 20.00,
                'frequency': 'weekly', 
                'publisher': 'Herald Group',
                'description': 'Weekend special edition'
            },
            {
                'title': 'Tech Magazine',
                'type': 'magazine',
                'monthly_price': 25.00,
                'frequency': 'monthly',
                'publisher': 'Tech Media',
                'description': 'Latest in technology and innovation'
            },
            {
                'title': 'Sports Weekly', 
                'type': 'magazine',
                'monthly_price': 35.00,
                'frequency': 'weekly',
                'publisher': 'Sports Network',
                'description': 'Sports news and analysis'
            }
        ]
        
        for pub_data in publications:
            Publication.objects.get_or_create(
                title=pub_data['title'],
                defaults=pub_data
            )
        
        # Create sample customers
        customers_data = [
            {'username': 'robert_johnson', 'email': 'robert@email.com', 'first_name': 'Robert', 'last_name': 'Johnson', 'phone': '555-0101', 'address': '123 Main Street, Cityville'},
            {'username': 'sarah_williams', 'email': 'sarah@email.com', 'first_name': 'Sarah', 'last_name': 'Williams', 'phone': '555-0102', 'address': '456 Oak Avenue, Townsville'},
            {'username': 'michael_brown', 'email': 'michael@email.com', 'first_name': 'Michael', 'last_name': 'Brown', 'phone': '555-0103', 'address': '789 Pine Road, Villagetown'},
            {'username': 'emily_davis', 'email': 'emily@email.com', 'first_name': 'Emily', 'last_name': 'Davis', 'phone': '555-0104', 'address': '321 Elm Street, Hamletville'},
            {'username': 'david_wilson', 'email': 'david@email.com', 'first_name': 'David', 'last_name': 'Wilson', 'phone': '555-0105', 'address': '654 Maple Drive, Boroughcity'},
        ]
        
        for customer_data in customers_data:
            user, created = User.objects.get_or_create(
                username=customer_data['username'],
                defaults={
                    'email': customer_data['email'],
                    'first_name': customer_data['first_name'],
                    'last_name': customer_data['last_name'],
                    'phone': customer_data['phone'],
                    'address': customer_data['address'],
                    'user_type': 'customer'
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                Customer.objects.create(user=user)
        
        # Create employees
        employees_data = [
            {'username': 'manager1', 'email': 'manager@newsexpress.com', 'first_name': 'John', 'last_name': 'Manager', 'position': 'manager', 'salary': 60000},
            {'username': 'clerk1', 'email': 'clerk@newsexpress.com', 'first_name': 'Lisa', 'last_name': 'Clerk', 'position': 'clerk', 'salary': 40000},
            {'username': 'delivery1', 'email': 'delivery1@newsexpress.com', 'first_name': 'Mike', 'last_name': 'Delivery', 'position': 'delivery', 'salary': 35000, 'zone': 'Zone A'},
            {'username': 'delivery2', 'email': 'delivery2@newsexpress.com', 'first_name': 'Anna', 'last_name': 'Driver', 'position': 'delivery', 'salary': 35000, 'zone': 'Zone B'},
        ]
        
        for emp_data in employees_data:
            user, created = User.objects.get_or_create(
                username=emp_data['username'],
                defaults={
                    'email': emp_data['email'],
                    'first_name': emp_data['first_name'],
                    'last_name': emp_data['last_name'],
                    'user_type': emp_data['position']
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                Employee.objects.create(
                    user=user,
                    position=emp_data['position'],
                    salary=emp_data['salary'],
                    zone=emp_data.get('zone', '')
                )
        
        self.stdout.write(self.style.SUCCESS('Sample data populated successfully!'))