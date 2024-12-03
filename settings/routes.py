from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required
from src.models import User, UICustomizations, VendorProxies, db
from werkzeug.security import generate_password_hash

settings_bp = Blueprint('settings', __name__, template_folder='templates')

@settings_bp.route('/main-config', methods=['GET', 'POST'])
@login_required
def main_config(): 
    ui_customizations = UICustomizations.query.get(1)
    vendor_proxies = VendorProxies.query.get(1)
    
    if request.method == 'GET':
        return render_template('main-config.html', ui_customizations=ui_customizations,
                               vendor_proxies=vendor_proxies)
    
    elif request.method == 'POST':
        if request.args.get("f") == "ui":
            ui_customizations.integrator_title = request.form.get('integrator-title')
            db.session.add(ui_customizations)
            db.session.commit()
            flash('UI config updated', 'warning')
            
        elif request.args.get("f") == "vendorproxies":
            vendor_proxies.kaltura_proxy_enabled = True if request.form.get('kaltura-proxy-enabled') else False
            vendor_proxies.canvas_proxy_enabled = True if request.form.get('canvas-proxy-enabled') else False
            vendor_proxies.zoom_proxy_enabled = True if request.form.get('zoom-proxy-enabled') else False

            db.session.add(vendor_proxies)
            db.session.commit()
            flash('Proxy configurations updated', 'warning')
        
        return redirect(url_for('settings.main_config'))
    
@settings_bp.route('/adduser', methods=['GET','POST'])
@login_required
def adduser():
    if request.method == 'POST':
        
        # code to validate and add user to database goes here
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        role = request.form.get('role')

        user = User.query.filter_by(username=username).first() # if this returns a user, then the username already exists in database
        emailcheck = User.query.filter_by(email=email).first()
        if user:
            flash('User already exists. Please try again', 'warning')
            return redirect(url_for('adduser'))
        
        if emailcheck:
            flash('Email already associated with another user. Please Try again', 'warning')
            return redirect(url_for('adduser'))
        
        # create a new user with the form data. Hash the password so plaintext version isn't saved.
        new_user = User(username=username, password=generate_password_hash(password, method='pbkdf2'), email=email, role=role)

        # add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('New user ' + username + ' added', 'success')
        return redirect(url_for('settings.adduser'))
    
    elif request.method == 'GET':
        return render_template('adduser.html')