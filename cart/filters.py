from django_filters import rest_framework as filters
from .models import Purchase


class PurchaseFilter(filters.FilterSet):
    store = filters.CharFilter(
        field_name="store_name", lookup_expr="icontains")
    currency = filters.CharFilter(field_name="currency", lookup_expr="iexact")
    min_total = filters.NumberFilter(
        field_name="total_amount", lookup_expr="gte")
    max_total = filters.NumberFilter(
        field_name="total_amount", lookup_expr="lte")
    completed_after = filters.IsoDateTimeFilter(
        field_name="completed_at", lookup_expr="gte")
    completed_before = filters.IsoDateTimeFilter(
        field_name="completed_at", lookup_expr="lte")
    tag = filters.CharFilter(method="filter_tag")

    class Meta:
        model = Purchase
        fields = []

    def filter_tag(self, queryset, name, value):
        return queryset.filter(tags__contains=[value])
