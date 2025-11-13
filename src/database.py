import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime

DATABASE_PATH = 'pharmacy_saas.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with all tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Organizations (Pharmacies) table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            owner_email TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            logo_url TEXT,
            subscription_plan TEXT DEFAULT 'free',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users table (Admin and Pharmacist)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'pharmacist')),
            is_active BOOLEAN DEFAULT 0,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            UNIQUE(organization_id, email)
        )
    ''')
    
    # Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            generic_name TEXT,
            manufacturer TEXT,
            category TEXT,
            barcode TEXT,
            price REAL NOT NULL,
            cost_price REAL,
            quantity INTEGER DEFAULT 0,
            reorder_level INTEGER DEFAULT 10,
            expiry_date DATE,
            description TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id),
            UNIQUE(organization_id, barcode)
        )
    ''')
    
    # Customers/Clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            allow_credit BOOLEAN DEFAULT 0,
            credit_limit REAL DEFAULT 0,
            current_balance REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        )
    ''')
    
    # Sales table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            customer_id INTEGER,
            sale_number TEXT NOT NULL,
            subtotal REAL NOT NULL,
            discount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL CHECK(payment_method IN ('cash', 'card', 'mobile', 'credit')),
            amount_paid REAL DEFAULT 0,
            balance REAL DEFAULT 0,
            status TEXT DEFAULT 'completed' CHECK(status IN ('completed', 'pending', 'cancelled')),
            notes TEXT,
            sold_by INTEGER NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (sold_by) REFERENCES users(id),
            UNIQUE(organization_id, sale_number)
        )
    ''')
    
    # Sale items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    
    # Credit payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credit_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            sale_id INTEGER,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            notes TEXT,
            recorded_by INTEGER NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (recorded_by) REFERENCES users(id)
        )
    ''')
    
    # Inventory transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL CHECK(transaction_type IN ('add', 'remove', 'adjust', 'sale')),
            quantity INTEGER NOT NULL,
            previous_quantity INTEGER NOT NULL,
            new_quantity INTEGER NOT NULL,
            notes TEXT,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # AI chat sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_title TEXT DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # AI chat messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        )
    ''')
    
    # Activity logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def seed_demo_data():
    """Add demo data for testing"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if demo org exists
    cursor.execute("SELECT id FROM organizations WHERE slug = 'demo-pharmacy'")
    if cursor.fetchone():
        print("Demo data already exists!")
        conn.close()
        return
    
    # Create demo organization
    cursor.execute('''
        INSERT INTO organizations (name, slug, owner_email, phone, address, subscription_plan, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('Demo Pharmacy', 'demo-pharmacy', 'admin@demo.com', '+1234567890', 
          '123 Main Street, City', 'premium', 1))
    
    org_id = cursor.lastrowid
    
    # Create admin user
    admin_password = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO users (organization_id, username, email, password_hash, full_name, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (org_id, 'admin', 'admin@demo.com', admin_password, 'Admin User', 'admin', 1))
    
    admin_id = cursor.lastrowid
    
    # Create pharmacist user
    pharmacist_password = generate_password_hash('pharmacist123')
    cursor.execute('''
        INSERT INTO users (organization_id, username, email, password_hash, full_name, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (org_id, 'pharmacist', 'pharmacist@demo.com', pharmacist_password, 'Pharmacist User', 'pharmacist', 0))
    
    # Add sample products with barcodes
    products = [
        ('Paracetamol 500mg', 'Acetaminophen', 'PharmaCorp', 'Analgesic', '8901234567890', 5.99, 3.50, 100, 20),
        ('Amoxicillin 250mg', 'Amoxicillin', 'MediLabs', 'Antibiotic', '8901234567891', 12.99, 8.00, 75, 15),
        ('Ibuprofen 400mg', 'Ibuprofen', 'HealthCare Inc', 'NSAID', '8901234567892', 8.50, 5.00, 120, 25),
        ('Cetirizine 10mg', 'Cetirizine HCl', 'AllergyMed', 'Antihistamine', '8901234567893', 6.75, 4.00, 90, 20),
        ('Vitamin C 1000mg', 'Ascorbic Acid', 'VitaHealth', 'Supplement', '8901234567894', 15.99, 9.00, 60, 15),
    ]
    
    for product in products:
        cursor.execute('''
            INSERT INTO products (organization_id, name, generic_name, manufacturer, category, 
                                barcode, price, cost_price, quantity, reorder_level, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (org_id,) + product + (admin_id,))
    
    # Add sample customers
    customers = [
        ('John Doe', '+1234567001', 'john@example.com', '123 Oak Street', 1, 500.0, 0),
        ('Jane Smith', '+1234567002', 'jane@example.com', '456 Pine Avenue', 1, 1000.0, 0),
        ('Bob Johnson', '+1234567003', 'bob@example.com', '789 Maple Road', 0, 0, 0),
    ]
    
    for customer in customers:
        cursor.execute('''
            INSERT INTO customers (organization_id, full_name, phone, email, address, 
                                 allow_credit, credit_limit, current_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (org_id,) + customer)
    
    conn.commit()
    conn.close()
    print("Demo data seeded successfully!")
    print("\nDemo Credentials:")
    print("Admin - Email: admin@demo.com, Password: admin123")
    print("Pharmacist - Email: pharmacist@demo.com, Password: pharmacist123")

if __name__ == '__main__':
    init_db()
    seed_demo_data()
