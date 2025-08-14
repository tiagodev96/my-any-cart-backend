from django.db import models
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Purchase
from .serializers import PurchaseCreateSerializer, PurchaseSerializer


class PurchaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    queryset: models.QuerySet[Purchase] = Purchase.objects.all().order_by(
        "-completed_at")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return PurchaseCreateSerializer
        else:
            return PurchaseSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if "idempotency_key" not in data:
            header_key = request.headers.get("Idempotency-Key")
            if header_key:
                data["idempotency_key"] = header_key

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save()

        purchase.user = request.user
        purchase.save(update_fields=["user"])

        read = PurchaseSerializer(
            purchase, context=self.get_serializer_context())
        headers = self.get_success_headers(read.data)
        return Response(
            read.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
