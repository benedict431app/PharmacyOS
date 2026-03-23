import bcrypt
import types

# BCrypt workaround
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
import secrets
import httpx

from database import engine, get_db, Base
import models

# ==================== TUMA MPESA CONFIGURATION ====================
TUMA_API_KEY = "tuma_a16e1b5f60f0999dd52359a12785255ef165a9b847686536731540052d16808e_1773652843"
TUMA_EMAIL = "benedicto431@gmail.com"
TUMA_BASE_URL = "https://tuma.ke/api/v1"

# ==================== PASSWORD HANDLING ====================
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=30000,
    pbkdf2_sha256__salt_size=16
)

def hash_password(password: str) -> str:
    password = str(password).strip()
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if len(password) > 128:
        raise ValueError("Password must be 128 characters or less")
    return pwd_context.hash(password, scheme="pbkdf2_sha256")

def verify_password(password: str, hashed_password: str) -> bool:
    password = str(password).strip()
    if len(password) > 128:
        password = password[:128]
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(password, hashed_password)
    except:
        return False

# ==================== TUMA MPESA SERVICE ====================
class TumaMpesaService:
    def __init__(self):
        self.api_key = TUMA_API_KEY
        self.email = TUMA_EMAIL
        self.base_url = TUMA_BASE_URL
    
    async def initiate_payment(self, amount: float, phone: str, reference: str = None) -> dict:
        if not reference:
            reference = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        phone = phone.strip()
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/payments/mpesa",
                    json={
                        "api_key": self.api_key,
                        "email": self.email,
                        "amount": amount,
                        "phone": phone,
                        "reference": reference,
                        "callback_url": "https://pharmacyos-1.onrender.com/api/payment/callback"
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "payment_id": data.get("payment_id"), "reference": reference}
                return {"success": False, "error": "Payment initiation failed"}
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    async def check_payment_status(self, payment_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/payments/{payment_id}",
                    params={"api_key": self.api_key}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "status": data.get("status")}
                return {"success": False, "error": "Failed to check status"}
            except Exception as e:
                return {"success": False, "error": str(e)}

# ==================== COHERE AI SERVICE ====================
class CohereService:
    def __init__(self):
        api_key = os.getenv("COHERE_API_KEY")
        self.client = cohere.Client(api_key) if api_key else None
        self.model = "command-r-plus-08-2024"
    
    async def get_drug_information(self, query: str) -> str:
        if not self.client:
            return "AI assistant not configured. Please add COHERE_API_KEY."
        try:
            response = self.client.chat(
                model=self.model,
                message=query,
                preamble="You are an expert pharmacist assistant. Provide accurate information about drugs, dosages, interactions, and side effects. Always remind users to consult healthcare professionals.",
                max_tokens=1024
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

# ==================== DEMO DATA ====================
def create_demo_data(db: Session):
    if db.query(models.Organization).filter(models.Organization.name == "Demo Pharmacy").first():
        return
    
    print("Creating demo data...")
    
    org = models.Organization(
        id=str(uuid.uuid4()), name="Demo Pharmacy", slug="demo-pharmacy",
        owner_email="admin@demo.com", phone="555-0123", address="123 Main Street",
        subscription_plan="professional", is_active=True
    )
    db.add(org)
    db.flush()
    
    admin = models.User(
        id=str(uuid.uuid4()), organization_id=org.id, username="admin",
        email="admin@demo.com", password_hash=hash_password("admin123"),
        full_name="Demo Admin", role=models.UserRoleEnum.admin, is_active=True, phone="555-0101"
    )
    pharmacist = models.User(
        id=str(uuid.uuid4()), organization_id=org.id, username="pharmacist",
        email="pharmacist@demo.com", password_hash=hash_password("pharmacist123"),
        full_name="Demo Pharmacist", role=models.UserRoleEnum.pharmacist, is_active=True, phone="555-0102"
    )
    db.add_all([admin, pharmacist])
    db.flush()
    
    category = models.Category(id=str(uuid.uuid4()), organization_id=org.id, name="General Medicines")
    db.add(category)
    db.flush()
    
    supplier = models.Supplier(id=str(uuid.uuid4()), organization_id=org.id, name="MediSupplies Ltd")
    db.add(supplier)
    db.flush()
    
    drugs = [
        models.Drug(id=str(uuid.uuid4()), organization_id=org.id, name="Paracetamol 500mg", generic_name="Paracetamol", form=models.DrugFormEnum.tablet, strength=500.0, strength_unit=models.StrengthUnitEnum.mg, category_id=category.id, supplier_id=supplier.id, price=50.0, reorder_level=100, barcode="123456789012"),
        models.Drug(id=str(uuid.uuid4()), organization_id=org.id, name="Amoxicillin 500mg", generic_name="Amoxicillin", form=models.DrugFormEnum.capsule, strength=500.0, strength_unit=models.StrengthUnitEnum.mg, category_id=category.id, supplier_id=supplier.id, price=150.0, reorder_level=50, barcode="123456789013"),
        models.Drug(id=str(uuid.uuid4()), organization_id=org.id, name="Ibuprofen 400mg", generic_name="Ibuprofen", form=models.DrugFormEnum.tablet, strength=400.0, strength_unit=models.StrengthUnitEnum.mg, category_id=category.id, supplier_id=supplier.id, price=80.0, reorder_level=75, barcode="123456789014")
    ]
    db.add_all(drugs)
    db.flush()
    
    for drug in drugs:
        db.add(models.InventoryBatch(id=str(uuid.uuid4()), drug_id=drug.id, lot_number=f"LOT-{drug.name[:5]}", quantity_on_hand=200, expiry_date=date(2026,12,31), purchase_date=date(2025,1,1), cost_price=drug.price*0.6, status=models.BatchStatusEnum.active))
    
    db.add(models.Customer(id=str(uuid.uuid4()), organization_id=org.id, first_name="John", last_name="Smith", email="john@example.com", phone="555-0100", allow_credit=True, credit_limit=5000.0, current_balance=0.0))
    db.commit()
    print("Demo data created!")

Base.metadata.create_all(bind=engine)
db = next(get_db())
try:
    create_demo_data(db)
except:
    db.rollback()
finally:
    db.close()

# ==================== FASTAPI APP ====================
app = FastAPI(title="PharmaSaaS")

app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32), max_age=86400)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")

# FIX: Create templates with a custom environment to avoid cache issues
from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
    cache_size=0  # Disable template caching completely
)
templates = Jinja2Templates(directory="templates", env=env)

cohere_service = CohereService()
tuma_service = TumaMpesaService()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()

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
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("landing.html", {"request": request})

# ==================== REGISTRATION ====================
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
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
        password = password.strip()
        confirm_password = confirm_password.strip()
        email = email.strip().lower()
        
        if password != confirm_password:
            return templates.TemplateResponse("register.html", {
                "request": request, "error": "Passwords do not match"
            })
        
        if len(password) < 6:
            return templates.TemplateResponse("register.html", {
                "request": request, "error": "Password must be at least 6 characters"
            })
        
        existing_user = db.query(models.User).filter(models.User.email == email).first()
        if existing_user:
            return templates.TemplateResponse("register.html", {
                "request": request, "error": "Email already registered"
            })
        
        existing_org = db.query(models.Organization).filter(models.Organization.name == pharmacy_name).first()
        if existing_org:
            return templates.TemplateResponse("register.html", {
                "request": request, "error": "Pharmacy name already taken"
            })
        
        org = models.Organization(
            id=str(uuid.uuid4()),
            name=pharmacy_name,
            slug=pharmacy_name.lower().replace(' ', '-'),
            owner_email=email,
            phone=phone,
            address="",
            subscription_plan="free",
            is_active=True
        )
        db.add(org)
        db.flush()
        
        user = models.User(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            username=email.split('@')[0][:100],
            email=email,
            password_hash=hash_password(password),
            full_name=f"{first_name} {last_name}"[:255],
            role=models.UserRoleEnum.admin,
            is_active=True,
            phone=phone[:50]
        )
        db.add(user)
        db.commit()
        
        request.session["user_id"] = user.id
        request.session["role"] = user.role.value
        request.session["org_id"] = user.organization_id
        
        return RedirectResponse(url="/dashboard", status_code=302)
        
    except Exception as e:
        db.rollback()
        print(f"Registration error: {e}")
        return templates.TemplateResponse("register.html", {
            "request": request, "error": "Registration failed. Please try again."
        })

# ==================== AUTHENTICATION ====================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request, 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        email = email.strip().lower()
        password = password.strip()
        
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse("login.html", {
                "request": request, "error": "Invalid email or password"
            })
        
        if not user.is_active:
            return templates.TemplateResponse("login.html", {
                "request": request, "error": "Your account is pending approval"
            })
        
        request.session["user_id"] = user.id
        request.session["role"] = user.role.value
        request.session["org_id"] = user.organization_id
        
        return RedirectResponse(url="/dashboard", status_code=302)
        
    except Exception as e:
        print(f"Login error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "An error occurred. Please try again."
        })

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session")
    return response

# ==================== DASHBOARD ====================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    
    total_products = db.query(models.Drug).filter(models.Drug.organization_id == org_id).count()
    total_customers = db.query(models.Customer).filter(models.Customer.organization_id == org_id).count()
    total_sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).count()
    
    pending_credit = db.query(func.sum(models.Customer.current_balance)).filter(
        models.Customer.organization_id == org_id
    ).scalar() or 0
    
    low_stock_items = []
    drugs = db.query(models.Drug).filter(models.Drug.organization_id == org_id).all()
    
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
            models.InventoryBatch.drug_id == drug.id,
            models.InventoryBatch.status == models.BatchStatusEnum.active
        ).scalar() or 0
        if total_stock < drug.reorder_level:
            low_stock_items.append({"name": drug.name, "stock": total_stock, "reorder": drug.reorder_level})
    
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
            "barcode": drug.barcode
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
    org_id = request.session.get("org_id")
    
    product = db.query(models.Drug).filter(
        models.Drug.barcode == code,
        models.Drug.organization_id == org_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
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
    data = await request.json()
    org_id = request.session.get("org_id")
    
    try:
        sale_number = f"SALE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
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
        
        for item in data["lineItems"]:
            line_item = models.SalesLineItem(
                id=str(uuid.uuid4()),
                sales_order_id=sale.id,
                drug_id=item["productId"],
                quantity=item["quantity"],
                unit_price=item["unitPrice"],
                line_total=item["lineTotal"]
            )
            db.add(line_item)
            
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
                if batch.quantity_on_hand == 0:
                    batch.status = models.BatchStatusEnum.empty
        
        if data["paymentMethod"] == "credit" and data.get("customerId"):
            customer = db.query(models.Customer).filter(models.Customer.id == data["customerId"]).first()
            if customer:
                customer.current_balance += data.get("balance", 0)
        
        db.commit()
        
        return {
            "success": True, 
            "sale_id": sale.id, 
            "sale_number": sale.sale_number
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error creating sale: {e}")
        raise HTTPException(status_code=400, detail=str(e))

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
        
        customer.current_balance -= amount
        db.commit()
        return {"success": True, "new_balance": float(customer.current_balance)}
    except Exception as e:
        db.rollback()
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
        existing = db.query(models.User).filter(models.User.email == data["email"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        staff = models.User(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            username=data["username"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
            full_name=data["full_name"],
            role=models.UserRoleEnum(data["role"]),
            is_active=data.get("is_active", True),
            phone=data.get("phone", "")
        )
        db.add(staff)
        db.commit()
        return {"success": True, "id": staff.id}
    except Exception as e:
        db.rollback()
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
    data = await request.json()
    message = data.get("message")
    session_id = data.get("sessionId")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    if not session_id:
        chat_session = models.AIChatSession(
            id=str(uuid.uuid4()),
            user_id=user.id, 
            title=message[:50] + "..." if len(message) > 50 else message
        )
        db.add(chat_session)
        db.flush()
        session_id = chat_session.id
    
    user_msg = models.AIChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=message
    )
    db.add(user_msg)
    db.flush()
    
    response = await cohere_service.get_drug_information(message)
    
    ai_msg = models.AIChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=response
    )
    db.add(ai_msg)
    db.commit()
    
    return {"sessionId": session_id, "response": response}

# ==================== MPESA PAYMENTS ====================
@app.post("/api/payment/mpesa/initiate")
async def initiate_mpesa_payment(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    sale_id = data.get("sale_id")
    phone = data.get("phone")
    amount = data.get("amount")
    
    if not sale_id or not phone or not amount:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    sale = db.query(models.SalesOrder).filter(
        models.SalesOrder.id == sale_id,
        models.SalesOrder.organization_id == request.session.get("org_id")
    ).first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    result = await tuma_service.initiate_payment(
        amount=amount,
        phone=phone,
        reference=sale.sale_number
    )
    
    if result["success"]:
        payment = models.Payment(
            id=str(uuid.uuid4()),
            organization_id=sale.organization_id,
            customer_id=sale.customer_id,
            sale_id=sale.id,
            amount=amount,
            payment_date=datetime.now().date(),
            payment_method=models.PaymentMethodEnum.mpesa,
            reference=result["reference"],
            status="pending",
            transaction_id=result["payment_id"],
            created_by=user.id
        )
        db.add(payment)
        db.commit()
        
        return {
            "success": True,
            "payment_id": result["payment_id"],
            "checkout_url": result["checkout_url"],
            "reference": result["reference"]
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Payment initiation failed"))

@app.get("/api/payment/status/{payment_id}")
async def check_payment_status(
    payment_id: str,
    request: Request,
    user: models.User = Depends(require_auth)
):
    return await tuma_service.check_payment_status(payment_id)

@app.post("/api/payment/callback")
async def payment_callback(request: Request):
    data = await request.json()
    db = next(get_db())
    payment = db.query(models.Payment).filter(models.Payment.transaction_id == data.get("payment_id")).first()
    if payment:
        payment.status = data.get("status")
        payment.completed_at = datetime.now()
        if data.get("status") == "completed":
            sale = db.query(models.SalesOrder).filter(models.SalesOrder.id == payment.sale_id).first()
            if sale:
                sale.amount_paid += payment.amount
                sale.balance = sale.total - sale.amount_paid
        db.commit()
    db.close()
    return {"status": "received"}

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
    
    daily_sales = {}
    for sale in sales:
        day = sale.created_at.date().isoformat()
        daily_sales[day] = daily_sales.get(day, 0) + float(sale.total)
    
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
        } for s in sales[:100]]
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
    total_value = 0
    
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
            models.InventoryBatch.drug_id == drug.id,
            models.InventoryBatch.status == models.BatchStatusEnum.active
        ).scalar() or 0
        
        value = total_stock * drug.price
        total_value += value
        
        report.append({
            "name": drug.name,
            "stock": int(total_stock),
            "price": float(drug.price),
            "total_value": float(value),
            "reorder_level": drug.reorder_level,
            "status": "Low Stock" if total_stock < drug.reorder_level else "OK"
        })
    
    return {
        "items": report,
        "total_items": len(report),
        "total_inventory_value": float(total_value)
    }

# ==================== CATEGORIES & SUPPLIERS ====================
@app.get("/api/categories")
async def get_categories(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    categories = db.query(models.Category).filter(
        models.Category.organization_id == request.session.get("org_id")
    ).all()
    return [{"id": c.id, "name": c.name, "description": c.description} for c in categories]

@app.get("/api/suppliers")
async def get_suppliers(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    suppliers = db.query(models.Supplier).filter(
        models.Supplier.organization_id == request.session.get("org_id")
    ).all()
    return [{"id": s.id, "name": s.name, "contact_person": s.contact_person, "email": s.email, "phone": s.phone} for s in suppliers]

# ==================== ERROR HANDLER ====================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=302)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
