from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from django.views.static import serve

from shop import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/products/", views.product_list, name="product-list"),
    path("api/products/<slug:slug>/", views.product_detail, name="product-detail"),
    path("api/auth/csrf/", views.auth_csrf, name="auth-csrf"),
    path("api/auth/register/", views.auth_register, name="auth-register"),
    path("api/auth/login/", views.auth_login, name="auth-login"),
    path("api/auth/logout/", views.auth_logout, name="auth-logout"),
    path("api/auth/me/", views.auth_me, name="auth-me"),
    path("api/orders/", views.create_order, name="create-order"),
    path("api/orders/<str:reference>/payment/", views.submit_payment, name="submit-payment"),
    path("", views.storefront, name="storefront"),
    path("pinball-neon.svg", views.storefront_asset, {"filename": "pinball-neon.svg"}),
    path("assets/rocky/<str:filename>", views.rocky_asset, name="rocky-asset"),
    path("ultimate-pinball-logo.jpg", views.storefront_asset, {"filename": "ultimate-pinball-logo.jpg"}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
