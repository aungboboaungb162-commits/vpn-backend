from django.urls import path
from .views import (
    UserProfileView,
    VPNServerListView,
    VPNConnectView,
    VPNDisconnectView,
    SubscriptionPlanListView,  # အသစ်ထည့်ထားသော View
    SubscribePlanView,
    SubscriptionHistoryView
)

urlpatterns = [
    # 1. Profile & Info
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # 2. VPN Server Management
    path('servers/', VPNServerListView.as_view(), name='vpn-servers'),
    path('connect/', VPNConnectView.as_view(), name='vpn-connect'),
    path('disconnect/', VPNDisconnectView.as_view(), name='vpn-disconnect'),

    # 3. Subscription & Plans (Flutter Dynamic UI အတွက် အဓိက)
    path('plans/', SubscriptionPlanListView.as_view(), name='plan-list'),
    path('subscribe/', SubscribePlanView.as_view(), name='subscribe-plan'),
    path('subscribe/history/', SubscriptionHistoryView.as_view(), name='subscribe-history'),
]