from django.db import migrations


SOLD_OUT_SLUGS = [
    "side-armor-accessory-kit-john-wick",
    "jjp-sonic-arcade-edition-pinball-machine",
    "pinball-crazy-tee",
    "headphone-adaptor-spike-2",
    "godzilla-topper",
    "star-wars-fote-premium-pinball-machine",
    "jaws-pro-premium-out-of-stck",
    "pinball-cup-holder",
    "jaws-speaker-light-kit-ring-diffusers",
    "stern-black-flipper-socks",
]


def set_ten_sold_out(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    catalog = Product.objects.filter(is_active=True, external_id__isnull=False).exclude(external_id="")
    # Return previously sold-out catalog listings to a one-item starter stock,
    # then apply the requested ten sold-out listings. Preserve other quantities.
    catalog.filter(stock_quantity=0).update(stock_quantity=1)
    catalog.filter(slug__in=SOLD_OUT_SLUGS).update(stock_quantity=0)


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0005_productgalleryimage"),
    ]

    operations = [
        migrations.RunPython(set_ten_sold_out),
    ]
