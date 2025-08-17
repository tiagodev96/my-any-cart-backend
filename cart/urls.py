from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PurchaseViewSet
from .views_auth import (
    MeView, UserRegisterView, GoogleLoginView, RegisterView, WhoAmIView,
    SendConfirmationEmailView, ConfirmEmailView,
)

router = DefaultRouter()
router.register(r"purchases", PurchaseViewSet, basename="purchase")

urlpatterns: list = [
    path("", include(router.urls)),

    # Auth / Profile
    path("me/", MeView.as_view(), name="me"),
    path("users/", UserRegisterView.as_view(), name="user-register"),
    path("auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/whoami/", WhoAmIView.as_view(), name="auth-whoami"),

    path(
        "auth/send-confirmation-email/",
        SendConfirmationEmailView.as_view(),
        name="auth-send-confirmation-email",
    ),
    path(
        "auth/confirm-email/",
        ConfirmEmailView.as_view(),
        name="auth-confirm-email",
    ),
]
