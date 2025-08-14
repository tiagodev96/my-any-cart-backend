from django.contrib import admin
from .models import Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    fields = ("name", "unit_price", "quantity", "category", "brand",
              "barcode", "line_total_display", "created_at")
    readonly_fields = ("line_total_display", "created_at")

    @admin.display(description="Line total")
    def line_total_display(self, obj: PurchaseItem) -> str:
        if obj.pk:
            return f"{obj.quantity} × {obj.unit_price} = {obj.line_total}"
        return "-"


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "cart_name", "store_name", "items_count",
                    "currency", "total_amount", "completed_at")
    list_filter = ("currency", "store_name", "completed_at")
    search_fields = ("cart_name", "store_name",
                     "idempotency_key", "items__name")
    date_hierarchy = "completed_at"
    inlines = [PurchaseItemInline]
    readonly_fields = ("completed_at",)
    ordering = ("-completed_at",)

    fieldsets = (
        (None, {"fields": ("cart_name", ("store_name", "currency"),
                           "notes", "tags")}),
        ("Resumo", {"fields": (("items_count", "total_amount"),
         "idempotency_key", "completed_at")}),
    )


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ("id", "purchase", "name",
                    "unit_price", "quantity", "created_at")
    list_filter = ("created_at", "category", "brand")
    search_fields = ("name", "barcode", "brand",
                     "category", "purchase__cart_name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
