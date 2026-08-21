# PIST University Admission Ecosystem

PIST (Pakistan Institute of Science and Technology) is a fictional academic institution used to demonstrate a production-style university admissions and student management workflow.

## Project Overview

This project includes:

- Public university website
- Campus, department, and program database
- External admissions API
- Applicant receiving and processing pipeline
- Roll number generation and test scheduling
- Roll slip generation
- Staff-only university admin dashboard
- Seed data and tests

## Architecture

- Django templates for the public website and admin portal
- Django REST Framework for the external admissions endpoint
- Relational models for campuses, departments, programs, applicants, and test sessions
- Service layer for eligibility, roll numbers, and scheduling

## Technology Stack

- Python 3.12
- Django
- Django REST Framework
- django-filter
- SQLite for development
- Tailwind was not required; the UI is implemented with custom CSS

## Installation

1. Create and activate the virtual environment.
2. Install dependencies with `pip install -r backend/requirements.txt`.
3. Create a local `.env` file from `.env.example`.
4. Set `PIST_EXTERNAL_API_KEY` and `SECRET_KEY`.

## Environment Variables

- `SECRET_KEY`
- `DEBUG`
- `PIST_EXTERNAL_API_KEY`

## Database Setup

Run migrations:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

Seed the database:

```bash
cd backend
python manage.py seed_pist
```

## Running the Development Server

```bash
cd backend
python manage.py runserver
```

## Deployment

### PythonAnywhere backend

- Backend code is now inside `backend/`.
- Use `backend/passenger_wsgi.py` as the WSGI entrypoint.
- Set environment variables in the PythonAnywhere web app:
  - `SECRET_KEY`
  - `DEBUG=False`
  - `ALLOWED_HOSTS=your-domain.pythonanywhere.com`
  - `CSRF_TRUSTED_ORIGINS=https://your-domain.pythonanywhere.com`
  - `PIST_EXTERNAL_API_KEY=your-secret-key`
- Run:

```bash
cd backend
python manage.py migrate
python manage.py seed_pist
python manage.py collectstatic --noinput
```

### Vercel frontend

- Deploy the [frontend/](frontend) directory as a separate Vercel project.
- Update [frontend/vercel.json](frontend/vercel.json) with your PythonAnywhere backend domain.
- The frontend consumes the backend JSON endpoints at `/api/v1/public/site/` and `/api/v1/public/track/`.

## GitHub

This repository is ready to push to GitHub. The included [.github/workflows/django-ci.yml](.github/workflows/django-ci.yml) runs `manage.py check` and the Django tests on every push and pull request.

## Public URLs

- `/`
- `/campuses/`
- `/departments/`
- `/programs/`
- `/admissions/how-it-works/`
- `/admissions/track/`
- `/admissions/roll-slip/<uuid>/`
- `/verify/<uuid>/`

## API Documentation

### External Admissions Endpoint

`POST /api/v1/admissions/external-apply/`

Headers:

- `Content-Type: application/json`
- `X-PIST-API-KEY: your-secret-key`

### Sample cURL

```bash
curl -X POST http://localhost:8000/api/v1/admissions/external-apply/ \
  -H "Content-Type: application/json" \
  -H "X-PIST-API-KEY: your-secret-key" \
  -d '{
    "source_application_id": "CENTRAL-APP-001",
    "full_name": "Muhammad Hassan Raza",
    "father_name": "Father Name",
    "cnic": "00000-0000000-0",
    "email": "student@example.com",
    "phone": "03000000000",
    "address": "Islamabad",
    "matric_marks": 850,
    "matric_total": 1100,
    "fsc_marks": 920,
    "fsc_total": 1100,
    "tests": [{"type": "USAT", "score": 78}],
    "campus_code": "ISB",
    "program_code": "BSCS"
  }'
```

### Response

Successful applications return `HTTP 201 Created` with the generated application UUID, roll number, scheduled test details, and roll-slip URL.

## Admin Login Setup

Create a Django staff user:

```bash
cd backend
python manage.py createsuperuser
```

Then use `/university-admin/login/` to access the staff dashboard.

## Testing

```bash
cd backend
python manage.py test
```

The test suite covers:

- Campus, department, and program relationships
- External admissions API success, duplicate handling, eligibility failure, and API-key checks
- Roll slip rendering and application verification
- Staff-only admin access and status updates

## Project Structure

- `backend/admissions/` - public site, models, API, services, and seed command
- `backend/university_admin/` - staff portal and exports
- `backend/templates/` - shared layout and error pages
- `backend/static/` - global CSS and JavaScript
- `frontend/` - separate static frontend for Vercel
