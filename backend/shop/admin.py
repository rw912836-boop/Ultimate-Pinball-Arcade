from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone

from .models import CustomerProfile, Order, OrderItem, Product, ProductGalleryImage

admin.site.site_header = "Ultimate Pinball Arcade"
admin.site.site_title = "Store Manager"
admin.site.index_title = "Store Manager"
admin.site.index_template = "admin/index.html"


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "email", "phone", "created_at")
    search_fields = ("user__first_name", "user__last_name", "user__email", "phone")
    fields = ("user", "phone", "shipping_address", "created_at")
    readonly_fields = ("user", "phone", "shipping_address", "created_at")
    raw_id_fields = ("user",)
    list_per_page = 50
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    @admin.display(description="Name", ordering="user__first_name")
    def customer_name(self, obj):
        return obj.user.get_full_name() or obj.user.get_username()

    @admin.display(description="Email", ordering="user__email")
    def email(self, obj):
        return obj.user.email


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleImageField, self).clean(file, initial) for file in files]


class ProductAdminForm(forms.ModelForm):
    gallery_uploads = MultipleImageField(
        required=False,
        label="Product photos",
        help_text="Click Choose Files and select one or more photos. New photos are added to this product.",
    )

    class Meta:
        model = Product
        fields = "__all__"
        labels = {
            "title": "Product name",
            "description": "Short description",
            "price": "Price (USD)",
            "stock_quantity": "Quantity in stock",
        }


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    fields = ("title", "description", "price", "stock_quantity", "gallery_uploads")
    list_display = ("title", "price", "stock_quantity", "availability")
    search_fields = ("title",)
    list_per_page = 30
    ordering = ("title",)

    @admin.display(description="Status")
    def availability(self, obj):
        return "In stock" if obj.available else "Sold out"

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            base_slug = slugify(obj.title)[:180].strip("-") or "pinball-product"
            candidate = base_slug
            suffix = 2
            while Product.objects.exclude(pk=obj.pk).filter(slug=candidate).exists():
                ending = f"-{suffix}"
                candidate = f"{base_slug[:180 - len(ending)]}{ending}"
                suffix += 1
            obj.slug = candidate
        if not change and not obj.product_type:
            obj.product_type = "machines"
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        files = form.cleaned_data.get("gallery_uploads", [])
        next_position = (self.model.uploaded_gallery_images.filter(product=form.instance).order_by("-position").values_list("position", flat=True).first() or 0) + 1
        if files and not form.instance.images:
            form.instance.images = files.pop(0)
            form.instance.save(update_fields=["images"])
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
