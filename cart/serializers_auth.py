from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

User = get_user_model()


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

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Já existe um usuário com este e-mail.")
        return email

    def validate(self, attrs):
        pwd = attrs.get("password")
        pwd2 = attrs.get("password2") or ""
        if pwd2 and pwd != pwd2:
            raise ValidationError({"password2": "As senhas não conferem."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2", None)
        email = validated_data["email"].strip().lower()
        user = User(
            username=email,
            email=email,
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )
        user.set_password(validated_data["password"])
        user.save()
        return user
