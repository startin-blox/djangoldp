# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-11-08 15:58
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LDNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author', models.URLField()),
                ('object', models.URLField()),
                ('type', models.CharField(max_length=255)),
                ('summary', models.TextField()),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('view_todo', 'Read'), ('control_todo', 'Control')),
            },
        ),
        migrations.CreateModel(
            name='LDPSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('container', models.URLField()),
                ('federation', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ('federation',),
                'permissions': (('view_source', 'acl:Read'), ('control_source', 'acl:Control')),
            },
        ),
    ]
