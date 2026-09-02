# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Dev - Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install --no-cache-dir -r requirements-prod.txt

# Secrets are generated at container start, not at build time: a secret baked in
# with RUN sits in an image layer and is identical in every container built from
# that image. Supply FLASK_SECRET_KEY and JWT_SECRET as environment variables to
# override; otherwise entrypoint.sh generates a per-container pair.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Flask debug off
ENV DEBUG=False

# Build the starter sample database. The repository does not ship a prebuilt
# database -- it would carry sample admin credentials.
# RUN python build_test_db.py
# Build a production database - Note that SQLite will not persist within a vanilla Google Cloud Run configuration
# RUN python build_prod_db.py

# Dev - Make port 80 available to the world outside this container
EXPOSE 80

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Dev - Use Uvicorn to run the application, replace `app:app` with your application and variable
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]

# Production uses gunicorn
# CMD exec gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker  --threads 8 app:app
