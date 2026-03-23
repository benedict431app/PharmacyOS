import bcrypt
import types

# BCrypt workaround
try:
    bcrypt.__about__
except AttributeError:
    bcrypt.__about__ = types.SimpleNamespace()
    bcrypt.__about__.__version__ = "3.2.0"

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from passlib.context import CryptContext
from datetime import datetime, date, timedelta
import os
import uuid
import cohere
import secrets
import httpx
import json

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
    pbkdf2_sha256__default_rounds=30000
)

def hash_password(password: str) -> str:
    password = str(password).strip()
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    return pwd_context.hash(password, scheme="pbkdf2_sha256")

def verify_password(password: str, hashed_password: str) -> bool:
    password = str(password).strip()
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
    
    customer = models.Customer(id=str(uuid.uuid4()), organization_id=org.id, first_name="John", last_name="Smith", email="john@example.com", phone="555-0100", allow_credit=True, credit_limit=5000.0, current_balance=0.0)
    db.add(customer)
    db.flush()
    
    demo_medication = models.PatientMedication(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        patient_id=customer.id,
        drug_id=drugs[0].id,
        dosage_instructions="Take 1 tablet every 8 hours",
        quantity_given=90,
        quantity_remaining=15,
        unit="tablets",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        next_refill_date=date.today() + timedelta(days=2),
        last_refill_date=date.today() - timedelta(days=25),
        reminder_days_before=3,
        low_stock_threshold=10,
        status=models.MedicationStatusEnum.active,
        notes="Patient has hypertension, monitor blood pressure",
        created_by=admin.id
    )
    db.add(demo_medication)
    
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
templates = Jinja2Templates(directory="templates")
templates.env.cache = {}

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

def create_reminder(db: Session, medication, reminder_type, message):
    reminder = models.MedicationReminder(
        id=str(uuid.uuid4()),
        medication_id=medication.id,
        organization_id=medication.organization_id,
        patient_id=medication.patient_id,
        reminder_type=reminder_type,
        message=message,
        sent_at=datetime.now()
    )
    db.add(reminder)
    db.commit()
    return reminder

# ==================== AUTHENTICATION ROUTES ====================
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    if not user.is_active:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Account pending approval"})
    
    request.session["user_id"] = user.id
    request.session["role"] = user.role.value
    request.session["org_id"] = user.organization_id
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                   pharmacy_name: str = Form(...), email: str = Form(...), phone: str = Form(...),
                   password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm_password:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Passwords do not match"})
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Password too short"})
    
    email = email.strip().lower()
    if db.query(models.User).filter(models.User.email == email).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})
    if db.query(models.Organization).filter(models.Organization.name == pharmacy_name).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Pharmacy name taken"})
    
    org = models.Organization(id=str(uuid.uuid4()), name=pharmacy_name, slug=pharmacy_name.lower().replace(' ', '-'),
                              owner_email=email, phone=phone, subscription_plan="free", is_active=True)
    db.add(org)
    db.flush()
    
    user = models.User(id=str(uuid.uuid4()), organization_id=org.id, username=email.split('@')[0], email=email,
                       password_hash=hash_password(password), full_name=f"{first_name} {last_name}",
                       role=models.UserRoleEnum.admin, is_active=True, phone=phone)
    db.add(user)
    db.commit()
    
    request.session["user_id"] = user.id
    request.session["role"] = user.role.value
    request.session["org_id"] = user.organization_id
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/register-staff", response_class=HTMLResponse)
async def register_staff_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("register_staff.html", {"request": request})

@app.post("/register-staff")
async def register_staff(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                         pharmacy_name: str = Form(...), email: str = Form(...), phone: str = Form(...),
                         requested_role: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm_password:
        return templates.TemplateResponse("register_staff.html", {"request": request, "error": "Passwords do not match"})
    if len(password) < 6:
        return templates.TemplateResponse("register_staff.html", {"request": request, "error": "Password too short"})
    
    email = email.strip().lower()
    org = db.query(models.Organization).filter(models.Organization.name == pharmacy_name).first()
    if not org:
        return templates.TemplateResponse("register_staff.html", {"request": request, "error": "Pharmacy not found"})
    
    if db.query(models.User).filter(models.User.email == email).first():
        return templates.TemplateResponse("register_staff.html", {"request": request, "error": "Email already registered"})
    
    user = models.User(id=str(uuid.uuid4()), organization_id=org.id, username=email.split('@')[0], email=email,
                       password_hash=hash_password(password), full_name=f"{first_name} {last_name}",
                       role=models.UserRoleEnum(requested_role), is_active=False, phone=phone)
    db.add(user)
    db.commit()
    
    return templates.TemplateResponse("register_staff.html", {"request": request, "success": "Application submitted! Please wait for approval."})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

# ==================== DASHBOARD ====================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    
    total_products = db.query(models.Drug).filter(models.Drug.organization_id == org_id).count()
    total_customers = db.query(models.Customer).filter(models.Customer.organization_id == org_id).count()
    total_sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).count()
    pending_credit = db.query(func.sum(models.Customer.current_balance)).filter(models.Customer.organization_id == org_id).scalar() or 0
    pending_staff = db.query(models.User).filter(models.User.organization_id == org_id, models.User.is_active == False).count()
    
    low_stock_items = []
    for drug in db.query(models.Drug).filter(models.Drug.organization_id == org_id).all():
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == drug.id).scalar() or 0
        if stock < drug.reorder_level:
            low_stock_items.append({"name": drug.name, "stock": stock, "reorder": drug.reorder_level})
    
    recent_sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).order_by(models.SalesOrder.created_at.desc()).limit(5).all()
    
    medication_alerts = db.query(models.PatientMedication).filter(
        models.PatientMedication.organization_id == org_id,
        models.PatientMedication.status == models.MedicationStatusEnum.active,
        or_(
            models.PatientMedication.quantity_remaining <= models.PatientMedication.low_stock_threshold,
            models.PatientMedication.next_refill_date <= date.today()
        )
    ).count()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "total_products": total_products,
        "total_customers": total_customers,
        "total_sales": total_sales,
        "pending_credit": float(pending_credit),
        "pending_staff": pending_staff,
        "low_stock_items": low_stock_items,
        "recent_sales": recent_sales,
        "medication_alerts": medication_alerts
    })

# ==================== INVENTORY MANAGEMENT ====================
@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("inventory.html", {"request": request, "user": user})

@app.get("/api/inventory")
async def get_inventory(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), page: int = 1, limit: int = 20, search: str = ""):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    
    query = db.query(models.Drug).filter(models.Drug.organization_id == org_id)
    if search:
        query = query.filter(or_(
            models.Drug.name.ilike(f"%{search}%"),
            models.Drug.generic_name.ilike(f"%{search}%"),
            models.Drug.barcode.ilike(f"%{search}%")
        ))
    
    total = query.count()
    drugs = query.offset(offset).limit(limit).all()
    
    items = []
    for d in drugs:
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == d.id).scalar() or 0
        items.append({
            "id": d.id, "name": d.name, "price": float(d.price), "stock": int(stock),
            "reorder_level": d.reorder_level, "barcode": d.barcode
        })
    
    return {"items": items, "total": total, "pages": (total + limit - 1) // limit}

@app.post("/api/inventory")
async def add_inventory(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    try:
        drug = models.Drug(
            id=str(uuid.uuid4()), organization_id=org_id, name=data["name"],
            generic_name=data.get("generic_name", ""), manufacturer=data.get("manufacturer", ""),
            form=models.DrugFormEnum(data["form"]), strength=data.get("strength", 0),
            strength_unit=models.StrengthUnitEnum(data.get("strength_unit", "mg")),
            category_id=data.get("category_id"), supplier_id=data.get("supplier_id"),
            description=data.get("description", ""), usage_instructions=data.get("usage_instructions", ""),
            side_effects=data.get("side_effects", ""), contraindications=data.get("contraindications", ""),
            price=data.get("price", 0), reorder_level=data.get("reorder_level", 50), barcode=data.get("barcode", "")
        )
        db.add(drug)
        db.flush()
        
        if data.get("initial_quantity", 0) > 0:
            db.add(models.InventoryBatch(
                id=str(uuid.uuid4()), drug_id=drug.id, lot_number=data.get("lot_number", f"LOT-{datetime.now().strftime('%Y%m%d')}"),
                quantity_on_hand=data["initial_quantity"],
                expiry_date=datetime.strptime(data["expiry_date"], "%Y-%m-%d").date() if data.get("expiry_date") else None,
                purchase_date=datetime.now().date(), cost_price=data.get("cost_price", drug.price * 0.6),
                status=models.BatchStatusEnum.active
            ))
        
        db.commit()
        return {"success": True, "id": drug.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

@app.put("/api/inventory/{drug_id}")
async def update_inventory(drug_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    drug = db.query(models.Drug).filter(models.Drug.id == drug_id).first()
    if not drug:
        raise HTTPException(404, "Not found")
    
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

@app.delete("/api/inventory/{drug_id}")
async def delete_inventory(drug_id: str, request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drug = db.query(models.Drug).filter(models.Drug.id == drug_id).first()
    if not drug:
        raise HTTPException(404, "Not found")
    
    has_sales = db.query(models.SalesLineItem).filter(models.SalesLineItem.drug_id == drug_id).first()
    if has_sales:
        raise HTTPException(400, "Cannot delete product with existing sales")
    
    db.query(models.InventoryBatch).filter(models.InventoryBatch.drug_id == drug_id).delete()
    db.delete(drug)
    db.commit()
    return {"success": True}

# ==================== POINT OF SALE ====================
@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("pos.html", {"request": request, "user": user})

@app.get("/api/product_by_barcode")
async def product_by_barcode(code: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    product = db.query(models.Drug).filter(models.Drug.barcode == code).first()
    if not product:
        raise HTTPException(404, "Not found")
    stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == product.id).scalar() or 0
    return {"id": product.id, "name": product.name, "price": float(product.price), "stock": int(stock)}

@app.get("/api/products/search")
async def search_products(request: Request, q: str, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    products = db.query(models.Drug).filter(or_(
        models.Drug.name.ilike(f"%{q}%"),
        models.Drug.barcode.ilike(f"%{q}%")
    )).limit(20).all()
    
    result = []
    for p in products:
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == p.id).scalar() or 0
        result.append({"id": p.id, "name": p.name, "price": float(p.price), "stock": int(stock)})
    return result

@app.post("/api/sales")
async def create_sale(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    try:
        sale_number = f"SALE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        sale = models.SalesOrder(
            id=str(uuid.uuid4()), organization_id=org_id, customer_id=data.get("customerId"),
            sale_number=sale_number, subtotal=data["subtotal"], tax=data.get("tax", 0),
            discount=data.get("discount", 0), total=data["total"],
            payment_method=models.PaymentMethodEnum(data["paymentMethod"]),
            amount_paid=data.get("amountPaid", data["total"]), balance=data.get("balance", 0),
            created_by=user.id
        )
        db.add(sale)
        db.flush()
        
        for item in data["lineItems"]:
            db.add(models.SalesLineItem(id=str(uuid.uuid4()), sales_order_id=sale.id, drug_id=item["productId"],
                                         quantity=item["quantity"], unit_price=item["unitPrice"], line_total=item["lineTotal"]))
            remaining = item["quantity"]
            for batch in db.query(models.InventoryBatch).filter(
                models.InventoryBatch.drug_id == item["productId"],
                models.InventoryBatch.quantity_on_hand > 0
            ).order_by(models.InventoryBatch.expiry_date).all():
                if remaining <= 0: break
                take = min(batch.quantity_on_hand, remaining)
                batch.quantity_on_hand -= take
                remaining -= take
        
        if data["paymentMethod"] == "credit" and data.get("customerId"):
            customer = db.query(models.Customer).filter(models.Customer.id == data["customerId"]).first()
            if customer:
                customer.current_balance += data.get("balance", 0)
        
        db.commit()
        return {"success": True, "sale_id": sale.id, "sale_number": sale.sale_number}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

@app.get("/api/sales")
async def get_sales(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), page: int = 1, limit: int = 20):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    query = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id)
    total = query.count()
    sales = query.order_by(models.SalesOrder.created_at.desc()).offset(offset).limit(limit).all()
    result = [{"id": s.id, "sale_number": s.sale_number, "date": s.created_at.isoformat(),
               "customer_name": s.customer.full_name if s.customer else "Walk-in Customer",
               "total": float(s.total), "payment_method": s.payment_method.value} for s in sales]
    return {"items": result, "total": total, "pages": (total + limit - 1) // limit}

# ==================== CUSTOMER MANAGEMENT ====================
@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("customers.html", {"request": request, "user": user})

@app.get("/api/customers")
async def get_customers(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), page: int = 1, limit: int = 20, search: str = ""):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    
    query = db.query(models.Customer).filter(models.Customer.organization_id == org_id)
    if search:
        query = query.filter(or_(
            models.Customer.first_name.ilike(f"%{search}%"),
            models.Customer.last_name.ilike(f"%{search}%"),
            models.Customer.email.ilike(f"%{search}%"),
            models.Customer.phone.ilike(f"%{search}%")
        ))
    
    total = query.count()
    customers = query.offset(offset).limit(limit).all()
    items = [{"id": c.id, "full_name": c.full_name, "email": c.email, "phone": c.phone, "current_balance": float(c.current_balance)} for c in customers]
    return {"items": items, "total": total, "pages": (total + limit - 1) // limit}

@app.post("/api/customers")
async def add_customer(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    customer = models.Customer(
        id=str(uuid.uuid4()), organization_id=request.session.get("org_id"),
        first_name=data["first_name"], last_name=data["last_name"], email=data.get("email", ""),
        phone=data.get("phone", ""), address=data.get("address", ""),
        date_of_birth=datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date() if data.get("date_of_birth") else None,
        allergies=data.get("allergies", ""), medical_conditions=data.get("medical_conditions", ""),
        allow_credit=data.get("allow_credit", False), credit_limit=data.get("credit_limit", 0), current_balance=0
    )
    db.add(customer)
    db.commit()
    return {"success": True, "id": customer.id}

@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Not found")
    
    for key, value in data.items():
        if hasattr(customer, key) and key not in ["id", "organization_id", "created_at"]:
            if key == "date_of_birth" and value:
                setattr(customer, key, datetime.strptime(value, "%Y-%m-%d").date())
            else:
                setattr(customer, key, value)
    db.commit()
    return {"success": True}

@app.post("/api/customers/{customer_id}/payment")
async def add_customer_payment(customer_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Not found")
    
    customer.current_balance -= data.get("amount", 0)
    db.commit()
    return {"success": True, "new_balance": float(customer.current_balance)}

# ==================== STAFF MANAGEMENT ====================
@app.get("/staff", response_class=HTMLResponse)
async def staff_page(request: Request, user: models.User = Depends(require_role("admin"))):
    return templates.TemplateResponse("staff.html", {"request": request, "user": user})

@app.get("/api/staff")
async def get_staff(request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    staff = db.query(models.User).filter(
        models.User.organization_id == request.session.get("org_id"),
        models.User.role != models.UserRoleEnum.admin
    ).all()
    return [{"id": s.id, "full_name": s.full_name, "email": s.email, "role": s.role.value, "is_active": s.is_active} for s in staff]

@app.post("/api/staff")
async def add_staff(request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    data = await request.json()
    if db.query(models.User).filter(models.User.email == data["email"]).first():
        raise HTTPException(400, "Email exists")
    
    staff = models.User(id=str(uuid.uuid4()), organization_id=request.session.get("org_id"), username=data["username"],
                        email=data["email"], password_hash=hash_password(data["password"]), full_name=data["full_name"],
                        role=models.UserRoleEnum(data["role"]), is_active=True, phone=data.get("phone", ""))
    db.add(staff)
    db.commit()
    return {"success": True, "id": staff.id}

@app.put("/api/staff/{staff_id}")
async def update_staff(staff_id: str, request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    data = await request.json()
    staff = db.query(models.User).filter(models.User.id == staff_id).first()
    if not staff:
        raise HTTPException(404, "Not found")
    
    for key, value in data.items():
        if hasattr(staff, key) and key not in ["id", "organization_id", "created_at", "password_hash"]:
            if key == "role":
                setattr(staff, key, models.UserRoleEnum(value))
            else:
                setattr(staff, key, value)
    
    if data.get("password"):
        staff.password_hash = hash_password(data["password"])
    
    db.commit()
    return {"success": True}

@app.post("/api/staff/{staff_id}/approve")
async def approve_staff(staff_id: str, request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    staff = db.query(models.User).filter(models.User.id == staff_id).first()
    if not staff:
        raise HTTPException(404, "Not found")
    staff.is_active = True
    db.commit()
    return {"success": True}

@app.delete("/api/staff/{staff_id}")
async def delete_staff(staff_id: str, request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    if staff_id == user.id:
        raise HTTPException(400, "Cannot delete yourself")
    staff = db.query(models.User).filter(models.User.id == staff_id).first()
    if not staff:
        raise HTTPException(404, "Not found")
    db.delete(staff)
    db.commit()
    return {"success": True}

# ==================== AI CHAT ====================
@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("ai_chat.html", {"request": request, "user": user})

@app.post("/api/ai/chat")
async def ai_chat(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    message = data.get("message")
    session_id = data.get("sessionId")
    
    if not message:
        raise HTTPException(400, "Message required")
    
    if not session_id:
        session = models.AIChatSession(id=str(uuid.uuid4()), user_id=user.id, title=message[:50])
        db.add(session)
        db.flush()
        session_id = session.id
    
    db.add(models.AIChatMessage(id=str(uuid.uuid4()), session_id=session_id, role="user", content=message))
    db.flush()
    
    response = await cohere_service.get_drug_information(message)
    db.add(models.AIChatMessage(id=str(uuid.uuid4()), session_id=session_id, role="assistant", content=response))
    db.commit()
    
    return {"sessionId": session_id, "response": response}

@app.get("/api/ai/sessions")
async def get_ai_sessions(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    sessions = db.query(models.AIChatSession).filter(models.AIChatSession.user_id == user.id).order_by(models.AIChatSession.updated_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in sessions]

@app.get("/api/ai/sessions/{session_id}/messages")
async def get_ai_messages(session_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    session = db.query(models.AIChatSession).filter(models.AIChatSession.id == session_id, models.AIChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    messages = db.query(models.AIChatMessage).filter(models.AIChatMessage.session_id == session_id).order_by(models.AIChatMessage.created_at).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages]

# ==================== PATIENT MEDICATION MONITORING ====================
@app.get("/patient-medications", response_class=HTMLResponse)
async def patient_medications_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("patient_medications.html", {"request": request, "user": user})

@app.get("/api/patient-medications")
async def get_patient_medications(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), page: int = 1, limit: int = 20, status: str = "active"):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    
    status_enum = models.MedicationStatusEnum.active if status == "active" else (models.MedicationStatusEnum.completed if status == "completed" else models.MedicationStatusEnum.discontinued)
    
    query = db.query(models.PatientMedication).filter(
        models.PatientMedication.organization_id == org_id,
        models.PatientMedication.status == status_enum
    )
    
    total = query.count()
    medications = query.offset(offset).limit(limit).all()
    
    result = []
    for m in medications:
        result.append({
            "id": m.id,
            "patient": {"id": m.patient.id, "name": m.patient.full_name},
            "drug": {"id": m.drug.id, "name": m.drug.name},
            "dosage_instructions": m.dosage_instructions,
            "quantity_given": m.quantity_given,
            "quantity_remaining": m.quantity_remaining,
            "unit": m.unit,
            "needs_alert": m.quantity_remaining <= m.low_stock_threshold,
            "status": m.status.value
        })
    
    return {"items": result, "total": total, "pages": (total + limit - 1) // limit}

@app.post("/api/patient-medications")
async def add_patient_medication(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    try:
        end_date = None
        next_refill_date = None
        if data.get("end_date"):
            end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
            next_refill_date = end_date - timedelta(days=data.get("reminder_days_before", 3))
        
        medication = models.PatientMedication(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            patient_id=data["patient_id"],
            drug_id=data["drug_id"],
            dosage_instructions=data["dosage_instructions"],
            quantity_given=data["quantity_given"],
            quantity_remaining=data["quantity_given"],
            unit=data.get("unit", "tablets"),
            start_date=datetime.strptime(data["start_date"], "%Y-%m-%d").date(),
            end_date=end_date,
            next_refill_date=next_refill_date,
            last_refill_date=datetime.now().date(),
            reminder_days_before=data.get("reminder_days_before", 3),
            low_stock_threshold=data.get("low_stock_threshold", 10),
            status=models.MedicationStatusEnum.active,
            notes=data.get("notes", ""),
            created_by=user.id
        )
        db.add(medication)
        db.commit()
        
        if medication.quantity_remaining <= medication.low_stock_threshold:
            create_reminder(db, medication, "low_stock", f"Low stock alert: Only {medication.quantity_remaining} {medication.unit} remaining")
        
        return {"success": True, "id": medication.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

@app.put("/api/patient-medications/{medication_id}/refill")
async def refill_medication(medication_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    medication = db.query(models.PatientMedication).filter(models.PatientMedication.id == medication_id).first()
    if not medication:
        raise HTTPException(404, "Not found")
    
    quantity_refilled = data.get("quantity", 0)
    medication.quantity_remaining += quantity_refilled
    medication.last_refill_date = datetime.now().date()
    
    if medication.end_date:
        medication.next_refill_date = medication.end_date - timedelta(days=medication.reminder_days_before)
    
    db.commit()
    
    create_reminder(db, medication, "refill_due", f"Medication refilled: {quantity_refilled} {medication.unit} added. New stock: {medication.quantity_remaining}")
    
    return {"success": True, "new_quantity": medication.quantity_remaining}

@app.post("/api/patient-medications/{medication_id}/adjust-stock")
async def adjust_medication_stock(medication_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    medication = db.query(models.PatientMedication).filter(models.PatientMedication.id == medication_id).first()
    if not medication:
        raise HTTPException(404, "Not found")
    
    new_quantity = data.get("quantity", 0)
    medication.quantity_remaining = new_quantity
    db.commit()
    
    if new_quantity <= medication.low_stock_threshold:
        create_reminder(db, medication, "low_stock", f"Low stock alert: Only {new_quantity} {medication.unit} remaining")
    
    return {"success": True, "new_quantity": new_quantity}

@app.get("/api/patient-medications/alerts")
async def get_medication_alerts(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    alerts = []
    
    low_stock = db.query(models.PatientMedication).filter(
        models.PatientMedication.organization_id == org_id,
        models.PatientMedication.status == models.MedicationStatusEnum.active,
        models.PatientMedication.quantity_remaining <= models.PatientMedication.low_stock_threshold
    ).all()
    
    for med in low_stock:
        alerts.append({
            "type": "low_stock",
            "medication_id": med.id,
            "patient": med.patient.full_name,
            "drug": med.drug.name,
            "message": f"Low stock: {med.quantity_remaining} {med.unit} remaining",
            "urgency": "high"
        })
    
    refill_due = db.query(models.PatientMedication).filter(
        models.PatientMedication.organization_id == org_id,
        models.PatientMedication.status == models.MedicationStatusEnum.active,
        models.PatientMedication.next_refill_date <= date.today(),
        models.PatientMedication.next_refill_date.isnot(None)
    ).all()
    
    for med in refill_due:
        alerts.append({
            "type": "refill_due",
            "medication_id": med.id,
            "patient": med.patient.full_name,
            "drug": med.drug.name,
            "message": f"Refill overdue",
            "urgency": "high"
        })
    
    return {"alerts": alerts, "count": len(alerts)}

@app.get("/api/patient-medications/{medication_id}/chat")
async def get_medication_chat(medication_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    messages = db.query(models.MedicationChat).filter(models.MedicationChat.medication_id == medication_id).order_by(models.MedicationChat.created_at).all()
    return [{
        "id": m.id,
        "message": m.message,
        "is_from_patient": m.is_from_patient,
        "sender_name": m.patient.full_name if m.is_from_patient else "Pharmacy",
        "created_at": m.created_at.isoformat()
    } for m in messages]

@app.post("/api/patient-medications/{medication_id}/chat")
async def send_medication_chat(medication_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    medication = db.query(models.PatientMedication).filter(models.PatientMedication.id == medication_id).first()
    if not medication:
        raise HTTPException(404, "Not found")
    
    chat = models.MedicationChat(
        id=str(uuid.uuid4()),
        medication_id=medication_id,
        organization_id=medication.organization_id,
        patient_id=medication.patient_id,
        user_id=user.id,
        message=data["message"],
        is_from_patient=False
    )
    db.add(chat)
    db.commit()
    return {"success": True, "id": chat.id}

@app.post("/api/check-medication-alerts")
async def check_medication_alerts(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    medications = db.query(models.PatientMedication).filter(
        models.PatientMedication.organization_id == org_id,
        models.PatientMedication.status == models.MedicationStatusEnum.active
    ).all()
    
    alerts_created = 0
    for med in medications:
        if med.quantity_remaining <= med.low_stock_threshold:
            existing = db.query(models.MedicationReminder).filter(
                models.MedicationReminder.medication_id == med.id,
                models.MedicationReminder.reminder_type == "low_stock",
                models.MedicationReminder.sent_at >= datetime.now() - timedelta(days=3)
            ).first()
            if not existing:
                create_reminder(db, med, "low_stock", f"⚠️ Low stock alert: Only {med.quantity_remaining} {med.unit} remaining. Please refill soon.")
                alerts_created += 1
        
        if med.next_refill_date and med.next_refill_date <= date.today():
            existing = db.query(models.MedicationReminder).filter(
                models.MedicationReminder.medication_id == med.id,
                models.MedicationReminder.reminder_type == "refill_due",
                models.MedicationReminder.sent_at >= datetime.now() - timedelta(days=3)
            ).first()
            if not existing:
                create_reminder(db, med, "refill_due", f"📅 Refill reminder: Medication refill is overdue. Please schedule a refill.")
                alerts_created += 1
    
    return {"success": True, "alerts_created": alerts_created}

# ==================== MPESA PAYMENTS ====================
@app.post("/api/payment/mpesa/initiate")
async def initiate_mpesa(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    sale = db.query(models.SalesOrder).filter(models.SalesOrder.id == data["sale_id"]).first()
    if not sale:
        raise HTTPException(404, "Sale not found")
    
    result = await tuma_service.initiate_payment(data["amount"], data["phone"], sale.sale_number)
    if result["success"]:
        payment = models.Payment(
            id=str(uuid.uuid4()),
            organization_id=sale.organization_id,
            sale_id=sale.id,
            amount=data["amount"],
            payment_method=models.PaymentMethodEnum.mpesa,
            reference=result["reference"],
            status="pending",
            transaction_id=result["payment_id"],
            created_by=user.id
        )
        db.add(payment)
        db.commit()
    return result

@app.get("/api/payment/status/{payment_id}")
async def payment_status(payment_id: str, request: Request):
    return await tuma_service.check_payment_status(payment_id)

@app.post("/api/payment/callback")
async def payment_callback(request: Request):
    data = await request.json()
    db = next(get_db())
    payment = db.query(models.Payment).filter(models.Payment.transaction_id == data.get("payment_id")).first()
    if payment:
        payment.status = data.get("status")
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
async def sales_report(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), start_date: str = None, end_date: str = None):
    org_id = request.session.get("org_id")
    query = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id)
    if start_date:
        query = query.filter(models.SalesOrder.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(models.SalesOrder.created_at <= datetime.fromisoformat(end_date))
    sales = query.all()
    total_sales = sum(s.total for s in sales)
    return {"total_sales": float(total_sales), "count": len(sales)}

@app.get("/api/reports/inventory")
async def inventory_report(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    drugs = db.query(models.Drug).all()
    items = []
    total_value = 0
    for d in drugs:
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == d.id).scalar() or 0
        value = stock * d.price
        total_value += value
        items.append({"name": d.name, "stock": int(stock), "value": float(value)})
    return {"items": items, "total_value": float(total_value)}

# ==================== CATEGORIES & SUPPLIERS ====================
@app.get("/api/categories")
async def get_categories(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    categories = db.query(models.Category).filter(models.Category.organization_id == request.session.get("org_id")).all()
    return [{"id": c.id, "name": c.name} for c in categories]

@app.get("/api/suppliers")
async def get_suppliers(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    suppliers = db.query(models.Supplier).filter(models.Supplier.organization_id == request.session.get("org_id")).all()
    return [{"id": s.id, "name": s.name, "phone": s.phone} for s in suppliers]

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=302)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
