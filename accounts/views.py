import uuid
import logging
import requests
from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.utils import timezone
from user_agents import parse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

from .serializers import RegisterSerializer
from .models import UserMovement, ActiveSession
from .serializers import UserProfileSerializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


User = get_user_model()
logger = logging.getLogger(__name__)

# --- 🛰 HELPERS ---

def track_movement(user, request, action_name):
    # 1. IP Parsing ကို ပိုမိုစိတ်ချရအောင် ပြင်ဆင်ခြင်း
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip() # strip() ထည့်ပါ
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    # 2. User Agent parsing
    ua_string = request.META.get('HTTP_USER_AGENT', '')
    try:
        user_agent = parse(ua_string)
        device_info = f"{user_agent.os.family} - {user_agent.browser.family}"
    except Exception:
        device_info = "Unknown Device"

    UserMovement.objects.create(
        user=user, 
        action=action_name, 
        ip_address=ip,
        device_name=device_info, 
        user_agent=ua_string
    )
    return ip, device_info

def check_and_update_session(user, device_id, device_name, ip):
    if not device_id: 
        return False, "device_id is required"
    
    # 1. ရှိပြီးသား session ကို အရင်စစ်ပါ
    session = ActiveSession.objects.filter(user=user, device_id=device_id).first()
    if session:
        session.ip_address = ip
        session.last_activity = timezone.now() # activity time ပါ update လုပ်သင့်ပါတယ်
        session.save()
        return True, "Updated"

    # 2. Device limit စစ်ဆေးခြင်း (user.active_sessions.count() ကို သုံးရန်)
    # မှတ်ချက်: မင်းရဲ့ model မှာ user ကနေ active_sessions ကို related_name ပေးထားဖို့လိုပါတယ်
    if user.active_sessions.count() >= user.max_devices:
        return False, f"Device limit reached ({user.max_devices})"

    # 3. Session အသစ်ဆောက်ခြင်း
    ActiveSession.objects.create(
        user=user, 
        device_id=device_id, 
        device_name=device_name, 
        ip_address=ip
    )
    return True, "Created"
# --- 1️⃣ AUTHENTICATION ---

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            track_movement(user, request, "Registration")
            return Response({"success": True}, status=201)
        return Response(serializer.errors, status=400)

class UserLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        device_id = request.data.get('device_id', 'web_default')
        
        user = authenticate(username=username, password=password)
        if user:
            if not user.is_active: return Response({"error": "Blocked"}, status=403)
            
            ip, device = track_movement(user, request, "Login")
            allowed, msg = check_and_update_session(user, device_id, device, ip)
            if not allowed: return Response({"error": msg}, status=403)

            user.last_login_ip = ip
            user.last_active_at = timezone.now()
            user.save()
            
            refresh = RefreshToken.for_user(user)
            return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'user_id': str(user.id)})
        return Response({"error": "Invalid"}, status=401)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            RefreshToken(request.data.get("refresh")).blacklist()
            track_movement(request.user, request, "Logout")
            return Response({"success": True})
        except: return Response({"error": "Invalid"}, status=400)

# --- 2️⃣ PASSWORD MANAGEMENT ---

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password") # ✅ Confirm password ထပ်ယူမယ်

        # ၁။ Field အားလုံး ပါမပါ စစ်မယ်
        if not all([old_password, new_password, confirm_password]):
            return Response(
                {"detail": "All password fields are required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # ၂။ Password အသစ် နှစ်ခု တူမတူ Backend မှာ ထပ်စစ်မယ်
        if new_password != confirm_password:
            return Response(
                {"detail": "New passwords do not match."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # ၃။ Password အဟောင်း မှန်မမှန် စစ်မယ်
        if not request.user.check_password(old_password):
            return Response(
                {"detail": "Current password is incorrect."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # ၄။ Password အသစ်ကို Save မယ်
        request.user.set_password(new_password)
        request.user.save()

        return Response({"success": True, "message": "Password changed successfully."})

class SecurePasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        
        if user:
            # ၁။ Token ထုတ်ခြင်း
            token = uuid.uuid4().hex
            
            # ၂။ Cache ထဲမှာ ၁ နာရီ သိမ်းခြင်း (user_id ကို String ပြောင်းသိမ်းပါ)
            cache.set(f"reset_{token}", str(user.id), 3600)
            
            # ၃။ ✅ Flutter Deep Link Format အတိုင်း Link တည်ဆောက်ခြင်း
            # format: vpnapp://reset-password?token=xxxx
            reset_link = f"vpnapp://reset-password?token={token}"
            
            # ၄။ ✅ Terminal မှာ တိုက်ရိုက်နှိပ်လို့ရအောင် Link ကို Print ထုတ်ခြင်း
            print("\n" + "="*50)
            print(f"PASSWORD RESET REQUEST for: {email}")
            print(f"TOKEN: {token}")
            print(f"CLICK TO OPEN IN APP: {reset_link}") # ဒီ link ကို နှိပ်ရင် App ပွင့်လာပါမယ်
            print("="*50 + "\n")
            
            return Response({
                "success": True, 
                "message": "Password reset link generated.",
                "token": token # Flutter ဘက်က လိုအပ်ရင် သုံးဖို့ token ပြန်ပေးထားခြင်း
            })
            
        return Response({"error": "User with this email not found"}, status=404)
    

class SecurePasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password') # Frontend ကနေ ပို့ပေးရမယ်

        # ၁။ Input Validation
        if not token or not password or not confirm_password:
            return Response({"error": "All fields are required."}, status=400)

        # ၂။ Password Match Validation
        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=400)

        # ၃။ Token check in Cache
        uid = cache.get(f"reset_{token}")
        
        if uid:
            try:
                user = User.objects.get(id=uid)
                user.set_password(password)
                user.save()
                cache.delete(f"reset_{token}") # သုံးပြီးသား token ဖျက်မယ်
                return Response({"success": True, "message": "Password changed successfully."})
            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=404)
        
        return Response({"error": "Invalid or expired token."}, status=400)

class UserStatusView(APIView): # သင့် URL ထဲက နာမည်အတိုင်း ပြန်ထားပေးပါတယ်
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        return Response({
            "username": user.username,
            "email": user.email,
            "is_premium": user.is_premium,
            "plan_type": user.plan_type,
            "expiry_date": user.expiry_date,
            "max_devices": user.max_devices
        })

class VPNAuthValidationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        device_id = request.data.get('device_id')
        ip = request.META.get('REMOTE_ADDR')

        if not user.is_active: return Response({"allowed": False, "reason": "Blocked"}, status=403)
        if not user.is_premium or (user.expiry_date and user.expiry_date < timezone.now()):
            return Response({"allowed": False, "reason": "Expired"}, status=403)

        allowed, msg = check_and_update_session(user, device_id, "VPN Connection", ip)
        if not allowed: return Response({"allowed": False, "reason": msg}, status=403)

        return Response({"allowed": True, "username": user.username})

# --- 4️⃣ ADMIN SERVICES ---

class UserListView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        users = User.objects.all().values('id', 'username', 'is_active', 'is_premium')
        return Response({"users": list(users)})

class UserBlockUnblockView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request):
        user = User.objects.get(id=request.data.get("user_id"))
        user.is_active = not user.is_active
        user.save()
        return Response({"success": True})

class UserActivityLogView(APIView): # ဒါကိုလည်း ပြန်ထည့်ပေးထားပါတယ်
    permission_classes = [IsAdminUser]
    def get(self, request, user_id):
        logs = UserMovement.objects.filter(user_id=user_id).values()
        return Response({"logs": list(logs)})

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        # ⚠️ is_valid() function ကို သေချာစစ်ပါ။ serializer_valid မဟုတ်ပါ။
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        
        if serializer.is_valid(): # ✅ အမှန်မှာ is_valid() ဖြစ်ရမည်
            serializer.save()
            return Response(serializer.data)
        
        # Validation error ရှိရင် 400 Bad Request ပြန်ပေးမည်
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserActiveSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # လက်ရှိ User ရဲ့ သက်တမ်းမကုန်သေးတဲ့ Token များကို ရှာသည်
        tokens = OutstandingToken.objects.filter(user=request.user)
        
        sessions = []
        for token in tokens:
            # Blacklist ထဲ ရောက်မနေတဲ့ Token တွေပဲ ယူမယ်
            if not BlacklistedToken.objects.filter(token=token).exists():
                sessions.append({
                    "id": token.id,
                    "device_name": "Unknown Device", # တကယ့် Device Name သိဖို့ User-Agent ကနေ ဖတ်ရပါမယ်
                    "location": "Myanmar", # IP ကနေတစ်ဆင့် ရှာဖွေရပါမယ်
                    "last_active": token.created_at.strftime("%b %d, %Y"),
                    "is_current": False # Logic ထပ်ထည့်ရန် လိုအပ်ပါသည်
                })
        
        return Response(sessions)

    def post(self, request):
        # Specific Session ကို Logout လုပ်ခြင်း
        token_id = request.data.get("session_id")
        try:
            token = OutstandingToken.objects.get(id=token_id, user=request.user)
            BlacklistedToken.objects.get_or_create(token=token)
            return Response({"success": True, "message": "Logged out successfully."})
        except OutstandingToken.DoesNotExist:
            return Response({"error": "Session not found"}, status=404)

# --- 5️⃣ SOCIAL ---

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://127.0.0.1:8000/api/auth/google/callback/"
    client_class = OAuth2Client
    permission_classes = [AllowAny]