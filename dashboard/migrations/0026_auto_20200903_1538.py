# Generated by Django 3.0.3 on 2020-09-03 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0025_auto_20200902_2049"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="snaptoant",
            options={"ordering": ["node", "snap"]},
        ),
        migrations.AlterField(
            model_name="snaptoant",
            name="node",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="snaptoant",
            name="snap",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
