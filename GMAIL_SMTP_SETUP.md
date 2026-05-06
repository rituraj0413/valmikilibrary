Gmail SMTP setup for Valmiki Library

1. Turn on 2-Step Verification in your Google account.
2. Create an App Password for Mail.
3. Start Django with these environment variables:

```bash
export EMAIL_HOST="smtp.gmail.com"
export EMAIL_PORT="587"
export EMAIL_USE_TLS="true"
export EMAIL_HOST_USER="realjyotish0001@gmail.com"
export EMAIL_HOST_PASSWORD="jekl aduw tbul zice"
export DEFAULT_FROM_EMAIL="Valmiki Library <yourgmail@gmail.com>"
python manage.py runserver
```

4. Open the student portal login page and use "Send Verification Email".
5. The email should now go to the student's real inbox instead of only printing in the terminal.

Notes

- Do not use your normal Gmail password. Use an App Password.
- If `EMAIL_HOST_USER` or `EMAIL_HOST_PASSWORD` is missing, the project falls back to console email for local development.
