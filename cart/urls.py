from django.urls import URLPattern, URLResolver, include, path
from rest_framework.routers import DefaultRouter
from .views_auth import GoogleLoginView, MeView, UserRegisterView
from .views import PurchaseViewSet

router = DefaultRouter()
router.register(r"purchases", PurchaseViewSet, basename="purchase")

urlpatterns: list[URLPattern | URLResolver] = [
    path("", include(router.urls)),
    path("auth/google/", GoogleLoginView.as_view(), name="auth-google"),
    path("users/", UserRegisterView.as_view(), name="user-register"),
    path("me/", MeView.as_view(), name="me"),
]
