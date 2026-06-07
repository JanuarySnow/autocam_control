from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autocam', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='autocamserver',
            name='session_password',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
