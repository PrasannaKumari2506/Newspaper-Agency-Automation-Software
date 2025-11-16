from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from naas.models import Publication

class Command(BaseCommand):
    help = 'Create initial data for the application'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Create manager user
        if not User.objects.filter(username='manager').exists():
            manager = User.objects.create_user(
                username='manager',
                email='manager@newsexpress.com',
                password='manager.123',
                user_type='manager',
                first_name='Michael',
                last_name='Johnson',
                is_staff=True
            )
            self.stdout.write(self.style.SUCCESS('Created manager user: manager@newsexpress.com'))

        # Create clerk user
        if not User.objects.filter(username='clerk').exists():
            clerk = User.objects.create_user(
                username='clerk',
                email='clerk@newsexpress.com',
                password='clerk.123',
                user_type='clerk',
                first_name='John',
                last_name='Doe',
                is_staff=True
            )
            self.stdout.write(self.style.SUCCESS('Created clerk user: clerk@newsexpress.com'))

        # Create delivery user
        if not User.objects.filter(username='delivery').exists():
            delivery = User.objects.create_user(
                username='delivery',
                email='delivery@newsexpress.com',
                password='delivery.123',
                user_type='delivery',
                first_name='John',
                last_name='Smith',
                is_staff=False
            )
            self.stdout.write(self.style.SUCCESS('Created delivery user: delivery@newsexpress.com'))

        # Create sample customer
        if not User.objects.filter(username='customer1').exists():
            customer = User.objects.create_user(
                username='customer1',
                email='customer1@newsexpress.in',
                password='customer1.123',
                user_type='customer',
                first_name='Robert',
                last_name='Johnson',
                phone='+91 9876543210',
                address='123 Main Street, Apt 4B, New York, NY 10001',
                is_staff=False
            )
            self.stdout.write(self.style.SUCCESS('Created customer user: customer1@newsexpress.in'))

        # Create sample publications
        publications = [
            {
                'name': 'The Daily Times',
                'description': 'Comprehensive national and international news coverage',
                'monthly_price': 300.00,
            },
            {
                'name': 'Morning Herald', 
                'description': 'Business and financial news with market analysis',
                'monthly_price': 250.00,
            },
            {
                'name': 'Evening Gazette',
                'description': 'Local news, events, and community updates', 
                'monthly_price': 200.00,
            },
            {
                'name': 'Weekly Digest',
                'description': 'In-depth analysis and feature stories weekly',
                'monthly_price': 150.00,
            },
        ]
        
        for pub_data in publications:
            publication, created = Publication.objects.get_or_create(
                name=pub_data['name'],
                defaults=pub_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created publication: {pub_data["name"]}'))
        
        self.stdout.write(self.style.SUCCESS('Initial data created successfully!'))
        self.stdout.write(self.style.SUCCESS('\nLogin credentials:'))
        self.stdout.write(self.style.SUCCESS('Manager: manager@newsexpress.com / manager.123'))
        self.stdout.write(self.style.SUCCESS('Clerk: clerk@newsexpress.com / clerk.123'))
        self.stdout.write(self.style.SUCCESS('Delivery: delivery@newsexpress.com / delivery.123'))
        self.stdout.write(self.style.SUCCESS('Customer: customer1@newsexpress.in / customer1.123'))