# Generated by Django 3.1.7 on 2021-05-23 19:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainApp', '0004_auto_20210523_1738'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='player_won',
            field=models.IntegerField(choices=[(0, 'connect'), (1, 'cut')], default=0),
            preserve_default=False,
        ),
    ]
