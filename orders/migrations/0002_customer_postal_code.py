# Generated by Django 5.1.1 on 2024-09-30 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='postal_code',
            field=models.TextField(default=0),
            preserve_default=False,
        ),
    ]
