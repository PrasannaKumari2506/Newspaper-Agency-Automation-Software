from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from naas.models import Publication, CustomUser

class Command(BaseCommand):
    help = 'Create sample data for the application'

    def handle(self, *args, **options):
        User = get_user_model()
        
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
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))