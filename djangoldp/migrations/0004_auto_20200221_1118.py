# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-02-21 11:18
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0003_auto_20190911_0931'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ldpsource',
            options={'ordering': ('federation',)},
        ),
    ]
