import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="customer_profile", on_delete=models.CASCADE)
    phone = models.CharField(max_length=40, blank=True)
    shipping_address = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "customer"
        verbose_name_plural = "customers"

    def __str__(self):
        return self.user.get_full_name() or self.user.email or self.user.get_username()


class Product(models.Model):
    external_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    slug = models.SlugField(max_length=180, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    product_type = models.CharField(max_length=120, blank=True)
    tags = models.JSONField(default=list, blank=True)
    images = models.ImageField(upload_to="products/", blank=True, null=True)
    gallery_images = models.JSONField(default=list, blank=True, help_text="Optional additional image URLs as a JSON list.")
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    @property
    def available(self):
        return self.is_active and self.stock_quantity > 0


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending_payment", "Awaiting payment"
        SUBMITTED = "payment_submitted", "Payment submitted"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    class Asset(models.TextChoices):
        BTC = "btc", "Bitcoin (BTC)"
        ETH = "eth", "Ethereum (ETH)"
        USDT = "usdt", "Tether (USDT)"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_account = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="pinball_orders", null=True, blank=True, on_delete=models.SET_NULL)
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=40, blank=True)
    shipping_address = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    payment_asset = models.CharField(max_length=8, choices=Asset.choices)
    payment_network = models.CharField(max_length=80)
    receiving_address = models.CharField(max_length=180)
    total_usd = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_hash = models.CharField(max_length=160, unique=True, null=True, blank=True)
    access_token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"UPA-{self.reference.hex[:10].upper()}"

    @property
    def reservation_expired(self):
        return self.expires_at <= timezone.now()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.PROTECT)
    title_snapshot = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.quantity} × {self.title_snapshot}"
