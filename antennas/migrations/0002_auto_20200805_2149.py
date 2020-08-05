# Generated by Django 3.0.3 on 2020-08-05 21:49

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("antennas", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="antennastatus", name="apriori_status",),
        migrations.RemoveField(model_name="antennastatus", name="frequencies",),
        migrations.RemoveField(model_name="antennastatus", name="spectra",),
        migrations.CreateModel(
            name="AutoSpectra",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "spectra",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.FloatField(), size=None
                    ),
                ),
                (
                    "frequencies",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.FloatField(), size=None
                    ),
                ),
                ("time", models.DateTimeField(verbose_name="Status Time")),
                (
                    "antenna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="antennas.Antenna",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AprioriStatus",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("time", models.DateTimeField(verbose_name="Status Time")),
                (
                    "apriori_status",
                    models.CharField(
                        choices=[
                            ("DhM", "Dish Maintenance"),
                            ("DhO", "Dish OK"),
                            ("RFM", "RF Maintenance"),
                            ("RFO", "RF OK"),
                            ("DiM", "Digital Maintenance"),
                            ("DiO", "Digital OK"),
                            ("CaM", "Calibration Maintenance"),
                            ("CaO", "Calibration OK"),
                            ("CaT", "Calibration Triage"),
                        ],
                        max_length=3,
                    ),
                ),
                (
                    "antenna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="antennas.Antenna",
                    ),
                ),
            ],
        ),
    ]
