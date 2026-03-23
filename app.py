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
from sqlalchemy import func, or_, and_
from passlib.context import CryptContext
from datetime import datetime, date
import os
import uuid
import cohere
import secrets
import httpx

from database import engine, get_db, Base
import models

# ==================== CONFIGURATION ====================
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

# ==================== SERVICES ====================
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
templates = Jinja2Templates(directory="templates")
# Fix for template error
templates.env.autoescape = True

cohere_service = CohereService()
tuma_service = TumaMpesaService()

def get_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()

# ==================== PUBLIC PAGES ====================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
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
        return templates.TemplateResponse("login.html", {"request": request, "error": "Account inactive"})
    
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
        return templates.TemplateResponse("register.html", {"request": request, "error": "Passwords don't match"})
    if len(password) < 6:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Password too short"})
    
    email = email.strip().lower()
    if db.query(models.User).filter(models.User.email == email).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email exists"})
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

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

# ==================== PROTECTED PAGES ====================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    org_id = request.session.get("org_id")
    products = db.query(models.Drug).filter(models.Drug.organization_id == org_id).count()
    customers = db.query(models.Customer).filter(models.Customer.organization_id == org_id).count()
    sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).count()
    credit = db.query(func.sum(models.Customer.current_balance)).filter(models.Customer.organization_id == org_id).scalar() or 0
    
    low_stock = []
    for drug in db.query(models.Drug).filter(models.Drug.organization_id == org_id).all():
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == drug.id).scalar() or 0
        if stock < drug.reorder_level:
            low_stock.append({"name": drug.name, "stock": stock, "reorder": drug.reorder_level})
    
    recent = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).order_by(models.SalesOrder.created_at.desc()).limit(5).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "total_products": products, "total_customers": customers,
        "total_sales": sales, "pending_credit": float(credit), "low_stock_items": low_stock, "recent_sales": recent
    })

@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("inventory.html", {"request": request})

@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("pos.html", {"request": request})

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("customers.html", {"request": request})

@app.get("/staff", response_class=HTMLResponse)
async def staff_page(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("staff.html", {"request": request})

@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat_page(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("ai_chat.html", {"request": request})

# ==================== INVENTORY API (FULL CRUD) ====================
@app.get("/api/inventory")
async def get_inventory(request: Request, db: Session = Depends(get_db), page: int = 1, limit: int = 20, search: str = ""):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
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
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
            models.InventoryBatch.drug_id == d.id,
            models.InventoryBatch.status == models.BatchStatusEnum.active
        ).scalar() or 0
        items.append({
            "id": d.id, "name": d.name, "generic_name": d.generic_name, "manufacturer": d.manufacturer,
            "form": d.form.value, "strength": d.strength, "strength_unit": d.strength_unit.value,
            "price": float(d.price), "stock": int(stock), "reorder_level": d.reorder_level,
            "barcode": d.barcode, "description": d.description, "usage_instructions": d.usage_instructions,
            "side_effects": d.side_effects, "contraindications": d.contraindications
        })
    return {"items": items, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}

@app.post("/api/inventory")
async def add_inventory(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        raise HTTPException(401, "Unauthorized")
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
async def update_inventory(drug_id: str, request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    data = await request.json()
    
    drug = db.query(models.Drug).filter(models.Drug.id == drug_id).first()
    if not drug:
        raise HTTPException(404, "Not found")
    
    try:
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
        raise HTTPException(400, detail=str(e))

@app.delete("/api/inventory/{drug_id}")
async def delete_inventory(drug_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        raise HTTPException(403, "Forbidden")
    
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

# ==================== POS API ====================
@app.get("/api/product_by_barcode")
async def product_by_barcode(code: str, request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    product = db.query(models.Drug).filter(models.Drug.barcode == code).first()
    if not product:
        raise HTTPException(404, "Not found")
    stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == product.id).scalar() or 0
    return {"id": product.id, "name": product.name, "price": float(product.price), "barcode": product.barcode, "stock": int(stock)}

@app.get("/api/products/search")
async def search_products(request: Request, q: str, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    products = db.query(models.Drug).filter(
        or_(models.Drug.name.ilike(f"%{q}%"), models.Drug.barcode.ilike(f"%{q}%"))
    ).limit(20).all()
    
    result = []
    for p in products:
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == p.id).scalar() or 0
        result.append({"id": p.id, "name": p.name, "price": float(p.price), "stock": int(stock), "barcode": p.barcode})
    return result

@app.post("/api/sales")
async def create_sale(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        raise HTTPException(401, "Unauthorized")
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
async def get_sales(request: Request, db: Session = Depends(get_db), page: int = 1, limit: int = 20):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    
    query = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id)
    total = query.count()
    sales = query.order_by(models.SalesOrder.created_at.desc()).offset(offset).limit(limit).all()
    
    result = [{
        "id": s.id, "sale_number": s.sale_number, "date": s.created_at.isoformat(),
        "customer_name": s.customer.full_name if s.customer else "Walk-in Customer",
        "total": float(s.total), "payment_method": s.payment_method.value
    } for s in sales]
    
    return {"items": result, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}

# ==================== CUSTOMER API ====================
@app.get("/api/customers")
async def get_customers(request: Request, db: Session = Depends(get_db), page: int = 1, limit: int = 20, search: str = ""):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    
    query = db.query(models.Customer).filter(models.Customer.organization_id == org_id)
    if search:
        query = query.filter(or_(
            models.Customer.first_name.ilike(f"%{search}%"),
            models.Customer.last_name.ilike(f"%{search}%"),
            models.Customer.email.ilike(f"%{search}%")
        ))
    
    total = query.count()
    customers = query.offset(offset).limit(limit).all()
    items = [{
        "id": c.id, "first_name": c.first_name, "last_name": c.last_name, "full_name": c.full_name,
        "email": c.email, "phone": c.phone, "address": c.address,
        "allow_credit": c.allow_credit, "credit_limit": float(c.credit_limit) if c.credit_limit else 0,
        "current_balance": float(c.current_balance) if c.current_balance else 0
    } for c in customers]
    
    return {"items": items, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}

@app.post("/api/customers")
async def add_customer(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    data = await request.json()
    
    customer = models.Customer(
        id=str(uuid.uuid4()), organization_id=request.session.get("org_id"),
        first_name=data["first_name"], last_name=data["last_name"], email=data.get("email", ""),
        phone=data.get("phone", ""), address=data.get("address", ""),
        allow_credit=data.get("allow_credit", False), credit_limit=data.get("credit_limit", 0), current_balance=0
    )
    db.add(customer)
    db.commit()
    return {"success": True, "id": customer.id}

@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: str, request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    data = await request.json()
    
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Not found")
    
    for key, value in data.items():
        if hasattr(customer, key) and key not in ["id", "organization_id", "created_at"]:
            setattr(customer, key, value)
    db.commit()
    return {"success": True}

@app.post("/api/customers/{customer_id}/payment")
async def add_customer_payment(customer_id: str, request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    data = await request.json()
    
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Not found")
    
    amount = data.get("amount", 0)
    if amount <= 0:
        raise HTTPException(400, "Invalid amount")
    
    customer.current_balance -= amount
    db.commit()
    return {"success": True, "new_balance": float(customer.current_balance)}

# ==================== STAFF API ====================
@app.get("/api/staff")
async def get_staff(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        raise HTTPException(403, "Forbidden")
    
    staff = db.query(models.User).filter(
        models.User.organization_id == request.session.get("org_id"),
        models.User.role != models.UserRoleEnum.admin
    ).all()
    
    return [{"id": s.id, "username": s.username, "email": s.email, "full_name": s.full_name,
             "role": s.role.value, "is_active": s.is_active, "phone": s.phone} for s in staff]

@app.post("/api/staff")
async def add_staff(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        raise HTTPException(403, "Forbidden")
    data = await request.json()
    
    if db.query(models.User).filter(models.User.email == data["email"]).first():
        raise HTTPException(400, "Email exists")
    
    staff = models.User(
        id=str(uuid.uuid4()), organization_id=request.session.get("org_id"),
        username=data["username"], email=data["email"], password_hash=hash_password(data["password"]),
        full_name=data["full_name"], role=models.UserRoleEnum(data["role"]),
        is_active=data.get("is_active", True), phone=data.get("phone", "")
    )
    db.add(staff)
    db.commit()
    return {"success": True, "id": staff.id}

@app.put("/api/staff/{staff_id}")
async def update_staff(staff_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        raise HTTPException(403, "Forbidden")
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

@app.delete("/api/staff/{staff_id}")
async def delete_staff(staff_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin" or staff_id == user.id:
        raise HTTPException(403, "Forbidden")
    
    staff = db.query(models.User).filter(models.User.id == staff_id).first()
    if not staff:
        raise HTTPException(404, "Not found")
    
    db.delete(staff)
    db.commit()
    return {"success": True}

# ==================== AI CHAT API ====================
@app.post("/api/ai/chat")
async def ai_chat(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        raise HTTPException(401, "Unauthorized")
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
async def get_ai_sessions(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        raise HTTPException(401, "Unauthorized")
    
    sessions = db.query(models.AIChatSession).filter(models.AIChatSession.user_id == user.id).order_by(models.AIChatSession.updated_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in sessions]

# ==================== MPESA PAYMENTS ====================
@app.post("/api/payment/mpesa/initiate")
async def initiate_mpesa(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        raise HTTPException(401, "Unauthorized")
    data = await request.json()
    
    sale = db.query(models.SalesOrder).filter(models.SalesOrder.id == data["sale_id"]).first()
    if not sale:
        raise HTTPException(404, "Sale not found")
    
    result = await tuma_service.initiate_payment(data["amount"], data["phone"], sale.sale_number)
    if result["success"]:
        payment = models.Payment(
            id=str(uuid.uuid4()), organization_id=sale.organization_id, sale_id=sale.id, amount=data["amount"],
            payment_method=models.PaymentMethodEnum.mpesa, reference=result["reference"], status="pending",
            transaction_id=result["payment_id"], created_by=user.id
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
async def sales_report(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    org_id = request.session.get("org_id")
    sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).all()
    return {"total_sales": sum(float(s.total) for s in sales), "count": len(sales)}

@app.get("/api/reports/inventory")
async def inventory_report(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    drugs = db.query(models.Drug).all()
    items = []
    for d in drugs:
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == d.id).scalar() or 0
        items.append({"name": d.name, "stock": int(stock), "value": float(stock * d.price)})
    return {"items": items, "total_value": sum(i["value"] for i in items)}

# ==================== CATEGORIES & SUPPLIERS ====================
@app.get("/api/categories")
async def get_categories(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    categories = db.query(models.Category).filter(models.Category.organization_id == request.session.get("org_id")).all()
    return [{"id": c.id, "name": c.name, "description": c.description} for c in categories]

@app.get("/api/suppliers")
async def get_suppliers(request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    suppliers = db.query(models.Supplier).filter(models.Supplier.organization_id == request.session.get("org_id")).all()
    return [{"id": s.id, "name": s.name, "contact_person": s.contact_person, "email": s.email, "phone": s.phone} for s in suppliers]

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
