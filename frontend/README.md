# PIST Frontend

This folder is the Vercel-deployable public frontend for PIST.

## What it does

- Renders the public university landing page
- Loads campus and program data from the backend JSON API
- Provides application tracking against the backend API

## Vercel setup

- Set the project root to this `frontend/` folder
- Update `vercel.json` with the PythonAnywhere backend domain
- The frontend expects these backend routes:
  - `/api/v1/public/site/`
  - `/api/v1/public/track/?reference=...`

## Files

- `index.html` - public page shell
- `styles.css` - institutional UI styling
- `app.js` - data loading and tracking logic
- `vercel.json` - API rewrite to the backend
