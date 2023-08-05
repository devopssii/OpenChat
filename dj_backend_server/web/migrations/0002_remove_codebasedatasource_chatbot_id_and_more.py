# Generated by Django 4.2.3 on 2023-08-05 19:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='codebasedatasource',
            name='chatbot_id',
        ),
        migrations.AddField(
            model_name='codebasedatasource',
            name='chatbot',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='codebase_data_source', to='web.chatbot'),
            preserve_default=False,
        ),
    ]
