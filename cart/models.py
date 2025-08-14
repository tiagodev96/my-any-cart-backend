import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q


class Purchase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    cart_name = models.CharField(max_length=120)

    completed_at = models.DateTimeField(auto_now_add=True)

    store_name = models.CharField(max_length=120, blank=True, default="")
    currency = models.CharField(max_length=3, default="EUR")

    notes = models.TextField(blank=True, default="")
    tags = models.JSONField(blank=True, null=True)

    items_count = models.PositiveIntegerField(default=0)

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    idempotency_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["completed_at"]),
            models.Index(fields=["store_name"]),
        ]
        ordering = ["-completed_at"]

    def __str__(self) -> str:
        return f"{self.cart_name} • {self.completed_at:%Y-%m-%d}"

    @property
    def has_items(self) -> bool:
        return self.items_count > 0


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(
        Purchase, related_name="items", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=180)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Agora em unidades inteiras (1, 2, 3, ...)
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    # REMOVIDO: unit = models.CharField(max_length=16, blank=True, default="")
    category = models.CharField(max_length=64, blank=True, default="")
    brand = models.CharField(max_length=64, blank=True, default="")
    barcode = models.CharField(max_length=64, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["purchase"]),
        ]
        constraints = [
            CheckConstraint(
                check=Q(unit_price__gte=0),
                name="item_unit_price_non_negative",
            ),
            CheckConstraint(
                check=Q(quantity__gte=1),
                name="item_quantity_at_least_one",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} x {self.quantity}"

    @property
    def line_total(self) -> Decimal:
        return (Decimal(self.quantity) or Decimal("0")) * (
            self.unit_price or Decimal("0"))
