# Generated by Django 3.1.4 on 2022-04-21 17:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0031_auto_20220105_1650"),
    ]

    operations = [
        migrations.AlterField(
            model_name="antennastatus",
            name="fem_switch",
            field=models.CharField(
                choices=[
                    ("ANT", "Antenna"),
                    ("LOAD", "Load"),
                    ("NOISE", "Noise"),
                    ("UNKNOWN", "Unknown"),
                    ("FAILED", "Failed"),
                ],
                max_length=7,
                null=True,
            ),
        ),
    ]