from django.db import models
from django.utils.text import slugify
import os

def food_image_path(instance, filename):
    return _image_upload_path('food', instance, filename)

def shop_image_path(instance, filename):
    return _image_upload_path('shop', instance, filename)

class Shop(models.Model):
    """A business that lists surplus food (bakery, restaurant, grocery, etc.)."""

    name = models.CharField(max_length=120)
    owner_name = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    cuisine = models.CharField(
        max_length=80,
        blank=True,
        help_text="e.g. Bakery, Japanese, Middle Eastern, Grocery",
    )
    emoji = models.CharField(
        max_length=8,
        default="🏪",
        help_text="A single emoji used as the shop's visual mark.",
    )
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, default=4.5,
        help_text="Rating out of 5.0",
    )
    image = models.ImageField(
        upload_to=shop_image_path,
        blank=True,
        null=True,
        help_text="Shop logo or storefront photo (optional).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this shop and all its foods from the site.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Food(models.Model):
    """A surplus food listing from a shop."""

    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name="foods",
    )

    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)

    original_price = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Regular price in AED before discount.",
    )
    discounted_price = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Price the customer pays in AED.",
    )

    quantity = models.PositiveIntegerField(
        default=1,
        help_text="How many of this item are available.",
    )

    pickup_start = models.DateTimeField(
        help_text="When customers can start picking up this item.",
    )
    pickup_end = models.DateTimeField(
        help_text="Latest time customers can pick up this item.",
    )

    emoji = models.CharField(
        max_length=8,
        default="🍽️",
        help_text="A single emoji shown on the listing card.",
    )

    image = models.ImageField(
        upload_to=food_image_path,
        blank=True,
        null=True,
        help_text="Photo of the food item (optional).",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this listing from the browse page.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pickup_end"]

    def __str__(self):
        return f"{self.title} — {self.shop.name}"

    @property
    def discount_percent(self):
        """Return the % off, rounded. e.g. 67 for a 67% discount."""
        if not self.original_price:
            return 0
        saving = self.original_price - self.discounted_price
        return round((saving / self.original_price) * 100)

    @property
    def savings(self):
        """Money saved in AED."""
        return self.original_price - self.discounted_price

def _image_upload_path(folder, instance, filename):
    """
    Build a path like: <folder>/<pk>/<original-basename>.<ext>

    Example: food/12/pastry-box.png  or  shop/3/sunrise-bakery.jpg

    Note: we keep the original filename (sanitized) so admins can tell
    files apart when browsing the media folder.
    """
    # Get the file extension (lowercased)
    ext = os.path.splitext(filename)[1].lower() or '.png'

    # Sanitize the base name: 'Sunrise Bakery Photo 1' -> 'sunrise-bakery-photo-1'
    base = os.path.splitext(filename)[0]
    base = slugify(base) or 'image'

    # instance.pk should exist because images are added *after* the row is created
    # (see the note below for the edge case)
    pk = instance.pk or 'temp'

    return f"{folder}/{pk}/{base}{ext}"