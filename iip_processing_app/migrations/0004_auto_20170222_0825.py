# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-22 08:25


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iip_processing_app', '0003_auto_20170217_0732'),
    ]

    operations = [
        migrations.AlterField(
            model_name='status',
            name='inscription_id',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
