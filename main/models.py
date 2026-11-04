import os, random
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta


def _image_upload_path(folder, instance, filename):
    ext = os.path.splitext(filename)[1].lower() or '.png'
    base = slugify(os.path.splitext(filename)[0]) or 'image'
    pk = instance.pk or 'temp'
    return f"{folder}/{pk}/{base}{ext}"


def food_image_path(instance, filename):
    return _image_upload_path('food', instance, filename)


def shop_image_path(instance, filename):
    return _image_upload_path('shop', instance, filename)


class User(AbstractUser):
    CUSTOMER = 'customer'
    BUSINESS = 'business'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (CUSTOMER, 'Customer'),
        (BUSINESS, 'Business'),
        (ADMIN, 'Admin'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=CUSTOMER,
    )

    def is_customer(self):
        return self.role == self.CUSTOMER

    def is_business(self):
        return self.role == self.BUSINESS


class Shop(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shops',
        limit_choices_to={'role': User.BUSINESS},
    )
    name = models.CharField(max_length=120)
    owner_name = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    cuisine = models.CharField(max_length=80, blank=True)
    emoji = models.CharField(max_length=8, default='🏪')
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=4.5)
    image = models.ImageField(
        upload_to=shop_image_path,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Food(models.Model):
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='foods',
    )
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    original_price = models.DecimalField(max_digits=8, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    pickup_start = models.DateTimeField()
    pickup_end = models.DateTimeField()
    emoji = models.CharField(max_length=8, default='🍽️')
    image = models.ImageField(
        upload_to=food_image_path,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['pickup_end']

    def __str__(self):
        return f"{self.title} — {self.shop.name}"

    @property
    def discount_percent(self):
        if not self.original_price:
            return 0
        saving = self.original_price - self.discounted_price
        return round((saving / self.original_price) * 100)

    @property
    def savings(self):
        return self.original_price - self.discounted_price


COURIERS = [
    {"name": "Talabat Express", "base_fee": Decimal("12.00")},
    {"name": "Careem Now", "base_fee": Decimal("15.00")},
    {"name": "Deliveroo", "base_fee": Decimal("18.00")},
    {"name": "Aramex Go", "base_fee": Decimal("10.00")},
    {"name": "Fetchr", "base_fee": Decimal("13.00")},
]


class Order(models.Model):
    PICKUP = "pickup"
    DELIVERY = "delivery"
    FULFILLMENT_CHOICES = [(PICKUP, "Pickup"), (DELIVERY, "Delivery")]

    PENDING = "pending"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
        (NO_SHOW, "No-show"),
    ]

    CANCEL_WINDOW = timedelta(minutes=2)

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    food = models.ForeignKey(Food, on_delete=models.SET_NULL, null=True, related_name="orders")
    quantity = models.PositiveIntegerField(default=1)

    fulfillment = models.CharField(
        max_length=10, choices=FULFILLMENT_CHOICES, default=PICKUP,
    )
    delivery_address = models.CharField(max_length=255, blank=True)
    courier_name = models.CharField(max_length=80, blank=True)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=8, decimal_places=2)

    eta = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} — {self.food.title if self.food else 'deleted'} for {self.customer.username}"

    @property
    def effective_status(self):
        if self.status != self.PENDING:
            return self.status
        if self.fulfillment == self.DELIVERY and self.eta and timezone.now() >= self.eta:
            return self.DELIVERED
        if (
            self.fulfillment == self.PICKUP
            and self.food
            and timezone.now() >= self.food.pickup_end
        ):
            return self.NO_SHOW
        return self.PENDING

    @property
    def is_delivered(self):
        return self.effective_status == self.DELIVERED

    @property
    def can_cancel(self):
        if self.effective_status != self.PENDING:
            return False
        if self.fulfillment == self.DELIVERY:
            return timezone.now() - self.created_at <= self.CANCEL_WINDOW
        if self.food:
            return timezone.now() < self.food.pickup_end
        return False

    @property
    def cancel_deadline(self):
        return self.created_at + self.CANCEL_WINDOW