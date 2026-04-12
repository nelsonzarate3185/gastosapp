#!/usr/bin/env bash
set -o errexit

# Instalar Tesseract OCR y soporte para español
apt-get install -y tesseract-ocr tesseract-ocr-spa

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superusuario creado.')
else:
    print('Superusuario ya existe.')
"