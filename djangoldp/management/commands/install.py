import subprocess
import sys
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):

    help = 'Install server dependencies'

    def handle(self, *args, **options):

        try:
            # load dependencies from the configuration
            from django.conf import settings
            cmd = [sys.executable, "-m", "pip", "install"]
            cmd.extend(settings.DEPENDENCIES)
            subprocess.run(cmd).check_returncode()

            self.stdout.write(self.style.SUCCESS('Installation done!'))

        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f'Error with: {e}'))

