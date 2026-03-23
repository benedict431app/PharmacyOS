from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, Text, ForeignKey, Enum, Numeric, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

# Enums
class UserRoleEnum:
    admin = "admin"
    pharmacist = "pharmacist"
    cashier = "cashier"

class DrugFormEnum:
    tablet = "tablet"
    capsule = "capsule"
    syrup = "syrup"
    injection = "injection"
    cream = "cream"
    drops = "drops"

class StrengthUnitEnum:
    mg = "mg"
    g = "g"
    ml = "ml"
    mcg = "mcg"

class BatchStatusEnum:
    active = "active"
    empty = "empty"
    expired = "expired"
    recalled = "recalled"

class PaymentMethodEnum:
    cash = "cash"
    card = "card"
    mpesa = "mpesa"
    credit = "credit"
    mobile_payment = "mobile_payment"

class SalesOrderStatusEnum:
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"
    refunded = "refunded"

# ==================== ORGANIZATION ====================
class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    owner_email = Column(String(200), nullable=False)
    phone = Column(String(50))
    address = Column(Text)
    subscription_plan = Column(String(50), default="free")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==================== USERS ====================
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    username = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="pharmacist")
    is_active = Column(Boolean, default=True)
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", backref="users")

# ==================== CATEGORIES ====================
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", backref="categories")

# ==================== SUPPLIERS ====================
class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    contact_person = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", backref="suppliers")

# ==================== DRUGS ====================
class Drug(Base):
    __tablename__ = "drugs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    generic_name = Column(String(200))
    manufacturer = Column(String(200))
    form = Column(String(50))
    strength = Column(Float)
    strength_unit = Column(String(20))
    category_id = Column(String(36), ForeignKey("categories.id"))
    supplier_id = Column(String(36), ForeignKey("suppliers.id"))
    description = Column(Text)
    usage_instructions = Column(Text)
    side_effects = Column(Text)
    contraindications = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    reorder_level = Column(Integer, default=50)
    barcode = Column(String(100), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", backref="drugs")
    category = relationship("Category", backref="drugs")
    supplier = relationship("Supplier", backref="drugs")

# ==================== INVENTORY BATCHES ====================
class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    drug_id = Column(String(36), ForeignKey("drugs.id"), nullable=False)
    lot_number = Column(String(100), nullable=False)
    quantity_on_hand = Column(Integer, default=0)
    expiry_date = Column(Date)
    purchase_date = Column(Date)
    cost_price = Column(Numeric(10, 2))
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    drug = relationship("Drug", backref="batches")

# ==================== CUSTOMERS ====================
class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(200))
    phone = Column(String(50))
    address = Column(Text)
    date_of_birth = Column(Date)
    allergies = Column(Text)
    medical_conditions = Column(Text)
    allow_credit = Column(Boolean, default=False)
    credit_limit = Column(Numeric(10, 2), default=0)
    current_balance = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", backref="customers")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

# ==================== SALES ORDERS ====================
class SalesOrder(Base):
    __tablename__ = "sales_orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"))
    sale_number = Column(String(100), unique=True, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax = Column(Numeric(10, 2), default=0)
    discount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    amount_paid = Column(Numeric(10, 2), default=0)
    balance = Column(Numeric(10, 2), default=0)
    status = Column(String(50), default="completed")
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", backref="sales_orders")
    customer = relationship("Customer", backref="sales_orders")
    user = relationship("User", backref="sales_orders")

# ==================== SALES LINE ITEMS ====================
class SalesLineItem(Base):
    __tablename__ = "sales_line_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sales_order_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=False)
    drug_id = Column(String(36), ForeignKey("drugs.id"), nullable=False)
    batch_id = Column(String(36), ForeignKey("inventory_batches.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sales_order = relationship("SalesOrder", backref="items")
    drug = relationship("Drug", backref="sales_items")
    batch = relationship("InventoryBatch", backref="sales_items")

# ==================== PAYMENTS ====================
class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"))
    sale_id = Column(String(36), ForeignKey("sales_orders.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, default=datetime.now().date)
    payment_method = Column(String(50), nullable=False)
    reference = Column(String(100))
    status = Column(String(50), default="completed")
    transaction_id = Column(String(100))
    notes = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    organization = relationship("Organization", backref="payments")
    customer = relationship("Customer", backref="payments")
    sale = relationship("SalesOrder", backref="payments")
    user = relationship("User", backref="payments")

# ==================== AI CHAT SESSIONS ====================
class AIChatSession(Base):
    __tablename__ = "ai_chat_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", backref="chat_sessions")

class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("ai_chat_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("AIChatSession", backref="messages")

# ==================== PATIENT MEDICATION MONITORING ====================
class PatientMedication(Base):
    __tablename__ = "patient_medications"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    patient_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    drug_id = Column(String(36), ForeignKey("drugs.id"), nullable=False)
    
    # Medication details
    dosage_instructions = Column(Text, nullable=False)
    quantity_given = Column(Integer, nullable=False)
    quantity_remaining = Column(Integer, nullable=False)
    unit = Column(String(20), default="tablets")
    
    # Schedule
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    next_refill_date = Column(Date, nullable=True)
    last_refill_date = Column(Date, nullable=True)
    
    # Reminder settings
    reminder_days_before = Column(Integer, default=3)
    low_stock_threshold = Column(Integer, default=10)
    
    # Status
    status = Column(String(50), default="active")
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id"))
    
    # Relationships
    organization = relationship("Organization", backref="patient_medications")
    patient = relationship("Customer", backref="patient_medications")
    drug = relationship("Drug", backref="patient_medications")
    user = relationship("User", backref="patient_medications")

class MedicationRefill(Base):
    __tablename__ = "medication_refills"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medication_id = Column(String(36), ForeignKey("patient_medications.id"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    
    refill_date = Column(Date, nullable=False)
    quantity_refilled = Column(Integer, nullable=False)
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    medication = relationship("PatientMedication", backref="refills")
    organization = relationship("Organization", backref="medication_refills")
    user = relationship("User", backref="medication_refills")

class MedicationReminder(Base):
    __tablename__ = "medication_reminders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medication_id = Column(String(36), ForeignKey("patient_medications.id"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    patient_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    
    reminder_type = Column(String(50), nullable=False)  # low_stock, refill_due, missed_dose, general
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # For SMS/Email tracking
    sms_sent = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    
    # Relationships
    medication = relationship("PatientMedication", backref="reminders")
    organization = relationship("Organization", backref="medication_reminders")
    patient = relationship("Customer", backref="medication_reminders")

class MedicationChat(Base):
    __tablename__ = "medication_chats"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medication_id = Column(String(36), ForeignKey("patient_medications.id"), nullable=False)
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    patient_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    message = Column(Text, nullable=False)
    is_from_patient = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    medication = relationship("PatientMedication", backref="chats")
    organization = relationship("Organization", backref="medication_chats")
    patient = relationship("Customer", backref="medication_chats")
    user = relationship("User", backref="medication_chats")
