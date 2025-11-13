import re
from datetime import datetime

def generate_sale_number(org_id):
    """Generate unique sale number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"SALE-{org_id}-{timestamp}"

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"

def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text

def calculate_sale_total(items):
    """Calculate sale total from items"""
    subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
    return subtotal

def log_activity(conn, org_id, user_id, action, entity_type=None, entity_id=None, details=None, ip_address=None):
    """Log user activity"""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_logs (organization_id, user_id, action, entity_type, entity_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (org_id, user_id, action, entity_type, entity_id, details, ip_address))
    conn.commit()
