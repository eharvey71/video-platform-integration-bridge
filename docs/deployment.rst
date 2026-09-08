.. _deployment-docs-ref:

Deployment
==========

There are several deployment strategies for the Integration Bridge application.

#. Self-hosted. Build from the repository and host in a datacenter at your institution.
#. Vendor-hosted. Bundle with a solution and give institutional admins access for configuration.
#. Cloud-hosted and managed by the developer. Hosted and customized for your needs. Depending on use-case, cost would be fair. For example, hosting an instance on Google Cloud has resulted in pennies a month due to the low network and storage utilization.

In all cases, customizations of the integration bridge may be required. More is covered in the :doc:`customization` section of this doc.

Recommended deployment (Docker)
-------------------------------

Development Server
^^^^^^^^^^^^^^^^^^

1. Clone the repo from: https://github.com/eharvey71/edtech-platform-integration-bridge
2. From the command line, change to the root of the cloned repo. Edit the Dockerfile and ensure proper config for local dev. Depending on your environment, it should look something like the following:

.. code-block::
    :caption: **Dockerfile**

    # Use an official Python runtime as a parent image
    FROM python:3.12-slim

    # Set the working directory in the container
    WORKDIR /usr/src/app

    # Copy the current directory contents into the container at /usr/src/app
    COPY . .

    # Install any needed packages specified in requirements.txt
    RUN pip install --no-cache-dir -r requirements.txt

    # Secrets are generated per container at start-up by entrypoint.sh, not baked
    # into an image layer at build time.
    COPY entrypoint.sh /usr/local/bin/entrypoint.sh
    RUN chmod +x /usr/local/bin/entrypoint.sh

    # Flask Debug off
    ENV DEBUG=False

    # Make port 80 available to the world outside this container
    EXPOSE 80

    ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

    # Use Uvicorn to run the application, replace `app:app` with your application and variable
    CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]

.. important::
    The application refuses to start unless ``FLASK_SECRET_KEY`` and ``JWT_SECRET``
    are set (the only exception is ``DEBUG=True``, which generates throwaway values
    for that process). Earlier versions silently fell back to a constant string
    compiled into the source, which meant anyone who had read the repository could
    forge a session cookie or an API token.

    Do not generate these with ``RUN`` in the Dockerfile: a secret written during
    the build is stored in an image layer and is identical in every container
    started from that image. Pass them in as environment variables, or let
    ``entrypoint.sh`` mint a per-container pair.

3. Build the sample database. The repository no longer ships a prebuilt
   ``database/epib.db`` -- it carried sample administrator password hashes and the
   Kaltura, Zoom and Canvas client secrets entered through the admin UI.

.. code-block::

    cp .env.example .env    # then fill in FLASK_SECRET_KEY and JWT_SECRET
    python build_test_db.py

4. From the root directory of the repo, build the image and launch a container (or use Docker desktop to perfom the run action)

.. code-block::

    docker build . -t integration-bridge-test
    docker run -p 4000:80 \
      -e FLASK_SECRET_KEY="$(openssl rand -base64 32)" \
      -e JWT_SECRET="$(openssl rand -base64 32)" \
      integration-bridge-test

5. Connect to http://localhost:4000/

Production Server
^^^^^^^^^^^^^^^^^

The following examples don't take into account the necessary optimization that may be required to deploy the Integation Bridge within certain cloud environments.
Please use them as a guide to get things started on certain target platforms.

The build_prod_db.py script isn't included in the repository, but you can create your own
by using the prod_test_db.py as a template.

Containerized App on Google Cloud Run - Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. important::
    In this example, it is important to note that configuration changes made within the app will not persist
    while using the default configuration, since SQLite and a static, local log files are used.

    Configuration updates and logging will appear to work fine, initially, but will likely disappear
    due to the nature of local storage on GCloud Run. If you don't intend to make changes beyond a single initial
    configuration, you'll want to make your changes in the build_prod_db.py, which will create the initial database
    during deployment with all of your desired configuration and apptokens. Logging, however, will not persist.
    In this case, you will want to automate a periodic pull of logs via the logs endpoint in order to retain udpates.

    If GCloud Run is preferred for deployment, `Google offers many storage options`_ that you'll want to explore.

    .. _Google offers many storage options: https://cloud.google.com/run/docs/storage-options

This is just one method for deploying to Google Cloud Run. 
Using the UI provided by Google for deployment works fine but may be confusing, so this assumes knowlege of the Google CLI.
This is a simplified version to help get you started. Please refer to Google's documentation
for configuring your serverless instance and setting up your monitoring dashboard.

1. Install the `Google Cloud CLI`_ for your OS
   
.. _Google Cloud CLI: https://cloud.google.com/sdk/docs/install

2. Clone the repo from: https://github.com/eharvey71/edtech-platform-integration-bridge

3. From the command line, change to the root of the cloned repo. Edit the Dockerfile for "production"

.. code-block::
    :caption: **Dockerfile**

    # Use an official Python runtime as a parent image
    FROM python:3.8-slim

    # Set the working directory in the container
    WORKDIR /usr/src/app

    # Copy the current directory contents into the container at /usr/src/app
    COPY . .

    # Install any needed packages specified in requirements.txt
    RUN pip install --no-cache-dir -r requirements-prod.txt

    # Generate a random secret key and store it in an environment variable
    # See the note above: supply FLASK_SECRET_KEY and JWT_SECRET as deployment
    # environment variables (Cloud Run: --set-secrets or --set-env-vars) instead
    # of generating them into an image layer.
    RUN echo "FLASK_SECRET_KEY=$(openssl rand -base64 32)" > .env

    # Generate a random key for JWT Auth
    RUN echo "JWT_SECRET=$(openssl rand -base64 32)" >> .env

    # Flask Debug off
    RUN echo "DEBUG=False" >> .env

    # Build the production database
    RUN python build_prod_db.py 

    # Production uses gunicorn
    CMD exec gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker  --threads 8 app:app

4. From your current cloned project directory, you may need to initialize and get your project id before completing the next steps

.. code-block::

    gcloud init
    gcloud config get-value project

5. Set your region. This example assumes us-east-5

.. code-block::

    gcloud config set run/region us-east5

6. Build the new container image using the gcloud CLI and record the resulting container URL for the next step

.. code-block::

    gcloud builds submit --tag gcr.io/{YOUR-PROJECT-ID}/integration-bridge 

7. Launch the new containerized deployment from the glcoud container registry

.. code-block::

    gcloud run deploy integration-bridge --image {CONTAINER-URL} --platform managed

Step-by-Step Full Deployment
----------------------------

The integration bridge is built using the following frameworks and libaries:

* Connexion 3 Python web framework (with Flask, Uvicorn, Swagger-UI extras)
* React 18 + TypeScript, built with Vite, for the admin interface
* SQL Alchemy ORM
* Additional Swagger-UI Bundle (when additional customization is required)

Building the admin interface
----------------------------

The admin screens are a single-page app under ``frontend/`` rather than
server-rendered templates. Flask serves the built bundle, so a deployment needs
it built first:

.. code-block::

    cd frontend
    npm install
    npm run build

That writes ``frontend/dist/``, which Flask serves for any route it does not
own. The Dockerfile does this in a separate ``node:22-slim`` stage, so a
container build needs no extra step -- and the runtime image carries only the
bundle, not the Node toolchain.

For development, run Vite's dev server alongside Flask:

.. code-block::

    uvicorn app:app --port 8000      # one terminal
    cd frontend && npm run dev       # another; serves on :5173

Vite proxies the API paths through to Flask so the browser sees a single origin
and the session cookie works unchanged. This is why ``CORS_ALLOWED_ORIGINS``
ships empty: the SPA is same-origin in both development and production, and
nothing needs a cross-origin grant.

More to come ...

