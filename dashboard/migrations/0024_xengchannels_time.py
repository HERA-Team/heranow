# Generated by Django 3.0.3 on 2020-09-02 19:59

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0023_auto_20200902_1936"),
    ]

    operations = [
        migrations.AddField(
            model_name="xengchannels",
            name="time",
            field=models.DateTimeField(
                default=datetime.datetime(2020, 9, 2, 19, 59, 30, 365164, tzinfo=utc)
            ),
            preserve_default=False,
        ),
    ]
