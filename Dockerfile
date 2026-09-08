# --- Stage 1: build the admin single-page app ------------------------------
FROM node:22-slim AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: the application ----------------------------------------------
FROM python:3.12-slim

WORKDIR /usr/src/app

COPY . .
# The built bundle, not the toolchain: node stays out of the runtime image.
COPY --from=frontend /build/dist ./frontend/dist

# Dev - Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install --no-cache-dir -r requirements-prod.txt

# Secrets are generated at container start, not at build time: a secret baked in
# with RUN sits in an image layer and is identical in every container built from
# that image. Supply FLASK_SECRET_KEY and JWT_SECRET as environment variables to
# override; otherwise entrypoint.sh generates a per-container pair.
RUN chmod +x /usr/src/app/entrypoint.sh

# Flask debug off
ENV DEBUG=False

# Build the starter sample database. The repository does not ship a prebuilt
# database -- it would carry sample admin credentials.
# RUN python build_test_db.py
# Build a production database - Note that SQLite will not persist within a vanilla Google Cloud Run configuration
# RUN python build_prod_db.py

# Dev - Make port 80 available to the world outside this container
EXPOSE 80

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]

# Dev - Use Uvicorn to run the application, replace `app:app` with your application and variable
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]

# Production uses gunicorn
# CMD exec gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker  --threads 8 app:app
