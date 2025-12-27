from rest_framework import serializers
from .models import VPNServer, VPNConnectionLog

class VPNServerSerializer(serializers.ModelSerializer):
    current_load = serializers.SerializerMethodField()

    class Meta:
        model = VPNServer
        fields = ['id', 'name', 'ip_address', 'country', 'country_code', 'is_premium', 'port', 'config_data','current_load']

    def get_current_load(self, obj):
        # အဲဒီ Server မှာ is_active=True ဖြစ်နေတဲ့ log အရေအတွက်ကို ရေတွက်မယ်
        return VPNConnectionLog.objects.filter(server=obj, is_active=True).count()