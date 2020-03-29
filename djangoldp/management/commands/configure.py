from django.core import management
from django.conf import settings
from django.db.utils import IntegrityError
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError

class Command(BaseCommand):

    help = 'Initialize the DjangoLDP backend'

    def handle(self, *args, **options):

        """Wrapper command around default django initialization commands."""

        try:
            # migrate data
            management.call_command('migrate', interactive=False)

        except CommandError as e:
            setf.stdout.write(self.style.ERROR(f'Data migration failed: {e}'))

        try:
            if settings.DEBUG:
                # create a default super user
                from django.contrib.auth import get_user_model
                User = get_user_model()
                User.objects.create_superuser('admin', 'admin@example.org', 'admin')

            else:
                # call default createsuperuser command
                management.call_command('createsuperuser', interactive=True)

        except (ValidationError, IntegrityError):
            self.stdout.write('User "admin" already exists. Skipping...')
            pass

        except CommandError as e:
            setf.stdout.write(self.style.ERROR(f'Superuser creation failed: {e}'))
            pass

        try:
            # creatersakey
            management.call_command('creatersakey', interactive=False)

        except CommandError as e:
            setf.stdout.write(self.style.ERROR(f'RSA key creation failed: {e}'))
