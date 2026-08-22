# Deployment Guide

## Backend: PythonAnywhere

1. Create a new PythonAnywhere web app with the same Python version used locally.
2. Point the WSGI configuration to `backend/passenger_wsgi.py` or use the Django WSGI app from `backend/config/wsgi.py`.
3. Set the environment variables:
   - `SECRET_KEY`
   - `DEBUG=False`
   - `ALLOWED_HOSTS=your-domain.pythonanywhere.com`
   - `CSRF_TRUSTED_ORIGINS=https://your-domain.pythonanywhere.com`
   - `PIST_EXTERNAL_API_KEY=your-secret-key`
   - `USE_HTTPS_PROXY=True`
   - `SESSION_COOKIE_SECURE=True`
   - `CSRF_COOKIE_SECURE=True`
   - `SECURE_SSL_REDIRECT=True`
4. Run migrations and seed data:

```bash
cd backend
python manage.py migrate
python manage.py seed_pist
python manage.py collectstatic --noinput
```

5. Map `/static/` and `/media/` in the PythonAnywhere web tab if you are not using WhiteNoise.

Student document and profile files should be served through the authenticated portal views in production. Do not expose the development `MEDIA_URL` mapping publicly for private student records.

## Frontend: Vercel

1. Create a separate Vercel project with the root directory set to `frontend/`.
2. Edit `frontend/vercel.json` and replace `YOUR-PYTHONANYWHERE-USERNAME.pythonanywhere.com` with your actual backend domain.
3. Deploy the static site.
4. The frontend calls the backend using the proxied `/api/v1/...` routes.

## Notes

- The Django backend and Vercel frontend are intentionally separated.
- The admin portal stays on the PythonAnywhere backend.
- The backend public JSON endpoints support the Vercel frontend without CORS.
