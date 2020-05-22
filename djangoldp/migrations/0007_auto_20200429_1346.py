# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-04-29 13:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0006_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='allow_create_backlink',
            field=models.BooleanField(default=True, help_text='set to False to disable backlink creation after Model save'),
        ),
        migrations.AddField(
            model_name='ldpsource',
            name='allow_create_backlink',
            field=models.BooleanField(default=True, help_text='set to False to disable backlink creation after Model save'),
        ),
    ]
