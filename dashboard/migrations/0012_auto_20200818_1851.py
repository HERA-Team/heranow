# Generated by Django 3.0.3 on 2020-08-18 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0011_auto_20200817_1739"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="commissioningissue",
            name="exists",
        ),
        migrations.AddField(
            model_name="commissioningissue",
            name="number",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
