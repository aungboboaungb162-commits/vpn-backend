from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # admin.as_view() မဟုတ်ဘဲ admin.site.urls ဖြစ်ရပါမယ်
    path('admin/', admin.site.urls),
    
    # ကျွန်တော်တို့ ဆောက်ထားတဲ့ accounts app က URL တွေကို ချိတ်ဆက်ခြင်း
    path('api/auth/', include('accounts.urls')),
    path('api/vpn/', include('vpn_service.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)              