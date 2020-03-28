import click
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
def start(name, production):

    """Start a DjangoLDP project."""

    try:
        # set a directory from project name in pwd
        directory = Path.cwd() / name

        # create dir
        directory.mkdir(parents=False, exist_ok=False)

        # wrap the default django-admin startproject command
        management.call_command('startproject', name, directory, template=get_template(production))

    except FileExistsError:
        click.echo(f'Error: the folder {directory} already exists')
    except CommandError as e:
        click.echo(f'Error: {e}')


def get_template(production):

    """Return the path of project template from package resouces."""

    if production:
        return resource_filename(__name__, 'templates/production')

    return resource_filename(__name__, 'templates/development')
