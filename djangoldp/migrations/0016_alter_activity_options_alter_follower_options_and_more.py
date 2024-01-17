# Generated by Django 4.2.3 on 2023-08-31 15:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0015_auto_20210125_1847'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='activity',
            options={'default_permissions': {'delete', 'change', 'view', 'add', 'control'}},
        ),
        migrations.AlterModelOptions(
            name='follower',
            options={'default_permissions': {'delete', 'change', 'view', 'add', 'control'}},
        ),
        migrations.AlterModelOptions(
            name='ldpsource',
            options={'default_permissions': {'delete', 'change', 'view', 'add', 'control'}, 'ordering': ('federation',)},
        ),
        migrations.AlterModelOptions(
            name='scheduledactivity',
            options={'default_permissions': {'delete', 'change', 'view', 'add', 'control'}},
        ),
    ]