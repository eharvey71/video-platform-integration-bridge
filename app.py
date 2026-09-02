from flask import send_from_directory, jsonify, request
from flask_login import login_required
import config, os
from src.models import User
from config import login_manager
from src.oauth2_config import init_oauth

# Import Blueprints
from auth.routes import auth_bp
from canvas.routes import canvas_bp
from adminapi.routes import adminapi_bp
from src.models import VendorProxies

app = config.connex_app

# Initialize OAuth
init_oauth(app.app)

# The built single-page admin UI. `npm run build` in frontend/ writes here.
SPA_DIST = config.basedir / "frontend" / "dist"


def get_vendor_proxies():
    return VendorProxies.query.get(1)


# Add API based on proxies
with app.app.app_context():
    proxies = get_vendor_proxies()
    if proxies:
        if proxies.kaltura_proxy_enabled:
            app.add_api(config.basedir / 'apispecs/swagger.yml', 
                        options={
                            "security_definitions": {
                                "oauth2_github": {
                                    "type": "oauth2",
                                    "flow": "accessCode",
                                    "authorizationUrl": "https://github.com/login/oauth/authorize",
                                    "tokenUrl": "https://github.com/login/oauth/access_token",
                                    "scopes": {
                                        "user:email": "Read user email address"
                                    }
                                },
                                "oauth2_okta": {
                                    "type": "oauth2",
                                    "flow": "accessCode",
                                    "authorizationUrl": f"{app.app.config['OKTA_DOMAIN']}/oauth2/default/v1/authorize",
                                    "tokenUrl": f"{app.app.config['OKTA_DOMAIN']}/oauth2/default/v1/token",
                                    "scopes": {
                                        "openid": "OpenID Connect scope",
                                        "profile": "User profile information",
                                        "email": "User email address"
                                    }
                                }
                            },
                            "security": [{"oauth2_github": ["user:email"]}, {"oauth2_okta": ["openid", "profile", "email"]}]
                        }, swagger_ui_options=config.swagoptions)
        if proxies.zoom_proxy_enabled:
            app.add_api(config.basedir / 'apispecs/swaggerzoom.yml', swagger_ui_options=config.swagoptions)

# Register Blueprints
app.app.register_blueprint(auth_bp, url_prefix='/auth')
app.app.register_blueprint(canvas_bp, url_prefix='/canvas')
app.app.register_blueprint(adminapi_bp, url_prefix='/adminapi')


@login_manager.user_loader
def user_loader(user_id):
    """Given *user_id*, return the associated User object."""
    return User.query.get(user_id)


@login_manager.unauthorized_handler
def unauthorized():
    """The admin UI talks JSON, so an expired session must not redirect it to an
    HTML login page -- the SPA reads the 401 and shows its own."""
    if request.path.startswith('/adminapi/'):
        return jsonify({"error": "Authentication required"}), 401
    return send_spa()


@app.route('/logs/<path:path>')
@login_required
def send_report(path):
    return send_from_directory('logs', path)


@app.route('/assets/<path:path>')
def spa_assets(path):
    """Hashed JS/CSS bundles emitted by Vite."""
    return send_from_directory(SPA_DIST / 'assets', path)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(config.basedir / 'static', 'favicon.ico')


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def send_spa(path=''):
    """Serve the SPA shell for any route the server does not own.

    Client-side routing means /kaltura/tokens et al. must return index.html on a
    hard refresh. Registered last so the API blueprints and the Connexion-mounted
    vendor specs keep their paths.
    """
    index = SPA_DIST / 'index.html'
    if not index.exists():
        return (
            "<h1>Admin UI is not built</h1>"
            "<p>Run <code>npm install &amp;&amp; npm run build</code> in <code>frontend/</code>, "
            "or <code>npm run dev</code> for the dev server.</p>",
            503,
        )
    return send_from_directory(SPA_DIST, 'index.html')


if __name__ == "__main__":
    # Local development entry point only. Production runs under uvicorn/gunicorn
    # (see Dockerfile).
    app.run(host=os.getenv("DEV_BIND_HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
