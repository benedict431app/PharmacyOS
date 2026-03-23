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

# ==================== LANDING PAGE ====================
LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>PharmaSaaS - Pharmacy Management System</title>
<script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<style>.gradient-bg{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);}.card-hover{transition:transform 0.3s;}.card-hover:hover{transform:translateY(-5px);}</style></head>
<body class="bg-gray-50">
<div class="gradient-bg text-white"><div class="container mx-auto px-6 py-16 text-center"><i class="fas fa-hospital-user text-5xl mb-4"></i><h1 class="text-4xl md:text-5xl font-bold mb-4">PharmaSaaS</h1><p class="text-xl mb-8">Complete Pharmacy Management System for Modern Pharmacies</p><div class="flex gap-4 justify-center flex-wrap"><a href="/register" class="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition"><i class="fas fa-rocket mr-2"></i> Register as Pharmacy Owner</a><a href="/register-staff" class="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition"><i class="fas fa-user-plus mr-2"></i> Apply as Staff</a><a href="/login" class="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition"><i class="fas fa-sign-in-alt mr-2"></i> Login</a></div><div class="mt-8 flex gap-6 justify-center"><div><div class="text-2xl font-bold">500+</div><div class="text-sm">Pharmacies</div></div><div><div class="text-2xl font-bold">10k+</div><div class="text-sm">Daily Transactions</div></div><div><div class="text-2xl font-bold">24/7</div><div class="text-sm">Support</div></div></div></div></div>
<div class="container mx-auto px-6 py-20"><div class="text-center mb-12"><h2 class="text-3xl md:text-4xl font-bold mb-4">Powerful Features</h2><p class="text-xl text-gray-600">Everything you need to run your pharmacy</p></div><div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8"><div class="bg-white rounded-xl shadow-lg p-6 card-hover"><i class="fas fa-qrcode text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold mb-2">Barcode Scanning</h3><p class="text-gray-600">Scan product barcodes instantly</p></div><div class="bg-white rounded-xl shadow-lg p-6 card-hover"><i class="fas fa-users text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold mb-2">Staff Management</h3><p class="text-gray-600">Add staff and approve applications</p></div><div class="bg-white rounded-xl shadow-lg p-6 card-hover"><i class="fas fa-credit-card text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold mb-2">Credit Management</h3><p class="text-gray-600">Manage client credit accounts</p></div><div class="bg-white rounded-xl shadow-lg p-6 card-hover"><i class="fas fa-robot text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold mb-2">AI Assistant</h3><p class="text-gray-600">Get drug information instantly</p></div><div class="bg-white rounded-xl shadow-lg p-6 card-hover"><i class="fas fa-chat text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold mb-2">Patient Chat</h3><p class="text-gray-600">Communicate with patients</p></div><div class="bg-white rounded-xl shadow-lg p-6 card-hover"><i class="fas fa-shopping-cart text-3xl text-purple-600 mb-3"></i><h3 class="text-xl font-semibold mb-2">Point of Sale</h3><p class="text-gray-600">Fast POS with M-Pesa</p></div></div></div>
<div class="gradient-bg text-white py-16"><div class="container mx-auto px-6 text-center"><h2 class="text-3xl md:text-4xl font-bold mb-4">Ready to transform your pharmacy?</h2><div class="flex gap-4 justify-center flex-wrap"><a href="/register" class="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition">Register as Owner</a><a href="/register-staff" class="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition">Apply as Staff</a></div></div></div>
<footer class="bg-gray-900 text-white py-8 text-center"><p>&copy; 2025 PharmaSaaS. All rights reserved.</p></footer>
</body></html>"""

# ==================== REGISTER PAGES ====================
REGISTER_HTML = """<!DOCTYPE html>
<html><head><title>Register - PharmaSaaS</title><script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet"></head>
<body class="bg-gradient-to-r from-purple-600 to-indigo-600 min-h-screen flex items-center justify-center p-4"><div class="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md"><div class="text-center mb-6"><i class="fas fa-hospital-user text-4xl text-purple-600"></i><h1 class="text-2xl font-bold mt-2">Register Your Pharmacy</h1></div><div id="errorMsg" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 hidden"></div><form id="registerForm" method="POST" action="/register"><div class="grid grid-cols-2 gap-3 mb-3"><input type="text" name="first_name" placeholder="First Name" required class="w-full px-3 py-2 border rounded-lg"><input type="text" name="last_name" placeholder="Last Name" required class="w-full px-3 py-2 border rounded-lg"></div><input type="text" name="pharmacy_name" placeholder="Pharmacy Name" required class="w-full px-3 py-2 border rounded-lg mb-3"><input type="email" name="email" placeholder="Email" required class="w-full px-3 py-2 border rounded-lg mb-3"><input type="tel" name="phone" placeholder="Phone" required class="w-full px-3 py-2 border rounded-lg mb-3"><input type="password" name="password" placeholder="Password" required minlength="6" class="w-full px-3 py-2 border rounded-lg mb-3"><input type="password" name="confirm_password" placeholder="Confirm Password" required class="w-full px-3 py-2 border rounded-lg mb-4"><button type="submit" class="w-full bg-purple-600 text-white py-2 rounded-lg font-semibold hover:bg-purple-700">Create Pharmacy Account</button></form><div class="mt-6 text-center"><p>Already have an account? <a href="/login" class="text-purple-600">Login</a></p><p><a href="/register-staff" class="text-purple-600">Apply as Staff</a></p><a href="/" class="text-gray-500 text-sm">← Back</a></div></div><script>document.getElementById('registerForm').addEventListener('submit',async(e)=>{e.preventDefault();const fd=new FormData(e.target);const r=await fetch('/register',{method:'POST',body:fd});if(r.redirected)window.location.href=r.url;else if((await r.text()).includes('error'))document.getElementById('errorMsg').innerText='Registration failed';document.getElementById('errorMsg').classList.remove('hidden');});</script></body></html>"""

STAFF_REGISTER_HTML = """<!DOCTYPE html>
<html><head><title>Apply as Staff - PharmaSaaS</title><script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet"></head>
<body class="bg-gradient-to-r from-purple-600 to-indigo-600 min-h-screen flex items-center justify-center p-4"><div class="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md"><div class="text-center mb-6"><i class="fas fa-user-md text-4xl text-purple-600"></i><h1 class="text-2xl font-bold mt-2">Apply as Pharmacy Staff</h1></div><div id="errorMsg" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 hidden"></div><form id="registerForm" method="POST" action="/register-staff"><div class="grid grid-cols-2 gap-3 mb-3"><input type="text" name="first_name" placeholder="First Name" required class="w-full px-3 py-2 border rounded-lg"><input type="text" name="last_name" placeholder="Last Name" required class="w-full px-3 py-2 border rounded-lg"></div><input type="text" name="pharmacy_name" placeholder="Pharmacy Name (exact name)" required class="w-full px-3 py-2 border rounded-lg mb-3"><input type="email" name="email" placeholder="Email" required class="w-full px-3 py-2 border rounded-lg mb-3"><input type="tel" name="phone" placeholder="Phone" required class="w-full px-3 py-2 border rounded-lg mb-3"><select name="requested_role" class="w-full px-3 py-2 border rounded-lg mb-3"><option value="pharmacist">Pharmacist</option><option value="cashier">Cashier</option></select><input type="password" name="password" placeholder="Password" required minlength="6" class="w-full px-3 py-2 border rounded-lg mb-3"><input type="password" name="confirm_password" placeholder="Confirm Password" required class="w-full px-3 py-2 border rounded-lg mb-4"><button type="submit" class="w-full bg-purple-600 text-white py-2 rounded-lg font-semibold hover:bg-purple-700">Submit Application</button></form><div class="mt-6 text-center"><p>Already have an account? <a href="/login" class="text-purple-600">Login</a></p><p><a href="/register" class="text-purple-600">Register as Owner</a></p><a href="/" class="text-gray-500 text-sm">← Back</a></div></div><script>document.getElementById('registerForm').addEventListener('submit',async(e)=>{e.preventDefault();const fd=new FormData(e.target);const r=await fetch('/register-staff',{method:'POST',body:fd});if(r.redirected)window.location.href=r.url;else if((await r.text()).includes('error'))document.getElementById('errorMsg').innerText='Application failed';document.getElementById('errorMsg').classList.remove('hidden');});</script></body></html>"""

LOGIN_HTML = """<!DOCTYPE html>
<html><head><title>Login - PharmaSaaS</title><script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet"></head>
<body class="bg-gradient-to-r from-purple-600 to-indigo-600 min-h-screen flex items-center justify-center p-4"><div class="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md"><div class="text-center mb-8"><i class="fas fa-hospital-user text-4xl text-purple-600"></i><h1 class="text-2xl font-bold mt-2">PharmaSaaS</h1></div><div id="errorMsg" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 hidden"></div><form id="loginForm" method="POST" action="/login"><input type="email" name="email" placeholder="Email" required class="w-full px-4 py-2 border rounded-lg mb-4"><input type="password" name="password" placeholder="Password" required class="w-full px-4 py-2 border rounded-lg mb-6"><button type="submit" class="w-full bg-purple-600 text-white py-2 rounded-lg font-semibold hover:bg-purple-700">Login</button></form><div class="mt-6 p-4 bg-gray-50 rounded-lg"><p class="font-semibold">Demo Credentials:</p><p>Admin: admin@demo.com / admin123</p><p>Pharmacist: pharmacist@demo.com / pharmacist123</p></div><div class="mt-6 text-center"><p><a href="/register" class="text-purple-600">Register as Owner</a> | <a href="/register-staff" class="text-purple-600">Apply as Staff</a></p><a href="/" class="text-gray-500 text-sm">← Back</a></div></div><script>document.getElementById('loginForm').addEventListener('submit',async(e)=>{e.preventDefault();const fd=new FormData(e.target);const r=await fetch('/login',{method:'POST',body:fd});if(r.redirected)window.location.href=r.url;else if((await r.text()).includes('error'))document.getElementById('errorMsg').innerText='Invalid credentials';document.getElementById('errorMsg').classList.remove('hidden');});</script></body></html>"""

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=LANDING_HTML)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=REGISTER_HTML)

@app.get("/register-staff", response_class=HTMLResponse)
async def register_staff_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=STAFF_REGISTER_HTML)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=LOGIN_HTML)

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

@app.post("/register-staff")
async def register_staff(request: Request, first_name: str = Form(...), last_name: str = Form(...),
                         pharmacy_name: str = Form(...), email: str = Form(...), phone: str = Form(...),
                         requested_role: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)):
    if password != confirm_password:
        return HTMLResponse(content=STAFF_REGISTER_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Passwords do not match</div>'))
    if len(password) < 6:
        return HTMLResponse(content=STAFF_REGISTER_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Password too short</div>'))
    
    email = email.strip().lower()
    org = db.query(models.Organization).filter(models.Organization.name == pharmacy_name).first()
    if not org:
        return HTMLResponse(content=STAFF_REGISTER_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Pharmacy not found. Please check the pharmacy name.</div>'))
    
    if db.query(models.User).filter(models.User.email == email).first():
        return HTMLResponse(content=STAFF_REGISTER_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Email already registered</div>'))
    
    user = models.User(id=str(uuid.uuid4()), organization_id=org.id, username=email.split('@')[0], email=email,
                       password_hash=hash_password(password), full_name=f"{first_name} {last_name}",
                       role=models.UserRoleEnum(requested_role), is_active=False, phone=phone)
    db.add(user)
    db.commit()
    
    return HTMLResponse(content="""<!DOCTYPE html><html><body style="font-family:Arial;text-align:center;padding:50px;"><h2>✓ Application Submitted!</h2><p>Your application has been sent to the pharmacy owner for approval.</p><a href="/login" style="display:inline-block;margin-top:20px;padding:10px 20px;background:#667eea;color:white;text-decoration:none;border-radius:5px;">Return to Login</a></body></html>""")

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(content=LOGIN_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Invalid credentials</div>'))
    if not user.is_active:
        return HTMLResponse(content=LOGIN_HTML.replace('<div id="errorMsg" class="hidden"></div>', '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">Account pending approval. Please wait for pharmacy owner to activate your account.</div>'))
    
    request.session["user_id"] = user.id
    request.session["role"] = user.role.value
    request.session["org_id"] = user.organization_id
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

# ==================== DASHBOARD ====================
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
    
    pending_staff_html = ""
    if user.role.value == "admin" and pending_staff > 0:
        pending_staff_html = f'<div class="bg-blue-50 border-l-4 border-blue-500 p-3 rounded mb-4"><div class="flex justify-between items-center"><span><strong>{pending_staff}</strong> staff application(s) pending approval</span><a href="/staff" class="bg-blue-600 text-white px-3 py-1 rounded text-sm">Review</a></div></div>'
    
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Dashboard - PharmaSaaS</title><script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet"><style>.gradient-bg{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);}}.card-hover{{transition:transform 0.2s;}}.card-hover:hover{{transform:translateY(-5px);}}</style></head>
<body class="bg-gray-100">
<nav class="gradient-bg text-white shadow-lg"><div class="container mx-auto px-6 py-4"><div class="flex justify-between items-center flex-wrap gap-4"><div class="flex items-center space-x-3"><i class="fas fa-hospital-user text-2xl"></i><span class="font-bold text-xl">PharmaSaaS</span></div><div class="flex space-x-4 flex-wrap gap-2"><a href="/dashboard" class="bg-white bg-opacity-20 px-3 py-2 rounded">Dashboard</a><a href="/inventory" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">Inventory</a><a href="/sales" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">POS</a><a href="/customers" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">Customers</a><a href="/patient-medications" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded relative">Patient Monitor{f'<span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">{medication_alerts}</span>' if medication_alerts > 0 else ''}</a>{f'<a href="/staff" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">Staff</a>' if user.role.value == "admin" else ''}<a href="/ai-chat" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">AI Chat</a><a href="/logout" class="hover:bg-white hover:bg-opacity-20 px-3 py-2 rounded">Logout</a></div></div></div></nav>
<div class="gradient-bg text-white py-8"><div class="container mx-auto px-6"><h1 class="text-3xl font-bold mb-2">Welcome back, {user.full_name}!</h1><p class="text-purple-100">{user.role.value.title()} • {user.organization.name}</p></div></div>
<div class="container mx-auto px-6 py-8">
{pending_staff_html}
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
</body></html>""")

# ==================== OTHER PAGES ====================
INVENTORY_HTML = """<!DOCTYPE html>
<html><head><title>Inventory</title><script src="https://cdn.tailwindcss.com"></script><script>
let currentPage=1,totalPages=1;
async function loadInventory(){const s=document.getElementById('search').value;const r=await fetch(`/api/inventory?page=${currentPage}&limit=20&search=${encodeURIComponent(s)}`);const d=await r.json();const tbody=document.getElementById('tbody');tbody.innerHTML='';d.items.forEach(i=>{tbody.innerHTML+=`<tr><td class="border p-2">${i.name}</td><td class="border p-2">Ksh ${i.price}</td><td class="border p-2">${i.stock}</td><td class="border p-2">${i.barcode||'-'}</td><td class="border p-2"><button onclick="deleteProduct('${i.id}')" class="bg-red-500 text-white px-2 py-1 rounded">Delete</button></td></tr>`});totalPages=d.pages;updatePagination();}
function updatePagination(){const p=document.getElementById('pagination');p.innerHTML='';if(totalPages<=1)return;for(let i=1;i<=Math.min(totalPages,5);i++){const btn=document.createElement('button');btn.textContent=i;btn.className='mx-1 px-3 py-1 border rounded '+(i===currentPage?'bg-purple-600 text-white':'bg-white');btn.onclick=()=>{currentPage=i;loadInventory();};p.appendChild(btn);}}
async function deleteProduct(id){if(confirm('Delete product?')){await fetch(`/api/inventory/${id}`,{method:'DELETE'});loadInventory();}}
function showAddModal(){document.getElementById('addModal').style.display='flex';}
function closeModal(){document.getElementById('addModal').style.display='none';}
document.getElementById('productForm').addEventListener('submit',async(e)=>{e.preventDefault();const data={name:document.getElementById('name').value,generic_name:document.getElementById('generic_name').value,manufacturer:document.getElementById('manufacturer').value,form:document.getElementById('form').value,strength:parseFloat(document.getElementById('strength').value),strength_unit:document.getElementById('strength_unit').value,price:parseFloat(document.getElementById('price').value),reorder_level:parseInt(document.getElementById('reorder_level').value),barcode:document.getElementById('barcode').value,initial_quantity:parseInt(document.getElementById('initial_quantity').value),expiry_date:document.getElementById('expiry_date').value};const r=await fetch('/api/inventory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(r.ok){closeModal();loadInventory();document.getElementById('productForm').reset();}else alert('Error');});
loadInventory();</script></head>
<body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold mb-4">Inventory Management</h1><div class="bg-white rounded shadow p-4"><div class="flex gap-2 mb-4"><input id="search" placeholder="Search..." class="flex-1 p-2 border rounded" onkeyup="loadInventory()"><button onclick="showAddModal()" class="bg-purple-600 text-white px-4 py-2 rounded">+ Add Product</button></div><table class="w-full"><thead><tr class="bg-gray-200"><th class="border p-2">Name</th><th class="border p-2">Price</th><th class="border p-2">Stock</th><th class="border p-2">Barcode</th><th class="border p-2">Actions</th></tr></thead><tbody id="tbody"></tbody></table><div id="pagination" class="mt-4 text-center"></div></div><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back</a></div>
<div id="addModal" class="fixed inset-0 bg-black bg-opacity-50 hidden justify-center items-center"><div class="bg-white p-6 rounded-lg w-96"><h2 class="text-xl font-bold mb-4">Add Product</h2><form id="productForm"><div class="mb-2"><input type="text" id="name" placeholder="Name*" required class="w-full p-2 border rounded"></div><div class="mb-2"><input type="text" id="generic_name" placeholder="Generic Name" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="text" id="manufacturer" placeholder="Manufacturer" class="w-full p-2 border rounded"></div><div class="mb-2"><select id="form" class="w-full p-2 border rounded"><option value="tablet">Tablet</option><option value="capsule">Capsule</option><option value="syrup">Syrup</option></select></div><div class="mb-2"><input type="number" id="strength" placeholder="Strength" step="0.01" class="w-full p-2 border rounded"></div><div class="mb-2"><select id="strength_unit" class="w-full p-2 border rounded"><option value="mg">mg</option><option value="g">g</option><option value="ml">ml</option></select></div><div class="mb-2"><input type="number" id="price" placeholder="Price*" step="0.01" required class="w-full p-2 border rounded"></div><div class="mb-2"><input type="number" id="reorder_level" placeholder="Reorder Level" value="50" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="text" id="barcode" placeholder="Barcode" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="number" id="initial_quantity" placeholder="Initial Quantity" value="0" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="date" id="expiry_date" class="w-full p-2 border rounded"></div><div class="flex gap-2 justify-end mt-4"><button type="button" onclick="closeModal()" class="px-4 py-2 border rounded">Cancel</button><button type="submit" class="px-4 py-2 bg-purple-600 text-white rounded">Save</button></div></form></div></div></body></html>"""

POS_HTML = """<!DOCTYPE html>
<html><head><title>POS</title><script src="https://cdn.tailwindcss.com"></script><script>
let cart=[];let scannerActive=false;
async function searchProducts(){const q=document.getElementById('search').value;if(!q){document.getElementById('results').innerHTML='';return;}const r=await fetch(`/api/products/search?q=${encodeURIComponent(q)}`);const p=await r.json();document.getElementById('results').innerHTML=p.map(pr=>`<div onclick="addToCart(${JSON.stringify(pr).replace(/"/g,'&quot;')})" class="bg-gray-100 p-2 m-1 rounded cursor-pointer hover:bg-gray-200">${pr.name} - Ksh ${pr.price}</div>`).join('');}
function addToCart(p){const e=cart.find(i=>i.id===p.id);if(e){if(e.quantity+1>p.stock){alert('Insufficient stock');return;}e.quantity++;}else cart.push({...p,quantity:1});updateCart();}
function updateCart(){const div=document.getElementById('cart');let total=0;div.innerHTML=cart.map((item,i)=>`<div class="flex justify-between p-2 border-b"><div><span class="font-medium">${item.name}</span><br><small>Ksh ${item.price} x ${item.quantity}</small></div><div><span class="font-bold">Ksh ${(item.price*item.quantity).toFixed(2)}</span><br><button onclick="updateQty(${i},-1)" class="text-blue-500">-</button><button onclick="updateQty(${i},1)" class="text-blue-500 ml-2">+</button><button onclick="removeItem(${i})" class="text-red-500 ml-2">×</button></div></div>`).join('');total=cart.reduce((s,i)=>s+i.price*i.quantity,0);const tax=total*0.16;const finalTotal=total+tax;document.getElementById('subtotal').innerText=total.toFixed(2);document.getElementById('tax').innerText=tax.toFixed(2);document.getElementById('total').innerText=finalTotal.toFixed(2);}
function updateQty(i,d){const newQty=cart[i].quantity+d;if(newQty<1)cart.splice(i,1);else if(newQty>cart[i].stock)alert('Insufficient stock');else cart[i].quantity=newQty;updateCart();}
function removeItem(i){cart.splice(i,1);updateCart();}
function clearCart(){if(confirm('Clear cart?')){cart=[];updateCart();}}
async function completeSale(){if(cart.length===0){alert('Cart empty');return;}const total=parseFloat(document.getElementById('total').innerText);const method=document.getElementById('payment-method').value;if(method==='cash'){const received=parseFloat(document.getElementById('cash-amount').value);if(received<total){alert(`Insufficient. Total: Ksh ${total.toFixed(2)}`);return;}}if(method==='mpesa'){const phone=document.getElementById('mpesa-phone').value;if(!phone){alert('Enter phone number');return;}}const saleData={subtotal:parseFloat(document.getElementById('subtotal').innerText),tax:parseFloat(document.getElementById('tax').innerText),discount:0,total:total,paymentMethod:method,amountPaid:method==='credit'?0:total,balance:method==='credit'?total:0,lineItems:cart.map(i=>({productId:i.id,quantity:i.quantity,unitPrice:i.price,lineTotal:i.price*i.quantity}))};const r=await fetch('/api/sales',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(saleData)});const res=await r.json();if(res.success){if(method==='mpesa'){alert('M-Pesa payment initiated. Complete on your phone.');}else{alert(`Sale #${res.sale_number} completed!`);}cart=[];updateCart();searchProducts();}else alert('Sale failed');}
function togglePaymentFields(){const m=document.getElementById('payment-method').value;document.getElementById('mpesa-fields').style.display=m==='mpesa'?'block':'none';document.getElementById('cash-fields').style.display=m==='cash'?'block':'none';}
function startScanner(){if(scannerActive)return;scannerActive=true;Quagga.init({inputStream:{name:"Live",type:"LiveStream",target:document.getElementById('scanner-container'),constraints:{facingMode:"environment"}},decoder:{readers:["ean_reader","code_128_reader"]}},function(err){if(err){alert('Camera not available');scannerActive=false;}else Quagga.start();});Quagga.onDetected((result)=>{handleBarcode(result.codeResult.code);});}
function stopScanner(){scannerActive=false;Quagga.stop();document.getElementById('scanner-container').innerHTML='';}
async function handleBarcode(code){const r=await fetch(`/api/product_by_barcode?code=${code}`);if(r.ok){const p=await r.json();addToCart(p);}else alert('Product not found');}
async function handleManualBarcode(){const code=document.getElementById('manual-barcode').value;if(code){await handleBarcode(code);document.getElementById('manual-barcode').value='';}}
</script><script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script></head>
<body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold mb-4">Point of Sale</h1><div class="grid grid-cols-1 lg:grid-cols-2 gap-6"><div><div class="bg-white rounded shadow p-4 mb-4"><h3 class="font-bold mb-2">📱 Barcode Scanner</h3><div class="flex gap-2 mb-2"><button onclick="startScanner()" class="bg-purple-600 text-white px-3 py-1 rounded">Start Camera</button><button onclick="stopScanner()" class="bg-red-500 text-white px-3 py-1 rounded">Stop Camera</button></div><div id="scanner-container" style="height:200px;background:#000;"></div><input id="manual-barcode" placeholder="Enter barcode" class="w-full mt-2 p-2 border rounded" onkeypress="if(event.key==='Enter')handleManualBarcode()"></div><div class="bg-white rounded shadow p-4"><h3 class="font-bold mb-2">🔍 Search Products</h3><input id="search" placeholder="Search by name or barcode..." class="w-full p-2 border rounded mb-2" oninput="searchProducts()"><div id="results" class="max-h-64 overflow-y-auto"></div></div></div><div><div class="bg-white rounded shadow p-4"><h3 class="font-bold mb-2">🛍️ Shopping Cart</h3><div id="cart" class="max-h-80 overflow-y-auto"></div><div class="border-t pt-2 mt-2"><div class="flex justify-between"><span>Subtotal:</span><strong>Ksh <span id="subtotal">0.00</span></strong></div><div class="flex justify-between"><span>Tax (16%):</span><strong>Ksh <span id="tax">0.00</span></strong></div><div class="flex justify-between text-xl font-bold"><span>Total:</span><span class="text-purple-600">Ksh <span id="total">0.00</span></span></div></div><div class="mt-4"><label>Payment Method</label><select id="payment-method" class="w-full p-2 border rounded mt-1" onchange="togglePaymentFields()"><option value="cash">💵 Cash</option><option value="mpesa">📱 M-Pesa</option><option value="credit">🏦 Credit</option></select><div id="mpesa-fields" style="display:none" class="mt-2"><input id="mpesa-phone" placeholder="Phone number" class="w-full p-2 border rounded"></div><div id="cash-fields" style="display:none" class="mt-2"><input id="cash-amount" type="number" placeholder="Amount received" class="w-full p-2 border rounded"></div><div class="flex gap-2 mt-4"><button onclick="completeSale()" class="flex-1 bg-green-600 text-white py-2 rounded font-semibold">Complete Sale</button><button onclick="clearCart()" class="flex-1 bg-red-500 text-white py-2 rounded">Clear Cart</button></div></div></div></div></div><a href="/dashboard" class="inline-block mt-6 text-purple-600">Back to Dashboard</a></div></body></html>"""

CUSTOMER_HTML = """<!DOCTYPE html>
<html><head><title>Customers</title><script src="https://cdn.tailwindcss.com"></script><script>
let currentPage=1,totalPages=1;
async function loadCustomers(){const s=document.getElementById('search').value;const r=await fetch(`/api/customers?page=${currentPage}&limit=20&search=${encodeURIComponent(s)}`);const d=await r.json();const tbody=document.getElementById('tbody');tbody.innerHTML='';d.items.forEach(c=>{tbody.innerHTML+=`<tr><td class="border p-2">${c.full_name}</td><td class="border p-2">${c.email||'-'}</td><td class="border p-2">${c.phone||'-'}</td><td class="border p-2">Ksh ${c.current_balance.toFixed(2)}</td><td class="border p-2"><button onclick="recordPayment('${c.id}')" class="bg-green-500 text-white px-2 py-1 rounded">Record Payment</button></td></tr>`});totalPages=d.pages;updatePagination();}
function updatePagination(){const p=document.getElementById('pagination');p.innerHTML='';if(totalPages<=1)return;for(let i=1;i<=Math.min(totalPages,5);i++){const btn=document.createElement('button');btn.textContent=i;btn.className='mx-1 px-3 py-1 border rounded '+(i===currentPage?'bg-purple-600 text-white':'bg-white');btn.onclick=()=>{currentPage=i;loadCustomers();};p.appendChild(btn);}}
async function recordPayment(id){const amt=prompt('Enter payment amount:');if(amt&&!isNaN(amt)&&amt>0){const r=await fetch(`/api/customers/${id}/payment`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({amount:parseFloat(amt)})});if(r.ok){loadCustomers();alert('Payment recorded');}else alert('Error');}}
function showAddModal(){document.getElementById('addModal').style.display='flex';}
function closeModal(){document.getElementById('addModal').style.display='none';}
document.getElementById('customerForm').addEventListener('submit',async(e)=>{e.preventDefault();const data={first_name:document.getElementById('first_name').value,last_name:document.getElementById('last_name').value,email:document.getElementById('email').value,phone:document.getElementById('phone').value,address:document.getElementById('address').value,date_of_birth:document.getElementById('date_of_birth').value,allergies:document.getElementById('allergies').value,medical_conditions:document.getElementById('medical_conditions').value,allow_credit:document.getElementById('allow_credit').checked,credit_limit:parseFloat(document.getElementById('credit_limit').value)};const r=await fetch('/api/customers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(r.ok){closeModal();loadCustomers();document.getElementById('customerForm').reset();}else alert('Error');});
loadCustomers();</script></head>
<body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold mb-4">Customer Management</h1><div class="bg-white rounded shadow p-4"><div class="flex gap-2 mb-4"><input id="search" placeholder="Search by name, email, phone..." class="flex-1 p-2 border rounded" onkeyup="loadCustomers()"><button onclick="showAddModal()" class="bg-purple-600 text-white px-4 py-2 rounded">+ Add Customer</button></div><table class="w-full"><thead><tr class="bg-gray-200"><th class="border p-2">Name</th><th class="border p-2">Email</th><th class="border p-2">Phone</th><th class="border p-2">Balance</th><th class="border p-2">Actions</th></tr></thead><tbody id="tbody"></tbody></table><div id="pagination" class="mt-4 text-center"></div></div><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back</a></div>
<div id="addModal" class="fixed inset-0 bg-black bg-opacity-50 hidden justify-center items-center"><div class="bg-white p-6 rounded-lg w-96 max-h-screen overflow-y-auto"><h2 class="text-xl font-bold mb-4">Add Customer</h2><form id="customerForm"><div class="mb-2"><input type="text" id="first_name" placeholder="First Name*" required class="w-full p-2 border rounded"></div><div class="mb-2"><input type="text" id="last_name" placeholder="Last Name*" required class="w-full p-2 border rounded"></div><div class="mb-2"><input type="email" id="email" placeholder="Email" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="tel" id="phone" placeholder="Phone" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="text" id="address" placeholder="Address" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="date" id="date_of_birth" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="text" id="allergies" placeholder="Allergies" class="w-full p-2 border rounded"></div><div class="mb-2"><input type="text" id="medical_conditions" placeholder="Medical Conditions" class="w-full p-2 border rounded"></div><div class="mb-2"><label><input type="checkbox" id="allow_credit"> Allow Credit</label></div><div class="mb-2"><input type="number" id="credit_limit" placeholder="Credit Limit" step="0.01" value="0" class="w-full p-2 border rounded"></div><div class="flex gap-2 justify-end mt-4"><button type="button" onclick="closeModal()" class="px-4 py-2 border rounded">Cancel</button><button type="submit" class="px-4 py-2 bg-purple-600 text-white rounded">Save</button></div></form></div></div></body></html>"""

STAFF_HTML = """<!DOCTYPE html>
<html><head><title>Staff</title><script src="https://cdn.tailwindcss.com"></script><script>
async function loadStaff(){const r=await fetch('/api/staff');const s=await r.json();const pending=s.filter(x=>!x.is_active);const active=s.filter(x=>x.is_active);document.getElementById('pending').innerHTML=pending.map(p=>`<div class="flex justify-between p-3 border-b"><div><strong>${p.full_name}</strong><br><small>${p.email} - ${p.role}</small></div><div><button onclick="approve('${p.id}')" class="bg-green-500 text-white px-2 py-1 rounded mr-2">Approve</button><button onclick="reject('${p.id}')" class="bg-red-500 text-white px-2 py-1 rounded">Reject</button></div></div>`).join('')||'<div class="text-center py-4 text-gray-400">No pending applications</div>';document.getElementById('active').innerHTML=active.map(a=>`<div class="flex justify-between p-3 border-b"><div><strong>${a.full_name}</strong><br><small>${a.email} - ${a.role}</small></div><button onclick="remove('${a.id}')" class="bg-red-500 text-white px-2 py-1 rounded">Remove</button></div>`).join('')||'<div class="text-center py-4 text-gray-400">No active staff</div>';}
async function approve(id){await fetch(`/api/staff/${id}/approve`,{method:'POST'});loadStaff();}
async function reject(id){if(confirm('Reject this application?')){await fetch(`/api/staff/${id}`,{method:'DELETE'});loadStaff();}}
async function remove(id){if(confirm('Remove this staff member?')){await fetch(`/api/staff/${id}`,{method:'DELETE'});loadStaff();}}
loadStaff();</script></head>
<body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold mb-4">Staff Management</h1><div class="bg-white rounded shadow p-4 mb-4"><h2 class="font-bold mb-2">Pending Approvals</h2><div id="pending"></div></div><div class="bg-white rounded shadow p-4"><h2 class="font-bold mb-2">Active Staff</h2><div id="active"></div></div><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div></body></html>"""

AI_CHAT_HTML = """<!DOCTYPE html>
<html><head><title>AI Assistant</title><script src="https://cdn.tailwindcss.com"></script><script>
let sid=null;
async function send(){const msg=document.getElementById('msg').value;if(!msg)return;addMsg(msg,'user');document.getElementById('msg').value='';document.getElementById('typing').style.display='block';const r=await fetch('/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,sessionId:sid})});const d=await r.json();sid=d.sessionId;document.getElementById('typing').style.display='none';addMsg(d.response,'assistant');}
function addMsg(t,r){const div=document.getElementById('msgs');const m=document.createElement('div');m.className=`p-2 my-1 rounded ${r==='user'?'bg-purple-100 text-right':'bg-gray-200'}`;m.innerText=t;div.appendChild(m);div.scrollTop=div.scrollHeight;}
function sendOnEnter(e){if(e.key==='Enter')send();}
</script></head>
<body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold mb-4">🤖 AI Pharmacy Assistant</h1><div class="bg-white rounded shadow p-4"><div id="msgs" class="h-96 overflow-y-auto mb-4"></div><div id="typing" class="hidden mb-2"><span class="text-gray-500">Typing...</span></div><div class="flex"><input id="msg" type="text" placeholder="Ask about medications, dosages, interactions..." class="flex-1 p-2 border rounded-l" onkeypress="sendOnEnter(event)"><button onclick="send()" class="bg-purple-600 text-white px-4 py-2 rounded-r">Send</button></div></div><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div></body></html>"""

PATIENT_MED_HTML = """<!DOCTYPE html>
<html><head><title>Patient Monitor</title><script src="https://cdn.tailwindcss.com"></script><script>
let currentStatus='active';
async function loadMedications(){const r=await fetch(`/api/patient-medications?status=${currentStatus}&limit=50`);const d=await r.json();const div=document.getElementById('list');div.innerHTML='';d.items.forEach(m=>{div.innerHTML+=`<div class="bg-white rounded shadow p-4 mb-2"><div class="flex justify-between"><div><strong>${m.patient.name}</strong> - ${m.drug.name}</div>${m.needs_alert?'<span class="text-red-500">⚠️ Low Stock</span>':''}</div><div class="text-sm mt-1">${m.dosage_instructions}</div><div class="text-sm">Remaining: <strong>${m.quantity_remaining} ${m.unit}</strong> / ${m.quantity_given}</div>${m.next_refill_date?`<div class="text-sm">Next refill: ${m.next_refill_date}</div>`:''}<div class="flex gap-2 mt-2"><button onclick="openChat('${m.id}','${m.patient.name}','${m.drug.name}')" class="bg-purple-600 text-white px-2 py-1 rounded text-sm">Chat</button><button onclick="refill('${m.id}',${m.quantity_remaining})" class="bg-green-600 text-white px-2 py-1 rounded text-sm">Refill</button><button onclick="adjustStock('${m.id}',${m.quantity_remaining})" class="bg-yellow-500 text-white px-2 py-1 rounded text-sm">Adjust</button></div></div>`});}
async function loadAlerts(){const r=await fetch('/api/patient-medications/alerts');const d=await r.json();const div=document.getElementById('alerts');div.innerHTML='';d.alerts.forEach(a=>{div.innerHTML+=`<div class="bg-red-50 border-l-4 border-red-500 p-3 rounded mb-2"><div class="font-semibold">${a.patient} - ${a.drug}</div><div>${a.message}</div><button onclick="openChat('${a.medication_id}','${a.patient}','${a.drug}')" class="mt-1 bg-purple-600 text-white px-2 py-1 rounded text-sm">Chat</button></div>`});if(!d.alerts.length)div.innerHTML='<div class="text-center py-4 text-gray-400">No active alerts</div>';}
async function checkAlerts(){const r=await fetch('/api/check-medication-alerts',{method:'POST'});const d=await r.json();alert(`${d.alerts_created} new alerts created`);loadAlerts();loadMedications();}
async function refill(id,current){const qty=prompt(`Current stock: ${current}\nEnter quantity to add:`);if(qty&&!isNaN(qty)&&qty>0){const r=await fetch(`/api/patient-medications/${id}/refill`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:parseInt(qty)})});if(r.ok){alert('Refill recorded');loadMedications();loadAlerts();}else alert('Error');}}
async function adjustStock(id,current){const newQty=prompt(`Current stock: ${current}\nEnter new stock quantity:`);if(newQty!==null&&!isNaN(newQty)&&newQty>=0){const r=await fetch(`/api/patient-medications/${id}/adjust-stock`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:parseInt(newQty),reason:'Manual adjustment'})});if(r.ok){alert('Stock updated');loadMedications();loadAlerts();}else alert('Error');}}
let chatId=null;
async function openChat(id,name,drug){chatId=id;document.getElementById('chatTitle').innerText=`Chat: ${name} - ${drug}`;document.getElementById('chatModal').style.display='flex';const r=await fetch(`/api/patient-medications/${id}/chat`);const msgs=await r.json();const div=document.getElementById('chatMsgs');div.innerHTML='';msgs.forEach(m=>{div.innerHTML+=`<div style="text-align:${m.is_from_patient?'left':'right'}" class="mb-2"><div class="inline-block p-2 rounded ${m.is_from_patient?'bg-gray-200':'bg-purple-600 text-white'}">${m.message}</div><div class="text-xs text-gray-500">${new Date(m.created_at).toLocaleTimeString()}</div></div>`;});div.scrollTop=div.scrollHeight;}
async function sendChat(){const msg=document.getElementById('chatInput').value;if(!msg||!chatId)return;const r=await fetch(`/api/patient-medications/${chatId}/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});if(r.ok){document.getElementById('chatInput').value='';openChat(chatId,'','');}}
function closeChat(){document.getElementById('chatModal').style.display='none';chatId=null;}
function setStatus(s){currentStatus=s;document.querySelectorAll('.tab').forEach(t=>t.classList.remove('border-purple-600','text-purple-600'));event.target.classList.add('border-purple-600','text-purple-600');loadMedications();}
loadMedications();loadAlerts();</script></head>
<body class="bg-gray-100"><div class="container mx-auto px-6 py-8"><h1 class="text-2xl font-bold mb-4">Patient Medication Monitor</h1><div class="bg-white rounded shadow p-4 mb-4"><div class="flex justify-between items-center mb-2"><h2 class="font-bold">⚠️ Active Alerts</h2><button onclick="checkAlerts()" class="bg-purple-600 text-white px-3 py-1 rounded text-sm">Check Alerts</button></div><div id="alerts"></div></div><div class="bg-white rounded shadow p-4"><div class="flex gap-4 border-b mb-4"><button class="tab border-b-2 border-purple-600 text-purple-600 pb-2" onclick="setStatus('active')">Active</button><button class="tab pb-2" onclick="setStatus('completed')">Completed</button><button class="tab pb-2" onclick="setStatus('discontinued')">Discontinued</button></div><div id="list"></div></div><a href="/dashboard" class="inline-block mt-4 text-purple-600">Back to Dashboard</a></div>
<div id="chatModal" class="fixed inset-0 bg-black bg-opacity-50 hidden justify-center items-center"><div class="bg-white rounded-lg w-96 h-96 flex flex-col"><div class="p-4 border-b flex justify-between"><h3 id="chatTitle" class="font-bold">Chat</h3><button onclick="closeChat()" class="text-gray-500">×</button></div><div id="chatMsgs" class="flex-1 overflow-y-auto p-4"></div><div class="p-4 border-t flex"><input id="chatInput" type="text" placeholder="Type message..." class="flex-1 p-2 border rounded-l"><button onclick="sendChat()" class="bg-purple-600 text-white px-3 py-2 rounded-r">Send</button></div></div></div></body></html>"""

@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=INVENTORY_HTML)

@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=POS_HTML)

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=CUSTOMER_HTML)

@app.get("/staff", response_class=HTMLResponse)
async def staff_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=STAFF_HTML)

@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=AI_CHAT_HTML)

@app.get("/patient-medications", response_class=HTMLResponse)
async def patient_medications_page(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=PATIENT_MED_HTML)

# ==================== API ENDPOINTS ====================
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

@app.get("/api/customers")
async def get_customers(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), page: int = 1, limit: int = 20, search: str = ""):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    query = db.query(models.Customer).filter(models.Customer.organization_id == org_id)
    if search:
        query = query.filter(or_(models.Customer.first_name.ilike(f"%{search}%"), models.Customer.last_name.ilike(f"%{search}%"), models.Customer.email.ilike(f"%{search}%")))
    total = query.count()
    customers = query.offset(offset).limit(limit).all()
    items = [{"id": c.id, "first_name": c.first_name, "last_name": c.last_name, "full_name": c.full_name, "email": c.email, "phone": c.phone, "current_balance": float(c.current_balance)} for c in customers]
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

@app.get("/api/patient-medications")
async def get_patient_medications(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db), page: int = 1, limit: int = 20, status: str = "active"):
    org_id = request.session.get("org_id")
    offset = (page - 1) * limit
    status_enum = models.MedicationStatusEnum.active if status == "active" else (models.MedicationStatusEnum.completed if status == "completed" else models.MedicationStatusEnum.discontinued)
    query = db.query(models.PatientMedication).filter(models.PatientMedication.organization_id == org_id, models.PatientMedication.status == status_enum)
    total = query.count()
    medications = query.offset(offset).limit(limit).all()
    result = [{
        "id": m.id,
        "patient": {"id": m.patient.id, "name": m.patient.full_name},
        "drug": {"id": m.drug.id, "name": m.drug.name},
        "dosage_instructions": m.dosage_instructions,
        "quantity_given": m.quantity_given,
        "quantity_remaining": m.quantity_remaining,
        "unit": m.unit,
        "next_refill_date": m.next_refill_date.isoformat() if m.next_refill_date else None,
        "needs_alert": m.quantity_remaining <= m.low_stock_threshold,
        "status": m.status.value
    } for m in medications]
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
            id=str(uuid.uuid4()), organization_id=org_id, patient_id=data["patient_id"], drug_id=data["drug_id"],
            dosage_instructions=data["dosage_instructions"], quantity_given=data["quantity_given"],
            quantity_remaining=data["quantity_given"], unit=data.get("unit", "tablets"),
            start_date=datetime.strptime(data["start_date"], "%Y-%m-%d").date(), end_date=end_date,
            next_refill_date=next_refill_date, last_refill_date=datetime.now().date(),
            reminder_days_before=data.get("reminder_days_before", 3), low_stock_threshold=data.get("low_stock_threshold", 10),
            status=models.MedicationStatusEnum.active, notes=data.get("notes", ""), created_by=user.id
        )
        db.add(medication)
        db.commit()
        if medication.quantity_remaining <= medication.low_stock_threshold:
            create_reminder(db, medication, models.ReminderTypeEnum.low_stock, f"Low stock alert: Only {medication.quantity_remaining} {medication.unit} remaining for {medication.patient.full_name}")
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
    old_quantity = medication.quantity_remaining
    new_quantity = old_quantity + quantity_refilled
    refill = models.MedicationRefill(id=str(uuid.uuid4()), medication_id=medication_id, organization_id=medication.organization_id,
                                      refill_date=datetime.now().date(), quantity_refilled=quantity_refilled,
                                      previous_quantity=old_quantity, new_quantity=new_quantity, notes=data.get("notes", ""), created_by=user.id)
    db.add(refill)
    medication.quantity_remaining = new_quantity
    medication.last_refill_date = datetime.now().date()
    if medication.end_date:
        medication.next_refill_date = medication.end_date - timedelta(days=medication.reminder_days_before)
    db.commit()
    create_reminder(db, medication, models.ReminderTypeEnum.refill_due, f"Medication refilled: {quantity_refilled} {medication.unit} added. New stock: {new_quantity} {medication.unit}")
    return {"success": True, "new_quantity": new_quantity}

@app.post("/api/patient-medications/{medication_id}/adjust-stock")
async def adjust_medication_stock(medication_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    medication = db.query(models.PatientMedication).filter(models.PatientMedication.id == medication_id).first()
    if not medication:
        raise HTTPException(404, "Not found")
    new_quantity = data.get("quantity", 0)
    old_quantity = medication.quantity_remaining
    medication.quantity_remaining = new_quantity
    medication.notes = f"{medication.notes}\n[{datetime.now().strftime('%Y-%m-%d')}] Stock adjusted from {old_quantity} to {new_quantity}. Reason: {data.get('reason', 'Manual adjustment')}"
    db.commit()
    if new_quantity <= medication.low_stock_threshold:
        create_reminder(db, medication, models.ReminderTypeEnum.low_stock, f"Low stock alert: Only {new_quantity} {medication.unit} remaining")
    return {"success": True, "new_quantity": new_quantity}

@app.get("/api/patient-medications/alerts")
async def get_medication_alerts(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    alerts = []
    low_stock = db.query(models.PatientMedication).filter(models.PatientMedication.organization_id == org_id, models.PatientMedication.status == models.MedicationStatusEnum.active, models.PatientMedication.quantity_remaining <= models.PatientMedication.low_stock_threshold).all()
    for med in low_stock:
        alerts.append({"type": "low_stock", "medication_id": med.id, "patient": med.patient.full_name, "drug": med.drug.name, "message": f"Low stock: {med.quantity_remaining} {med.unit} remaining (threshold: {med.low_stock_threshold})", "urgency": "high"})
    refill_due = db.query(models.PatientMedication).filter(models.PatientMedication.organization_id == org_id, models.PatientMedication.status == models.MedicationStatusEnum.active, models.PatientMedication.next_refill_date <= date.today(), models.PatientMedication.next_refill_date.isnot(None)).all()
    for med in refill_due:
        days_overdue = (date.today() - med.next_refill_date).days
        alerts.append({"type": "refill_due", "medication_id": med.id, "patient": med.patient.full_name, "drug": med.drug.name, "message": f"Refill overdue by {days_overdue} days", "urgency": "high"})
    return {"alerts": alerts, "count": len(alerts)}

@app.get("/api/patient-medications/{medication_id}/chat")
async def get_medication_chat(medication_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    messages = db.query(models.MedicationChat).filter(models.MedicationChat.medication_id == medication_id).order_by(models.MedicationChat.created_at).all()
    return [{"id": m.id, "message": m.message, "is_from_patient": m.is_from_patient, "sender_name": m.patient.full_name if m.is_from_patient else (m.user.full_name if m.user else "Pharmacy"), "created_at": m.created_at.isoformat()} for m in messages]

@app.post("/api/patient-medications/{medication_id}/chat")
async def send_medication_chat(medication_id: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    data = await request.json()
    medication = db.query(models.PatientMedication).filter(models.PatientMedication.id == medication_id).first()
    if not medication:
        raise HTTPException(404, "Not found")
    chat = models.MedicationChat(id=str(uuid.uuid4()), medication_id=medication_id, organization_id=medication.organization_id,
                                  patient_id=medication.patient_id, user_id=user.id, message=data["message"], is_from_patient=False)
    db.add(chat)
    db.commit()
    return {"success": True, "id": chat.id}

@app.post("/api/check-medication-alerts")
async def check_medication_alerts(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    medications = db.query(models.PatientMedication).filter(models.PatientMedication.organization_id == org_id, models.PatientMedication.status == models.MedicationStatusEnum.active).all()
    alerts_created = 0
    for med in medications:
        if med.quantity_remaining <= med.low_stock_threshold:
            existing = db.query(models.MedicationReminder).filter(models.MedicationReminder.medication_id == med.id, models.MedicationReminder.reminder_type == models.ReminderTypeEnum.low_stock, models.MedicationReminder.sent_at >= datetime.now() - timedelta(days=3)).first()
            if not existing:
                create_reminder(db, med, models.ReminderTypeEnum.low_stock, f"⚠️ Low stock alert: Only {med.quantity_remaining} {med.unit} remaining. Please refill soon.")
                alerts_created += 1
        if med.next_refill_date and med.next_refill_date <= date.today():
            existing = db.query(models.MedicationReminder).filter(models.MedicationReminder.medication_id == med.id, models.MedicationReminder.reminder_type == models.ReminderTypeEnum.refill_due, models.MedicationReminder.sent_at >= datetime.now() - timedelta(days=3)).first()
            if not existing:
                days_overdue = (date.today() - med.next_refill_date).days
                create_reminder(db, med, models.ReminderTypeEnum.refill_due, f"📅 Refill reminder: Medication refill is {days_overdue} days overdue. Please schedule a refill.")
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

# ==================== REPORTS ====================
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
