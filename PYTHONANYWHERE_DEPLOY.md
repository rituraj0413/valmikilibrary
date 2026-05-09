# PythonAnywhere Deployment

This project is ready to deploy on PythonAnywhere with a manual Django web app.

Important:
- This project uses `Django 6.0.3`, so use `Python 3.12` or `Python 3.13`.
- Keep `DJANGO_DEBUG=False` on the live site.
- Replace `<your-username>` everywhere below with your real PythonAnywhere username.

## 1. Upload the code

Open a Bash console on PythonAnywhere and run:

```bash
cd ~
git clone <your-github-repo-url> valmikilibrary
cd ~/valmikilibrary
```

If your code is already there:

```bash
cd ~/valmikilibrary
git pull origin main
```

## 2. Create a virtualenv

Use Python 3.13 if your account supports it. Otherwise use 3.12.

```bash
mkvirtualenv --python=/usr/bin/python3.13 valmikilibrary-venv
workon valmikilibrary-venv
cd ~/valmikilibrary
pip install -r requirements.txt
```

## 3. Create the web app

In the PythonAnywhere `Web` tab:

1. Click `Add a new web app`
2. Choose `Manual configuration`
3. Choose `Python 3.13` or `Python 3.12`
4. Set:
   - `Source code`: `/home/<your-username>/valmikilibrary`
   - `Working directory`: `/home/<your-username>/valmikilibrary`
   - `Virtualenv`: `/home/<your-username>/.virtualenvs/valmikilibrary-venv`

## 4. Edit the WSGI file

Open the WSGI file from the `Web` tab and use this:

```python
import os
import sys

path = '/home/<your-username>/valmikilibrary'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'valmikilibrary.settings')

os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DJANGO_ALLOWED_HOSTS'] = '<your-username>.pythonanywhere.com'
os.environ['DJANGO_CSRF_TRUSTED_ORIGINS'] = 'https://<your-username>.pythonanywhere.com'
os.environ['DJANGO_SECRET_KEY'] = 'replace-with-a-new-secret-key'

# Gmail SMTP
os.environ['EMAIL_HOST'] = 'smtp.gmail.com'
os.environ['EMAIL_PORT'] = '587'
os.environ['EMAIL_USE_TLS'] = 'true'
os.environ['EMAIL_HOST_USER'] = 'yourgmail@gmail.com'
os.environ['EMAIL_HOST_PASSWORD'] = 'your-16-char-app-password'
os.environ['DEFAULT_FROM_EMAIL'] = 'Valmiki Library <yourgmail@gmail.com>'

# Public access request email
os.environ['LIBRARY_ACCESS_REQUEST_EMAIL'] = 'realjyotish0001@gmail.com'

# Razorpay
os.environ['RAZORPAY_KEY_ID'] = 'your_razorpay_key_id'
os.environ['RAZORPAY_KEY_SECRET'] = 'your_razorpay_key_secret'
os.environ['RAZORPAY_CURRENCY'] = 'INR'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 5. Run migrations and collect static

Back in a Bash console:

```bash
workon valmikilibrary-venv
cd ~/valmikilibrary
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
```

## 6. Static and media mappings

In the `Web` tab, add these mappings:

- URL: `/static/`
  Path: `/home/<your-username>/valmikilibrary/staticfiles`

- URL: `/media/`
  Path: `/home/<your-username>/valmikilibrary/media`

## 7. Create admin login

If you do not already have a superuser on the server:

```bash
workon valmikilibrary-venv
cd ~/valmikilibrary
python manage.py createsuperuser
```

## 8. Reload the web app

Go to the `Web` tab and click `Reload`.

## 9. Update after future code changes

Whenever you push new code:

```bash
cd ~/valmikilibrary
git pull origin main
workon valmikilibrary-venv
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
```

Then click `Reload` in the `Web` tab.

## Notes

- This project currently uses `SQLite`. It can work on PythonAnywhere, but for bigger production usage PostgreSQL is a stronger long-term option.
- If your site shows `Bad Request (400)`, it usually means `DJANGO_ALLOWED_HOSTS` or `DJANGO_CSRF_TRUSTED_ORIGINS` is wrong.
- If admin CSS is missing, run `collectstatic` again and re-check the `/static/` mapping.
