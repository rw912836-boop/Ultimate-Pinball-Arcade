import os
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
load_dotenv(REPO_ROOT / ".env")

DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes"}
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-only-change-me")
if not DEBUG and SECRET_KEY == "local-development-only-change-me":
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY in production.")

ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
CORS_ALLOWED_ORIGINS = sorted({origin.strip() for origin in os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()} | {
    "https://ultimatepinballarcade.com",
    "https://www.ultimatepinballarcade.com",
})
CORS_ALLOW_CREDENTIALS = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "shop.apps.ShopConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
default_sqlite_path = Path(volume_mount) / "db.sqlite3" if volume_mount else BASE_DIR / "db.sqlite3"
configured_sqlite_path = os.getenv("SQLITE_PATH", "").strip()
SQLITE_PATH = Path(configured_sqlite_path) if configured_sqlite_path else default_sqlite_path
SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": SQLITE_PATH}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
default_media_root = Path(volume_mount) / "media" if volume_mount else BASE_DIR / "media"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(default_media_root)))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

CRYPTO_WALLETS = {
    "btc": {"label": "Bitcoin (BTC)", "network": "Bitcoin network", "address": os.getenv("WALLET_BTC_ADDRESS", "")},
    "eth": {"label": "Ethereum (ETH)", "network": "Ethereum mainnet", "address": os.getenv("WALLET_ETH_ADDRESS", "")},
    "usdt": {"label": "Tether (USDT)", "network": "TRON / TRC20", "address": os.getenv("WALLET_USDT_TRC20_ADDRESS", "")},
}
ORDER_RESERVATION_MINUTES = int(os.getenv("ORDER_RESERVATION_MINUTES", "30"))

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "true").lower() in {"1", "true", "yes"}
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
