from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0003_order_customer_account_customerprofile"),
    ]

    operations = [
        migrations.RenameField(
            model_name="product",
            old_name="images",
            new_name="gallery_images",
        ),
        migrations.AlterField(
            model_name="product",
            name="gallery_images",
            field=models.JSONField(blank=True, default=list, help_text="Optional additional image URLs as a JSON list."),
        ),
        migrations.AddField(
            model_name="product",
            name="images",
            field=models.ImageField(blank=True, null=True, upload_to="products/"),
        ),
    ]
