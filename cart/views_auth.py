from __future__ import annotations

import re
from typing import Any, Tuple, Optional, TYPE_CHECKING, Protocol, cast

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.shortcuts import redirect
from django.utils.text import slugify

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers_auth import (
    UserRegisterSerializer,
    MeSerializer,
    MeUpdateSerializer,
)

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

if TYPE_CHECKING:
    # Import from this app to keep tooling happy without runtime import cycles
    from .models import UserProfile


# ----------------------
# Protocols (for mypy)
# ----------------------
class _UserWithNames(Protocol):
    id: int
    email: str
    first_name: str
    last_name: str
    userprofile: "UserProfile"

    def save(self, *args: Any, **kwargs: Any) -> None: ...


# ----------------------
# Helpers
# ----------------------
def _make_username_from_email(email: str) -> str:
    base = slugify(email.split("@")[0]) or "user"
    base = re.sub(r"[^a-z0-9._-]", "", base)
    return base[:30]


def _get_or_create_user(
    email: str,
    name: Optional[str]
) -> Tuple[_UserWithNames, bool]:
    """
    Get or create user by e-mail (typed in a mypy-friendly way).
    """
    User = get_user_model()
    user_obj = User.objects.filter(email__iexact=email).first()
    created = False

    if not user_obj:
        # Manager type is not precise for mypy;
        # cast to Any to access create_user
        manager = cast(Any, User.objects)
        user_obj = manager.create_user(
            username=_make_username_from_email(email),
            email=email,
        )
        created = True

    user = cast(_UserWithNames, user_obj)

    if created and name:
        parts = name.strip().split(" ", 1)
        user.first_name = parts[0][:30]
        if len(parts) > 1:
            user.last_name = parts[1][:150]
        user.save(update_fields=["first_name", "last_name"])

    return user, created


def _issue_tokens(user: Any) -> dict:
    """
    Issue JWT tokens.
    Typed as Any to avoid mypy complaining about SimpleJWT type vars.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": getattr(user, "id", None),
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
    GET  /api/me/   -> return authenticated user's data
    PATCH /api/me/  -> update first_name, last_name and avatar
    (multipart/form-data)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args, **kwargs) -> Response:
        s = MeSerializer(request.user, context={"request": request})
        return Response(s.data, status=status.HTTP_200_OK)

    def patch(self, request: Request, *args, **kwargs) -> Response:
        s = MeUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.update(cast(_UserWithNames, request.user), s.validated_data)
        read = MeSerializer(user, context={"request": request})
        return Response(read.data, status=status.HTTP_200_OK)


class UserRegisterView(APIView):
    """
    POST /api/users/
    Body: { first_name, last_name, email, password, password2? }
    Returns JWT tokens to log in immediately.
    """
    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        s = UserRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = cast(_UserWithNames, s.save())
        tokens = _issue_tokens(user)
        # keep compatibility with your previous shape
        return Response(
            {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "access": tokens["access"],
                "refresh": tokens["refresh"],
            },
            status=status.HTTP_201_CREATED,
        )


class GoogleLoginView(APIView):
    """
    Receives a Google ID Token (credential/id_token),
    validates signature & issuer,
    checks the 'aud' against GOOGLE_CLIENT_IDS and issues JWT (SimpleJWT).
    """
    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        token = request.data.get("credential") or request.data.get("id_token")
        if not token:
            return Response(
                {"detail": "Missing Google id_token/credential."},
                status=status.HTTP_400_BAD_REQUEST
            )

        allowed_clients = getattr(settings, "GOOGLE_CLIENT_IDS", None)
        if not allowed_clients:
            single = getattr(settings, "GOOGLE_CLIENT_ID", "")
            allowed_clients = [single] if single else []

        if not allowed_clients:
            return Response(
                {"detail": "Server not configured for Google login."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), audience=None)

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
    If using the default Django User where email is not unique,
    duplication is prevented here.
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

        # Use cast(Any, ...)
        # to avoid mypy complaining about Manager not having create_user
        manager = cast(Any, User.objects)
        user = cast(
            _UserWithNames,
            manager.create_user(
                username=_make_username_from_email(email),
                email=email,
                password=password,
            ),
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
    """Simple endpoint to validate the client's JWT."""
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args, **kwargs) -> Response:
        user = cast(_UserWithNames, request.user)
        return Response(
            {
                "id": user.id,
                "email": getattr(user, "email", ""),
                "first_name": getattr(user, "first_name", ""),
                "last_name": getattr(user, "last_name", ""),
            },
            status=status.HTTP_200_OK,
        )


# ----------------------
# Email confirmation
# ----------------------
class SendConfirmationEmailView(APIView):
    """
    POST /api/auth/send-confirmation-email/
    Sends an email with a signed link.
    Free in development via console email backend.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args, **kwargs) -> Response:
        user = cast(_UserWithNames, request.user)
        profile = cast("UserProfile", getattr(user, "userprofile", None))
        if profile and profile.email_confirmed:
            return Response(
                {"detail": "E-mail already confirmed."},
                status=status.HTTP_200_OK,
            )

        signer = TimestampSigner()
        token = signer.sign(f"{user.id}:{user.email}")  # contains id + email

        backend_base = getattr(settings, "BACKEND_BASE_URL", "").rstrip("/")
        confirm_url = f"{backend_base}/api/auth/confirm-email/?token={token}"

        subject = "Confirm your e-mail"
        message = (
            f"Hi {user.first_name or ''},\n\n"
            "To confirm your e-mail, click the link below "
            "(valid for 3 days):\n"
            f"{confirm_url}\n\n"
            "If this wasn't you, just ignore this message."
        )
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [user.email], fail_silently=False)
        return Response(
            {"detail": "Confirmation e-mail sent."},
            status=status.HTTP_200_OK,
        )


class ConfirmEmailView(APIView):
    """
    GET /api/auth/confirm-email/?token=...
    Validates the signature and sets email_confirmed=True
    """
    permission_classes = [AllowAny]

    def get(self, request: Request, *args, **kwargs) -> Response:
        token = request.query_params.get("token")
        if not token:
            return Response(
                {"detail": "Missing token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signer = TimestampSigner()
        try:
            raw = signer.unsign(token, max_age=60 * 60 * 24 * 3)  # 3 days
            user_id_str, email = raw.split(":", 1)
            User = get_user_model()
            user_obj = User.objects.filter(
                id=int(user_id_str), email__iexact=email).first()
            if not user_obj:
                return Response(
                    {"detail": "User not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = cast(_UserWithNames, user_obj)
            profile = cast("UserProfile", getattr(user, "userprofile", None))
            if profile and not profile.email_confirmed:
                profile.email_confirmed = True
                profile.save(update_fields=["email_confirmed"])
        except SignatureExpired:
            return Response(
                {"detail": "Token expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except BadSignature:
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional: redirect to the frontend after success
        frontend = getattr(settings, "FRONTEND_BASE_URL", "").rstrip("/")
        if frontend:
            # cast to Response to please mypy
            # (DRF accepts HttpResponseRedirect)
            return cast(
                Response,
                redirect(f"{frontend}/pt/profile?verified=1"),
            )

        return Response(
            {"detail": "E-mail successfully confirmed."},
            status=status.HTTP_200_OK,
        )
