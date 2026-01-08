# Generated migration for adding timestamp fields to all LDP models
# These fields support HTTP caching headers (Last-Modified, If-Modified-Since)

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0020_rename_sitesettings_sitesetting'),
    ]

    operations = [
        # Activity already has created_at from migration 0006, only add updated_at
        migrations.AddField(
            model_name='activity',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # Add created_at field to Follower model
        migrations.AddField(
            model_name='follower',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        # Add updated_at field to Follower model
        migrations.AddField(
            model_name='follower',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # Add created_at field to LDPSource model
        migrations.AddField(
            model_name='ldpsource',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        # Add updated_at field to LDPSource model
        migrations.AddField(
            model_name='ldpsource',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # Note: SiteSetting is not an LDP model (inherits from models.Model, not djangoldp.models.Model)
        # so it does not get timestamp fields
    ]
