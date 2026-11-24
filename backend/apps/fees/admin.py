from django.contrib import admin

from .models import (
    Discount,
    FeeItem,
    FeeStructure,
    FeeStructureLine,
    Invoice,
    InvoiceLine,
)


@admin.register(FeeItem)
class FeeItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "school", "is_active")
    list_filter = ("school", "is_active")
    search_fields = ("code", "name")


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ("school", "term", "class_stream")
    list_filter = ("school", "term", "class_stream")
    search_fields = ("school__name",)


@admin.register(FeeStructureLine)
class FeeStructureLineAdmin(admin.ModelAdmin):
    list_display = ("fee_structure", "fee_item", "amount")
    list_filter = ("fee_structure__school",)
    search_fields = ("fee_item__code",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "school", "student", "status", "issued_at")
    list_filter = ("school", "status")
    search_fields = ("invoice_number", "student__admission_number")


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "fee_item", "amount")
    list_filter = ("invoice__school",)
    search_fields = ("invoice__invoice_number",)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("student", "term", "kind", "value", "status")
    list_filter = ("school", "status")
    search_fields = ("student__admission_number",)
