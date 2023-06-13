# Generated by Django 4.2.1 on 2023-06-13 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drpapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeadClick',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('url', models.URLField()),
                ('x', models.IntegerField()),
                ('y', models.IntegerField()),
                ('tag_name', models.CharField(max_length=255)),
                ('class_name', models.CharField(max_length=255)),
                ('element_id', models.CharField(max_length=255)),
            ],
        ),
    ]
