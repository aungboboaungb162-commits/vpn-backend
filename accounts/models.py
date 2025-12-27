import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan_type = models.CharField(max_length=20, default='Free')
    is_premium = models.BooleanField(default=False)
    expiry_date = models.DateTimeField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    max_devices = models.IntegerField(default=5)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_device = models.CharField(max_length=255, null=True, blank=True)
    last_active_at = models.DateTimeField(null=True, blank=True)
    subscribed_plan = models.ForeignKey('vpn_service.SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.username

class ActiveSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='active_sessions')
    device_id = models.CharField(max_length=255) 
    device_name = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'device_id')

    def __str__(self):
        return f"{self.user.username} - {self.device_name}"

# Movement tracking (Audit Log)
class UserMovement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movements')
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_name = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField(null=True, blank=True)