web: python backend/manage.py migrate --noinput && python backend/manage.py import_catalog && gunicorn --chdir backend config.wsgi:application --bind 0.0.0.0:$PORT
