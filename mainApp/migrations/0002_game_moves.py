# Generated by Django 3.1.7 on 2021-05-06 17:07

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='moves',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=[0, 1, 2], size=None),
            preserve_default=False,
        ),
    ]
