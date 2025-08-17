from __future__ import annotations

import os
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser as User

# -----------------------------
# Validators & constants
# -----------------------------
ISO4217_CHOICES: list[tuple[str, str]] = [
    ("USD", "USD"),
    ("EUR", "EUR"),
    ("CNY", "CNY"),
    ("JPY", "JPY"),
    ("GBP", "GBP"),
    ("INR", "INR"),
    ("BRL", "BRL"),
    ("AUD", "AUD"),
    ("CAD", "CAD"),
    ("CHF", "CHF"),
    ("MXN", "MXN"),
    ("KRW", "KRW"),
    ("TRY", "TRY"),
    ("ZAR", "ZAR"),
]

iso4217_upper_validator = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Currency must be a 3-letter ISO 4217 code (uppercase).",
)


def validate_avatar_file(value: Any) -> None:
    """Validate avatar file size and extension."""
    max_bytes = 10 * 1024 * 1024  # 10 MB
    if getattr(value, "size", 0) > max_bytes:
        raise ValidationError("Avatar exceeds 10MB.")
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    ext = os.path.splitext(getattr(value, "name", ""))[1].lower()
    if ext not in valid_exts:
        raise ValidationError("Invalid format. Use JPG, PNG or WEBP.")


def user_avatar_path(instance: "UserProfile", filename: str) -> str:
    return f"avatars/user_{instance.user.pk}/{filename}"


# -----------------------------
# Purchase
# -----------------------------
class Purchase(models.Model):
    user: models.ForeignKey["User", models.Model] = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchases",
        db_index=True,
    )

    id: models.UUIDField = models.UUIDField(primary_key=True, editable=False)

    cart_name: models.CharField = models.CharField(max_length=120)
    completed_at: models.DateTimeField = models.DateTimeField(
        auto_now_add=True)

    store_name: models.CharField = models.CharField(
        max_length=120, blank=True, default="")
    currency: models.CharField = models.CharField(
        max_length=3,
        default="EUR",
        validators=[iso4217_upper_validator],
        choices=ISO4217_CHOICES,
        db_index=True,
    )

    notes: models.TextField = models.TextField(blank=True, default="")
    tags: models.JSONField = models.JSONField(blank=True, null=True)

    items_count: models.PositiveIntegerField = models.PositiveIntegerField(
        default=0)

    total_amount: models.DecimalField = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    idempotency_key: models.CharField = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["completed_at"]),
            models.Index(fields=["store_name"]),
            models.Index(fields=["user", "completed_at"]),
        ]
        ordering = ["-completed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                name="unique_idempotency_per_user",
                condition=(Q(idempotency_key__isnull=False)
                           & ~Q(idempotency_key="")),
            ),
            models.CheckConstraint(
                check=Q(items_count__gte=0),
                name="purchase_items_count_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.cart_name} • {self.completed_at:%Y-%m-%d}"

    @property
    def has_items(self) -> bool:
        return self.items_count > 0


# -----------------------------
# PurchaseItem
# -----------------------------
class PurchaseItem(models.Model):
    purchase: models.ForeignKey["Purchase", models.Model] = models.ForeignKey(
        Purchase, related_name="items", on_delete=models.CASCADE)
    name: models.CharField = models.CharField(max_length=180)

    unit_price: models.DecimalField = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    quantity: models.PositiveIntegerField = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["purchase"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(unit_price__gte=0),
                name="item_unit_price_non_negative",
            ),
            models.CheckConstraint(
                check=Q(quantity__gte=1),
                name="item_quantity_at_least_one",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} x {self.quantity}"

    @property
    def line_total(self) -> Decimal:
        return (
            Decimal(self.quantity) or Decimal("0")) * (
                self.unit_price or Decimal("0")
        )


# -----------------------------
# UserProfile
# -----------------------------
class UserProfile(models.Model):
    user: models.OneToOneField["User", models.Model] = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    avatar: models.ImageField = models.ImageField(
        upload_to=user_avatar_path,
        null=True,
        blank=True,
        validators=[validate_avatar_file],
    )
    email_confirmed: models.BooleanField = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Profile({self.user.pk})"


@receiver(post_save, sender=get_user_model())
def create_user_profile(
    sender: type["User"],
    instance: "User",
    created: bool,
    **kwargs: Any,
) -> None:
    if created:
        UserProfile.objects.create(user=instance)
