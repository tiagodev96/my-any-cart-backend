from __future__ import annotations

import re
from typing import Tuple, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers_auth import UserRegisterSerializer


from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests


# ----------------------
# Helpers
# ----------------------
def _make_username_from_email(email: str) -> str:
    base = slugify(email.split("@")[0]) or "user"
    base = re.sub(r"[^a-z0-9._-]", "", base)
    return base[:30]


def _get_or_create_user(
    email: str,
    name: Optional[str],
) -> Tuple[object, bool]:
    """
    Get or create user by email.
    """
    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first()
    created = False
    if not user:
        user = User.objects.create_user(
            username=_make_username_from_email(email),
            email=email,
        )
        created = True

    if created and name:
        parts = name.strip().split(" ", 1)
        user.first_name = parts[0][:30]
        if len(parts) > 1:
            user.last_name = parts[1][:150]
        user.save(update_fields=["first_name", "last_name"])
    return user, created


def _issue_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "email": getattr(user, "email", ""),
            "first_name": getattr(user, "first_name", ""),
            "last_name": getattr(user, "last_name", ""),
        },
    }


# ----------------------
# Views
# ----------------------
class MeView(APIView):
    """
    GET /api/me/
    Retorna dados do usuário autenticado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        u = request.user
        full_name = f"{u.first_name} {u.last_name}".strip()
        data = {
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "name": full_name or None,
            "avatar_url": None,
            "is_staff": u.is_staff,
        }
        return Response(data, status=status.HTTP_200_OK)


class UserRegisterView(APIView):
    """
    POST /api/users/
    Body: { first_name, last_name, email, password, password2? }
    Retorna também tokens JWT para já logar no frontend.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        s = UserRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class GoogleLoginView(APIView):
    """
    Receives a Google ID Token (credential/id_token),
    validates signature + issuer,
    checks the 'aud' against GOOGLE_CLIENT_IDS and issues JWT (SimpleJWT).
    """
    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        token = request.data.get("credential") or request.data.get("id_token")
        if not token:
            return Response(
                {"detail": "Missing Google id_token/credential."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_clients = getattr(settings, "GOOGLE_CLIENT_IDS", None)
        if not allowed_clients:
            single = getattr(settings, "GOOGLE_CLIENT_ID", "")
            allowed_clients = [single] if single else []

        if not allowed_clients:
            return Response(
                {"detail": "Server not configured for Google login."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            idinfo = google_id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience=None,
            )

            iss = idinfo.get("iss", "")
            if iss not in (
                "accounts.google.com",
                "https://accounts.google.com",
            ):
                return Response(
                    {"detail": "Invalid token issuer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            aud = idinfo.get("aud")
            if aud not in allowed_clients:
                return Response(
                    {"detail": "Invalid audience."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            email_verified = idinfo.get("email_verified", False)
            email = idinfo.get("email")
            name = idinfo.get("name") or ""
            if not email or not email_verified:
                return Response(
                    {"detail": "Email not verified by Google."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            if getattr(settings, "DEBUG", False):
                return Response(
                    {"detail": "Invalid Google token.", "error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"detail": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, _ = _get_or_create_user(email=email, name=name)
        data = _issue_tokens(user)
        return Response(data, status=status.HTTP_200_OK)


class RegisterView(APIView):
    """
    Simple email/password registration. Returns JWT on creation.
    (If using the default Django User, email is not unique -
    we prevent duplication here.)
    """
    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        name = (request.data.get("name") or "").strip()

        if "@" not in email:
            return Response(
                {"detail": "Invalid email."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(password) < 8:
            return Response(
                {"detail": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "Email already registered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            username=_make_username_from_email(email),
            email=email,
            password=password,
        )

        if name:
            parts = name.split(" ", 1)
            user.first_name = parts[0][:30]
            if len(parts) > 1:
                user.last_name = parts[1][:150]
            user.save(update_fields=["first_name", "last_name"])

        data = _issue_tokens(user)
        return Response(data, status=status.HTTP_201_CREATED)


class WhoAmIView(APIView):
    """
    Simple endpoint to validate the client's JWT.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args, **kwargs) -> Response:
        user = request.user
        return Response(
            {
                "id": user.id,
                "email": getattr(user, "email", ""),
                "first_name": getattr(user, "first_name", ""),
                "last_name": getattr(user, "last_name", ""),
            },
            status=status.HTTP_200_OK,
        )
