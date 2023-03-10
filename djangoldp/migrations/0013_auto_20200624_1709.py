# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-06-24 17:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0012_auto_20200617_1817'),
    ]

    operations = [
        migrations.AddField(
            model_name='follower',
            name='follower',
            field=models.URLField(blank=True, help_text='(optional) the resource/actor following the object'),
        ),
        migrations.AlterField(
            model_name='follower',
            name='inbox',
            field=models.URLField(help_text='the inbox recipient of updates'),
        ),
        migrations.AlterField(
            model_name='follower',
            name='object',
            field=models.URLField(help_text='the object being followed'),
        ),
    ]
