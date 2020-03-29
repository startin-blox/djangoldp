import click
import sys
import yaml
import subprocess
from pkg_resources import resource_filename
from pathlib import Path
from django.core import management
from django.core.management.base import CommandError
from . import __version__


# click entrypoint
@click.group()
@click.version_option(__version__)
def main():

    """DjangoLDP"""


@main.command()
@click.argument('name', nargs=1)
@click.option('--production', is_flag=True, default=False, help='Use a production template')
def startproject(name, production):

    """Start a DjangoLDP project."""

    try:
        # set a directory from project name in pwd
        directory = Path.cwd() / name

        # get the template path
        template = resource_filename(__name__, 'templates/development')
        if production:
             template = resource_filename(__name__, 'templates/production')

        # create dir
        directory.mkdir(parents=False, exist_ok=False)

        # wrap the default django-admin startproject command
        # this call import django settings and configure it
        # see: https://docs.djangoproject.com/fr/1.11/topics/settings/#calling-django-setup-is-required-for-standalone-django-usage
        management.call_command('startproject', name, directory, template=template)

    except FileExistsError:
        click.echo(f'Error: the folder {directory} already exists')

    except CommandError as e:
        click.echo(f'Error: {e}')


@main.command()
def install():

    """Install project dependencies."""

    try:
        # load dependencies from config file
        path = Path.cwd() / 'config.yml'
        with open(path, 'r') as f:
            dependencies = yaml.safe_load(f).get('dependencies', [])

        # install them by calling pip command
        cmd = [sys.executable, "-m", "pip", "install"]
        cmd.extend(dependencies)
        subprocess.run(cmd).check_returncode()

        click.echo('Installation done!')

    except FileNotFoundError:
        click.echo('Config error: no config.yml file in this directory')

    except subprocess.CalledProcessError as e:
        click.echo(f'Installation error: {e}')


@main.command()
def configure():

    """Configure the project."""
    pass
