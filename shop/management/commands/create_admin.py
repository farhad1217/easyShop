from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create admin user if not exists'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@easyshop.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Admin created: username=admin, password=admin123'))
        else:
            self.stdout.write('Admin user already exists.')
