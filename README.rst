Welcome to the Video Platform Integration Bridge
================================================================

Have a look at the documentation for more:
https://edtech-platform-integration-bridge.readthedocs.io/en/latest/index.html

This iteration serves as a "middleware" application and abstraction tool for working with Kaltura and Zoom APIs.
Due to policies and standards in dealing with sensitive data (students, trainees) it is important for schools (Higher Ed, K12) and corporations to track interactions between third party (external, SaaS, cloud-hosted) vendor integrations and internal platforms.

The integration bridge currently performs the following
-----------------------------------------------------------------------

* Allows administrators to securely store and track Kaltura App Tokens. In some cases, many app tokens may need to be created in order to provide proper security.
* Can create customized API endpoints for third party vendors who want to integrate with Kaltura, abstracting existing APIs into only those that are needed.
* Now supports Zoom API integration. Similar to Kaltura in that it abstracts the Zoom APIs into only those that are needed and provides a way to track interactions.
* Logs all events.
* Creates a way to filter on allowed Kaltura categories.
* Labels (tied to app tokens) can be created. Vendors use the labels for creating Kaltura sessions, preventing direct access to the Kaltura APIs.
* Leverages a swagger UI for rapid endpoint development and testing on the fly.
* Easy Deployment. Open Source. Host anywhere.
* Administration is a React + TypeScript single-page app, served by the same Flask process.

Purpose
-------

* The demand for adherance to standards by third party companies and solution providers.
* While the Kaltura video content management platform is a wonderful product (and comes highly recommended), there are some shortfalls when scaled to enterprise levels within the institution:

  * Multiple app tokens need to be created and tracked in order to provide the security and restrictions that university admins desire (read-only access to specific categories).
  * Setting entitlements on specific categories manually in KMC isn’t scalable and may not provide the granularity necessary when a third party is using APIs.
  * Setting Privacy Contexts in the KMC would provide access to specific categories that could then be applied to a single app token… but it breaks in production: “Cannot set multiple privacy contexts when Disable Category Limit feature is turned on”.

Getting started
---------------

.. code-block::

    cp .env.example .env      # then set FLASK_SECRET_KEY and JWT_SECRET
    pip install -r requirements.txt
    python build_test_db.py   # creates database/epib.db with sample data

    cd frontend && npm install && npm run build && cd ..
    uvicorn app:app --port 8000

The app will not start without ``FLASK_SECRET_KEY`` and ``JWT_SECRET`` -- see
``.env.example``. The sample database is generated rather than committed, so a
fresh clone never carries credentials.

Future development
------------------

* Shifting focus from LMS Support to purely video management platforms and lecture capture.
* YouTube, Panopto, Canvas Studio, and Yuja are on the roadmap.
* One connection, abstracting endpoints from many tools into what is needed for a single third party tool.
* Done - Kaltura support will become a separate module. Support for major LMSs.

Visit my website: `edutechdev.com <https://www.edutechdev.com/>`_

