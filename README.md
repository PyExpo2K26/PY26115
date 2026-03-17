# FloodGuard

FloodGuard is a Flask web app that estimates flood risk for Chennai using rainfall, elevation, and user reports. It includes user login, an admin dashboard, and APIs for flood checks, history, and evacuation routing.

## Features
- Flood risk checks by location with geocoding
- Hourly background job to build risk history
- Crowd-sourced flood depth reports
- Evacuation routing using OpenStreetMap data

## Local Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run the app:
   ```bash
   python app.py
   ```

The app runs at http://127.0.0.1:5000.

## Docker

Build and run the container:
```bash
docker build -t floodguard .
docker run -p 10000:10000 -e SECRET_KEY=dev -e DB_PATH=/data/flood.db -v flood-data:/data floodguard
```

## Render Deployment (Docker)

This project includes [render.yaml](render.yaml) for one-click deployment.

1. Push this repository to GitHub.
2. In Render, click **New +** → **Blueprint** and select the repo.
3. Set required environment variables in the Render dashboard:
   - `SECRET_KEY` (required)
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` (optional email alerts)
4. Deploy. Render provisions a persistent disk at `/data` for `flood.db`.

### Notes
- `RUN_SCHEDULER=1` starts the hourly background job in the web process. Keep workers at 1 to avoid duplicate jobs.
- `SKIP_SEED=1` disables the initial grid seeding if you want a faster first boot.
- `ENABLE_ROUTING=0` disables evacuation routing if you want to reduce resource usage.

## Environment Variables
- `SECRET_KEY`: Flask session secret key
- `DB_PATH`: Path to SQLite DB (default: `flood.db` in project root)
- `RUN_SCHEDULER`: Set to `0` to disable hourly background job
- `SKIP_SEED`: Set to `1` to skip location seeding
- `ENABLE_ROUTING`: Set to `0` to disable evacuation routing
- `GUNICORN_WORKERS`: Gunicorn worker count (default 1)
- `GUNICORN_THREADS`: Gunicorn thread count per worker (default 4)
- `GUNICORN_TIMEOUT`: Gunicorn timeout in seconds (default 120)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`: Email notifications
