from flask import render_template, redirect, url_for, send_from_directory, request, flash
from flask_login import login_required, current_user
import config, logging, os
from src.models import User, UICustomizations, VendorProxies
from config import login_manager
from src.oauth2_config import init_oauth, github_token_info, okta_token_info, oauth2_scope_validate

# Import Blueprints
from auth.routes import auth_bp
from kaltura.routes import kaltura_bp
from settings.routes import settings_bp
from canvas.routes import canvas_bp
from zoom.routes import zoom_bp

def get_vendor_proxies():
    return VendorProxies.query.get(1)

@config.connex_app.app.context_processor
def app_globals():
    app_title = UICustomizations.query.get(1)
    proxies = get_vendor_proxies()
    if app_title:
        title = app_title.integrator_title
    else:
        title = 'Integration Manager'
    # With no VendorProxies row these names used to go unbound and every render
    # raised UnboundLocalError. Absent configuration means nothing is enabled.
    return dict(custom_title=title,
                kaltura_enabled=bool(proxies and proxies.kaltura_proxy_enabled),
                canvas_enabled=bool(proxies and proxies.canvas_proxy_enabled),
                zoom_enabled=bool(proxies and proxies.zoom_proxy_enabled))

app = config.connex_app

# Initialize OAuth
init_oauth(app.app)

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
app.app.register_blueprint(kaltura_bp, url_prefix='/kaltura')
app.app.register_blueprint(settings_bp, url_prefix='/settings')
app.app.register_blueprint(canvas_bp, url_prefix='/canvas')
app.app.register_blueprint(zoom_bp, url_prefix='/zoom')

@login_manager.user_loader
def user_loader(user_id):
    """Given *user_id*, return the associated User object.
    :param unicode user_id: user_id (email) user to retrieve
    """
    return User.query.get(user_id)

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('logpage'))
    else:
        return redirect(url_for('auth.login'))

@app.route('/log')
@login_required
def logpage():
    #b_lines = [row for row in reversed(list(open("logs/log", "r")))]
    
    logger = logging.getLogger("RotatingLog")
    b_lines = [row for row in reversed(list(open(logger.handlers[0].baseFilename, "r")))]

    return render_template('log.html', b_lines=b_lines)

@app.route('/logs/<path:path>')
@login_required
def send_report(path):
    return send_from_directory('logs', path)

@app.route('/apidocs')
@login_required
def apidocs():
    api_type = request.args.get('api_type', 'kaltura')  # Default to Kaltura if not specified
    proxies = get_vendor_proxies()

    if api_type == 'kaltura' and proxies and proxies.kaltura_proxy_enabled:
        api_url = "/api/ui/"
    elif api_type == 'zoom' and proxies and proxies.zoom_proxy_enabled:
        api_url = "/zoomapi/ui/"
    else:
        # Handle the case where the requested API is not enabled
        flash('The requested API documentation is not available.', 'warning')
        return redirect(url_for('home'))

    return render_template('apidocs.html', api_url=api_url)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', username=current_user.username, role=current_user.role)
    
if __name__ == "__main__":
    # Local development entry point only. Production runs under uvicorn/gunicorn
    # (see Dockerfile).
    app.run(host=os.getenv("DEV_BIND_HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
