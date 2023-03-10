# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-04-21 19:43
from __future__ import unicode_literals

from django.db import migrations, models
import djangoldp.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djangoldp', '0005_auto_20200221_1127'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('urlid', djangoldp.fields.LDPUrlField(blank=True, null=True, unique=True)),
                ('aid', djangoldp.fields.LDPUrlField(null=True)),
                ('local_id', djangoldp.fields.LDPUrlField()),
                ('payload', models.BinaryField()),
                ('created_at', models.DateField(auto_now_add=True)),
            ],
            options={
                'abstract': False,
                'default_permissions': ('add', 'change', 'delete', 'view', 'control'),
            },
        ),
    ]
