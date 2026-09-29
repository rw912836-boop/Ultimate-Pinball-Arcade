from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from .models import CustomerProfile, Order, OrderItem, Product, ProductGalleryImage


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "email", "phone", "created_at")
    search_fields = ("user__first_name", "user__last_name", "user__email", "phone")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user",)

    @admin.display(description="Name", ordering="user__first_name")
    def customer_name(self, obj):
        return obj.user.get_full_name() or obj.user.get_username()

    @admin.display(description="Email", ordering="user__email")
    def email(self, obj):
        return obj.user.email


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(file, initial) for file in files]


class ProductGalleryImageInline(admin.TabularInline):
    model = ProductGalleryImage
    extra = 0
    fields = ("image", "position", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class ProductAdminForm(forms.ModelForm):
    gallery_uploads = MultipleFileField(
        required=False,
        label="Upload gallery images",
        help_text="Select multiple image files at once. Existing gallery images are kept.",
    )

    class Meta:
        model = Product
        fields = "__all__"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ("title", "product_type", "price", "stock_quantity", "is_active", "updated_at")
    list_filter = ("is_active", "product_type")
    search_fields = ("title", "slug", "external_id")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = (ProductGalleryImageInline,)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        files = form.cleaned_data.get("gallery_uploads", [])
        next_position = (self.model.uploaded_gallery_images.filter(product=form.instance).order_by("-position").values_list("position", flat=True).first() or 0) + 1
        for offset, image in enumerate(files):
            ProductGalleryImage.objects.create(
                product=form.instance,
                image=image,
                position=next_position + offset,
            )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "title_snapshot", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "customer_name", "customer_email", "customer_account_email", "total_usd", "payment_asset", "status", "created_at")
    list_filter = ("status", "payment_asset", "created_at")
    search_fields = ("customer_name", "customer_email", "customer_account__email", "transaction_hash")
    readonly_fields = ("reference", "access_token_hash", "customer_account", "created_at", "updated_at", "expires_at")
    inlines = (OrderItemInline,)
    actions = ("mark_verified_paid", "cancel_and_return_stock")
    fieldsets = (
        ("Order", {"fields": ("reference", "status", "total_usd", "created_at", "expires_at")}),
        ("Customer", {"fields": ("customer_account", "customer_name", "customer_email", "customer_phone", "shipping_address")}),
        ("Payment", {"fields": ("payment_asset", "payment_network", "receiving_address", "transaction_hash", "access_token_hash")}),
    )

    @admin.display(description="Account")
    def customer_account_email(self, obj):
        return obj.customer_account.email if obj.customer_account_id else "Guest checkout"

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
