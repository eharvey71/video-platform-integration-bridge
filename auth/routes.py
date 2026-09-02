"""Server-side OAuth2 sign-in flows.

Username/password sign-in lives in the admin JSON API (POST /adminapi/session).
What stays here is the part that cannot be done from the SPA: the redirect out
to the identity provider and the callback it returns to.
"""
from flask import Blueprint, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required

from src.models import User
import src.logger as logger
from src.csrf import rotate_csrf_token
from src.oauth2_config import oauth

auth_bp = Blueprint('auth', __name__)


def _complete_login(provider, user_info, token):
    """Shared tail of both callbacks."""
    email = user_info.get('email')
    if not email:
        # A provider may withhold the address (GitHub hides private ones).
        # Looking that up would query for email IS NULL instead of failing closed.
        flash(f'Your {provider} account does not expose a usable email address.', 'error')
        logger.log(f"{provider} login failed: provider returned no email address")
        return redirect('/login?error=no_email')

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('No user found with this email. Please contact your administrator.', 'error')
        logger.log(f"{provider} login failed: No user found for email {email}")
        return redirect('/login?error=unknown_user')

    login_user(user)
    session['oauth_token'] = token
    session['oauth_provider'] = provider.lower()
    rotate_csrf_token()
    logger.log(f"{provider} login successful for user: {user.username}")
    return redirect('/')


@auth_bp.route('/login/github')
def login_github():
    redirect_uri = url_for('auth.github_callback', _external=True)
    logger.log(f"GitHub OAuth redirect URI: {redirect_uri}")
    return oauth.github.authorize_redirect(redirect_uri)


@auth_bp.route('/login/okta')
def login_okta():
    redirect_uri = url_for('auth.okta_callback', _external=True)
    return oauth.okta.authorize_redirect(redirect_uri)


@auth_bp.route('/github/callback')
def github_callback():
    try:
        token = oauth.github.authorize_access_token()
        user_info = oauth.github.get('user', token=token).json()
    except Exception as e:
        logger.log(f"Error in GitHub callback: {str(e)}")
        flash('An error occurred during GitHub authentication.', 'error')
        return redirect('/login?error=oauth_failed')
    return _complete_login('GitHub', user_info, token)


@auth_bp.route('/okta/callback')
def okta_callback():
    try:
        token = oauth.okta.authorize_access_token()
        user_info = oauth.okta.get('v1/userinfo', token=token).json()
    except Exception as e:
        logger.log(f"Error in Okta callback: {str(e)}")
        flash('An error occurred during Okta authentication.', 'error')
        return redirect('/login?error=oauth_failed')
    return _complete_login('Okta', user_info, token)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('oauth_token', None)
    session.pop('oauth_provider', None)
    rotate_csrf_token()
    return redirect('/login')
