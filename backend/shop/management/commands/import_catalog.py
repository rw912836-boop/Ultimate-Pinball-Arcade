import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from shop.models import Product


class Command(BaseCommand):
    help = "Import the bundled storefront catalog into the Django database."

    def handle(self, *args, **options):
        catalog_file = Path(__file__).resolve().parents[2] / "fixtures" / "catalog.json"
        try:
            catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read {catalog_file}: {exc}") from exc

        created = updated = 0
        for row in catalog:
            slug = row.get("handle")
            if not slug:
                continue
            defaults = {
                "external_id": str(row.get("variant_id") or "") or None,
                "title": row.get("title", "")[:255],
                "description": row.get("description", ""),
                "price": row.get("price", "0.00"),
                "product_type": row.get("product_type", "")[:120],
                "tags": row.get("tags") or [],
                "gallery_images": row.get("images") or [],
                "is_active": True,
            }
            product, was_created = Product.objects.get_or_create(
                slug=slug,
                defaults={**defaults, "stock_quantity": 1 if row.get("available") else 0},
            )
            if was_created:
                created += 1
            else:
                for field, value in defaults.items():
                    setattr(product, field, value)
                product.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Catalog imported: {created} created, {updated} updated."))
        self.stdout.write("New items marked in stock start at quantity 1; verify and correct counts in Django Admin before taking live orders.")
