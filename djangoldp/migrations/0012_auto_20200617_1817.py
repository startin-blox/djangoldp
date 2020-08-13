# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-06-17 18:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0011_auto_20200610_1323'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='is_backlink',
            field=models.BooleanField(default=False, help_text='set automatically to indicate the Model is a backlink'),
        ),
        migrations.AlterField(
            model_name='follower',
            name='is_backlink',
            field=models.BooleanField(default=False, help_text='set automatically to indicate the Model is a backlink'),
        ),
        migrations.AlterField(
            model_name='ldpsource',
            name='is_backlink',
            field=models.BooleanField(default=False, help_text='set automatically to indicate the Model is a backlink'),
        ),
    ]