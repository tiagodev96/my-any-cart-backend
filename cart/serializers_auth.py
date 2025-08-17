from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserProfile

User = get_user_model()

# ---------------------------------
# Registration
# ---------------------------------


class UserRegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(
        write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "password", "password2"]
        extra_kwargs = {
            "password": {"write_only": True, "min_length": 8},
            "email": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate_email(self, value: str) -> str:
        email = (value or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "A user with this e-mail already exists.")
        return email

    def validate(self, attrs: dict) -> dict:
        pwd = attrs.get("password")
        pwd2 = attrs.get("password2") or ""
        if pwd2 and pwd != pwd2:
            raise serializers.ValidationError(
                {"password2": "Passwords do not match."})
        return attrs

    def create(self, validated_data: dict):
        validated_data.pop("password2", None)
        email: str = validated_data["email"].strip().lower()
        user = User(
            username=email,  # keep username as email for simplicity
            email=email,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


# ---------------------------------
# Me (read/update profile)
# ---------------------------------
class MeSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    email_confirmed = serializers.BooleanField(
        source="userprofile.email_confirmed", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "avatar_url",
            "is_staff",
            "email_confirmed",
        ]

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        # Defensive: ensure profile exists and has avatar
        if hasattr(obj, "userprofile") and getattr(
                obj.userprofile, "avatar", None):
            url = obj.userprofile.avatar.url
            return request.build_absolute_uri(url) if request else url
        return None


class MeUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(
        required=False, allow_blank=True, max_length=30)
    last_name = serializers.CharField(
        required=False, allow_blank=True, max_length=150)
    # When set to null, we remove the current avatar
    avatar = serializers.ImageField(required=False, allow_null=True)

    def validate_avatar(self, value):
        # Size/type are validated by model validators;
        # keep hook for early rejection if needed
        return value

    def update(self, instance, validated_data):
        # Names
        if "first_name" in validated_data:
            instance.first_name = validated_data["first_name"]
        if "last_name" in validated_data:
            instance.last_name = validated_data["last_name"]
        instance.save(update_fields=["first_name", "last_name"])

        # Avatar
        profile: UserProfile = instance.userprofile
        if "avatar" in validated_data:
            avatar = validated_data["avatar"]
            if avatar is None:
                # Remove avatar
                if profile.avatar:
                    profile.avatar.delete(save=False)
                profile.avatar = None
            else:
                profile.avatar = avatar
            profile.save(update_fields=["avatar"])
        return instance
