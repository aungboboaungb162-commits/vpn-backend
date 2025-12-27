from django.contrib import admin
from .models import VPNServer, VPNConnectionLog
from .models import SubscriptionPlan    

@admin.register(VPNServer)
class VPNServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'ip_address', 'is_active', 'is_premium')
    list_filter = ('is_active', 'is_premium', 'country')
    search_fields = ('name', 'ip_address')

@admin.register(VPNConnectionLog)
class VPNConnectionLogAdmin(admin.ModelAdmin):
    # Admin မှာ မြင်ရမယ့် Column များ
    list_display = ('user', 'server', 'connected_at', 'disconnected_at', 'is_active')
    
    # ညာဘက်မှာ Filter ထည့်ခြင်း (Active ဖြစ်နေတာပဲ ကြည့်မလား စသည်ဖြင့်)
    list_filter = ('is_active', 'server', 'connected_at')
    
    # User name နဲ့ ရှာရလွယ်အောင်
    search_fields = ('user__username', 'server__name')
    
    # အချိန်တွေကို ပြင်လို့မရအောင် Read Only လုပ်ထားခြင်း (Security အတွက်)
    readonly_fields = ('connected_at', 'disconnected_at')

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'is_active')