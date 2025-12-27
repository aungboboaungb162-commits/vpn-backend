from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.utils.html import format_html
from .models import User, UserMovement,ActiveSession

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'plan_status_display', 
        'expiry_date', 'days_left', 'is_active'
    )
    
    # ညာဘက်ခြမ်းတွင် Premium နှင့် Plan အလိုက် စစ်ထုတ်ရန်
    list_filter = ('is_premium', 'plan_type', 'subscribed_plan')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)

    # --- Premium User နှင့် Free User ကို အပြတ်အသတ် ခွဲခြားပြသရန် Logic ---
    def plan_status_display(self, obj):
        if obj.is_premium:
            plan_name = obj.subscribed_plan.name if obj.subscribed_plan else "Premium"
            price = f"(${obj.subscribed_plan.price})" if obj.subscribed_plan else ""
            
            # Premium ဖြစ်ပါက ရွှေရောင်နောက်ခံ (သို့) တောက်ပသော အစိမ်းရောင်ဖြင့် ပြမည်
            return format_html(
                '<span style="background-color: #ffd700; color: #000; padding: 3px 10px; '
                'border-radius: 10px; font-weight: bold; font-size: 11px;">'
                '👑 PREMIUM: {} {}</span>',
                plan_name.upper(),
                price
            )
        
        # သာမန် User ဖြစ်ပါက မီးခိုးရောင်ဖြင့် ပြမည်
        return format_html(
            '<span style="color: #999; font-style: italic;">Standard (Free)</span>'
        )
    
    plan_status_display.short_description = 'User Membership'

    def days_left(self, obj):
        if obj.is_premium and obj.expiry_date:
            remaining = obj.expiry_date - timezone.now()
            if remaining.days > 0:
                return format_html(
                    '<b style="color: #28a745;">{} Days Remaining</b>', 
                    remaining.days
                )
            return format_html('<b style="color: #dc3545;">EXPIRED</b>')
        return format_html('<span style="color: #ccc;">-</span>')
    
    days_left.short_description = 'Access Duration'

    # Detail View အတွက် Layout
    fieldsets = (
        ('Account Credentials', {'fields': ('username', 'password')}),
        ('User Profile', {'fields': ('email', 'phone_number', 'country')}),
        ('Membership Details', {
            'fields': ('is_premium', 'plan_type', 'subscribed_plan', 'expiry_date'),
            'description': "Check or upgrade the user's premium membership status."
        }),
        ('Technical & Security', {
            'fields': ('max_devices', 'last_login_ip', 'last_login_device', 'last_active_at'),
            'classes': ('collapse',),
        }),
    )

admin.site.register(User, CustomUserAdmin)

@admin.register(ActiveSession)
class ActiveSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'device_id', 'ip_address', 'last_activity')
    search_fields = ('user__username', 'device_id')

@admin.register(UserMovement)
class UserMovementAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'location', 'timestamp')
    list_filter = ('action', 'timestamp')