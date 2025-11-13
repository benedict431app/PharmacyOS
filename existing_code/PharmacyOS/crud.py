from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta, date
from decimal import Decimal
import models

# ==================== DRUGS/INVENTORY ====================
def get_drugs(db: Session, search: str = None):
    query = db.query(models.Drug).options(
        joinedload(models.Drug.category),
        joinedload(models.Drug.supplier)
    )
    
    if search:
        query = query.filter(
            or_(
                models.Drug.name.ilike(f"%{search}%"),
                models.Drug.generic_name.ilike(f"%{search}%")
            )
        )
    
    drugs = query.all()
    
    # Add total stock calculation
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand))\
            .filter(models.InventoryBatch.drug_id == drug.id)\
            .scalar() or 0
        drug.total_stock = total_stock
    
    return drugs

def get_drug(db: Session, drug_id: str):
    return db.query(models.Drug).filter(models.Drug.id == drug_id).first()

def create_drug(db: Session, drug_data: dict):
    drug = models.Drug(**drug_data)
    db.add(drug)
    db.commit()
    db.refresh(drug)
    return drug

def update_drug(db: Session, drug_id: str, drug_data: dict):
    drug = db.query(models.Drug).filter(models.Drug.id == drug_id).first()
    if drug:
        for key, value in drug_data.items():
            setattr(drug, key, value)
        db.commit()
        db.refresh(drug)
    return drug

def delete_drug(db: Session, drug_id: str):
    drug = db.query(models.Drug).filter(models.Drug.id == drug_id).first()
    if drug:
        db.delete(drug)
        db.commit()
    return drug

# ==================== CATEGORIES ====================
def get_categories(db: Session):
    return db.query(models.Category).all()

def create_category(db: Session, name: str, description: str = None):
    category = models.Category(name=name, description=description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

# ==================== SUPPLIERS ====================
def get_suppliers(db: Session):
    return db.query(models.Supplier).all()

def create_supplier(db: Session, supplier_data: dict):
    supplier = models.Supplier(**supplier_data)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

# ==================== CUSTOMERS ====================
def get_customers(db: Session, search: str = None):
    query = db.query(models.Customer)
    
    if search:
        query = query.filter(
            or_(
                models.Customer.first_name.ilike(f"%{search}%"),
                models.Customer.last_name.ilike(f"%{search}%"),
                models.Customer.email.ilike(f"%{search}%"),
                models.Customer.phone.ilike(f"%{search}%")
            )
        )
    
    return query.all()

def create_customer(db: Session, customer_data: dict):
    customer = models.Customer(**customer_data)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

# ==================== PRESCRIPTIONS ====================
def get_prescriptions(db: Session):
    return db.query(models.Prescription)\
        .options(joinedload(models.Prescription.customer))\
        .order_by(desc(models.Prescription.created_at))\
        .all()

def create_prescription(db: Session, prescription_data: dict):
    prescription = models.Prescription(**prescription_data)
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription

# ==================== SALES ====================
def create_sale(db: Session, sale_data: dict):
    # Create sales order
    line_items_data = sale_data.pop("lineItems", [])
    
    sales_order = models.SalesOrder(**sale_data)
    db.add(sales_order)
    db.flush()
    
    # Create line items and deduct from inventory
    for item_data in line_items_data:
        line_item = models.SalesLineItem(
            sales_order_id=sales_order.id,
            **item_data
        )
        db.add(line_item)
        
        # Deduct from inventory
        batches = db.query(models.InventoryBatch)\
            .filter(
                models.InventoryBatch.drug_id == item_data["drug_id"],
                models.InventoryBatch.status == models.BatchStatusEnum.active,
                models.InventoryBatch.quantity_on_hand > 0
            )\
            .order_by(models.InventoryBatch.expiry_date)\
            .all()
        
        remaining_qty = item_data["quantity"]
        for batch in batches:
            if remaining_qty <= 0:
                break
            
            deduct = min(batch.quantity_on_hand, remaining_qty)
            batch.quantity_on_hand -= deduct
            remaining_qty -= deduct
            
            if batch.quantity_on_hand == 0:
                batch.status = models.BatchStatusEnum.low_stock
    
    db.commit()
    db.refresh(sales_order)
    return sales_order

def get_sales_trend(db: Session, days: int = 7):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    sales = db.query(
        func.date(models.SalesOrder.sale_date).label("date"),
        func.sum(models.SalesOrder.total).label("sales")
    ).filter(
        models.SalesOrder.sale_date >= start_date
    ).group_by(
        func.date(models.SalesOrder.sale_date)
    ).all()
    
    return [{"date": str(s.date), "sales": float(s.sales or 0)} for s in sales]

# ==================== AI CHAT ====================
def create_chat_session(db: Session, session_data: dict):
    session = models.AIChatSession(**session_data)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_chat_messages(db: Session, session_id: str):
    return db.query(models.AIChatMessage)\
        .filter(models.AIChatMessage.session_id == session_id)\
        .order_by(models.AIChatMessage.timestamp)\
        .all()

def create_chat_message(db: Session, message_data: dict):
    message = models.AIChatMessage(**message_data)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

# ==================== ANALYTICS & DASHBOARD ====================
def get_dashboard_stats(db: Session):
    total_drugs = db.query(func.count(models.Drug.id)).scalar() or 0
    
    # Today's sales
    today = datetime.now().date()
    today_sales = db.query(func.sum(models.SalesOrder.total))\
        .filter(func.date(models.SalesOrder.sale_date) == today)\
        .scalar() or Decimal(0)
    
    # Low stock items
    low_stock_count = 0
    drugs = db.query(models.Drug).all()
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand))\
            .filter(models.InventoryBatch.drug_id == drug.id)\
            .scalar() or 0
        if total_stock <= (drug.reorder_level or 10):
            low_stock_count += 1
    
    # Expiring soon (30 days)
    thirty_days = datetime.now().date() + timedelta(days=30)
    expiring_soon = db.query(func.count(models.InventoryBatch.id))\
        .filter(
            models.InventoryBatch.expiry_date <= thirty_days,
            models.InventoryBatch.expiry_date >= datetime.now().date()
        )\
        .scalar() or 0
    
    return {
        "totalDrugs": total_drugs,
        "todaySales": float(today_sales),
        "lowStockCount": low_stock_count,
        "expiringSoon": expiring_soon
    }

def get_alerts(db: Session):
    alerts = []
    
    # Low stock alerts
    drugs = db.query(models.Drug).all()
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand))\
            .filter(models.InventoryBatch.drug_id == drug.id)\
            .scalar() or 0
        
        if total_stock == 0:
            alerts.append({
                "id": f"stock_{drug.id}",
                "severity": "critical",
                "title": "Out of Stock",
                "message": f"{drug.name} is out of stock"
            })
        elif total_stock <= (drug.reorder_level or 10):
            alerts.append({
                "id": f"stock_{drug.id}",
                "severity": "warning",
                "title": "Low Stock",
                "message": f"{drug.name} is running low (Stock: {total_stock})"
            })
    
    # Expiring drugs
    thirty_days = datetime.now().date() + timedelta(days=30)
    expiring_batches = db.query(models.InventoryBatch)\
        .options(joinedload(models.InventoryBatch.drug))\
        .filter(
            models.InventoryBatch.expiry_date <= thirty_days,
            models.InventoryBatch.expiry_date >= datetime.now().date()
        )\
        .all()
    
    for batch in expiring_batches[:5]:  # Limit to 5
        days_left = (batch.expiry_date - datetime.now().date()).days
        alerts.append({
            "id": f"expiry_{batch.id}",
            "severity": "warning" if days_left > 7 else "critical",
            "title": "Expiring Soon",
            "message": f"{batch.drug.name} (Lot: {batch.lot_number}) expires in {days_left} days"
        })
    
    return alerts[:10]  # Return top 10 alerts

def get_low_stock_drugs(db: Session):
    drugs = db.query(models.Drug).all()
    low_stock = []
    
    for drug in drugs:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand))\
            .filter(models.InventoryBatch.drug_id == drug.id)\
            .scalar() or 0
        
        if total_stock <= (drug.reorder_level or 10):
            drug.total_stock = total_stock
            low_stock.append(drug)
    
    return low_stock

def get_expiring_drugs(db: Session, days: int = 30):
    target_date = datetime.now().date() + timedelta(days=days)
    
    return db.query(models.InventoryBatch)\
        .options(joinedload(models.InventoryBatch.drug))\
        .filter(
            models.InventoryBatch.expiry_date <= target_date,
            models.InventoryBatch.expiry_date >= datetime.now().date()
        )\
        .order_by(models.InventoryBatch.expiry_date)\
        .all()

def get_revenue_stats(db: Session):
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    total_revenue = db.query(func.sum(models.SalesOrder.total))\
        .filter(models.SalesOrder.sale_date >= thirty_days_ago)\
        .scalar() or Decimal(0)
    
    products_sold = db.query(func.sum(models.SalesLineItem.quantity))\
        .join(models.SalesOrder)\
        .filter(models.SalesOrder.sale_date >= thirty_days_ago)\
        .scalar() or 0
    
    num_transactions = db.query(func.count(models.SalesOrder.id))\
        .filter(models.SalesOrder.sale_date >= thirty_days_ago)\
        .scalar() or 0
    
    avg_transaction = float(total_revenue) / num_transactions if num_transactions > 0 else 0
    
    return {
        "total": float(total_revenue),
        "productsSold": products_sold,
        "avgTransaction": avg_transaction
    }

def get_top_selling_drugs(db: Session, limit: int = 10):
    results = db.query(
        models.Drug.name.label("drugName"),
        func.sum(models.SalesLineItem.quantity).label("unitsSold"),
        func.sum(models.SalesLineItem.line_total).label("revenue")
    ).join(
        models.SalesLineItem
    ).group_by(
        models.Drug.name
    ).order_by(
        desc(func.sum(models.SalesLineItem.quantity))
    ).limit(limit).all()
    
    return [
        {
            "drugName": r.drugName,
            "unitsSold": r.unitsSold,
            "revenue": float(r.revenue or 0)
        }
        for r in results
    ]

def get_sales_by_category(db: Session):
    results = db.query(
        models.Category.name.label("category"),
        func.sum(models.SalesLineItem.line_total).label("sales")
    ).join(
        models.Drug
    ).join(
        models.SalesLineItem
    ).filter(
        models.Drug.category_id == models.Category.id
    ).group_by(
        models.Category.name
    ).all()
    
    return [
        {
            "category": r.category,
            "sales": float(r.sales or 0)
        }
        for r in results
    ]
