import bcrypt
import types

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
    return pwd_context.hash(password, scheme="pbkdf2_sha256")

def verify_password(password: str, hashed_password: str) -> bool:
    password = str(password).strip()
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

# IMPORTANT: Fix for template caching - use string response instead
# We'll use direct HTML responses for landing, login, register pages to avoid Jinja2 issues
# But keep templates for dashboard and other pages

cohere_service = CohereService()
tuma_service = TumaMpesaService()

def get_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()

# ==================== DIRECT HTML PAGES (No template issues) ====================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>PharmaSaaS</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f5f7fa; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 60px 20px; text-align: center; }
        .header h1 { font-size: 48px; margin: 0; }
        .header p { font-size: 20px; margin: 20px 0; }
        .btn { display: inline-block; padding: 12px 30px; margin: 10px; border-radius: 5px; text-decoration: none; font-weight: bold; }
        .btn-primary { background: white; color: #667eea; }
        .btn-secondary { background: transparent; border: 2px solid white; color: white; }
        .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .feature { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .feature h3 { color: #667eea; margin-top: 0; }
        .footer { background: #333; color: white; text-align: center; padding: 20px; }
        @media (max-width: 768px) { .header h1 { font-size: 32px; } .header p { font-size: 16px; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 PharmaSaaS</h1>
        <p>Complete Pharmacy Management System</p>
        <div>
            <a href="/register" class="btn btn-primary">Get Started</a>
            <a href="/login" class="btn btn-secondary">Login</a>
        </div>
    </div>
    <div class="container">
        <div class="features">
            <div class="feature"><h3>📱 Barcode Scanning</h3><p>Scan product barcodes instantly</p></div>
            <div class="feature"><h3>👥 Multi-User Support</h3><p>Admin and Pharmacist roles</p></div>
            <div class="feature"><h3>💳 Credit Management</h3><p>Manage client credit accounts</p></div>
            <div class="feature"><h3>🤖 AI Assistant</h3><p>Get drug information</p></div>
            <div class="feature"><h3>📊 Analytics Dashboard</h3><p>Real-time sales analytics</p></div>
            <div class="feature"><h3>🏪 Point of Sale</h3><p>Fast POS with M-Pesa</p></div>
        </div>
    </div>
    <div class="footer">
        <p>&copy; 2025 PharmaSaaS. All rights reserved.</p>
    </div>
</body>
</html>
    """)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head><title>Login - PharmaSaaS</title><style>
body{font-family:Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;margin:0}
.login-box{background:white;padding:40px;border-radius:10px;width:350px;box-shadow:0 10px 25px rgba(0,0,0,0.2)}
.login-box h2{text-align:center;color:#667eea}
input{width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;border-radius:5px}
button{width:100%;padding:10px;background:#667eea;color:white;border:none;border-radius:5px;cursor:pointer}
.demo{background:#f0f0f0;padding:10px;margin-top:20px;border-radius:5px;font-size:12px}
a{color:#667eea;text-decoration:none}
</style></head>
<body>
<div class="login-box">
<h2>🏥 PharmaSaaS</h2>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="POST" action="/login">
<input type="email" name="email" placeholder="Email" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Login</button>
</form>
<div class="demo"><strong>Demo:</strong> admin@demo.com / admin123<br>pharmacist@demo.com / pharmacist123</div>
<p style="text-align:center;margin-top:15px"><a href="/register">Create account</a> | <a href="/">Back</a></p>
</div>
</body>
</html>
    """)

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(content=f"""
<!DOCTYPE html>
<html><body><div class="login-box"><h2>Login Failed</h2><p style="color:red">Invalid credentials</p><a href="/login">Try again</a></div></body></html>
        """)
    
    request.session["user_id"] = user.id
    request.session["role"] = user.role.value
    request.session["org_id"] = user.organization_id
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content="""
<!DOCTYPE html>
<html><head><title>Register - PharmaSaaS</title><style>
body{font-family:Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;margin:0}
.register-box{background:white;padding:30px;border-radius:10px;width:400px}
input{width:100%;padding:8px;margin:8px 0;border:1px solid #ddd;border-radius:5px}
button{width:100%;padding:10px;background:#667eea;color:white;border:none;border-radius:5px;cursor:pointer}
.row{display:flex;gap:10px}
.row input{flex:1}
</style></head>
<body>
<div class="register-box">
<h2>Create Pharmacy Account</h2>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
<form method="POST" action="/register">
<div class="row"><input type="text" name="first_name" placeholder="First Name" required><input type="text" name="last_name" placeholder="Last Name" required></div>
<input type="text" name="pharmacy_name" placeholder="Pharmacy Name" required>
<input type="email" name="email" placeholder="Email" required>
<input type="tel" name="phone" placeholder="Phone" required>
<input type="password" name="password" placeholder="Password" required>
<input type="password" name="confirm_password" placeholder="Confirm Password" required>
<button type="submit">Register</button>
</form>
<p style="text-align:center"><a href="/login">Already have an account? Login</a> | <a href="/">Back</a></p>
</div>
</body>
</html>
    """)

@app.post("/register")
async def register(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                   pharmacy_name: str = Form(...), email: str = Form(...), phone: str = Form(...),
                   password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm_password:
        return HTMLResponse("<script>alert('Passwords do not match'); window.location='/register';</script>")
    if len(password) < 6:
        return HTMLResponse("<script>alert('Password too short'); window.location='/register';</script>")
    
    email = email.strip().lower()
    if db.query(models.User).filter(models.User.email == email).first():
        return HTMLResponse("<script>alert('Email already registered'); window.location='/register';</script>")
    
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

# ==================== DASHBOARD (Use template) ====================
templates = Jinja2Templates(directory="templates")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    org_id = request.session.get("org_id")
    total_products = db.query(models.Drug).filter(models.Drug.organization_id == org_id).count()
    total_customers = db.query(models.Customer).filter(models.Customer.organization_id == org_id).count()
    total_sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).count()
    pending_credit = db.query(func.sum(models.Customer.current_balance)).filter(models.Customer.organization_id == org_id).scalar() or 0
    
    low_stock_items = []
    for drug in db.query(models.Drug).filter(models.Drug.organization_id == org_id).all():
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == drug.id).scalar() or 0
        if stock < drug.reorder_level:
            low_stock_items.append({"name": drug.name, "stock": stock, "reorder": drug.reorder_level})
    
    recent_sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).order_by(models.SalesOrder.created_at.desc()).limit(5).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "total_products": total_products, "total_customers": total_customers,
        "total_sales": total_sales, "pending_credit": float(pending_credit), "low_stock_items": low_stock_items,
        "recent_sales": recent_sales
    })

# ==================== OTHER PAGES ====================
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

# ==================== API ENDPOINTS ====================
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
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == d.id).scalar() or 0
        items.append({
            "id": d.id, "name": d.name, "generic_name": d.generic_name, "price": float(d.price),
            "stock": int(stock), "reorder_level": d.reorder_level, "barcode": d.barcode
        })
    return {"items": items, "total": total, "pages": (total + limit - 1) // limit}

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
    products = db.query(models.Drug).filter(or_(models.Drug.name.ilike(f"%{q}%"), models.Drug.barcode.ilike(f"%{q}%"))).limit(20).all()
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
        "id": c.id, "full_name": c.full_name, "email": c.email, "phone": c.phone,
        "current_balance": float(c.current_balance) if c.current_balance else 0
    } for c in customers]
    return {"items": items, "total": total, "pages": (total + limit - 1) // limit}

@app.post("/api/customers/{customer_id}/payment")
async def add_customer_payment(customer_id: str, request: Request, db: Session = Depends(get_db)):
    if not get_user(request, db):
        raise HTTPException(401, "Unauthorized")
    data = await request.json()
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Not found")
    customer.current_balance -= data.get("amount", 0)
    db.commit()
    return {"success": True, "new_balance": float(customer.current_balance)}

@app.get("/api/staff")
async def get_staff(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        raise HTTPException(403, "Forbidden")
    staff = db.query(models.User).filter(models.User.organization_id == request.session.get("org_id"), models.User.role != models.UserRoleEnum.admin).all()
    return [{"id": s.id, "full_name": s.full_name, "email": s.email, "role": s.role.value, "is_active": s.is_active} for s in staff]

@app.post("/api/staff")
async def add_staff(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        raise HTTPException(403, "Forbidden")
    data = await request.json()
    if db.query(models.User).filter(models.User.email == data["email"]).first():
        raise HTTPException(400, "Email exists")
    staff = models.User(id=str(uuid.uuid4()), organization_id=request.session.get("org_id"), username=data["username"],
                        email=data["email"], password_hash=hash_password(data["password"]), full_name=data["full_name"],
                        role=models.UserRoleEnum(data["role"]), is_active=True, phone=data.get("phone", ""))
    db.add(staff)
    db.commit()
    return {"success": True, "id": staff.id}

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

@app.post("/api/ai/chat")
async def ai_chat(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user:
        raise HTTPException(401, "Unauthorized")
    data = await request.json()
    message = data.get("message")
    if not message:
        raise HTTPException(400, "Message required")
    
    session_id = data.get("sessionId")
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
        payment = models.Payment(id=str(uuid.uuid4()), organization_id=sale.organization_id, sale_id=sale.id, amount=data["amount"],
                                  payment_method=models.PaymentMethodEnum.mpesa, reference=result["reference"], status="pending",
                                  transaction_id=result["payment_id"], created_by=user.id)
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
