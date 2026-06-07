from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AutoCamServer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Server name', max_length=200)),
                ('host', models.CharField(blank=True, help_text='Server hostname or IP', max_length=100)),
                ('port', models.IntegerField(default=9600, help_text='Server port')),
                ('is_active', models.BooleanField(default=True)),
                ('last_seen', models.DateTimeField(blank=True, null=True)),
                ('track_name', models.CharField(blank=True, default='', max_length=200)),
                ('session_label', models.CharField(blank=True, default='', help_text='e.g. Online, Offline, Replay', max_length=50)),
                ('is_auto_registered', models.BooleanField(default=False, help_text='Created automatically by AutoCam on startup')),
            ],
            options={
                'ordering': ['-last_seen'],
            },
        ),
        migrations.CreateModel(
            name='AutoCamCommand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('command', models.CharField(
                    choices=[
                        ('focus_car', 'Focus on specific car'),
                        ('set_camera', 'Set camera type'),
                        ('clear_override', 'Clear manual override'),
                        ('next_car', 'Next car'),
                        ('previous_car', 'Previous car'),
                        ('toggle_switching', 'Toggle automatic switching'),
                    ],
                    max_length=50,
                )),
                ('car_id', models.IntegerField(blank=True, help_text='Car ID for focus_car command', null=True)),
                ('camera_id', models.IntegerField(blank=True, help_text='Camera ID (0-9) for set_camera command', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('executed_at', models.DateTimeField(blank=True, null=True)),
                ('is_executed', models.BooleanField(default=False)),
                ('server', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='commands',
                    to='autocam.autocamserver',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CarState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('car_id', models.IntegerField()),
                ('driver_name', models.CharField(max_length=200)),
                ('car_model', models.CharField(blank=True, max_length=200)),
                ('is_connected', models.BooleanField(default=True)),
                ('position', models.IntegerField(blank=True, null=True)),
                ('lap_count', models.IntegerField(default=0)),
                ('last_lap_time', models.FloatField(blank=True, help_text='Last lap time in milliseconds', null=True)),
                ('is_in_pits', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('server', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cars',
                    to='autocam.autocamserver',
                )),
            ],
            options={
                'ordering': ['car_id'],
            },
        ),
        migrations.AddIndex(
            model_name='autocamcommand',
            index=models.Index(fields=['server', 'is_executed', '-created_at'], name='autocam_cmd_exec_idx'),
        ),
        migrations.AddIndex(
            model_name='carstate',
            index=models.Index(fields=['server', 'is_connected'], name='autocam_car_conn_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='carstate',
            unique_together={('server', 'car_id')},
        ),
    ]
