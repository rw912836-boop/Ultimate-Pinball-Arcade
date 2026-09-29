# Ultimate Pinball Arcade Django backend

This Django 5.2.17+ backend provides the product catalog API, inventory-backed order creation, crypto payment instructions, transaction-hash submission, and the staff admin. Python 3.11 is supported.

## Run locally (Windows PowerShell)

From the repository root:

```powershell
Copy-Item .env.example .env
Set-Location backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py import_catalog
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/` for the storefront and `/admin/` to manage products, stock, and orders. The first catalog import initializes currently available products with quantity 1 and sold-out products with quantity 0. Replace those starter values with your confirmed stock counts in Admin before accepting live orders. Re-importing updates product details while preserving stock quantities.

## Crypto checkout setup

Set these environment variables on the Django host before enabling checkout:

| Variable | Payment network |
| --- | --- |
| `WALLET_BTC_ADDRESS` | Bitcoin |
| `WALLET_ETH_ADDRESS` | Ethereum mainnet |
| `WALLET_USDT_TRC20_ADDRESS` | USDT on TRON (TRC20) |

The API creates an order from database prices, reserves stock for 30 minutes, and returns the selected wallet address. Customers can submit a transaction hash. Staff must verify each payment on-chain and mark it paid in Admin; the app does not detect blockchain payments automatically or calculate a live crypto conversion quote. Run `python manage.py expire_orders` periodically to release stock reserved by unpaid orders.

## Deploying

GitHub Pages serves static files and cannot run Django or its database. Set the hosting service root directory to `backend` and deploy it to a Python web host with PostgreSQL, set a strong `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=false`, configure `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, and the wallet variables, then run `python manage.py collectstatic --noinput`, apply migrations, and run `python manage.py import_catalog`. The Django app serves the storefront at `/` and the logo/animation assets from the repository root.

For a separately hosted frontend, set the `api-base` meta tag in `index.html` to the Django API origin and set `DJANGO_CORS_ALLOWED_ORIGINS` to the exact storefront origin. Keep the API and browser page on HTTPS in production.

## API

- `GET /api/products/` — product list; optional `q` search.
- `GET /api/products/<slug>/` — product details.
- `POST /api/orders/` — create and reserve an order from product slugs and quantities.
- `POST /api/orders/<reference>/payment/` — attach a transaction hash using the bearer order token returned at order creation.

The public API never marks an order paid. Payment verification and inventory adjustments are handled in Django Admin.
