# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-05-19 10:37
from __future__ import unicode_literals

from django.db import migrations, models
import djangoldp.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0009_auto_20200505_1733'),
    ]

    operations = [
        migrations.CreateModel(
            name='Follower',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('urlid', djangoldp.fields.LDPUrlField(blank=True, null=True, unique=True)),
                ('is_backlink', models.BooleanField(default=False, help_text='set automatically to indicate the Model is a backlink')),
                ('allow_create_backlink', models.BooleanField(default=True, help_text='set to False to disable backlink creation after Model save')),
                ('object', models.URLField()),
                ('inbox', models.URLField()),
            ],
            options={
                'abstract': False,
                'default_permissions': ('add', 'change', 'delete', 'view', 'control'),
            },
        ),
    ]
