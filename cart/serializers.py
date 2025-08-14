from decimal import Decimal
from typing import List

from rest_framework import serializers

from .models import Purchase, PurchaseItem


class PurchaseItemInputSerializer(serializers.Serializer):
    """
    Entry item to create a purchase from the frontend.
    """
    name = serializers.CharField(max_length=180)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.00"))
    quantity = serializers.IntegerField(min_value=1)
    category = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default="")
    brand = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default="")
    barcode = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default="")


class PurchaseItemSerializer(serializers.ModelSerializer):
    """
    Read-only item returned by the API.
    """
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseItem
        fields = ["id", "name", "unit_price", "quantity", "category",
                  "brand", "barcode", "line_total", "created_at"]

    def get_line_total(self, obj: PurchaseItem) -> str:
        return str(obj.line_total)


class PurchaseSerializer(serializers.ModelSerializer):
    """
    Read-only purchase including items and totals.
    """
    items = PurchaseItemSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id", "cart_name", "store_name", "currency", "notes", "tags",
            "items_count", "total_amount", "completed_at", "idempotency_key",
            "items",
        ]


class PurchaseCreateSerializer(serializers.ModelSerializer):
    """
    Create a purchase from a list of products.
    Calculates items_count and total_amount in the backend.
    Respects idempotency_key.
    """
    products = PurchaseItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = Purchase
        # the client does not send items_count/total_amount/completed_at
        read_only_fields = ["items_count", "total_amount", "completed_at"]
        fields = [
            "cart_name", "store_name", "currency", "notes", "tags",
            "idempotency_key", "products",
        ]

    def validate_currency(self, value: str) -> str:
        v = (value or "").upper()
        if len(v) != 3 or not v.isalpha():
            raise serializers.ValidationError(
                "Currency must be an ISO-4217 code (e.g.: 'EUR').")
        return v

    def validate_products(self, value: List[dict]) -> List[dict]:
        if not value:
            raise serializers.ValidationError(
                "At least one product is required.")
        return value

    def create(self, validated_data: dict) -> Purchase:
        products = validated_data.pop("products")
        idem = validated_data.get("idempotency_key")

        # Idempotency: if it already exists, return the same record
        if idem:
            existing = Purchase.objects.filter(idempotency_key=idem).first()
            if existing:
                return existing

        # Calculations
        subtotal = Decimal("0.00")
        for p in products:
            subtotal += (p["price"] * Decimal(p["quantity"]))

        purchase = Purchase.objects.create(
            **validated_data,
            items_count=len(products),
            total_amount=subtotal,
        )

        # Create items (snapshot)
        items = [
            PurchaseItem(
                purchase=purchase,
                name=p["name"],
                unit_price=p["price"],
                quantity=int(p["quantity"]),
                category=p.get("category", ""),
                brand=p.get("brand", ""),
                barcode=p.get("barcode", ""),
            )
            for p in products
        ]
        PurchaseItem.objects.bulk_create(items)

        return purchase
