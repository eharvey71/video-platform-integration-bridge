# Admin UI

React + TypeScript single-page app, built with Vite. It replaces the Jinja
templates the bridge used to render server-side.

## Running it

The app talks to the Flask backend at `/adminapi` on the **same origin**, so the
session cookie is sent without any CORS involvement. That shapes both workflows
below.

### Development

Two processes. Flask on 8000:

```bash
cp .env.example .env          # from the repo root; fill in the two secrets
python build_test_db.py       # first run only
uvicorn app:app --port 8000
```

Vite on 5173, in this directory:

```bash
npm install
npm run dev
```

Then open http://localhost:5173. Vite proxies `/adminapi`, `/auth`, `/canvas`,
`/api`, `/zoomapi` and `/logs` through to Flask, so the browser still sees one
origin and the session cookie works. Nothing needs to go in
`CORS_ALLOWED_ORIGINS` for this.

### Production

```bash
npm run build
```

writes `frontend/dist/`, which Flask serves: `index.html` for any route it does
not own, and hashed bundles from `/assets/`. The Dockerfile does this in a
separate `node:22-slim` stage so the runtime image carries the bundle without
the toolchain.

## Layout

```
src/
  api/client.ts       typed fetch wrapper; attaches the CSRF header
  api/types.ts        response shapes, mirroring adminapi/routes.py
  auth/               session context: who is signed in, login, logout
  components/         Layout, shared UI primitives, useResource
  pages/              one screen per route
  styles.css          design tokens and every rule; no CSS framework
```

## Two things worth knowing

**CSRF.** The server mints a token into the session and mirrors it into a
JS-readable `csrf_token` cookie. `api/client.ts` sends it back as
`X-CSRF-Token` on every non-GET. Both halves are required, and a cross-site page
cannot read the cookie to forge the header. The token rotates on login and
logout.

**Secrets are one-way.** Zoom and Canvas client secrets are never returned by
the API — reads report `clientSecretSet: true/false` instead. The forms send a
secret only when the field is non-empty, so saving the rest of a form leaves the
stored secret alone rather than blanking it.
