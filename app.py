import bcrypt
import types

# BCrypt workaround
try:
    bcrypt.__about__
except AttributeError:
    bcrypt.__about__ = types.SimpleNamespace()
    bcrypt.__about__.__version__ = "3.2.0"

from fastapi import FastAPI, Request, Form, HTTPException, Depends
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
    
    customer = models.Customer(id=str(uuid.uuid4()), organization_id=org.id, first_name="John", last_name="Smith", email="john@example.com", phone="555-0100", allow_credit=True, credit_limit=5000.0, current_balance=0.0)
    db.add(customer)
    db.flush()
    
    # Create demo patient medication
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

# ==================== LANDING PAGE (DIRECT HTML) ====================
LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PharmaSaaS - Pharmacy Management System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>.gradient-bg{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);}</style>
</head>
<body class="bg-gray-50">
    <div class="gradient-bg text-white">
        <div class="container mx-auto px-6 py-16 text-center">
            <i class="fas fa-hospital-user text-5xl mb-4"></i>
            <h1 class="text-4xl md:text-5xl font-bold mb-4">PharmaSaaS</h1>
            <p class="text-xl mb-8">Complete Pharmacy Management System for Modern Pharmacies</p>
            <div class="flex gap-4 justify-center flex-wrap">
                <a href="/register" class="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition"><i class="fas fa-rocket mr-2"></i> Get Started</a>
                <a href="/login" class="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition"><i class="fas fa-sign-in-alt mr-2"></i> Login</a>
            </div>
        </div>
    </div>
    <div class="container mx-auto px-6 py-20">
        <div class="text-center mb-12"><h2 class="text-3xl font-bold">Powerful Features</h2></div>
        <div class="grid md:grid-cols-3 gap-8">
            <div class="bg-white rounded-xl shadow-lg p-6"><i class="fas fa-qrcode text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold">Barcode Scanning</h3><p class="text-gray-600">Scan product barcodes instantly</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6"><i class="fas fa-users text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold">Multi-User Support</h3><p class="text-gray-600">Admin and Pharmacist roles</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6"><i class="fas fa-credit-card text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold">Credit Management</h3><p class="text-gray-600">Manage client credit accounts</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6"><i class="fas fa-robot text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold">AI Assistant</h3><p class="text-gray-600">Get drug information instantly</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6"><i class="fas fa-chart-line text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold">Analytics Dashboard</h3><p class="text-gray-600">Real-time sales analytics</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6"><i class="fas fa-shopping-cart text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold">Point of Sale</h3><p class="text-gray-600">Fast POS with M-Pesa</p></div>
        </div>
    </div>
    <div class="bg-gray-100 py-20">
        <div class="container mx-auto px-6 text-center">
            <h2 class="text-3xl font-bold mb-4">Ready to transform your pharmacy?</h2>
            <a href="/register" class="bg-purple-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-purple-700 transition inline-block">Start Free Trial</a>
        </div>
    </div>
    <footer class="bg-gray-900 text-white py-8 text-center"><p>&copy; 2025 PharmaSaaS. All rights reserved.</p></footer>
</body>
</html>"""

# ==================== LOGIN PAGE (DIRECT HTML) ====================
LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - PharmaSaaS</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gradient-to-r from-purple-600 to-indigo-600 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md">
        <div class="text-center mb-8"><i class="fas fa-hospital-user text-4xl text-purple-600"></i><h1 class="text-2xl font-bold mt-2">PharmaSaaS</h1><p class="text-gray-600">Login to your pharmacy</p></div>
        <div id="errorMsg" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 hidden"></div>
        <form id="loginForm" method="POST" action="/login">
            <div class="mb-4"><label class="block text-gray-700 font-semibold mb-2">Email</label><input type="email" id="email" name="email" required class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"></div>
            <div class="mb-6"><label class="block text-gray-700 font-semibold mb-2">Password</label><input type="password" id="password" name="password" required class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"></div>
            <button type="submit" class="w-full bg-purple-600 text-white py-2 rounded-lg font-semibold hover:bg-purple-700 transition">Login</button>
        </form>
        <div class="mt-6 p-4 bg-gray-50 rounded-lg"><p class="font-semibold text-gray-700">Demo Credentials:</p><p class="text-sm text-gray-600">Admin: admin@demo.com / admin123</p><p class="text-sm text-gray-600">Pharmacist: pharmacist@demo.com / pharmacist123</p></div>
        <div class="mt-6 text-center"><p class="text-gray-600">Don't have an account? <a href="/register" class="text-purple-600 font-semibold">Sign up</a></p><a href="/" class="text-gray-500 text-sm mt-2 inline-block">← Back to home</a></div>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/login', {method: 'POST', body: formData});
            if (response.redirected) { window.location.href = response.url; }
            else { const text = await response.text(); if(text.includes('error')) { document.getElementById('errorMsg').innerText = 'Invalid credentials'; document.getElementById('errorMsg').classList.remove('hidden'); } }
        });
    </script>
</body>
</html>"""

# ==================== REGISTER PAGE (DIRECT HTML) ====================
REGISTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - PharmaSaaS</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gradient-to-r from-purple-600 to-indigo-600 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md">
        <div class="text-center mb-6"><i class="fas fa-hospital-user text-4xl text-purple-600"></i><h1 class="text-2xl font-bold mt-2">Create Account</h1><p class="text-gray-600">Start your pharmacy journey</p></div>
        <div id="errorMsg" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 hidden"></div>
        <form id="registerForm" method="POST" action="/register">
            <div class="grid grid-cols-2 gap-3 mb-3"><div><input type="text" name="first_name" placeholder="First Name" required class="w-full px-3 py-2 border rounded-lg"></div><div><input type="text" name="last_name" placeholder="Last Name" required class="w-full px-3 py-2 border rounded-lg"></div></div>
            <input type="text" name="pharmacy_name" placeholder="Pharmacy Name" required class="w-full px-3 py-2 border rounded-lg mb-3">
            <input type="email" name="email" placeholder="Email" required class="w-full px-3 py-2 border rounded-lg mb-3">
            <input type="tel" name="phone" placeholder="Phone" required class="w-full px-3 py-2 border rounded-lg mb-3">
            <input type="password" name="password" placeholder="Password" required minlength="6" class="w-full px-3 py-2 border rounded-lg mb-3">
            <input type="password" name="confirm_password" placeholder="Confirm Password" required class="w-full px-3 py-2 border rounded-lg mb-4">
            <button type="submit" class="w-full bg-purple-600 text-white py-2 rounded-lg font-semibold hover:bg-purple-700 transition">Create Account</button>
        </form>
        <div class="mt-6 text-center"><p class="text-gray-600">Already have an account? <a href="/login" class="text-purple-600 font-semibold">Login</a></p><a href="/" class="text-gray-500 text-sm mt-2 inline-block">← Back to home</a></div>
    </div>
    <script>
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/register', {method: 'POST', body: formData});
            if (response.redirected) { window.location.href = response.url; }
            else { const text = await response.text(); if(text.includes('error')) { document.getElementById('errorMsg').innerText = 'Registration failed'; document.getElementById('errorMsg').classList.remove('hidden'); } }
        });
    </script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=LANDING_HTML)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=LOGIN_HTML)

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(content=LOGIN_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Invalid credentials</div>'))
    if not user.is_active:
        return HTMLResponse(content=LOGIN_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Account inactive</div>'))
    
    request.session["user_id"] = user.id
    request.session["role"] = user.role.value
    request.session["org_id"] = user.organization_id
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=REGISTER_HTML)

@app.post("/register")
async def register(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                   pharmacy_name: str = Form(...), email: str = Form(...), phone: str = Form(...),
                   password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm_password:
        return HTMLResponse(content=REGISTER_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Passwords do not match</div>'))
    if len(password) < 6:
        return HTMLResponse(content=REGISTER_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Password too short</div>'))
    
    email = email.strip().lower()
    if db.query(models.User).filter(models.User.email == email).first():
        return HTMLResponse(content=REGISTER_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Email already registered</div>'))
    if db.query(models.Organization).filter(models.Organization.name == pharmacy_name).first():
        return HTMLResponse(content=REGISTER_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Pharmacy name taken</div>'))
    
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

# ==================== DASHBOARD (DIRECT HTML) ====================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
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
    
    medication_alerts = db.query(models.PatientMedication).filter(
        models.PatientMedication.organization_id == org_id,
        models.PatientMedication.status == models.MedicationStatusEnum.active,
        or_(
            models.PatientMedication.quantity_remaining <= models.PatientMedication.low_stock_threshold,
            models.PatientMedication.next_refill_date <= date.today()
        )
    ).count()
    
    # Build dashboard HTML dynamically
    low_stock_html = ""
    for item in low_stock_items:
        low_stock_html += f'<div class="bg-yellow-50 border-l-4 border-yellow-500 p-3 rounded mb-2"><div class="flex justify-between"><span class="font-medium">{item["name"]}</span><span class="text-sm">Stock: {item["stock"]} / {item["reorder"]}</span></div></div>'
    if not low_stock_items:
        low_stock_html = '<div class="text-center py-8 text-gray-400"><i class="fas fa-check-circle text-4xl mb-2"></i><p>All products are well stocked!</p></div>'
    
    recent_sales_html = ""
    for sale in recent_sales:
        recent_sales_html += f'<div class="flex justify-between border-b pb-3 mb-3"><div><p class="font-medium">{sale.sale_number}</p><p class="text-sm text-gray-500">{sale.created_at.strftime("%Y-%m-%d %H:%M")}</p></div><div class="text-right"><p class="font-bold text-green-600">Ksh {sale.total:.2f}</p><p class="text-xs text-gray-400">{sale.payment_method.value}</p></div></div>'
    if not recent_sales:
        recent_sales_html = '<div class="text-center py-8 text-gray-400"><i class="fas fa-receipt text-4xl mb-2"></i><p>No sales yet</p></div>'
    
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dashboard - PharmaSaaS</title>
<script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>.gradient-bg{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);}}.card-hover{{transition:transform 0.2s;}}.card-hover:hover{{transform:translateY(-5px);}}</style>
</head>
<body class="bg-gray-100">
<nav class="gradient-bg text-white shadow-lg"><div class="container mx-auto px-6 py-4"><div class="flex justify-between items-center flex-wrap gap-4"><div class="flex items-center space-x-3"><i class="fas fa-hospital-user text-2xl"></i><span class="font-bold text-xl">PharmaSaaS</span></div><div class="flex space-x-4 flex-wrap gap-2"><a href="/dashboard" class="bg-white bg-opacity-20 px-3 py-2 rounded">Dashboard</a><a href="/inventory" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">Inventory</a><a href="/sales" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">POS</a><a href="/customers" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">Customers</a><a href="/patient-medications" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded relative">Patient Monitor{f'<span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">{medication_alerts}</span>' if medication_alerts > 0 else ''}</a>{f'<a href="/staff" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">Staff</a>' if user.role.value == "admin" else ''}<a href="/ai-chat" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">AI Chat</a><a href="/logout" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">Logout</a></div></div></div></nav>
<div class="gradient-bg text-white py-8"><div class="container mx-auto px-6"><h1 class="text-3xl font-bold mb-2">Welcome back, {user.full_name}!</h1><p class="text-purple-100">{user.role.value.title()} • {user.organization.name}</p></div></div>
<div class="container mx-auto px-6 py-8">
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
<div class="bg-white rounded-xl shadow-md p-6 card-hover"><div class="flex justify-between"><div><p class="text-gray-500 text-sm">Total Products</p><p class="text-3xl font-bold text-purple-600">{total_products}</p></div><div class="bg-purple-100 rounded-full p-3"><i class="fas fa-capsules text-purple-600 text-xl"></i></div></div></div>
<div class="bg-white rounded-xl shadow-md p-6 card-hover"><div class="flex justify-between"><div><p class="text-gray-500 text-sm">Total Customers</p><p class="text-3xl font-bold text-blue-600">{total_customers}</p></div><div class="bg-blue-100 rounded-full p-3"><i class="fas fa-users text-blue-600 text-xl"></i></div></div></div>
<div class="bg-white rounded-xl shadow-md p-6 card-hover"><div class="flex justify-between"><div><p class="text-gray-500 text-sm">Total Sales</p><p class="text-3xl font-bold text-green-600">{total_sales}</p></div><div class="bg-green-100 rounded-full p-3"><i class="fas fa-chart-line text-green-600 text-xl"></i></div></div></div>
<div class="bg-white rounded-xl shadow-md p-6 card-hover"><div class="flex justify-between"><div><p class="text-gray-500 text-sm">Pending Credit</p><p class="text-3xl font-bold text-orange-600">Ksh {pending_credit:.2f}</p></div><div class="bg-orange-100 rounded-full p-3"><i class="fas fa-credit-card text-orange-600 text-xl"></i></div></div></div>
<div class="bg-white rounded-xl shadow-md p-6 card-hover"><div class="flex justify-between"><div><p class="text-gray-500 text-sm">Patient Alerts</p><p class="text-3xl font-bold text-red-600">{medication_alerts}</p></div><div class="bg-red-100 rounded-full p-3"><i class="fas fa-heartbeat text-red-600 text-xl"></i></div></div></div>
</div>
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
<div class="bg-white rounded-xl shadow-md p-6"><h3 class="text-lg font-semibold mb-4"><i class="fas fa-exclamation-triangle text-yellow-500 mr-2"></i>Low Stock Alerts</h3>{low_stock_html}</div>
<div class="bg-white rounded-xl shadow-md p-6"><h3 class="text-lg font-semibold mb-4"><i class="fas fa-clock text-blue-500 mr-2"></i>Recent Sales</h3>{recent_sales_html}</div>
</div>
<div class="grid grid-cols-2 md:grid-cols-4 gap-4"><a href="/sales" class="bg-purple-600 text-white rounded-xl p-4 text-center hover:bg-purple-700"><i class="fas fa-shopping-cart text-2xl mb-2 block"></i>New Sale</a><a href="/inventory" class="bg-blue-600 text-white rounded-xl p-4 text-center hover:bg-blue-700"><i class="fas fa-plus-circle text-2xl mb-2 block"></i>Add Product</a><a href="/customers" class="bg-green-600 text-white rounded-xl p-4 text-center hover:bg-green-700"><i class="fas fa-user-plus text-2xl mb-2 block"></i>Add Customer</a><a href="/patient-medications" class="bg-red-600 text-white rounded-xl p-4 text-center hover:bg-red-700"><i class="fas fa-heartbeat text-2xl mb-2 block"></i>Patient Monitor</a></div>
</div>
</body>
</html>""")

# ==================== SIMPLE PLACEHOLDER PAGES ====================
@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>Inventory</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold">Inventory Management</h1><p class="mt-4">Inventory features coming soon. Use the POS for sales.</p><a href="/sales" class="inline-block mt-4 bg-purple-600 text-white px-4 py-2 rounded">Go to POS</a><br><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div></body></html>""")

@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>POS</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold">Point of Sale</h1><p class="mt-4">POS features coming soon.</p><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div></body></html>""")

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>Customers</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold">Customer Management</h1><p class="mt-4">Customer features coming soon.</p><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div></body></html>""")

@app.get("/staff", response_class=HTMLResponse)
async def staff_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>Staff</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold">Staff Management</h1><p class="mt-4">Admin only - Staff features coming soon.</p><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div></body></html>""")

@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>AI Assistant</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold">AI Pharmacy Assistant</h1><p class="mt-4">AI Chat features coming soon.</p><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div></body></html>""")

@app.get("/patient-medications", response_class=HTMLResponse)
async def patient_medications_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content="""<!DOCTYPE html><html><head><title>Patient Monitor</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold">Patient Medication Monitoring</h1><p class="mt-4">Patient monitoring features coming soon.</p><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div></body></html>""")

# ==================== API ENDPOINTS (KEEP ALL) ====================
@app.get("/api/inventory")
async def get_inventory(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), page: int = 1, limit: int = 20, search: str = ""):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    query = db.query(models.Drug).filter(models.Drug.organization_id == org_id)
    if search:
        query = query.filter(or_(models.Drug.name.ilike(f"%{search}%"), models.Drug.barcode.ilike(f"%{search}%")))
    total = query.count()
    drugs = query.offset(offset).limit(limit).all()
    items = []
    for d in drugs:
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == d.id).scalar() or 0
        items.append({"id": d.id, "name": d.name, "price": float(d.price), "stock": int(stock), "reorder_level": d.reorder_level, "barcode": d.barcode})
    return {"items": items, "total": total, "pages": (total + limit - 1) // limit}

@app.get("/api/product_by_barcode")
async def product_by_barcode(code: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    product = db.query(models.Drug).filter(models.Drug.barcode == code).first()
    if not product:
        raise HTTPException(404, "Not found")
    stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == product.id).scalar() or 0
    return {"id": product.id, "name": product.name, "price": float(product.price), "stock": int(stock), "barcode": product.barcode}

@app.get("/api/products/search")
async def search_products(request: Request, q: str, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    products = db.query(models.Drug).filter(or_(models.Drug.name.ilike(f"%{q}%"), models.Drug.barcode.ilike(f"%{q}%"))).limit(20).all()
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
            for batch in db.query(models.InventoryBatch).filter(models.InventoryBatch.drug_id == item["productId"], models.InventoryBatch.quantity_on_hand > 0).order_by(models.InventoryBatch.expiry_date).all():
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
async def get_customers(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), page: int = 1, limit: int = 20, search: str = ""):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    query = db.query(models.Customer).filter(models.Customer.organization_id == org_id)
    if search:
        query = query.filter(or_(models.Customer.first_name.ilike(f"%{search}%"), models.Customer.last_name.ilike(f"%{search}%"), models.Customer.email.ilike(f"%{search}%")))
    total = query.count()
    customers = query.offset(offset).limit(limit).all()
    items = [{"id": c.id, "full_name": c.full_name, "email": c.email, "phone": c.phone, "current_balance": float(c.current_balance)} for c in customers]
    return {"items": items, "total": total, "pages": (total + limit - 1) // limit}

@app.post("/api/customers/{customer_id}/payment")
async def add_customer_payment(customer_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Not found")
    customer.current_balance -= data.get("amount", 0)
    db.commit()
    return {"success": True, "new_balance": float(customer.current_balance)}

@app.get("/api/staff")
async def get_staff(request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    staff = db.query(models.User).filter(models.User.organization_id == request.session.get("org_id"), models.User.role != models.UserRoleEnum.admin).all()
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

@app.post("/api/payment/mpesa/initiate")
async def initiate_mpesa(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
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

@app.get("/api/reports/sales")
async def sales_report(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).all()
    return {"total_sales": sum(float(s.total) for s in sales), "count": len(sales)}

@app.get("/api/reports/inventory")
async def inventory_report(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    drugs = db.query(models.Drug).all()
    items = []
    for d in drugs:
        stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(models.InventoryBatch.drug_id == d.id).scalar() or 0
        items.append({"name": d.name, "stock": int(stock), "value": float(stock * d.price)})
    return {"items": items, "total_value": sum(i["value"] for i in items)}

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
