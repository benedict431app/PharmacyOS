from sqlalchemy import Column, String, Text, Integer, Numeric, DateTime, Date, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import uuid

def generate_uuid():
    return str(uuid.uuid4())

# Enums
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
    insurance = "insurance"
    mobile_payment = "mobile_payment"

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

# Models
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    drugs = relationship("Drug", back_populates="category")

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
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
    name = Column(String(255), nullable=False)
    generic_name = Column(String(255))
    manufacturer = Column(String(255))
    form = Column(Enum(DrugFormEnum), nullable=False)
    strength = Column(Numeric(10, 2))
    strength_unit = Column(Enum(StrengthUnitEnum))
    category_id = Column(String, ForeignKey("categories.id"))
    supplier_id = Column(String, ForeignKey("suppliers.id"))
    description = Column(Text)
    usage_instructions = Column(Text)
    side_effects = Column(Text)
    contraindications = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    reorder_level = Column(Integer, default=10)
    barcode = Column(String(100))
    image_url = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    
    category = relationship("Category", back_populates="drugs")
    supplier = relationship("Supplier", back_populates="drugs")
    inventory_batches = relationship("InventoryBatch", back_populates="drug")
    prescription_items = relationship("PrescriptionItem", back_populates="drug")
    sales_line_items = relationship("SalesLineItem", back_populates="drug")

class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    drug_id = Column(String, ForeignKey("drugs.id"), nullable=False)
    lot_number = Column(String(100), nullable=False)
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    expiry_date = Column(Date, nullable=False)
    purchase_date = Column(Date)
    cost_price = Column(Numeric(10, 2))
    status = Column(Enum(BatchStatusEnum), default=BatchStatusEnum.active)
    created_at = Column(DateTime, server_default=func.now())
    
    drug = relationship("Drug", back_populates="inventory_batches")
    sales_line_items = relationship("SalesLineItem", back_populates="batch")

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    date_of_birth = Column(Date)
    allergies = Column(Text)
    medical_conditions = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    prescriptions = relationship("Prescription", back_populates="customer")
    sales_orders = relationship("SalesOrder", back_populates="customer")

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
    customer_id = Column(String, ForeignKey("customers.id"))
    prescription_id = Column(String, ForeignKey("prescriptions.id"))
    sale_date = Column(DateTime, server_default=func.now())
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax = Column(Numeric(10, 2), default=0)
    discount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethodEnum), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    customer = relationship("Customer", back_populates="sales_orders")
    prescription = relationship("Prescription", back_populates="sales_orders")
    line_items = relationship("SalesLineItem", back_populates="sales_order")

class SalesLineItem(Base):
    __tablename__ = "sales_line_items"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sales_order_id = Column(String, ForeignKey("sales_orders.id"), nullable=False)
    drug_id = Column(String, ForeignKey("drugs.id"), nullable=False)
    batch_id = Column(String, ForeignKey("inventory_batches.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)
    
    sales_order = relationship("SalesOrder", back_populates="line_items")
    drug = relationship("Drug", back_populates="sales_line_items")
    batch = relationship("InventoryBatch", back_populates="sales_line_items")

class AIChatSession(Base):
    __tablename__ = "ai_chat_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(255), default="New Conversation")
    created_at = Column(DateTime, server_default=func.now())
    
    messages = relationship("AIChatMessage", back_populates="session")

class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("ai_chat_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    
    session = relationship("AIChatSession", back_populates="messages")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    order_date = Column(Date, nullable=False)
    expected_delivery = Column(Date)
    status = Column(String(50), default="pending")
    total_amount = Column(Numeric(10, 2))
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
    unit_cost = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)
    
    purchase_order = relationship("PurchaseOrder", back_populates="items")

class DemandForecast(Base):
    __tablename__ = "demand_forecasts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    drug_id = Column(String, ForeignKey("drugs.id"), nullable=False)
    forecast_date = Column(Date, nullable=False)
    forecasted_units = Column(Integer, nullable=False)
    confidence_level = Column(Numeric(5, 2))
    model = Column(String(100), default="simple_average")
    horizon = Column(Integer, default=30)
    historical_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
