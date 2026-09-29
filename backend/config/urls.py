from django.contrib import admin
from django.urls import path

from shop import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/products/", views.product_list, name="product-list"),
    path("api/products/<slug:slug>/", views.product_detail, name="product-detail"),
    path("api/orders/", views.create_order, name="create-order"),
    path("api/orders/<str:reference>/payment/", views.submit_payment, name="submit-payment"),
    path("", views.storefront, name="storefront"),
    path("pinball-neon.svg", views.storefront_asset, {"filename": "pinball-neon.svg"}),
    path("ultimate-pinball-logo.jpg", views.storefront_asset, {"filename": "ultimate-pinball-logo.jpg"}),
]
