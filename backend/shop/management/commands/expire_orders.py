from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from shop.models import Order, Product


class Command(BaseCommand):
    help = "Expire unpaid orders after their reservation window and return their stock."

    def handle(self, *args, **options):
        expired = 0
        candidates = Order.objects.filter(status=Order.Status.PENDING, expires_at__lte=timezone.now()).values_list("pk", flat=True)
        for order_id in candidates.iterator():
            with transaction.atomic():
                order = Order.objects.select_for_update().filter(pk=order_id, status=Order.Status.PENDING).first()
                if not order or order.expires_at > timezone.now():
                    continue
                for item in order.items.all():
                    product = Product.objects.select_for_update().get(pk=item.product_id)
                    product.stock_quantity += item.quantity
                    product.save(update_fields=["stock_quantity", "updated_at"])
                order.status = Order.Status.EXPIRED
                order.save(update_fields=["status", "updated_at"])
                expired += 1
        self.stdout.write(self.style.SUCCESS(f"Expired {expired} unpaid order(s)."))
