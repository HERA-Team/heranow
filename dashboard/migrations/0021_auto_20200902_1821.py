# Generated by Django 3.0.3 on 2020-09-02 18:21

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0020_auto_20200831_1633"),
    ]

    operations = [
        migrations.CreateModel(
            name="XengChannels",
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
                ("number", models.IntegerField()),
                (
                    "chans",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.IntegerField(), size=None
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="xengchannels",
            constraint=models.UniqueConstraint(
                fields=("number", "chans"), name="xengs must have disjoint channels."
            ),
        ),
    ]
