# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-05-05 17:33
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0008_auto_20200501_1207'),
    ]

    operations = [
        migrations.RenameField(
            model_name='activity',
            old_name='backlink_created',
            new_name='is_backlink',
        ),
        migrations.RenameField(
            model_name='ldpsource',
            old_name='backlink_created',
            new_name='is_backlink',
        ),
    ]
