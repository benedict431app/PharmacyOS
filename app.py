import bcrypt
import types

# BCrypt workaround - Fix for passlib/bcrypt compatibility issue
try:
    bcrypt.__about__
except AttributeError:
    bcrypt.__about__ = types.SimpleNamespace()
    bcrypt.__about__.__version__ = "3.2.0"

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from passlib.context import CryptContext
from typing import Optional, List
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
import cohere
import json

from database import engine, get_db, Base
import models

# ==================== PASSWORD HANDLING ====================
# Use pbkdf2_sha256 exclusively to avoid bcrypt 72-byte limit
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=30000,
    pbkdf2_sha256__salt_size=16
)

def hash_password(password: str) -> str:
    """Hash password with pbkdf2_sha256 (no 72-byte limit)."""
    # Clean and validate password
    password = str(password).strip()
    
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    
    if len(password) > 128:
        raise ValueError("Password must be 128 characters or less")
    
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Hashing error: {e}")
        # Fallback to direct pbkdf2_sha256
        from passlib.hash import pbkdf2_sha256
        return pbkdf2_sha256.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    # Clean password
    password = str(password).strip()
    
    # Truncate if needed
    if len(password) > 128:
        password = password[:128]
    
    try:
        return pwd_context.verify(password, hashed_password)
    except Exception as e:
        print(f"Verification error: {e}")
        # Try with pbkdf2_sha256 directly
        from passlib.hash import pbkdf2_sha256
        try:
            return pbkdf2_sha256.verify(password, hashed_password)
        except:
            return False

class CohereService:
    def __init__(self):
        api_key = os.getenv("COHERE_API_KEY")
        self.client = cohere.Client(api_key) if api_key else None
        self.model = "command"
    
    async def get_drug_information(self, query: str) -> str:
        """Get drug information from Cohere"""
        if not self.client:
            return "AI assistant is not configured. Please add your COHERE_API_KEY to use this feature."
        
        try:
            response = self.client.chat(
                model=self.model,
                message=query,
                preamble="""You are an expert pharmacist assistant. Provide accurate, helpful information about:
- Drug information, usage, and dosages
- Drug interactions and contraindications
- Side effects and warnings
- Medical conditions and treatments
- Medication safety and storage
Always be clear, professional, and remind users to consult healthcare professionals for personalized advice.""",
                max_tokens=1024
            )
            return response.text
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}"

def create_demo_data(db: Session):
    """Create demo data for testing"""
    # Check if demo organization already exists
    existing_org = db.query(models.Organization).filter(models.Organization.name == "Demo Pharmacy").first()
    if existing_org:
        return
    
    # Create demo organization
    org = models.Organization(
        id=str(uuid.uuid4()),
        name="Demo Pharmacy",
        slug="demo-pharmacy",
        owner_email="admin@demo.com",
        phone="555-0123",
        address="123 Main Street, City, State",
        subscription_plan="professional",
        is_active=True
    )
    db.add(org)
    db.flush()
    
    # Create demo users with proper password hashing
    admin_user = models.User(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        username="admin",
        email="admin@demo.com",
        password_hash=hash_password("admin123"),
        full_name="Demo Admin",
        role=models.UserRoleEnum.admin,
        is_active=True,
        phone="555-0101"
    )
    
    pharmacist_user = models.User(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        username="pharmacist",
        email="pharmacist@demo.com",
        password_hash=hash_password("pharmacist123"),
        full_name="Demo Pharmacist",
        role=models.UserRoleEnum.pharmacist,
        is_active=True,
        phone="555-0102"
    )
    
    db.add_all([admin_user, pharmacist_user])
    db.flush()
    
    # Create demo category
    category = models.Category(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        name="General Medicines",
        description="General prescription and OTC medicines"
    )
    db.add(category)
    db.flush()
    
    # Create demo supplier
    supplier = models.Supplier(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        name="MediSupplies Ltd",
        contact_person="John Supplier",
        email="supplies@medisupplies.com",
        phone="555-0200",
        address="456 Supply Street, City, State"
    )
    db.add(supplier)
    db.flush()
    
    # Create demo drugs
    demo_drugs = [
        models.Drug(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            name="Paracetamol 500mg",
            generic_name="Paracetamol",
            manufacturer="Generic Pharma",
            form=models.DrugFormEnum.tablet,
            strength=500.0,
            strength_unit=models.StrengthUnitEnum.mg,
            category_id=category.id,
            supplier_id=supplier.id,
            description="Pain reliever and fever reducer",
            usage_instructions="Take 1-2 tablets every 4-6 hours as needed",
            side_effects="May cause nausea or rash in rare cases",
            contraindications="Liver disease, alcohol dependence",
            price=50.0,
            reorder_level=100,
            barcode="123456789012"
        ),
        models.Drug(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            name="Amoxicillin 500mg Capsules",
            generic_name="Amoxicillin",
            manufacturer="Antibio Labs",
            form=models.DrugFormEnum.capsule,
            strength=500.0,
            strength_unit=models.StrengthUnitEnum.mg,
            category_id=category.id,
            supplier_id=supplier.id,
            description="Broad-spectrum antibiotic",
            usage_instructions="Take as prescribed, usually 3 times daily",
            side_effects="Diarrhea, nausea, rash",
            contraindications="Penicillin allergy",
            price=150.0,
            reorder_level=50,
            barcode="123456789013"
        ),
        models.Drug(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            name="Ibuprofen 400mg",
            generic_name="Ibuprofen",
            manufacturer="PainFree Inc",
            form=models.DrugFormEnum.tablet,
            strength=400.0,
            strength_unit=models.StrengthUnitEnum.mg,
            category_id=category.id,
            supplier_id=supplier.id,
            description="NSAID for pain and inflammation",
            usage_instructions="Take with food, 1 tablet every 6-8 hours",
            side_effects="Stomach upset, dizziness",
            contraindications="Stomach ulcers, kidney problems",
            price=80.0,
            reorder_level=75,
            barcode="123456789014"
        )
    ]
    
    db.add_all(demo_drugs)
    db.flush()
    
    # Create inventory batches
    for drug in demo_drugs:
        batch = models.InventoryBatch(
            id=str(uuid.uuid4()),
            drug_id=drug.id,
            lot_number=f"LOT-001-{drug.name[:5].upper()}",
            quantity_on_hand=200,
            expiry_date=date(2026, 12, 31),
            purchase_date=date(2025, 1, 1),
            cost_price=drug.price * 0.6,
            status=models.BatchStatusEnum.active
        )
        db.add(batch)
    
    # Create demo customer
    demo_customer = models.Customer(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",
        phone="555-0100",
        address="789 Customer Ave, City, State",
        date_of_birth=date(1985, 5, 15),
        allergies="Penicillin, Sulfa drugs",
        medical_conditions="Hypertension",
        allow_credit=True,
        credit_limit=5000.0,
        current_balance=0.0
    )
    db.add(demo_customer)
    
    db.commit()
    print("Demo data created successfully!")

# Create tables
Base.metadata.create_all(bind=engine)

# Create demo data
db = next(get_db())
try:
    create_demo_data(db)
except Exception as e:
    print(f"Error creating demo data: {e}")
    db.rollback()
finally:
    db.close()

app = FastAPI(title="PharmaSaaS - Pharmacy Management System")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "your-secret-key-here-change-in-production"))

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize Cohere service
cohere_service = CohereService()

# Helper functions
def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.is_active == True
    ).first()
    return user

def require_auth(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_role(*roles):
    def decorator(request: Request, user: models.User = Depends(require_auth)):
        if user.role.value not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return decorator

# ==================== LANDING PAGE ====================
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page for pharmacy sign-up"""
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return templates.TemplateResponse("landing.html", {"request": request})

# ==================== REGISTRATION ====================
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    pharmacy_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Clean inputs
        password = password.strip()
        confirm_password = confirm_password.strip()
        email = email.strip().lower()
        
        # Validate passwords match
        if password != confirm_password:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Passwords do not match"
            })
        
        # Validate password length
        if len(password) < 6:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Password must be at least 6 characters"
            })
        
        if len(password) > 128:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Password must be 128 characters or less"
            })
        
        # Check if email exists
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Email already registered"
            })
        
        # Check if pharmacy name exists
        existing_org = db.query(models.Organization).filter(models.Organization.name == pharmacy_name).first()
        if existing_org:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Pharmacy name already taken"
            })
        
        # Create organization
        org = models.Organization(
            id=str(uuid.uuid4()),
            name=pharmacy_name,
            slug=pharmacy_name.lower().replace(' ', '-').replace("'", "").replace('"', ''),
            owner_email=email,
            phone=phone,
            address="",
            subscription_plan="free",
            is_active=True
        )
        db.add(org)
        db.flush()
        
        # Hash password
        try:
            hashed_password = hash_password(password)
        except ValueError as e:
            db.rollback()
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": str(e)
            })
        
        # Create user
        user = models.User(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            username=email.split('@')[0][:100],
            email=email,
            password_hash=hashed_password,
            full_name=f"{first_name} {last_name}"[:255],
            role=models.UserRoleEnum.admin,
            is_active=True,
            phone=phone[:50]
        )
        db.add(user)
        db.commit()
        
        # Set session
        request.session["user_id"] = user.id
        request.session["role"] = user.role.value
        request.session["org_id"] = user.organization_id
        
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        db.rollback()
        print(f"Registration error: {e}")
        import traceback
        traceback.print_exc()
        
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Registration failed. Please try again."
        })

# ==================== AUTHENTICATION ====================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request, 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        # Clean inputs
        email = email.strip().lower()
        password = password.strip()
        
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Invalid email or password"
            })
        
        # Truncate password if needed
        if len(password) > 128:
            password = password[:128]
        
        # Verify password
        try:
            password_valid = verify_password(password, user.password_hash)
        except Exception as e:
            print(f"Password verification error: {e}")
            password_valid = False
        
        if not password_valid:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Invalid email or password"
            })
        
        if not user.is_active:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Your account is pending approval"
            })
        
        # Set session
        request.session["user_id"] = user.id
        request.session["role"] = user.role.value
        request.session["org_id"] = user.organization_id
        
        return RedirectResponse(url="/dashboard", status_code=303)
        
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "An error occurred during login. Please try again."
        })

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# ==================== DASHBOARD ====================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    
    # Get statistics
    total_products = db.query(models.Drug).filter(models.Drug.organization_id == org_id).count()
    total_customers = db.query(models.Customer).filter(models.Customer.organization_id == org_id).count()
    total_sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).count()
    
    # Get pending credit
    pending_credit = db.query(func.sum(models.Customer.current_balance)).filter(
        models.Customer.organization_id == org_id
    ).scalar() or 0
    
    # Get low stock products
    low_stock_items = []
    drugs = db.query(models.Drug).filter(models.Drug.organization_id == org_id).all()
    
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
            models.InventoryBatch.drug_id == drug.id,
            models.InventoryBatch.status == models.BatchStatusEnum.active
        ).scalar() or 0
        
        if total_stock < drug.reorder_level:
            low_stock_items.append({
                "name": drug.name,
                "stock": total_stock,
                "reorder": drug.reorder_level
            })
    
    # Get recent sales
    recent_sales = db.query(models.SalesOrder).filter(
        models.SalesOrder.organization_id == org_id
    ).order_by(models.SalesOrder.created_at.desc()).limit(5).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "total_products": total_products,
        "total_customers": total_customers,
        "total_sales": total_sales,
        "pending_credit": float(pending_credit),
        "low_stock_items": low_stock_items,
        "recent_sales": recent_sales
    })

# ==================== INVENTORY MANAGEMENT ====================
@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("inventory.html", {"request": request, "user": user})

@app.get("/api/inventory")
async def get_inventory(
    request: Request, 
    user: models.User = Depends(require_auth), 
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 20,
    search: str = ""
):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    
    query = db.query(models.Drug).filter(models.Drug.organization_id == org_id)
    
    if search:
        query = query.filter(
            or_(
                models.Drug.name.ilike(f"%{search}%"),
                models.Drug.generic_name.ilike(f"%{search}%"),
                models.Drug.barcode.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    drugs = query.offset(offset).limit(limit).all()
    
    # Get stock levels
    result = []
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
            models.InventoryBatch.drug_id == drug.id,
            models.InventoryBatch.status == models.BatchStatusEnum.active
        ).scalar() or 0
        
        result.append({
            "id": drug.id,
            "name": drug.name,
            "generic_name": drug.generic_name,
            "manufacturer": drug.manufacturer,
            "form": drug.form.value,
            "strength": drug.strength,
            "strength_unit": drug.strength_unit.value,
            "price": float(drug.price),
            "stock": int(total_stock),
            "reorder_level": drug.reorder_level,
            "barcode": drug.barcode,
            "description": drug.description,
            "usage_instructions": drug.usage_instructions,
            "side_effects": drug.side_effects,
            "contraindications": drug.contraindications
        })
    
    return {
        "items": result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@app.post("/api/inventory")
async def add_inventory(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    try:
        # Create drug
        drug = models.Drug(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            name=data["name"],
            generic_name=data.get("generic_name", ""),
            manufacturer=data.get("manufacturer", ""),
            form=models.DrugFormEnum(data["form"]),
            strength=data.get("strength", 0),
            strength_unit=models.StrengthUnitEnum(data.get("strength_unit", "mg")),
            category_id=data.get("category_id"),
            supplier_id=data.get("supplier_id"),
            description=data.get("description", ""),
            usage_instructions=data.get("usage_instructions", ""),
            side_effects=data.get("side_effects", ""),
            contraindications=data.get("contraindications", ""),
            price=data.get("price", 0),
            reorder_level=data.get("reorder_level", 50),
            barcode=data.get("barcode", "")
        )
        db.add(drug)
        db.flush()
        
        # Add initial batch if quantity provided
        if data.get("initial_quantity", 0) > 0:
            batch = models.InventoryBatch(
                id=str(uuid.uuid4()),
                drug_id=drug.id,
                lot_number=data.get("lot_number", f"LOT-{datetime.now().strftime('%Y%m%d')}"),
                quantity_on_hand=data["initial_quantity"],
                expiry_date=datetime.strptime(data["expiry_date"], "%Y-%m-%d").date() if data.get("expiry_date") else None,
                purchase_date=datetime.now().date(),
                cost_price=data.get("cost_price", drug.price * 0.6),
                status=models.BatchStatusEnum.active
            )
            db.add(batch)
        
        db.commit()
        
        return {"success": True, "id": drug.id}
        
    except Exception as e:
        db.rollback()
        print(f"Error adding inventory: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/inventory/{drug_id}")
async def update_inventory(
    drug_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    drug = db.query(models.Drug).filter(
        models.Drug.id == drug_id,
        models.Drug.organization_id == org_id
    ).first()
    
    if not drug:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        # Update fields
        for key, value in data.items():
            if hasattr(drug, key) and key not in ["id", "organization_id", "created_at"]:
                if key == "form":
                    setattr(drug, key, models.DrugFormEnum(value))
                elif key == "strength_unit":
                    setattr(drug, key, models.StrengthUnitEnum(value))
                else:
                    setattr(drug, key, value)
        
        db.commit()
        return {"success": True}
        
    except Exception as e:
        db.rollback()
        print(f"Error updating inventory: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/inventory/{drug_id}")
async def delete_inventory(
    drug_id: str,
    request: Request,
    user: models.User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    org_id = request.session.get("org_id")
    
    drug = db.query(models.Drug).filter(
        models.Drug.id == drug_id,
        models.Drug.organization_id == org_id
    ).first()
    
    if not drug:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if product has sales
    has_sales = db.query(models.SalesLineItem).filter(models.SalesLineItem.drug_id == drug_id).first()
    if has_sales:
        raise HTTPException(status_code=400, detail="Cannot delete product with existing sales")
    
    try:
        # Delete batches first
        db.query(models.InventoryBatch).filter(models.InventoryBatch.drug_id == drug_id).delete()
        db.delete(drug)
        db.commit()
        return {"success": True}
        
    except Exception as e:
        db.rollback()
        print(f"Error deleting inventory: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ==================== POINT OF SALE ====================
@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("pos.html", {"request": request, "user": user})

@app.get("/api/product_by_barcode")
async def get_product_by_barcode(
    code: str, 
    request: Request, 
    user: models.User = Depends(require_auth), 
    db: Session = Depends(get_db)
):
    """Get product by barcode for scanner integration"""
    org_id = request.session.get("org_id")
    
    product = db.query(models.Drug).filter(
        models.Drug.barcode == code,
        models.Drug.organization_id == org_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get total stock
    total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
        models.InventoryBatch.drug_id == product.id,
        models.InventoryBatch.status == models.BatchStatusEnum.active
    ).scalar() or 0
    
    return {
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "barcode": product.barcode,
        "stock": int(total_stock)
    }

@app.get("/api/products/search")
async def search_products(
    request: Request,
    q: str,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    org_id = request.session.get("org_id")
    
    products = db.query(models.Drug).filter(
        models.Drug.organization_id == org_id,
        or_(
            models.Drug.name.ilike(f"%{q}%"),
            models.Drug.generic_name.ilike(f"%{q}%"),
            models.Drug.barcode.ilike(f"%{q}%")
        )
    ).limit(20).all()
    
    result = []
    for product in products:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
            models.InventoryBatch.drug_id == product.id,
            models.InventoryBatch.status == models.BatchStatusEnum.active
        ).scalar() or 0
        
        result.append({
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": int(total_stock),
            "barcode": product.barcode
        })
    
    return result

@app.post("/api/sales")
async def create_sale(
    request: Request, 
    user: models.User = Depends(require_auth), 
    db: Session = Depends(get_db)
):
    """Create new sale"""
    data = await request.json()
    org_id = request.session.get("org_id")
    
    try:
        # Generate sale number
        sale_number = f"SALE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create sale order
        sale = models.SalesOrder(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            customer_id=data.get("customerId"),
            sale_number=sale_number,
            subtotal=data["subtotal"],
            tax=data.get("tax", 0),
            discount=data.get("discount", 0),
            total=data["total"],
            payment_method=models.PaymentMethodEnum(data["paymentMethod"]),
            amount_paid=data.get("amountPaid", data["total"]),
            balance=data.get("balance", 0),
            created_by=user.id
        )
        db.add(sale)
        db.flush()
        
        # Add line items and update inventory
        for item in data["lineItems"]:
            # Get product to verify price
            product = db.query(models.Drug).filter(models.Drug.id == item["productId"]).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item['productId']} not found")
            
            line_item = models.SalesLineItem(
                id=str(uuid.uuid4()),
                sales_order_id=sale.id,
                drug_id=item["productId"],
                quantity=item["quantity"],
                unit_price=item["unitPrice"],
                line_total=item["lineTotal"]
            )
            db.add(line_item)
            
            # Update inventory - FIFO approach
            remaining_quantity = item["quantity"]
            batches = db.query(models.InventoryBatch).filter(
                models.InventoryBatch.drug_id == item["productId"],
                models.InventoryBatch.quantity_on_hand > 0,
                models.InventoryBatch.status == models.BatchStatusEnum.active
            ).order_by(models.InventoryBatch.expiry_date).all()
            
            for batch in batches:
                if remaining_quantity <= 0:
                    break
                    
                qty_to_take = min(batch.quantity_on_hand, remaining_quantity)
                batch.quantity_on_hand -= qty_to_take
                remaining_quantity -= qty_to_take
                
                # If batch is now empty, mark as inactive
                if batch.quantity_on_hand == 0:
                    batch.status = models.BatchStatusEnum.empty
            
            if remaining_quantity > 0:
                db.rollback()
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
        
        # Update customer credit balance if credit sale
        if data["paymentMethod"] == "credit" and data.get("customerId"):
            customer = db.query(models.Customer).filter(models.Customer.id == data["customerId"]).first()
            if customer:
                customer.current_balance += data.get("balance", 0)
        
        db.commit()
        
        return {
            "success": True, 
            "sale_id": sale.id, 
            "sale_number": sale.sale_number,
            "receipt": {
                "sale_number": sale.sale_number,
                "date": sale.created_at.isoformat(),
                "items": data["lineItems"],
                "subtotal": data["subtotal"],
                "tax": data.get("tax", 0),
                "discount": data.get("discount", 0),
                "total": data["total"],
                "payment_method": data["paymentMethod"],
                "amount_paid": data.get("amountPaid", data["total"]),
                "balance": data.get("balance", 0)
            }
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error creating sale: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sales")
async def get_sales(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 20
):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    
    query = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id)
    total = query.count()
    sales = query.order_by(models.SalesOrder.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for sale in sales:
        result.append({
            "id": sale.id,
            "sale_number": sale.sale_number,
            "date": sale.created_at.isoformat(),
            "customer_name": sale.customer.full_name if sale.customer else "Walk-in Customer",
            "total": float(sale.total),
            "payment_method": sale.payment_method.value,
            "status": sale.status.value if sale.status else "completed"
        })
    
    return {
        "items": result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

# ==================== CUSTOMER MANAGEMENT ====================
@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("customers.html", {"request": request, "user": user})

@app.get("/api/customers")
async def get_customers(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 20,
    search: str = ""
):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    
    query = db.query(models.Customer).filter(models.Customer.organization_id == org_id)
    
    if search:
        query = query.filter(
            or_(
                models.Customer.first_name.ilike(f"%{search}%"),
                models.Customer.last_name.ilike(f"%{search}%"),
                models.Customer.email.ilike(f"%{search}%"),
                models.Customer.phone.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    customers = query.offset(offset).limit(limit).all()
    
    result = []
    for customer in customers:
        result.append({
            "id": customer.id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "full_name": customer.full_name,
            "email": customer.email,
            "phone": customer.phone,
            "address": customer.address,
            "allow_credit": customer.allow_credit,
            "credit_limit": float(customer.credit_limit) if customer.credit_limit else 0,
            "current_balance": float(customer.current_balance) if customer.current_balance else 0
        })
    
    return {
        "items": result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@app.post("/api/customers")
async def add_customer(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    try:
        customer = models.Customer(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            address=data.get("address", ""),
            date_of_birth=datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date() if data.get("date_of_birth") else None,
            allergies=data.get("allergies", ""),
            medical_conditions=data.get("medical_conditions", ""),
            allow_credit=data.get("allow_credit", False),
            credit_limit=data.get("credit_limit", 0),
            current_balance=0
        )
        db.add(customer)
        db.commit()
        
        return {"success": True, "id": customer.id}
        
    except Exception as e:
        db.rollback()
        print(f"Error adding customer: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    customer = db.query(models.Customer).filter(
        models.Customer.id == customer_id,
        models.Customer.organization_id == org_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    try:
        for key, value in data.items():
            if hasattr(customer, key) and key not in ["id", "organization_id", "created_at"]:
                if key == "date_of_birth" and value:
                    setattr(customer, key, datetime.strptime(value, "%Y-%m-%d").date())
                else:
                    setattr(customer, key, value)
        
        db.commit()
        return {"success": True}
        
    except Exception as e:
        db.rollback()
        print(f"Error updating customer: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/customers/{customer_id}/payment")
async def add_customer_payment(
    customer_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    customer = db.query(models.Customer).filter(
        models.Customer.id == customer_id,
        models.Customer.organization_id == org_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    try:
        amount = data.get("amount", 0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid payment amount")
        
        # Update customer balance
        customer.current_balance -= amount
        
        # Record payment
        payment = models.Payment(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            customer_id=customer_id,
            amount=amount,
            payment_date=datetime.now().date(),
            payment_method=models.PaymentMethodEnum(data.get("payment_method", "cash")),
            reference=data.get("reference", ""),
            notes=data.get("notes", ""),
            created_by=user.id
        )
        db.add(payment)
        db.commit()
        
        return {"success": True, "new_balance": float(customer.current_balance)}
        
    except Exception as e:
        db.rollback()
        print(f"Error adding payment: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ==================== STAFF MANAGEMENT ====================
@app.get("/staff", response_class=HTMLResponse)
async def staff_page(request: Request, user: models.User = Depends(require_role("admin"))):
    return templates.TemplateResponse("staff.html", {"request": request, "user": user})

@app.get("/api/staff")
async def get_staff(
    request: Request,
    user: models.User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    org_id = request.session.get("org_id")
    
    staff = db.query(models.User).filter(
        models.User.organization_id == org_id,
        models.User.role != models.UserRoleEnum.admin
    ).all()
    
    result = []
    for member in staff:
        result.append({
            "id": member.id,
            "username": member.username,
            "email": member.email,
            "full_name": member.full_name,
            "role": member.role.value,
            "is_active": member.is_active,
            "phone": member.phone,
            "created_at": member.created_at.isoformat()
        })
    
    return result

@app.post("/api/staff")
async def add_staff(
    request: Request,
    user: models.User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    try:
        # Check if email exists
        existing = db.query(models.User).filter(models.User.email == data["email"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Hash password
        hashed_password = hash_password(data["password"])
        
        # Create staff user
        staff = models.User(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            username=data["username"],
            email=data["email"],
            password_hash=hashed_password,
            full_name=data["full_name"],
            role=models.UserRoleEnum(data["role"]),
            is_active=data.get("is_active", True),
            phone=data.get("phone", "")
        )
        db.add(staff)
        db.commit()
        
        return {"success": True, "id": staff.id}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        print(f"Error adding staff: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/staff/{staff_id}")
async def update_staff(
    staff_id: str,
    request: Request,
    user: models.User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    staff = db.query(models.User).filter(
        models.User.id == staff_id,
        models.User.organization_id == org_id
    ).first()
    
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    try:
        for key, value in data.items():
            if hasattr(staff, key) and key not in ["id", "organization_id", "created_at", "password_hash"]:
                if key == "role":
                    setattr(staff, key, models.UserRoleEnum(value))
                else:
                    setattr(staff, key, value)
        
        # Update password if provided
        if data.get("password"):
            staff.password_hash = hash_password(data["password"])
        
        db.commit()
        return {"success": True}
        
    except Exception as e:
        db.rollback()
        print(f"Error updating staff: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/staff/{staff_id}")
async def delete_staff(
    staff_id: str,
    request: Request,
    user: models.User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    org_id = request.session.get("org_id")
    
    # Don't allow deleting self
    if staff_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    staff = db.query(models.User).filter(
        models.User.id == staff_id,
        models.User.organization_id == org_id
    ).first()
    
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    try:
        db.delete(staff)
        db.commit()
        return {"success": True}
        
    except Exception as e:
        db.rollback()
        print(f"Error deleting staff: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ==================== AI CHAT ====================
@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("ai_chat.html", {"request": request, "user": user})

@app.post("/api/ai/chat")
async def ai_chat(
    request: Request, 
    user: models.User = Depends(require_auth), 
    db: Session = Depends(get_db)
):
    """AI chat endpoint"""
    data = await request.json()
    message = data.get("message")
    session_id = data.get("sessionId")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    # Create or get session
    if not session_id:
        chat_session = models.AIChatSession(
            id=str(uuid.uuid4()),
            user_id=user.id, 
            title=message[:50] + "..." if len(message) > 50 else message
        )
        db.add(chat_session)
        db.flush()
        session_id = chat_session.id
    
    # Save user message
    user_msg = models.AIChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=message
    )
    db.add(user_msg)
    db.flush()
    
    # Get AI response from Cohere
    response = await cohere_service.get_drug_information(message)
    
    # Save AI response
    ai_msg = models.AIChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=response
    )
    db.add(ai_msg)
    db.commit()
    
    return {"sessionId": session_id, "response": response}

@app.get("/api/ai/sessions")
async def get_ai_sessions(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get user's chat sessions"""
    sessions = db.query(models.AIChatSession).filter(
        models.AIChatSession.user_id == user.id
    ).order_by(models.AIChatSession.updated_at.desc()).all()
    
    return [{
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat()
    } for s in sessions]

@app.get("/api/ai/sessions/{session_id}/messages")
async def get_ai_messages(
    session_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get messages for a chat session"""
    # Verify session belongs to user
    session = db.query(models.AIChatSession).filter(
        models.AIChatSession.id == session_id,
        models.AIChatSession.user_id == user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(models.AIChatMessage).filter(
        models.AIChatMessage.session_id == session_id
    ).order_by(models.AIChatMessage.created_at).all()
    
    return [{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat()
    } for m in messages]

# ==================== REPORTS ====================
@app.get("/api/reports/sales")
async def get_sales_report(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db),
    start_date: str = None,
    end_date: str = None
):
    org_id = request.session.get("org_id")
    
    query = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id)
    
    if start_date:
        query = query.filter(models.SalesOrder.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(models.SalesOrder.created_at <= datetime.fromisoformat(end_date))
    
    sales = query.all()
    
    total_sales = sum(s.total for s in sales)
    total_tax = sum(s.tax for s in sales)
    total_discount = sum(s.discount for s in sales)
    
    # Group by day
    daily_sales = {}
    for sale in sales:
        day = sale.created_at.date().isoformat()
        if day not in daily_sales:
            daily_sales[day] = 0
        daily_sales[day] += float(sale.total)
    
    return {
        "total_sales": float(total_sales),
        "total_tax": float(total_tax),
        "total_discount": float(total_discount),
        "transaction_count": len(sales),
        "daily_sales": daily_sales,
        "sales": [{
            "sale_number": s.sale_number,
            "date": s.created_at.isoformat(),
            "total": float(s.total),
            "payment_method": s.payment_method.value
        } for s in sales[:100]]  # Return last 100 sales
    }

@app.get("/api/reports/inventory")
async def get_inventory_report(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    org_id = request.session.get("org_id")
    
    drugs = db.query(models.Drug).filter(models.Drug.organization_id == org_id).all()
    
    report = []
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
            models.InventoryBatch.drug_id == drug.id,
            models.InventoryBatch.status == models.BatchStatusEnum.active
        ).scalar() or 0
        
        total_value = total_stock * drug.price
        
        report.append({
            "name": drug.name,
            "stock": int(total_stock),
            "price": float(drug.price),
            "total_value": float(total_value),
            "reorder_level": drug.reorder_level,
            "status": "Low Stock" if total_stock < drug.reorder_level else "OK"
        })
    
    return {
        "items": report,
        "total_items": len(report),
        "total_inventory_value": sum(r["total_value"] for r in report)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
