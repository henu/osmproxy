# Generated by Django 3.0.4 on 2020-03-21 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proxy', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chunk',
            name='custom_data',
            field=models.BinaryField(blank=True, default=None, null=True),
        ),
    ]
