import hashlib
import json
import re
import secrets
import uuid
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import CustomerProfile, Order, OrderItem, Product


def storefront(_request):
    page = settings.REPO_ROOT / "index.html"
    if not page.is_file():
        raise Http404("Storefront is not available")
    return FileResponse(page.open("rb"), content_type="text/html; charset=utf-8")


def storefront_asset(_request, filename):
    if filename not in {"pinball-neon.svg", "ultimate-pinball-logo.jpg", "ultimate-pinball-icon.png", "sweet-hearts-full.jpg"}:
        raise Http404
    asset = settings.REPO_ROOT / filename
    if not asset.is_file():
        raise Http404
    return FileResponse(asset.open("rb"))


def rocky_asset(_request, filename):
    allowed = {
        "rocky-machine-angle.jpg",
        "rocky-machine-front.jpg",
        "rocky-backglass.jpg",
        "rocky-playfield-detail.jpg",
        "rocky-cabinet-detail.jpg",
        "rocky-plunger.jpg",
    }
    if filename not in allowed:
        raise Http404
    asset = settings.REPO_ROOT / "assets" / "rocky" / filename
    if not asset.is_file():
        raise Http404
    return FileResponse(asset.open("rb"), content_type="image/jpeg")


def serialize_product(product, request=None):
    images = []
    if product.images:
        uploaded_image = product.images.url
        if request is not None:
            uploaded_image = request.build_absolute_uri(uploaded_image)
        images.append(uploaded_image)
    uploaded_gallery = []
    for gallery_image in product.uploaded_gallery_images.all():
        gallery_url = gallery_image.image.url
        if request is not None:
            gallery_url = request.build_absolute_uri(gallery_url)
        uploaded_gallery.append(gallery_url)
    images.extend(uploaded_gallery)
    images.extend(product.gallery_images or [])
    return {
        "id": product.pk,
        "external_id": product.external_id,
        "slug": product.slug,
        "title": product.title,
        "description": product.description,
        "price": str(product.price),
        "product_type": product.product_type,
        "tags": product.tags,
        "images": images,
        "available": product.available,
        "inventory": product.stock_quantity if product.available else 0,
        "created_at": product.created_at.isoformat(),
    }


@require_GET
def product_list(request):
    products = Product.objects.filter(is_active=True)
    query = request.GET.get("q", "").strip()[:100]
    category = request.GET.get("category", "").strip().lower()
    if query:
        from django.db.models import Q
        products = products.filter(Q(title__icontains=query) | Q(product_type__icontains=query))
    if category in {"machines", "accessories", "parts", "merch"}:
        products = products.filter(product_type__icontains=category[:-1] if category.endswith("s") else category)
    products = products.order_by("-created_at", "title")
    return JsonResponse({"results": [serialize_product(product, request) for product in products]})


@require_GET
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return JsonResponse(serialize_product(product, request))


def read_json(request):
    if request.content_type != "application/json":
        raise ValueError("Send the request as application/json.")
    if len(request.body) > 32_768:
        raise ValueError("Request is too large.")
    try:
        value = json.loads(request.body or b"{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("The request body must contain valid JSON.") from exc
    if not isinstance(value, dict):
        raise ValueError("The request body must be a JSON object.")
    return value


def order_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def customer_account_data(user):
    profile = CustomerProfile.objects.filter(user=user).first()
    return {
        "name": user.get_full_name(),
        "email": user.email,
        "phone": profile.phone if profile else "",
        "shipping_address": profile.shipping_address if profile else "",
    }


@ensure_csrf_cookie
@require_GET
def auth_csrf(request):
    return JsonResponse({"csrf_token": get_token(request)})


@csrf_protect
@require_POST
def auth_register(request):
    try:
        data = read_json(request)
    except ValueError as exc:
        return order_error(str(exc))

    name = " ".join(str(data.get("name", "")).split())[:120]
    email = str(data.get("email", "")).strip().lower()[:254]
    phone = str(data.get("phone", "")).strip()[:40]
    shipping_address = str(data.get("shipping_address", "")).strip()[:1000]
    password = str(data.get("password", ""))
    if len(name) < 2:
        return order_error("Enter your name.")
    try:
        validate_email(email)
    except ValidationError:
        return order_error("Enter a valid email address.")
    if len(password) < 8:
        return order_error("Use a password with at least 8 characters.")

    User = get_user_model()
    if User.objects.filter(email__iexact=email).exists():
        return order_error("An account with this email already exists. Sign in instead.", 409)

    first_name, _, last_name = name.partition(" ")
    username = f"customer_{uuid.uuid4().hex}"
    user_candidate = User(username=username, email=email, first_name=first_name, last_name=last_name)
    try:
        validate_password(password, user=user_candidate)
    except ValidationError as exc:
        return order_error(" ".join(exc.messages))

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=False,
                is_superuser=False,
            )
            CustomerProfile.objects.create(user=user, phone=phone, shipping_address=shipping_address)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    except Exception:
        return order_error("We could not create your account. Please try again.", 503)
    return JsonResponse({"authenticated": True, "customer": customer_account_data(user)}, status=201)


@csrf_protect
@require_POST
def auth_login(request):
    try:
        data = read_json(request)
    except ValueError as exc:
        return order_error(str(exc))
    email = str(data.get("email", "")).strip().lower()[:254]
    password = str(data.get("password", ""))
    User = get_user_model()
    user_record = User.objects.filter(email__iexact=email, is_active=True).first()
    user = authenticate(request, username=user_record.get_username(), password=password) if user_record else None
    if not user:
        return order_error("Email or password is incorrect.", 401)
    login(request, user)
    return JsonResponse({"authenticated": True, "customer": customer_account_data(user)})


@csrf_protect
@require_POST
def auth_logout(request):
    logout(request)
    return JsonResponse({"authenticated": False})


@require_GET
def auth_me(request):
    if not request.user.is_authenticated or request.user.is_staff:
        return JsonResponse({"authenticated": False})
    return JsonResponse({"authenticated": True, "customer": customer_account_data(request.user)})


def expire_reservation(order):
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().filter(pk=order.pk, status=Order.Status.PENDING).first()
        if not locked_order or locked_order.expires_at > timezone.now():
            return False
        for item in locked_order.items.all():
            product = Product.objects.select_for_update().get(pk=item.product_id)
            product.stock_quantity += item.quantity
            product.save(update_fields=["stock_quantity", "updated_at"])
        locked_order.status = Order.Status.EXPIRED
        locked_order.save(update_fields=["status", "updated_at"])
        return True


@csrf_exempt
@require_POST
def create_order(request):
    try:
        data = read_json(request)
    except ValueError as exc:
        return order_error(str(exc))

    name = str(data.get("customer_name", "")).strip()[:120]
    email = str(data.get("customer_email", "")).strip()[:254].lower()
    phone = str(data.get("customer_phone", "")).strip()[:40]
    shipping_address = str(data.get("shipping_address", "")).strip()[:1000]
    asset = str(data.get("payment_asset", "")).strip().lower()
    items = data.get("items")
    wallet = settings.CRYPTO_WALLETS.get(asset)

    if len(name) < 2:
        return order_error("Enter your name.")
    try:
        validate_email(email)
    except ValidationError:
        return order_error("Enter a valid email address.")
    if not wallet:
        return order_error("Choose Bitcoin, Ethereum, or USDT.")
    if not wallet["address"]:
        return order_error("This payment option is not configured yet.", 503)
    if not isinstance(items, list) or not items or len(items) > 25:
        return order_error("Add at least one item to the order.")

    quantities = {}
    for item in items:
        if not isinstance(item, dict):
            return order_error("One of the cart items is invalid.")
        slug = str(item.get("slug", "")).strip()[:180]
        try:
            quantity = int(item.get("quantity", 0))
        except (TypeError, ValueError):
            return order_error("Enter a valid quantity for each item.")
        if not slug or quantity < 1 or quantity > 10:
            return order_error("Each item quantity must be between 1 and 10.")
        quantities[slug] = quantities.get(slug, 0) + quantity
        if quantities[slug] > 10:
            return order_error("The maximum quantity per item is 10.")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = timezone.now()
    try:
        with transaction.atomic():
            products = list(Product.objects.select_for_update().filter(slug__in=quantities, is_active=True))
            by_slug = {product.slug: product for product in products}
            if len(by_slug) != len(quantities):
                return order_error("A product in your cart is no longer available. Refresh the shop and try again.", 409)
            for slug, quantity in quantities.items():
                if by_slug[slug].stock_quantity < quantity:
                    return order_error(f"{by_slug[slug].title} does not have enough stock for that quantity.", 409)

            total = sum((by_slug[slug].price * quantity for slug, quantity in quantities.items()), start=0)
            order = Order.objects.create(
                customer_account=request.user if request.user.is_authenticated and not request.user.is_staff else None,
                customer_name=name,
                customer_email=email,
                customer_phone=phone,
                shipping_address=shipping_address,
                payment_asset=asset,
                payment_network=wallet["network"],
                receiving_address=wallet["address"],
                total_usd=total,
                access_token_hash=token_hash,
                expires_at=now + timedelta(minutes=settings.ORDER_RESERVATION_MINUTES),
            )
            for slug, quantity in quantities.items():
                product = by_slug[slug]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    title_snapshot=product.title,
                    unit_price=product.price,
                    quantity=quantity,
                )
                product.stock_quantity -= quantity
                product.save(update_fields=["stock_quantity", "updated_at"])
    except Exception:
        return order_error("We could not create your order right now. Please try again.", 503)

    return JsonResponse({
        "reference": str(order.reference),
        "status": order.status,
        "amount_usd": str(order.total_usd),
        "payment": {"asset": asset, "network": wallet["network"], "address": wallet["address"]},
        "instructions": "Send the current market equivalent of the USD total on this network only. Payments are checked manually; submit the transaction hash after sending.",
        "order_token": raw_token,
        "expires_at": order.expires_at.isoformat(),
    }, status=201)


@csrf_exempt
@require_POST
def submit_payment(request, reference):
    try:
        data = read_json(request)
    except ValueError as exc:
        return order_error(str(exc))
    token = request.headers.get("Authorization", "")
    if not token.startswith("Bearer "):
        return order_error("Order access token is required.", 401)
    provided_hash = hashlib.sha256(token[7:].encode("utf-8")).hexdigest()
    order = get_object_or_404(Order, reference=reference)
    if not secrets.compare_digest(provided_hash, order.access_token_hash):
        return order_error("Order access token is invalid.", 403)
    if order.status == Order.Status.PENDING and order.reservation_expired:
        expire_reservation(order)
        return order_error("This order reservation expired. Create a new order before sending payment.", 409)
    if order.status in {Order.Status.PAID, Order.Status.CANCELLED, Order.Status.EXPIRED}:
        return order_error("This order can no longer accept payment submissions.", 409)
    tx_hash = str(data.get("transaction_hash", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9:_-]{8,160}", tx_hash):
        return order_error("Enter a valid transaction ID or hash.")
    if Order.objects.exclude(pk=order.pk).filter(transaction_hash=tx_hash).exists():
        return order_error("That transaction ID is already attached to another order.", 409)
    order.transaction_hash = tx_hash
    order.status = Order.Status.SUBMITTED
    order.save(update_fields=["transaction_hash", "status", "updated_at"])
    return JsonResponse({"reference": str(order.reference), "status": order.status, "message": "Transaction received. The store will verify it manually."})
