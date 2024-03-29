# Generated by Django 3.0.3 on 2020-08-26 23:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0017_auto_20200826_2304"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="snapspectra",
            name="unique snap input per time",
        ),
        migrations.AddConstraint(
            model_name="snapspectra",
            constraint=models.UniqueConstraint(
                fields=("time", "hostname", "input_number"),
                name="unique snap spectra per time",
            ),
        ),
    ]
