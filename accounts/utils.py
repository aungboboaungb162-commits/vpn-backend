# accounts/utils.py
import requests
from user_agents import parse
from .models import UserMovement

def record_movement(user, request, action):
    try:
        # IP ယူခြင်း
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Device Info ယူခြင်း
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(ua_string)
        device = f"{user_agent.os.family} / {user_agent.browser.family} ({user_agent.device.family})"

        # Location Info (IP-API သုံးခြင်း)
        location = "Localhost"
        if ip not in ['127.0.0.1', '::1']:
            try:
                response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
                data = response.json()
                if data.get('status') == 'success':
                    location = f"{data.get('city')}, {data.get('country')}"
            except:
                location = "Unknown Location"

        # Database ထဲသို့ သိမ်းဆည်းခြင်း
        UserMovement.objects.create(
            user=user,
            action=action,
            ip_address=ip,
            device_name=device,
            location=location,
            user_agent=ua_string
        )
        print(f"Successfully tracked: {action} for {user.username}")
    except Exception as e:
        print(f"Tracking Failed: {str(e)}")