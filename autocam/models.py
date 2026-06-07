from django.db import models
from django.utils import timezone


class AutoCamServer(models.Model):
    name = models.CharField(max_length=200, help_text="Server name")
    host = models.CharField(max_length=100, blank=True, help_text="Server hostname or IP")
    port = models.IntegerField(default=9600, help_text="Server port")
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    track_name = models.CharField(max_length=200, blank=True, default='')
    session_label = models.CharField(max_length=50, blank=True, default='', help_text="e.g. Online, Offline, Replay")
    session_password = models.CharField(max_length=200, blank=True, default='')
    is_auto_registered = models.BooleanField(default=False, help_text="Created automatically by AutoCam on startup")

    def __str__(self):
        return self.name

    @property
    def is_live(self):
        if not self.last_seen or not self.is_active:
            return False
        return (timezone.now() - self.last_seen).total_seconds() < 60

    class Meta:
        ordering = ['-last_seen']


class AutoCamCommand(models.Model):
    COMMAND_CHOICES = [
        ('focus_car', 'Focus on specific car'),
        ('set_camera', 'Set camera type'),
        ('clear_override', 'Clear manual override'),
        ('next_car', 'Next car'),
        ('previous_car', 'Previous car'),
        ('toggle_switching', 'Toggle automatic switching'),
    ]

    server = models.ForeignKey(AutoCamServer, on_delete=models.CASCADE, related_name='commands')
    command = models.CharField(max_length=50, choices=COMMAND_CHOICES)
    car_id = models.IntegerField(null=True, blank=True, help_text="Car ID for focus_car command")
    camera_id = models.IntegerField(null=True, blank=True, help_text="Camera ID (0-9) for set_camera command")
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    is_executed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['server', 'is_executed', '-created_at']),
        ]

    def __str__(self):
        if self.command == 'focus_car':
            return f"{self.command} (car {self.car_id})"
        elif self.command == 'set_camera':
            return f"{self.command} (camera {self.camera_id})"
        return self.command

    def mark_executed(self):
        self.is_executed = True
        self.executed_at = timezone.now()
        self.save(update_fields=['is_executed', 'executed_at'])


class CarState(models.Model):
    server = models.ForeignKey(AutoCamServer, on_delete=models.CASCADE, related_name='cars')
    car_id = models.IntegerField()
    driver_name = models.CharField(max_length=200)
    car_model = models.CharField(max_length=200, blank=True)
    is_connected = models.BooleanField(default=True)
    position = models.IntegerField(null=True, blank=True)
    lap_count = models.IntegerField(default=0)
    last_lap_time = models.FloatField(null=True, blank=True, help_text="Last lap time in milliseconds")
    is_in_pits = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['car_id']
        unique_together = ['server', 'car_id']
        indexes = [
            models.Index(fields=['server', 'is_connected']),
        ]

    def __str__(self):
        return f"{self.driver_name} (Car {self.car_id})"
