from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Purchase
from .serializers import PurchaseCreateSerializer, PurchaseSerializer


class PurchaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Purchase.objects.none()

    def get_queryset(self):
        return Purchase.objects.filter(
            user=self.request.user
        ).order_by("-completed_at")

    def get_serializer_class(self):
        if self.action == "create":
            return PurchaseCreateSerializer
        return PurchaseSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if not data.get("idempotency_key"):
            header_key = request.headers.get("Idempotency-Key")
            if header_key:
                data["idempotency_key"] = header_key

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        purchase = serializer.save()

        read = PurchaseSerializer(
            purchase, context=self.get_serializer_context())
        headers = self.get_success_headers(read.data)
        return Response(
            read.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
