from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from .models import Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "product_type", "price", "stock_quantity", "is_active", "updated_at")
    list_filter = ("is_active", "product_type")
    search_fields = ("title", "slug", "external_id")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "title_snapshot", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "customer_name", "customer_email", "total_usd", "payment_asset", "status", "created_at")
    list_filter = ("status", "payment_asset", "created_at")
    search_fields = ("customer_name", "customer_email", "transaction_hash")
    readonly_fields = ("reference", "access_token_hash", "created_at", "updated_at", "expires_at")
    inlines = (OrderItemInline,)
    actions = ("mark_verified_paid", "cancel_and_return_stock")
    fieldsets = (
        ("Order", {"fields": ("reference", "status", "total_usd", "created_at", "expires_at")}),
        ("Customer", {"fields": ("customer_name", "customer_email", "customer_phone", "shipping_address")}),
        ("Payment", {"fields": ("payment_asset", "payment_network", "receiving_address", "transaction_hash", "access_token_hash")}),
    )

    @admin.action(description="Mark selected orders paid after verifying crypto on-chain")
    def mark_verified_paid(self, request, queryset):
        updated = queryset.filter(status=Order.Status.SUBMITTED, transaction_hash__isnull=False).update(status=Order.Status.PAID, updated_at=timezone.now())
        self.message_user(request, f"Marked {updated} order(s) paid. Verify each transaction on-chain first.", messages.SUCCESS)

    @admin.action(description="Cancel selected unpaid orders and return reserved stock")
    def cancel_and_return_stock(self, request, queryset):
        cancelled = 0
        for selected in queryset:
            with transaction.atomic():
                order = Order.objects.select_for_update().filter(pk=selected.pk).first()
                if not order or order.status in {Order.Status.PAID, Order.Status.CANCELLED, Order.Status.EXPIRED}:
                    continue
                for item in order.items.select_related("product"):
                    product = Product.objects.select_for_update().get(pk=item.product_id)
                    product.stock_quantity += item.quantity
                    product.save(update_fields=["stock_quantity", "updated_at"])
                order.status = Order.Status.CANCELLED
                order.save(update_fields=["status", "updated_at"])
                cancelled += 1
        self.message_user(request, f"Cancelled {cancelled} order(s) and returned stock.", messages.SUCCESS)
