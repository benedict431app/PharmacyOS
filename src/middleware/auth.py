from functools import wraps
from flask import session, redirect, url_for, g, abort
from src.database import get_db

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            if session.get('role') not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def load_user():
    """Load user data before each request"""
    g.user = None
    g.organization = None
    
    if 'user_id' in session:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.*, o.name as org_name, o.slug as org_slug, o.logo_url 
            FROM users u 
            JOIN organizations o ON u.organization_id = o.id 
            WHERE u.id = ? AND u.is_active = 1 AND o.is_active = 1
        ''', (session['user_id'],))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            g.user = dict(user)
            g.organization = {
                'id': user['organization_id'],
                'name': user['org_name'],
                'slug': user['org_slug'],
                'logo_url': user['logo_url']
            }
        else:
            session.clear()
