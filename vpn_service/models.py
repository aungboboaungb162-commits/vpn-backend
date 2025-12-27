from django.db import models
from django.db import models
from django.conf import settings

class VPNServer(models.Model):
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    country = models.CharField(max_length=100)
    country_code = models.CharField(max_length=10) # ဥပမာ: US, SG
    city = models.CharField(max_length=100)
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    port = models.IntegerField(default=443)
    config_data = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.ip_address}"
    
class VPNConnectionLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    server = models.ForeignKey('VPNServer', on_delete=models.CASCADE)
    client_ip = models.GenericIPAddressField()
    connected_at = models.DateTimeField(auto_now_add=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.server.name}"
    
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100) # ဥပမာ- Monthly VIP, Yearly VIP
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(help_text="သက်တမ်းကာလ (ရက်ပေါင်း)")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ${self.price}"
    
class SubscriptionHistory(models.Model):
    # Braxton ဆိုတဲ့စာသားကို ဖယ်ထုတ်လိုက်ပါ
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    expiry_date_after_purchase = models.DateTimeField()
    payment_reference = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-payment_date']