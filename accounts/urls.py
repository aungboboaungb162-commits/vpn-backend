from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, UserLoginView, LogoutView, # LoginView ကို UserLoginView လို့ သုံးထားပါ (Naming Conflict မဖြစ်အောင်)
    ChangePasswordView, SecurePasswordResetRequestView, SecurePasswordResetConfirmView,
    UserStatusView, UserListView, UserBlockUnblockView, GoogleLogin, UserActivityLogView,VPNAuthValidationView,UserProfileView,
    UserActiveSessionsView
)

urlpatterns = [
    # --- Auth Core ---
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'), # views.py ထဲက နာမည်နဲ့ ကိုက်ရပါမယ်
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), 

    # --- Password Management ---
    path('password/change/', ChangePasswordView.as_view(), name='change-password'),
    path('password/reset/', SecurePasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', SecurePasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # --- User Services ---
    path('status/', UserStatusView.as_view(), name='user-status'),
    path('user/', UserProfileView.as_view(), name='user-profile'),
    path('sessions/', UserActiveSessionsView.as_view(), name='active-sessions'),
    
    # --- Admin Services ---
    path('admin/users/', UserListView.as_view(), name='admin-user-list'),
    path('admin/block-unblock/', UserBlockUnblockView.as_view(), name='admin-block-unblock'),
    path('admin/users/<uuid:user_id>/logs/', UserActivityLogView.as_view(), name='user_logs'),

    path('vpn/validate/', VPNAuthValidationView.as_view(), name='vpn-auth-validate'),

    # --- Social & Library Integrations ---
    # dj-rest-auth နဲ့ conflict မဖြစ်အောင် ဂရုစိုက်ပါ
    path('google/', GoogleLogin.as_view(), name='google-login'),
    path('auth/', include('dj_rest_auth.urls')), 
]