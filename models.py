from sqlalchemy import Column, String, Text, Integer, Float, DateTime, Date, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import uuid
from datetime import datetime

def generate_uuid():
    return str(uuid.uuid4())

# Enums
class UserRoleEnum(str, enum.Enum):
    admin = "admin"
    pharmacist = "pharmacist"

class DrugFormEnum(str, enum.Enum):
    tablet = "tablet"
    capsule = "capsule"
    syrup = "syrup"
    injection = "injection"
    cream = "cream"
    ointment = "ointment"
    drops = "drops"
    inhaler = "inhaler"
    powder = "powder"
    other = "other"

class StrengthUnitEnum(str, enum.Enum):
    mg = "mg"
    g = "g"
    ml = "ml"
    mcg = "mcg"
    iu = "iu"
    percentage = "percentage"

class PaymentMethodEnum(str, enum.Enum):
    cash = "cash"
    card = "card"
    credit = "credit"
    mobile_payment = "mobile_payment"
    mpesa = "mpesa"  # Added M-Pesa

class PrescriptionStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    dispensed = "dispensed"
    cancelled = "cancelled"

class BatchStatusEnum(str, enum.Enum):
    active = "active"
    low_stock = "low_stock"
    expired = "expired"
    recalled = "recalled"

# New enums for patient monitoring
class MedicationStatusEnum(str, enum.Enum):
    active = "active"
    completed = "completed"
    discontinued = "discontinued"

class ReminderTypeEnum(str, enum.Enum):
    low_stock = "low_stock"
    refill_due = "refill_due"
    missed_dose = "missed_dose"
    general = "general"

# Multi-tenant Models
class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True)
    owner_email = Column(String(255), nullable=False)
    phone = Column(String(50))
    address = Column(Text)
    logo_url = Column(String(500))
    subscription_plan = Column(String(50), default="free")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    drugs = relationship("Drug", back_populates="organization", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="organization", cascade="all, delete-orphan")
    sales_orders = relationship("SalesOrder", back_populates="organization", cascade="all, delete-orphan")
    # Add relationships for new tables
    patient_medications = relationship("PatientMedication", back_populates="organization", cascade="all, delete-orphan")
    medication_refills = relationship("MedicationRefill", back_populates="organization", cascade="all, delete-orphan")
    medication_reminders = relationship("MedicationReminder", back_populates="organization", cascade="all, delete-orphan")
    medication_chats = relationship("MedicationChat", back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    username = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRoleEnum), nullable=False)
    is_active = Column(Boolean, default=True)
    phone = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    
    organization = relationship("Organization", back_populates="users")
    chat_sessions = relationship("AIChatSession", back_populates="user", cascade="all, delete-orphan")
    # Add relationship for medication chats
    medication_chats = relationship("MedicationChat", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    drugs = relationship("Drug", back_populates="category")

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    drugs = relationship("Drug", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")

class Drug(Base):
    __tablename__ = "drugs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    generic_name = Column(String(255))
    manufacturer = Column(String(255))
    form = Column(Enum(DrugFormEnum), nullable=False)
    strength = Column(Float)
    strength_unit = Column(Enum(StrengthUnitEnum))
    category_id = Column(String, ForeignKey("categories.id"))
    supplier_id = Column(String, ForeignKey("suppliers.id"))
    description = Column(Text)
    usage_instructions = Column(Text)
    side_effects = Column(Text)
    contraindications = Column(Text)
    price = Column(Float, nullable=False)
    reorder_level = Column(Integer, default=10)
    barcode = Column(String(100))
    image_url = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    
    organization = relationship("Organization", back_populates="drugs")
    category = relationship("Category", back_populates="drugs")
    supplier = relationship("Supplier", back_populates="drugs")
    inventory_batches = relationship("InventoryBatch", back_populates="drug")
    prescription_items = relationship("PrescriptionItem", back_populates="drug")
    sales_line_items = relationship("SalesLineItem", back_populates="drug")
    # Add relationship for patient medications
    patient_medications = relationship("PatientMedication", back_populates="drug")

class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    drug_id = Column(String, ForeignKey("drugs.id"), nullable=False)
    lot_number = Column(String(100), nullable=False)
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    expiry_date = Column(Date, nullable=False)
    purchase_date = Column(Date)
    cost_price = Column(Float)
    status = Column(Enum(BatchStatusEnum), default=BatchStatusEnum.active)
    created_at = Column(DateTime, server_default=func.now())
    
    drug = relationship("Drug", back_populates="inventory_batches")
    sales_line_items = relationship("SalesLineItem", back_populates="batch")

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    date_of_birth = Column(Date)
    allergies = Column(Text)
    medical_conditions = Column(Text)
    allow_credit = Column(Boolean, default=False)
    credit_limit = Column(Float, default=0)
    current_balance = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())
    
    organization = relationship("Organization", back_populates="customers")
    prescriptions = relationship("Prescription", back_populates="customer")
    sales_orders = relationship("SalesOrder", back_populates="customer")
    credit_payments = relationship("CreditPayment", back_populates="customer")
    # Add relationships for patient monitoring
    patient_medications = relationship("PatientMedication", back_populates="patient")
    medication_reminders = relationship("MedicationReminder", back_populates="patient")
    medication_chats = relationship("MedicationChat", back_populates="patient")

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    customer_id = Column(String, ForeignKey("customers.id"))
    doctor_name = Column(String(255))
    doctor_license = Column(String(100))
    prescription_date = Column(Date, nullable=False)
    image_url = Column(String(500))
    ocr_text = Column(Text)
    status = Column(Enum(PrescriptionStatusEnum), default=PrescriptionStatusEnum.pending)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    customer = relationship("Customer", back_populates="prescriptions")
    items = relationship("PrescriptionItem", back_populates="prescription")
    sales_orders = relationship("SalesOrder", back_populates="prescription")

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    prescription_id = Column(String, ForeignKey("prescriptions.id"), nullable=False)
    drug_id = Column(String, ForeignKey("drugs.id"))
    quantity = Column(Integer, nullable=False)
    dosage = Column(String(255))
    frequency = Column(String(255))
    duration = Column(String(255))
    dispensed = Column(Boolean, default=False)
    
    prescription = relationship("Prescription", back_populates="items")
    drug = relationship("Drug", back_populates="prescription_items")

class SalesOrder(Base):
    __tablename__ = "sales_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"))
    prescription_id = Column(String, ForeignKey("prescriptions.id"))
    sale_number = Column(String(100))
    sale_date = Column(DateTime, server_default=func.now())
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, default=0)
    discount = Column(Float, default=0)
    total = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethodEnum), nullable=False)
    amount_paid = Column(Float, default=0)
    balance = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    organization = relationship("Organization", back_populates="sales_orders")
    customer = relationship("Customer", back_populates="sales_orders")
    prescription = relationship("Prescription", back_populates="sales_orders")
    line_items = relationship("SalesLineItem", back_populates="sales_order")
    payments = relationship("Payment", back_populates="sale")  # Add relationship for payments

class SalesLineItem(Base):
    __tablename__ = "sales_line_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sales_order_id = Column(String, ForeignKey("sales_orders.id"), nullable=False)
    drug_id = Column(String, ForeignKey("drugs.id"), nullable=False)
    batch_id = Column(String, ForeignKey("inventory_batches.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)
    
    sales_order = relationship("SalesOrder", back_populates="line_items")
    drug = relationship("Drug", back_populates="sales_line_items")
    batch = relationship("InventoryBatch", back_populates="sales_line_items")

class CreditPayment(Base):
    __tablename__ = "credit_payments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    sale_id = Column(String, ForeignKey("sales_orders.id"))
    amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethodEnum), nullable=False)
    notes = Column(Text)
    payment_date = Column(DateTime, server_default=func.now())
    
    customer = relationship("Customer", back_populates="credit_payments")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"))
    sale_id = Column(String, ForeignKey("sales_orders.id"))
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, default=datetime.now().date)
    payment_method = Column(Enum(PaymentMethodEnum), nullable=False)
    reference = Column(String(100))
    status = Column(String(50), default="completed")
    transaction_id = Column(String(100))
    notes = Column(Text)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    organization = relationship("Organization", backref="payments")
    customer = relationship("Customer", backref="payments")
    sale = relationship("SalesOrder", back_populates="payments")
    user = relationship("User", backref="payments")

class AIChatSession(Base):
    __tablename__ = "ai_chat_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default="New Conversation")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("AIChatMessage", back_populates="session")

class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("ai_chat_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    session = relationship("AIChatSession", back_populates="messages")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    order_date = Column(Date, nullable=False)
    expected_delivery = Column(Date)
    status = Column(String(50), default="pending")
    total_amount = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    purchase_order_id = Column(String, ForeignKey("purchase_orders.id"), nullable=False)
    drug_id = Column(String, ForeignKey("drugs.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)
    line_total = Column(Float, nullable=False)
    
    purchase_order = relationship("PurchaseOrder", back_populates="items")

# ==================== NEW PATIENT MEDICATION MONITORING TABLES ====================

class PatientMedication(Base):
    """Track patients on regular medications"""
    __tablename__ = "patient_medications"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    patient_id = Column(String, ForeignKey("customers.id"), nullable=False)
    drug_id = Column(String, ForeignKey("drugs.id"), nullable=False)
    
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
    status = Column(Enum(MedicationStatusEnum), default=MedicationStatusEnum.active)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    organization = relationship("Organization", back_populates="patient_medications")
    patient = relationship("Customer", back_populates="patient_medications")
    drug = relationship("Drug", back_populates="patient_medications")
    user = relationship("User", backref="created_medications")
    refills = relationship("MedicationRefill", back_populates="medication", cascade="all, delete-orphan")
    reminders = relationship("MedicationReminder", back_populates="medication", cascade="all, delete-orphan")
    chats = relationship("MedicationChat", back_populates="medication", cascade="all, delete-orphan")

class MedicationRefill(Base):
    """Track medication refills"""
    __tablename__ = "medication_refills"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    medication_id = Column(String, ForeignKey("patient_medications.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    
    refill_date = Column(Date, nullable=False)
    quantity_refilled = Column(Integer, nullable=False)
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    medication = relationship("PatientMedication", back_populates="refills")
    organization = relationship("Organization", back_populates="medication_refills")
    user = relationship("User", backref="medication_refills")

class MedicationReminder(Base):
    """Track reminders sent to patients"""
    __tablename__ = "medication_reminders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    medication_id = Column(String, ForeignKey("patient_medications.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    patient_id = Column(String, ForeignKey("customers.id"), nullable=False)
    
    reminder_type = Column(Enum(ReminderTypeEnum), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # For SMS/Email tracking
    sms_sent = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    
    # Relationships
    medication = relationship("PatientMedication", back_populates="reminders")
    organization = relationship("Organization", back_populates="medication_reminders")
    patient = relationship("Customer", back_populates="medication_reminders")

class MedicationChat(Base):
    """Chat between pharmacy and patient about medication"""
    __tablename__ = "medication_chats"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    medication_id = Column(String, ForeignKey("patient_medications.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    patient_id = Column(String, ForeignKey("customers.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    message = Column(Text, nullable=False)
    is_from_patient = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    medication = relationship("PatientMedication", back_populates="chats")
    organization = relationship("Organization", back_populates="medication_chats")
    patient = relationship("Customer", back_populates="medication_chats")
    user = relationship("User", back_populates="medication_chats")
