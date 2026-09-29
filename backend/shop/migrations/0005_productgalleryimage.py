import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0004_product_gallery_images_alter_product_images"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductGalleryImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="products/gallery/")),
                ("position", models.PositiveIntegerField(default=0)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="uploaded_gallery_images",
                        to="shop.product",
                    ),
                ),
            ],
            options={"ordering": ["position", "pk"]},
        ),
    ]
