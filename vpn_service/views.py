from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

from .models import VPNServer, VPNConnectionLog
from .serializers import VPNServerSerializer

# Models & Serializers Imports
from .models import VPNServer, VPNConnectionLog, SubscriptionPlan, SubscriptionHistory
from .serializers import VPNServerSerializer

class UserProfileView(APIView):
    """ User ရဲ့ Profile အချက်အလက်များကို ပြန်ပေးရန် """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "username": user.username,
            "email": user.email,
            "is_premium": user.is_premium,
            "plan_name": user.subscribed_plan.name if user.subscribed_plan else "Free User",
            "expiry_date": user.expiry_date.strftime("%Y-%m-%d %H:%M:%S") if user.expiry_date else "No expiry",
            "member_since": user.date_joined.strftime("%Y-%m-%d"),
            "device_info": getattr(user, 'last_login_device', "Unknown Device")
        }, status=status.HTTP_200_OK)

class SubscriptionPlanListView(APIView):
    """ Flutter မှ Plans များ Dynamic ဆွဲယူရန် """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # ✅ order_size ကို order_by လို့ ပြင်လိုက်ပါ
            plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
            
            data = [{
                "id": plan.id,
                "name": plan.name,
                "price": float(plan.price), # Serializer မသုံးဘဲ manually ပို့လျှင် float ပြောင်းပေးပါ
                "duration_days": plan.duration_days,
                # tag ရှိလျှင်ပြရန် (မရှိလျှင် Logic သုံးပါ)
                "tag": "Best Value" if plan.duration_days >= 365 else None
            } for plan in plans]
            
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            # ဘာကြောင့် error တက်လဲဆိုတာ သိရအောင် terminal မှာ print ထုတ်ကြည့်မည်
            print(f"Error in Plan List: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class VPNServerListView(APIView):
    """ Server List ကို Premium status ပေါ်မူတည်ပြီး ပြပေးရန် """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_premium:
            servers = VPNServer.objects.filter(is_active=True, is_premium=False)
        else:
            servers = VPNServer.objects.filter(is_active=True)
            
        serializer = VPNServerSerializer(servers, many=True)
        return Response(serializer.data)


class VPNConnectView(APIView):
    """ VPN စတင်ချိတ်ဆက်မှုအား Log မှတ်ရန်နှင့် Config ပို့ပေးရန် """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        server_id = request.data.get('server_id')
        if not server_id:
            return Response({
                "success": False, 
                "error": "server_id is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ၁။ Server ရှိမရှိနှင့် active ဖြစ်မဖြစ်စစ်ဆေးခြင်း
            server = VPNServer.objects.get(id=server_id, is_active=True)
            
            # ၂။ လက်ရှိ user မှာ active ဖြစ်နေတဲ့ တခြား connection logs တွေကို အကုန်ပိတ်ခြင်း
            VPNConnectionLog.objects.filter(user=request.user, is_active=True).update(
                is_active=False,
                disconnected_at=timezone.now()
            )

            # ၃။ User ရဲ့ IP address ကို ရယူခြင်း
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = client_ip.split(',')[0] if client_ip else request.META.get('REMOTE_ADDR', '0.0.0.0')

            # ၄။ Connection Log အသစ်ဖန်တီးခြင်း
            log = VPNConnectionLog.objects.create(
                user=request.user,
                server=server,
                client_ip=ip,
                is_active=True
            )
            
            # ၅။ ✅ Serializer သုံးပြီး server info (config_data အပါအဝင်) ကို ထည့်သွင်းခြင်း
            serializer = VPNServerSerializer(server)

            # ၆။ Flutter အတွက် JSON Response ပို့ခြင်း
            return Response({
                "success": True, 
                "status": "connected", 
                "log_id": log.id,
                "data": serializer.data  # Flutter မှ res['data']['config_data'] ဟု ခေါ်ယူနိုင်ရန်
            }, status=status.HTTP_201_CREATED)

        except VPNServer.DoesNotExist:
            return Response({
                "success": False, 
                "error": "Server not found or inactive"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "success": False, 
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VPNDisconnectView(APIView):
    """ VPN ချိတ်ဆက်မှု ဖြတ်တောက်ခြင်းအား မှတ်တမ်းတင်ရန် """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # လက်ရှိ active ဖြစ်နေတဲ့ log ကို ရှာဖွေခြင်း
        active_log = VPNConnectionLog.objects.filter(user=request.user, is_active=True).first()
        
        if active_log:
            active_log.is_active = False
            active_log.disconnected_at = timezone.now()
            active_log.save()
            
            duration = active_log.disconnected_at - active_log.connected_at
            
            return Response({
                "success": True,
                "message": "Disconnected successfully",
                "server": active_log.server.name,
                "duration": str(duration)
            }, status=status.HTTP_200_OK)
            
        return Response({
            "success": False, 
            "error": "No active connection found"
        }, status=status.HTTP_400_BAD_REQUEST)
    
class SubscribePlanView(APIView):
    """ Plan ဝယ်ယူခြင်း logic """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # ✅ Fix: ပို့လိုက်တဲ့ ID ကို Integer ပြောင်းရန် စစ်ဆေးခြင်း
        try:
            plan_id = int(request.data.get('plan_id'))
        except (TypeError, ValueError):
            return Response({"error": "Valid plan_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        payment_ref = request.data.get('payment_ref', 'WALLET_PAY')

        try:
            with transaction.atomic():
                plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
                user = request.user

                if hasattr(user, 'balance') and user.balance < plan.price:
                    return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)

                if hasattr(user, 'balance'):
                    user.balance -= plan.price
                
                now = timezone.now()
                start_from = user.expiry_date if (user.expiry_date and user.expiry_date > now) else now
                new_expiry = start_from + timedelta(days=plan.duration_days)

                user.is_premium = True
                user.expiry_date = new_expiry
                user.subscribed_plan = plan
                user.save()

                SubscriptionHistory.objects.create(
                    user=user, 
                    plan=plan, 
                    amount_paid=plan.price,
                    expiry_date_after_purchase=new_expiry, 
                    payment_reference=payment_ref
                )

                return Response({
                    "status": "success", 
                    "new_balance": str(getattr(user, 'balance', 'N/A')),
                    "expiry_date": new_expiry.strftime("%Y-%m-%d")
                }, status=status.HTTP_200_OK)

        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Invalid Subscription Plan"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Internal Server Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SubscriptionHistoryView(APIView):
    """ ဝယ်ယူခဲ့သော မှတ်တမ်းများ ပြန်ကြည့်ရန် """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        history = SubscriptionHistory.objects.filter(user=request.user).order_by('-payment_date')
        
        data = []
        for item in history:
            data.append({
                "plan_name": item.plan.name if item.plan else "Deleted Plan",
                "amount": str(item.amount_paid),
                "payment_date": item.payment_date.strftime("%Y-%m-%d %H:%M:%S"),
                "expiry_after": item.expiry_date_after_purchase.strftime("%Y-%m-%d"),
                "reference": item.payment_reference
            })
            
        return Response({
            "status": "success",
            "count": history.count(),
            "history": data
        }, status=status.HTTP_200_OK)