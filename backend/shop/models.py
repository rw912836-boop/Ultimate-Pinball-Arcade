import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Product(models.Model):
    external_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    slug = models.SlugField(max_length=180, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    product_type = models.CharField(max_length=120, blank=True)
    tags = models.JSONField(default=list, blank=True)
    images = models.JSONField(default=list, blank=True)
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
