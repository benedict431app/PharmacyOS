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
    
    category = models.Category(id=str(uuid.uuid4()), organization_id=org.id, name="General Medicines", description="General prescription and OTC medicines")
    db.add(category)
    db.flush()
    
    supplier = models.Supplier(id=str(uuid.uuid4()), organization_id=org.id, name="MediSupplies Ltd", contact_person="John Supplier", email="supplies@medisupplies.com", phone="555-0200", address="456 Supply Street")
    db.add(supplier)
    db.flush()
    
    drugs = [
        models.Drug(id=str(uuid.uuid4()), organization_id=org.id, name="Paracetamol 500mg", generic_name="Paracetamol", manufacturer="Generic Pharma", form=models.DrugFormEnum.tablet, strength=500.0, strength_unit=models.StrengthUnitEnum.mg, category_id=category.id, supplier_id=supplier.id, description="Pain reliever", usage_instructions="Take 1-2 tablets", side_effects="Nausea", contraindications="Liver disease", price=50.0, reorder_level=100, barcode="123456789012"),
        models.Drug(id=str(uuid.uuid4()), organization_id=org.id, name="Amoxicillin 500mg", generic_name="Amoxicillin", manufacturer="Antibio Labs", form=models.DrugFormEnum.capsule, strength=500.0, strength_unit=models.StrengthUnitEnum.mg, category_id=category.id, supplier_id=supplier.id, description="Antibiotic", usage_instructions="3 times daily", side_effects="Diarrhea", contraindications="Penicillin allergy", price=150.0, reorder_level=50, barcode="123456789013"),
        models.Drug(id=str(uuid.uuid4()), organization_id=org.id, name="Ibuprofen 400mg", generic_name="Ibuprofen", manufacturer="PainFree Inc", form=models.DrugFormEnum.tablet, strength=400.0, strength_unit=models.StrengthUnitEnum.mg, category_id=category.id, supplier_id=supplier.id, description="Anti-inflammatory", usage_instructions="With food", side_effects="Stomach upset", contraindications="Ulcers", price=80.0, reorder_level=75, barcode="123456789014")
    ]
    db.add_all(drugs)
    db.flush()
    
    for drug in drugs:
        db.add(models.InventoryBatch(id=str(uuid.uuid4()), drug_id=drug.id, lot_number=f"LOT-{drug.name[:5]}", quantity_on_hand=200, expiry_date=date(2026,12,31), purchase_date=date(2025,1,1), cost_price=drug.price*0.6, status=models.BatchStatusEnum.active))
    
    customer = models.Customer(id=str(uuid.uuid4()), organization_id=org.id, first_name="John", last_name="Smith", email="john@example.com", phone="555-0100", address="789 Customer Ave", date_of_birth=date(1985,5,15), allergies="None", medical_conditions="None", allow_credit=True, credit_limit=5000.0, current_balance=0.0)
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

# Templates for pages that need them (dashboard, inventory, etc.)
templates = Jinja2Templates(directory="templates")

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
    <title>PharmaSaaS - Complete Pharmacy Management System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card-hover { transition: transform 0.3s ease, box-shadow 0.3s ease; }
        .card-hover:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
        .pricing-card { transition: transform 0.3s ease; }
        .pricing-card:hover { transform: translateY(-10px); }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Hero Section -->
    <div class="gradient-bg text-white overflow-hidden">
        <div class="container mx-auto px-6 py-16">
            <div class="flex flex-col lg:flex-row items-center justify-between">
                <div class="lg:w-1/2 text-center lg:text-left">
                    <div class="flex justify-center lg:justify-start mb-4"><i class="fas fa-hospital-user text-5xl"></i></div>
                    <h1 class="text-4xl md:text-5xl font-bold mb-4">PharmaSaaS</h1>
                    <p class="text-xl mb-6 opacity-95">Complete Pharmacy Management System for Modern Pharmacies</p>
                    <div class="flex gap-4 justify-center lg:justify-start flex-wrap">
                        <a href="/register" class="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition inline-flex items-center"><i class="fas fa-rocket mr-2"></i> Get Started Free</a>
                        <a href="/login" class="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition inline-flex items-center"><i class="fas fa-sign-in-alt mr-2"></i> Login</a>
                    </div>
                    <div class="mt-8 flex gap-6 justify-center lg:justify-start">
                        <div class="text-center"><div class="text-2xl font-bold">500+</div><div class="text-sm opacity-80">Happy Pharmacies</div></div>
                        <div class="text-center"><div class="text-2xl font-bold">10k+</div><div class="text-sm opacity-80">Daily Transactions</div></div>
                        <div class="text-center"><div class="text-2xl font-bold">24/7</div><div class="text-sm opacity-80">Support</div></div>
                    </div>
                </div>
                <div class="lg:w-1/2 mt-12 lg:mt-0">
                    <div class="bg-white rounded-2xl shadow-2xl p-6">
                        <div class="flex items-center justify-between mb-4">
                            <div class="flex space-x-2"><div class="w-3 h-3 bg-red-500 rounded-full"></div><div class="w-3 h-3 bg-yellow-500 rounded-full"></div><div class="w-3 h-3 bg-green-500 rounded-full"></div></div>
                            <i class="fas fa-qrcode text-gray-400"></i>
                        </div>
                        <div class="bg-gray-100 rounded-lg p-4 mb-4">
                            <div class="flex items-center justify-between mb-2"><span class="font-mono text-sm">Scan Barcode:</span><i class="fas fa-camera text-purple-600"></i></div>
                            <div class="bg-white rounded p-2 font-mono text-sm">123456789012</div>
                        </div>
                        <div class="space-y-2">
                            <div class="flex justify-between"><span>Paracetamol 500mg</span><span class="font-bold">Ksh 50.00</span></div>
                            <div class="flex justify-between"><span>Amoxicillin 500mg</span><span class="font-bold">Ksh 150.00</span></div>
                            <div class="border-t pt-2 mt-2"><div class="flex justify-between font-bold"><span>Total:</span><span class="text-purple-600">Ksh 200.00</span></div></div>
                        </div>
                        <button class="w-full mt-4 bg-purple-600 text-white py-2 rounded-lg font-semibold">Complete Sale</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Features Section -->
    <div class="container mx-auto px-6 py-20">
        <div class="text-center mb-12">
            <h2 class="text-3xl md:text-4xl font-bold text-gray-800 mb-4">Powerful Features</h2>
            <p class="text-xl text-gray-600 max-w-2xl mx-auto">Everything you need to run your pharmacy efficiently</p>
        </div>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div class="bg-white rounded-xl shadow-lg p-6 card-hover"><div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4"><i class="fas fa-qrcode text-2xl text-purple-600"></i></div><h3 class="text-xl font-semibold mb-2">Barcode Scanning</h3><p class="text-gray-600">Use your phone camera to scan product barcodes for instant inventory management.</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6 card-hover"><div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4"><i class="fas fa-users text-2xl text-purple-600"></i></div><h3 class="text-xl font-semibold mb-2">Multi-User Support</h3><p class="text-gray-600">Admin and Pharmacist roles with custom permissions.</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6 card-hover"><div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4"><i class="fas fa-credit-card text-2xl text-purple-600"></i></div><h3 class="text-xl font-semibold mb-2">Credit Management</h3><p class="text-gray-600">Manage clients with credit accounts and payment tracking.</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6 card-hover"><div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4"><i class="fas fa-robot text-2xl text-purple-600"></i></div><h3 class="text-xl font-semibold mb-2">AI Assistant</h3><p class="text-gray-600">Built-in AI chat for drug information and dosage queries.</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6 card-hover"><div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4"><i class="fas fa-chart-line text-2xl text-purple-600"></i></div><h3 class="text-xl font-semibold mb-2">Analytics Dashboard</h3><p class="text-gray-600">Real-time sales analytics and inventory alerts.</p></div>
            <div class="bg-white rounded-xl shadow-lg p-6 card-hover"><div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4"><i class="fas fa-shopping-cart text-2xl text-purple-600"></i></div><h3 class="text-xl font-semibold mb-2">Point of Sale</h3><p class="text-gray-600">Fast POS with barcode scanning and M-Pesa integration.</p></div>
        </div>
    </div>

    <!-- Additional Features Banner -->
    <div class="gradient-bg text-white py-16">
        <div class="container mx-auto px-6">
            <div class="grid md:grid-cols-4 gap-8 text-center">
                <div><i class="fas fa-mobile-alt text-3xl mb-3"></i><h4 class="font-bold mb-1">Mobile Ready</h4><p class="text-sm opacity-90">Access from any device</p></div>
                <div><i class="fas fa-shield-alt text-3xl mb-3"></i><h4 class="font-bold mb-1">Secure</h4><p class="text-sm opacity-90">Bank-grade encryption</p></div>
                <div><i class="fas fa-clock text-3xl mb-3"></i><h4 class="font-bold mb-1">24/7 Support</h4><p class="text-sm opacity-90">Always here to help</p></div>
                <div><i class="fas fa-chart-bar text-3xl mb-3"></i><h4 class="font-bold mb-1">Reports</h4><p class="text-sm opacity-90">Detailed analytics</p></div>
            </div>
        </div>
    </div>

    <!-- Pricing Section -->
    <div class="bg-gray-100 py-20">
        <div class="container mx-auto px-6">
            <div class="text-center mb-12"><h2 class="text-3xl md:text-4xl font-bold text-gray-800 mb-4">Simple Pricing</h2><p class="text-xl text-gray-600">Choose the plan that fits your pharmacy's needs</p></div>
            <div class="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                <div class="bg-white rounded-2xl shadow-lg p-8 pricing-card text-center"><i class="fas fa-store text-3xl text-purple-600 mb-4"></i><h3 class="text-2xl font-bold mb-2">Starter</h3><div class="text-4xl font-bold text-purple-600 mb-4">Kes 180 <span class="text-lg text-gray-500">/month</span></div><ul class="space-y-2 mb-8 text-left"><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>1 Admin + 2 Pharmacists</li><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>Up to 500 products</li><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>Basic reporting</li></ul><a href="/register" class="block bg-gray-200 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-300">Get Started</a></div>
                <div class="bg-white rounded-2xl shadow-2xl p-8 pricing-card transform scale-105 border-2 border-purple-500 relative text-center"><div class="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-purple-600 text-white px-4 py-1 rounded-full text-sm font-bold">Most Popular</div><i class="fas fa-chart-line text-3xl text-purple-600 mb-4"></i><h3 class="text-2xl font-bold mb-2">Professional</h3><div class="text-4xl font-bold text-purple-600 mb-4">Kes 279 <span class="text-lg text-gray-500">/month</span></div><ul class="space-y-2 mb-8 text-left"><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>Unlimited users</li><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>Unlimited products</li><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>AI Assistant</li><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>M-Pesa Integration</li></ul><a href="/register" class="block bg-purple-600 text-white py-3 rounded-lg font-semibold hover:bg-purple-700">Get Started</a></div>
                <div class="bg-white rounded-2xl shadow-lg p-8 pricing-card text-center"><i class="fas fa-building text-3xl text-purple-600 mb-4"></i><h3 class="text-2xl font-bold mb-2">Enterprise</h3><div class="text-4xl font-bold text-purple-600 mb-4">Kes 499 <span class="text-lg text-gray-500">/month</span></div><ul class="space-y-2 mb-8 text-left"><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>Multiple locations</li><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>Custom integrations</li><li class="flex items-center"><i class="fas fa-check-circle text-green-500 mr-3"></i>24/7 phone support</li></ul><a href="/register" class="block bg-gray-200 text-gray-700 py-3 rounded-lg font-semibold hover:bg-gray-300">Contact Sales</a></div>
            </div>
            <div class="text-center mt-12"><p class="text-gray-600">All plans include 14-day free trial. No credit card required.</p><a href="/register" class="inline-block mt-4 text-purple-600 font-semibold hover:underline">Start your free trial →</a></div>
        </div>
    </div>

    <!-- Testimonials Section -->
    <div class="container mx-auto px-6 py-20">
        <div class="text-center mb-12"><h2 class="text-3xl md:text-4xl font-bold text-gray-800 mb-4">Trusted by Pharmacies</h2><p class="text-xl text-gray-600">Join hundreds of satisfied pharmacy owners</p></div>
        <div class="grid md:grid-cols-3 gap-8">
            <div class="bg-white rounded-xl shadow-lg p-6"><div class="flex items-center mb-4"><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i></div><p class="text-gray-600 mb-4">"PharmaSaaS has transformed our pharmacy operations. The POS system is incredibly fast and the M-Pesa integration is seamless."</p><div class="flex items-center"><div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mr-3"><i class="fas fa-user text-purple-600"></i></div><div><p class="font-semibold">Dr. Sarah Kimani</p><p class="text-sm text-gray-500">Nairobi Pharmacy</p></div></div></div>
            <div class="bg-white rounded-xl shadow-lg p-6"><div class="flex items-center mb-4"><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i></div><p class="text-gray-600 mb-4">"The AI assistant is a game-changer! It helps my staff answer customer questions about medications quickly and accurately."</p><div class="flex items-center"><div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mr-3"><i class="fas fa-user text-purple-600"></i></div><div><p class="font-semibold">James Otieno</p><p class="text-sm text-gray-500">Mombasa Chemists</p></div></div></div>
            <div class="bg-white rounded-xl shadow-lg p-6"><div class="flex items-center mb-4"><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i></div><p class="text-gray-600 mb-4">"Inventory management has never been easier. The low stock alerts save us from running out of essential medicines."</p><div class="flex items-center"><div class="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mr-3"><i class="fas fa-user text-purple-600"></i></div><div><p class="font-semibold">Mary Wanjiku</p><p class="text-sm text-gray-500">Nakuru Pharmacy</p></div></div></div>
        </div>
    </div>

    <!-- CTA Section -->
    <div class="gradient-bg text-white py-16">
        <div class="container mx-auto px-6 text-center">
            <h2 class="text-3xl md:text-4xl font-bold mb-4">Ready to transform your pharmacy?</h2>
            <p class="text-xl mb-8 opacity-90">Join thousands of pharmacies using PharmaSaaS to manage their operations efficiently</p>
            <div class="flex gap-4 justify-center flex-wrap">
                <a href="/register" class="bg-white text-purple-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition inline-flex items-center"><i class="fas fa-rocket mr-2"></i> Start Free Trial</a>
                <a href="/login" class="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-purple-600 transition inline-flex items-center"><i class="fas fa-sign-in-alt mr-2"></i> Login</a>
            </div>
            <p class="mt-8 text-sm opacity-75">No credit card required • 14-day free trial • Cancel anytime</p>
        </div>
    </div>

    <!-- Footer -->
    <footer class="bg-gray-900 text-white py-12">
        <div class="container mx-auto px-6 text-center">
            <div class="flex items-center justify-center mb-4"><i class="fas fa-hospital-user text-2xl mr-2"></i><span class="font-bold text-xl">PharmaSaaS</span></div>
            <p class="text-gray-400 text-sm mb-4">Complete pharmacy management solution for modern pharmacies.</p>
            <p class="text-gray-400 text-sm">&copy; 2025 PharmaSaaS. All rights reserved. Transform your pharmacy with intelligent management.</p>
        </div>
    </footer>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    return HTMLResponse(content=LANDING_HTML)

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
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "total_products": total_products,
        "total_customers": total_customers,
        "total_sales": total_sales,
        "pending_credit": float(pending_credit),
        "low_stock_items": low_stock_items,
        "recent_sales": recent_sales,
        "medication_alerts": medication_alerts
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
            "barcode": drug.barcode,
            "description": drug.description
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
        raise HTTPException(400, detail=str(e))

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
        raise HTTPException(404, "Product not found")
    
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
        raise HTTPException(404, "Product not found")
    
    has_sales = db.query(models.SalesLineItem).filter(models.SalesLineItem.drug_id == drug_id).first()
    if has_sales:
        raise HTTPException(400, "Cannot delete product with existing sales")
    
    try:
        db.query(models.InventoryBatch).filter(models.InventoryBatch.drug_id == drug_id).delete()
        db.delete(drug)
        db.commit()
        return {"success": True}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

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
        raise HTTPException(404, "Product not found")
    
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
        raise HTTPException(400, detail=str(e))

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
        raise HTTPException(400, detail=str(e))

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
        raise HTTPException(404, "Customer not found")
    
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
        raise HTTPException(400, detail=str(e))

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
        raise HTTPException(404, "Customer not found")
    
    try:
        amount = data.get("amount", 0)
        if amount <= 0:
            raise HTTPException(400, "Invalid payment amount")
        
        customer.current_balance -= amount
        db.commit()
        return {"success": True, "new_balance": float(customer.current_balance)}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

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
            raise HTTPException(400, detail="Email already exists")
        
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
        raise HTTPException(400, detail=str(e))

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
        raise HTTPException(404, detail="Staff member not found")
    
    try:
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
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

@app.delete("/api/staff/{staff_id}")
async def delete_staff(
    staff_id: str,
    request: Request,
    user: models.User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    org_id = request.session.get("org_id")
    
    if staff_id == user.id:
        raise HTTPException(400, detail="Cannot delete your own account")
    
    staff = db.query(models.User).filter(
        models.User.id == staff_id,
        models.User.organization_id == org_id
    ).first()
    
    if not staff:
        raise HTTPException(404, detail="Staff member not found")
    
    try:
        db.delete(staff)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

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
        raise HTTPException(400, detail="Message is required")
    
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

@app.get("/api/ai/sessions")
async def get_ai_sessions(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
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
    session = db.query(models.AIChatSession).filter(
        models.AIChatSession.id == session_id,
        models.AIChatSession.user_id == user.id
    ).first()
    
    if not session:
        raise HTTPException(404, detail="Session not found")
    
    messages = db.query(models.AIChatMessage).filter(
        models.AIChatMessage.session_id == session_id
    ).order_by(models.AIChatMessage.created_at).all()
    
    return [{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat()
    } for m in messages]

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
        raise HTTPException(400, detail="Missing required fields")
    
    sale = db.query(models.SalesOrder).filter(
        models.SalesOrder.id == sale_id,
        models.SalesOrder.organization_id == request.session.get("org_id")
    ).first()
    
    if not sale:
        raise HTTPException(404, detail="Sale not found")
    
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
        raise HTTPException(400, detail=result.get("error", "Payment initiation failed"))

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

# ==================== PATIENT MEDICATION MONITORING ====================
@app.get("/patient-medications", response_class=HTMLResponse)
async def patient_medications_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("patient_medications.html", {"request": request, "user": user})

@app.get("/api/patient-medications")
async def get_patient_medications(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 20,
    status: str = "active"
):
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
    for med in medications:
        days_remaining = None
        if med.next_refill_date:
            days_remaining = (med.next_refill_date - date.today()).days
        
        needs_alert = med.quantity_remaining <= med.low_stock_threshold
        
        result.append({
            "id": med.id,
            "patient": {
                "id": med.patient.id,
                "name": med.patient.full_name,
                "phone": med.patient.phone,
                "email": med.patient.email
            },
            "drug": {
                "id": med.drug.id,
                "name": med.drug.name,
                "price": float(med.drug.price)
            },
            "dosage_instructions": med.dosage_instructions,
            "quantity_given": med.quantity_given,
            "quantity_remaining": med.quantity_remaining,
            "unit": med.unit,
            "start_date": med.start_date.isoformat(),
            "end_date": med.end_date.isoformat() if med.end_date else None,
            "next_refill_date": med.next_refill_date.isoformat() if med.next_refill_date else None,
            "days_remaining": days_remaining,
            "needs_alert": needs_alert,
            "status": med.status.value if med.status else "active",
            "notes": med.notes
        })
    
    return {
        "items": result,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@app.post("/api/patient-medications")
async def add_patient_medication(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
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
            create_reminder(db, medication, models.ReminderTypeEnum.low_stock, 
                           f"Low stock alert: Only {medication.quantity_remaining} {medication.unit} remaining for {medication.patient.full_name}")
        
        return {"success": True, "id": medication.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

@app.put("/api/patient-medications/{medication_id}/refill")
async def refill_medication(
    medication_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    medication = db.query(models.PatientMedication).filter(
        models.PatientMedication.id == medication_id,
        models.PatientMedication.organization_id == org_id
    ).first()
    
    if not medication:
        raise HTTPException(404, "Medication record not found")
    
    try:
        quantity_refilled = data.get("quantity", 0)
        old_quantity = medication.quantity_remaining
        new_quantity = old_quantity + quantity_refilled
        
        refill = models.MedicationRefill(
            id=str(uuid.uuid4()),
            medication_id=medication_id,
            organization_id=org_id,
            refill_date=datetime.now().date(),
            quantity_refilled=quantity_refilled,
            previous_quantity=old_quantity,
            new_quantity=new_quantity,
            notes=data.get("notes", ""),
            created_by=user.id
        )
        db.add(refill)
        
        medication.quantity_remaining = new_quantity
        medication.last_refill_date = datetime.now().date()
        
        if medication.end_date:
            medication.next_refill_date = medication.end_date - timedelta(days=medication.reminder_days_before)
        
        db.commit()
        
        create_reminder(db, medication, models.ReminderTypeEnum.refill_due, 
                       f"Medication refilled: {quantity_refilled} {medication.unit} added. New stock: {new_quantity} {medication.unit}")
        
        return {"success": True, "new_quantity": new_quantity}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

@app.post("/api/patient-medications/{medication_id}/adjust-stock")
async def adjust_medication_stock(
    medication_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    medication = db.query(models.PatientMedication).filter(
        models.PatientMedication.id == medication_id,
        models.PatientMedication.organization_id == org_id
    ).first()
    
    if not medication:
        raise HTTPException(404, "Medication record not found")
    
    try:
        new_quantity = data.get("quantity", 0)
        reason = data.get("reason", "Manual adjustment")
        
        old_quantity = medication.quantity_remaining
        medication.quantity_remaining = new_quantity
        medication.notes = f"{medication.notes}\n[{datetime.now().strftime('%Y-%m-%d')}] Stock adjusted from {old_quantity} to {new_quantity}. Reason: {reason}"
        
        db.commit()
        
        if new_quantity <= medication.low_stock_threshold:
            create_reminder(db, medication, models.ReminderTypeEnum.low_stock, 
                           f"Low stock alert: Only {new_quantity} {medication.unit} remaining")
        
        return {"success": True, "new_quantity": new_quantity}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

@app.get("/api/patient-medications/alerts")
async def get_medication_alerts(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
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
            "message": f"Low stock: {med.quantity_remaining} {med.unit} remaining (threshold: {med.low_stock_threshold})",
            "urgency": "high"
        })
    
    refill_due = db.query(models.PatientMedication).filter(
        models.PatientMedication.organization_id == org_id,
        models.PatientMedication.status == models.MedicationStatusEnum.active,
        models.PatientMedication.next_refill_date <= date.today(),
        models.PatientMedication.next_refill_date.isnot(None)
    ).all()
    
    for med in refill_due:
        days_overdue = (date.today() - med.next_refill_date).days
        alerts.append({
            "type": "refill_due",
            "medication_id": med.id,
            "patient": med.patient.full_name,
            "drug": med.drug.name,
            "message": f"Refill overdue by {days_overdue} days",
            "urgency": "high"
        })
    
    return {"alerts": alerts, "count": len(alerts)}

@app.get("/api/patient-medications/{medication_id}/chat")
async def get_medication_chat(
    medication_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    org_id = request.session.get("org_id")
    
    medication = db.query(models.PatientMedication).filter(
        models.PatientMedication.id == medication_id,
        models.PatientMedication.organization_id == org_id
    ).first()
    
    if not medication:
        raise HTTPException(404, "Medication record not found")
    
    messages = db.query(models.MedicationChat).filter(
        models.MedicationChat.medication_id == medication_id
    ).order_by(models.MedicationChat.created_at).all()
    
    return [{
        "id": m.id,
        "message": m.message,
        "is_from_patient": m.is_from_patient,
        "sender_name": m.patient.full_name if m.is_from_patient else (m.user.full_name if m.user else "Pharmacy"),
        "created_at": m.created_at.isoformat()
    } for m in messages]

@app.post("/api/patient-medications/{medication_id}/chat")
async def send_medication_chat(
    medication_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    data = await request.json()
    org_id = request.session.get("org_id")
    
    medication = db.query(models.PatientMedication).filter(
        models.PatientMedication.id == medication_id,
        models.PatientMedication.organization_id == org_id
    ).first()
    
    if not medication:
        raise HTTPException(404, "Medication record not found")
    
    try:
        chat = models.MedicationChat(
            id=str(uuid.uuid4()),
            medication_id=medication_id,
            organization_id=org_id,
            patient_id=medication.patient_id,
            user_id=user.id,
            message=data["message"],
            is_from_patient=False
        )
        db.add(chat)
        db.commit()
        
        return {"success": True, "id": chat.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(400, detail=str(e))

@app.get("/api/patient-reminders")
async def get_patient_reminders(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db),
    unread_only: bool = False
):
    org_id = request.session.get("org_id")
    
    query = db.query(models.MedicationReminder).filter(
        models.MedicationReminder.organization_id == org_id
    )
    
    if unread_only:
        query = query.filter(models.MedicationReminder.is_read == False)
    
    reminders = query.order_by(models.MedicationReminder.sent_at.desc()).limit(50).all()
    
    return [{
        "id": r.id,
        "patient": r.patient.full_name,
        "drug": r.medication.drug.name,
        "type": r.reminder_type.value if r.reminder_type else "general",
        "message": r.message,
        "sent_at": r.sent_at.isoformat(),
        "is_read": r.is_read
    } for r in reminders]

@app.put("/api/patient-reminders/{reminder_id}/read")
async def mark_reminder_read(
    reminder_id: str,
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    reminder = db.query(models.MedicationReminder).filter(
        models.MedicationReminder.id == reminder_id
    ).first()
    
    if not reminder:
        raise HTTPException(404, "Reminder not found")
    
    reminder.is_read = True
    reminder.read_at = datetime.now()
    db.commit()
    
    return {"success": True}

@app.post("/api/check-medication-alerts")
async def check_medication_alerts(
    request: Request,
    user: models.User = Depends(require_auth),
    db: Session = Depends(get_db)
):
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
                models.MedicationReminder.reminder_type == models.ReminderTypeEnum.low_stock,
                models.MedicationReminder.sent_at >= datetime.now() - timedelta(days=3)
            ).first()
            
            if not existing:
                create_reminder(db, med, models.ReminderTypeEnum.low_stock, 
                               f"⚠️ Low stock alert: Only {med.quantity_remaining} {med.unit} remaining. Please refill soon.")
                alerts_created += 1
        
        if med.next_refill_date and med.next_refill_date <= date.today():
            existing = db.query(models.MedicationReminder).filter(
                models.MedicationReminder.medication_id == med.id,
                models.MedicationReminder.reminder_type == models.ReminderTypeEnum.refill_due,
                models.MedicationReminder.sent_at >= datetime.now() - timedelta(days=3)
            ).first()
            
            if not existing:
                days_overdue = (date.today() - med.next_refill_date).days
                create_reminder(db, med, models.ReminderTypeEnum.refill_due, 
                               f"📅 Refill reminder: Medication refill is {days_overdue} days overdue. Please schedule a refill.")
                alerts_created += 1
    
    return {"success": True, "alerts_created": alerts_created}

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

@app.post("/api/categories")
async def add_category(request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    data = await request.json()
    category = models.Category(
        id=str(uuid.uuid4()),
        organization_id=request.session.get("org_id"),
        name=data["name"],
        description=data.get("description", "")
    )
    db.add(category)
    db.commit()
    return {"success": True, "id": category.id}

@app.get("/api/suppliers")
async def get_suppliers(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    suppliers = db.query(models.Supplier).filter(
        models.Supplier.organization_id == request.session.get("org_id")
    ).all()
    return [{"id": s.id, "name": s.name, "contact_person": s.contact_person, "email": s.email, "phone": s.phone} for s in suppliers]

@app.post("/api/suppliers")
async def add_supplier(request: Request, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    data = await request.json()
    supplier = models.Supplier(
        id=str(uuid.uuid4()),
        organization_id=request.session.get("org_id"),
        name=data["name"],
        contact_person=data.get("contact_person", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        address=data.get("address", "")
    )
    db.add(supplier)
    db.commit()
    return {"success": True, "id": supplier.id}

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
