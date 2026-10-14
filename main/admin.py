from django.contrib import admin
from django.utils.html import format_html
from .models import Shop, Food
from .widgets import PasteImageWidget


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("id", "thumbnail", "name", "cuisine", "rating", "is_active", "created_at")
    list_filter = ("is_active", "cuisine")
    search_fields = ("name", "owner_name", "address", "cuisine")
    list_editable = ("is_active",)
    ordering = ("name",)
    readonly_fields = ("image_preview",)

    fieldsets = (
        ("Shop", {
            "fields": ("name", "owner_name", "cuisine", "rating", "emoji")
        }),
        ("Location", {
            "fields": ("address",)
        }),
        ("Image", {
            "fields": ("image", "image_preview")
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )

    @admin.display(description="")
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:36px;width:36px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return "—"

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:200px;border-radius:10px;" />',
                obj.image.url,
            )
        return "No image uploaded."

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "image":
            kwargs["widget"] = PasteImageWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "thumbnail",
        "title",
        "shop",
        "discounted_price",
        "discount_percent_display",
        "quantity",
        "pickup_end",
        "is_active",
    )
    list_filter = ("is_active", "shop")
    search_fields = ("title", "description", "shop__name")
    list_editable = ("is_active", "quantity")
    autocomplete_fields = ("shop",)
    date_hierarchy = "pickup_end"
    ordering = ("pickup_end",)
    readonly_fields = ("image_preview",)

    fieldsets = (
        ("Listing", {
            "fields": ("shop", "title", "description", "emoji")
        }),
        ("Pricing (AED)", {
            "fields": ("original_price", "discounted_price")
        }),
        ("Availability", {
            "fields": ("quantity", "pickup_start", "pickup_end", "is_active")
        }),
        ("Image", {
            "fields": ("image", "image_preview")
        }),
    )

    @admin.display(description="")
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:36px;width:36px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return "—"

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:200px;border-radius:10px;" />',
                obj.image.url,
            )
        return "No image uploaded."

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "image":
            kwargs["widget"] = PasteImageWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.display(description="Discount")
    def discount_percent_display(self, obj):
        return f"-{obj.discount_percent}%"