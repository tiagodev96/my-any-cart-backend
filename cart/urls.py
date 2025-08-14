from django.urls import URLPattern, URLResolver, include, path
from rest_framework.routers import DefaultRouter

from .views import PurchaseViewSet

router = DefaultRouter()
router.register(r"purchases", PurchaseViewSet, basename="purchase")

urlpatterns: list[URLPattern | URLResolver] = [
    path("", include(router.urls)),
]
