"""Initialize database with tables and demo data"""
from database import engine, Base
from models import *
from passlib.context import CryptContext
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_database():
    """Create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

def seed_demo_org():
    """Create demo organization with sample data"""
    from database import SessionLocal
    db = SessionLocal()
    
    try:
        # Check if demo org exists
        existing_org = db.query(Organization).filter_by(slug="demo-pharmacy").first()
        if existing_org:
            print("Demo data already exists!")
            return
        
        # Create demo organization
        org = Organization(
            name="Demo Pharmacy",
            slug="demo-pharmacy",
            owner_email="admin@demo.com",
            phone="+1234567890",
            address="123 Main Street, City",
            subscription_plan="premium",
            is_active=True
        )
        db.add(org)
        db.flush()
        
        # Create admin user
        admin = User(
            organization_id=org.id,
            username="admin",
            email="admin@demo.com",
            password_hash=pwd_context.hash("admin123"),
            full_name="Admin User",
            role=UserRoleEnum.admin,
            is_active=True
        )
        db.add(admin)
        
        # Create pharmacist user (inactive until approved)
        pharmacist = User(
            organization_id=org.id,
            username="pharmacist",
            email="pharmacist@demo.com",
            password_hash=pwd_context.hash("pharmacist123"),
            full_name="Pharmacist User",
            role=UserRoleEnum.pharmacist,
            is_active=False
        )
        db.add(pharmacist)
        db.flush()
        
        # Create sample category
        category = Category(
            organization_id=org.id,
            name="Analgesics",
            description="Pain relievers"
        )
        db.add(category)
        db.flush()
        
        # Create sample products with barcodes
        products = [
            {
                "name": "Paracetamol 500mg",
                "generic_name": "Acetaminophen",
                "manufacturer": "PharmaCorp",
                "barcode": "8901234567890",
                "price": 5.99,
                "form": DrugFormEnum.tablet,
                "category_id": category.id
            },
            {
                "name": "Ibuprofen 400mg",
                "generic_name": "Ibuprofen",
                "manufacturer": "HealthCare Inc",
                "barcode": "8901234567891",
                "price": 8.50,
                "form": DrugFormEnum.tablet,
                "category_id": category.id
            },
            {
                "name": "Amoxicillin 250mg",
                "generic_name": "Amoxicillin",
                "manufacturer": "MediLabs",
                "barcode": "8901234567892",
                "price": 12.99,
                "form": DrugFormEnum.capsule,
                "category_id": category.id
            },
        ]
        
        for prod_data in products:
            drug = Drug(organization_id=org.id, **prod_data)
            db.add(drug)
            db.flush()
            
            # Add inventory batch for each drug
            batch = InventoryBatch(
                drug_id=drug.id,
                lot_number=f"LOT-{drug.barcode}",
                quantity_on_hand=100,
                expiry_date="2026-12-31",
                purchase_date="2024-01-01",
                cost_price=float(drug.price) * 0.6,
                status=BatchStatusEnum.active
            )
            db.add(batch)
        
        # Create sample customers
        customers = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+1234567001",
                "email": "john@example.com",
                "address": "123 Oak Street",
                "allow_credit": True,
                "credit_limit": 500.00,
                "current_balance": 0
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "+1234567002",
                "email": "jane@example.com",
                "address": "456 Pine Avenue",
                "allow_credit": True,
                "credit_limit": 1000.00,
                "current_balance": 0
            },
        ]
        
        for cust_data in customers:
            customer = Customer(organization_id=org.id, **cust_data)
            db.add(customer)
        
        db.commit()
        print("\n" + "=" * 50)
        print("Demo data created successfully!")
        print("=" * 50)
        print("\nLogin Credentials:")
        print("-" * 50)
        print("Admin:")
        print("  Email: admin@demo.com")
        print("  Password: admin123")
        print("\nPharmacist (requires admin approval):")
        print("  Email: pharmacist@demo.com")
        print("  Password: pharmacist123")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
    seed_demo_org()
