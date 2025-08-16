from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from rest_framework import serializers

from .models import Purchase, PurchaseItem, ISO4217_CHOICES

TWOPL = Decimal("0.01")
VALID_CURRENCIES = {code for code, _ in ISO4217_CHOICES}


class PurchaseItemInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
    )
    unit_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
    )
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        price = attrs.get("price", None)
        unit_price = attrs.get("unit_price", None)
        if price is None and unit_price is None:
            raise serializers.ValidationError(
                "Either 'price' or 'unit_price' is required.")
        if price is None:
            price = unit_price
        attrs["price"] = price
        attrs.pop("unit_price", None)
        return attrs


class PurchaseCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    products = PurchaseItemInputSerializer(
        many=True, write_only=True, required=False)

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

    def to_internal_value(self, data):
        data = dict(data)
        if "products" not in data and "items" in data:
            data["products"] = data.pop("items")
        return super().to_internal_value(data)

    def validate_currency(self, value):
        if not value:
            return "EUR"
        v = (value or "").upper()
        if v not in VALID_CURRENCIES:
            raise serializers.ValidationError("Unsupported currency")
        return v

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
        norm_products = []
        for p in products:
            price = Decimal(p["price"]).quantize(TWOPL, rounding=ROUND_HALF_UP)
            qty = int(p["quantity"])
            line = (price * Decimal(qty)).quantize(TWOPL,
                                                   rounding=ROUND_HALF_UP)
            subtotal = (subtotal + line).quantize(TWOPL,
                                                  rounding=ROUND_HALF_UP)
            norm_products.append(
                {
                    "name": p["name"],
                    "unit_price": price,
                    "quantity": qty,
                }
            )

        purchase = Purchase.objects.create(
            user=user,
            **validated_data,
            items_count=len(norm_products),
            total_amount=subtotal,
        )

        if norm_products:
            PurchaseItem.objects.bulk_create(
                [PurchaseItem(purchase=purchase, **np) for np in norm_products]
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
