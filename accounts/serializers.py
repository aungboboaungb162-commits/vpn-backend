from rest_framework import serializers
from .models import User
import re

# --- ၁။ User Profile Serializer (Profile ပြသရန်အတွက်) ---
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Flutter UI တွင် ပြသလိုသည့် field များ
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id', 'username', 'email')


# --- ၂။ Register Serializer (အကောင့်သစ်ဖွင့်ရန်အတွက်) ---
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    # ✅ Password Strength Validation Logic
    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least one digit.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character.")
        return value

    # ✅ User အသစ်ဆောက်သည့် Logic (Password ကို Hash လုပ်ပေးသည်)
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user