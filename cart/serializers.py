from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from rest_framework import serializers

from .models import Purchase, PurchaseItem


TWOPL = Decimal("0.01")


class PurchaseItemInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.00")
    )
    quantity = serializers.IntegerField(min_value=1)


class PurchaseCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    products = PurchaseItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = Purchase
        fields = [
            "cart_name",
            "store_name",
            "currency",
            "notes",
            "tags",
            "idempotency_key",
            "products",
            "user",
        ]
        extra_kwargs = {
            "store_name": {"required": False, "allow_blank": True},
            "currency": {"required": False},
            "notes": {"required": False, "allow_blank": True},
            "tags": {"required": False, "allow_null": True},
            "idempotency_key": {
                "required": False,
                "allow_null": True,
                "allow_blank": True,
            },
        }

    def validate_idempotency_key(self, value):
        if value is None:
            return None
        v = (value or "").strip()
        return v or None

    def validate_tags(self, value):
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",")]
            return [p for p in parts if p]
        return value

    @transaction.atomic
    def create(self, validated_data):
        products = validated_data.pop("products", [])

        user = validated_data.pop("user", None)
        if not getattr(user, "is_authenticated", False):
            user = None

        idem = validated_data.get("idempotency_key", None)

        if idem:
            existing = Purchase.objects.filter(
                user=user, idempotency_key=idem).first()
            if existing:
                return existing

        subtotal = Decimal("0.00")
        for p in products:
            line = (p["price"] * Decimal(p["quantity"])
                    ).quantize(TWOPL, rounding=ROUND_HALF_UP)
            subtotal += line
        subtotal = subtotal.quantize(TWOPL, rounding=ROUND_HALF_UP)

        purchase = Purchase.objects.create(
            user=user,
            **validated_data,
            items_count=len(products),
            total_amount=subtotal,
        )

        PurchaseItem.objects.bulk_create(
            [
                PurchaseItem(
                    purchase=purchase,
                    name=p["name"],
                    unit_price=Decimal(p["price"]).quantize(
                        TWOPL, rounding=ROUND_HALF_UP),
                    quantity=p["quantity"],
                )
                for p in products
            ]
        )

        return purchase


class PurchaseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = ("name", "unit_price", "quantity", "created_at")


class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = (
            "id",
            "cart_name",
            "completed_at",
            "store_name",
            "currency",
            "notes",
            "tags",
            "items_count",
            "total_amount",
            "idempotency_key",
            "items",
        )
