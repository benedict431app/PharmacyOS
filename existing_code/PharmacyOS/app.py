from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os
from datetime import datetime, date
from decimal import Decimal

from database import engine, get_db, Base
import models
import crud
from openai_service import OpenAIService

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PharmaCare - Pharmacy Management System")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize OpenAI service
openai_service = OpenAIService()

# Helper function to add common template context
def get_template_context(request: Request, **kwargs):
    return {"request": request, **kwargs}

# ==================== HOME/DASHBOARD ====================
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = crud.get_dashboard_stats(db)
    alerts = crud.get_alerts(db)
    sales_trend = crud.get_sales_trend(db, days=7)
    
    return templates.TemplateResponse(
        "dashboard.html",
        get_template_context(request, stats=stats, alerts=alerts, sales_trend=sales_trend)
    )

# ==================== INVENTORY ====================
@app.get("/inventory", response_class=HTMLResponse)
async def inventory_list(request: Request, search: Optional[str] = None, db: Session = Depends(get_db)):
    drugs = crud.get_drugs(db, search=search)
    categories = crud.get_categories(db)
    suppliers = crud.get_suppliers(db)
    
    return templates.TemplateResponse(
        "inventory/list.html",
        get_template_context(request, drugs=drugs, categories=categories, suppliers=suppliers, search=search or "")
    )

@app.get("/inventory/add", response_class=HTMLResponse)
async def inventory_add_form(request: Request, db: Session = Depends(get_db)):
    categories = crud.get_categories(db)
    suppliers = crud.get_suppliers(db)
    
    return templates.TemplateResponse(
        "inventory/form.html",
        get_template_context(request, categories=categories, suppliers=suppliers, drug=None)
    )

@app.post("/inventory/add")
async def inventory_add(
    request: Request,
    name: str = Form(...),
    generic_name: Optional[str] = Form(None),
    manufacturer: Optional[str] = Form(None),
    form: str = Form(...),
    strength: Optional[str] = Form(None),
    strength_unit: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    supplier_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    usage_instructions: Optional[str] = Form(None),
    side_effects: Optional[str] = Form(None),
    price: str = Form(...),
    reorder_level: int = Form(10),
    barcode: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    drug_data = {
        "name": name,
        "generic_name": generic_name,
        "manufacturer": manufacturer,
        "form": form,
        "strength": Decimal(strength) if strength else None,
        "strength_unit": strength_unit,
        "category_id": category_id if category_id else None,
        "supplier_id": supplier_id if supplier_id else None,
        "description": description,
        "usage_instructions": usage_instructions,
        "side_effects": side_effects,
        "price": Decimal(price),
        "reorder_level": reorder_level,
        "barcode": barcode,
    }
    
    crud.create_drug(db, drug_data)
    return RedirectResponse(url="/inventory", status_code=303)

@app.get("/inventory/edit/{drug_id}", response_class=HTMLResponse)
async def inventory_edit_form(request: Request, drug_id: str, db: Session = Depends(get_db)):
    drug = crud.get_drug(db, drug_id)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    
    categories = crud.get_categories(db)
    suppliers = crud.get_suppliers(db)
    
    return templates.TemplateResponse(
        "inventory/form.html",
        get_template_context(request, categories=categories, suppliers=suppliers, drug=drug)
    )

@app.post("/inventory/edit/{drug_id}")
async def inventory_edit(
    request: Request,
    drug_id: str,
    name: str = Form(...),
    generic_name: Optional[str] = Form(None),
    manufacturer: Optional[str] = Form(None),
    form: str = Form(...),
    strength: Optional[str] = Form(None),
    strength_unit: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    supplier_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    usage_instructions: Optional[str] = Form(None),
    side_effects: Optional[str] = Form(None),
    price: str = Form(...),
    reorder_level: int = Form(10),
    barcode: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    drug_data = {
        "name": name,
        "generic_name": generic_name,
        "manufacturer": manufacturer,
        "form": form,
        "strength": Decimal(strength) if strength else None,
        "strength_unit": strength_unit,
        "category_id": category_id if category_id else None,
        "supplier_id": supplier_id if supplier_id else None,
        "description": description,
        "usage_instructions": usage_instructions,
        "side_effects": side_effects,
        "price": Decimal(price),
        "reorder_level": reorder_level,
        "barcode": barcode,
    }
    
    crud.update_drug(db, drug_id, drug_data)
    return RedirectResponse(url="/inventory", status_code=303)

@app.post("/inventory/delete/{drug_id}")
async def inventory_delete(drug_id: str, db: Session = Depends(get_db)):
    crud.delete_drug(db, drug_id)
    return RedirectResponse(url="/inventory", status_code=303)

# ==================== SALES/POS ====================
@app.get("/sales", response_class=HTMLResponse)
async def sales_pos(request: Request, db: Session = Depends(get_db)):
    drugs = crud.get_drugs(db)
    customers = crud.get_customers(db)
    
    return templates.TemplateResponse(
        "sales/pos.html",
        get_template_context(request, drugs=drugs, customers=customers)
    )

@app.post("/api/sales")
async def create_sale(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    sale = crud.create_sale(db, data)
    return JSONResponse({"success": True, "sale_id": sale.id})

# ==================== CUSTOMERS ====================
@app.get("/customers", response_class=HTMLResponse)
async def customers_list(request: Request, search: Optional[str] = None, db: Session = Depends(get_db)):
    customers = crud.get_customers(db, search=search)
    
    return templates.TemplateResponse(
        "customers/list.html",
        get_template_context(request, customers=customers, search=search or "")
    )

@app.get("/customers/add", response_class=HTMLResponse)
async def customers_add_form(request: Request):
    return templates.TemplateResponse(
        "customers/form.html",
        get_template_context(request, customer=None)
    )

@app.post("/customers/add")
async def customers_add(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    date_of_birth: Optional[date] = Form(None),
    allergies: Optional[str] = Form(None),
    medical_conditions: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    customer_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "address": address,
        "date_of_birth": date_of_birth,
        "allergies": allergies,
        "medical_conditions": medical_conditions,
    }
    
    crud.create_customer(db, customer_data)
    return RedirectResponse(url="/customers", status_code=303)

# ==================== PRESCRIPTIONS ====================
@app.get("/prescriptions", response_class=HTMLResponse)
async def prescriptions_list(request: Request, db: Session = Depends(get_db)):
    prescriptions = crud.get_prescriptions(db)
    
    return templates.TemplateResponse(
        "prescriptions/list.html",
        get_template_context(request, prescriptions=prescriptions)
    )

@app.get("/prescriptions/upload", response_class=HTMLResponse)
async def prescriptions_upload_form(request: Request, db: Session = Depends(get_db)):
    customers = crud.get_customers(db)
    
    return templates.TemplateResponse(
        "prescriptions/upload.html",
        get_template_context(request, customers=customers)
    )

@app.post("/prescriptions/upload")
async def prescriptions_upload(
    request: Request,
    customer_id: Optional[str] = Form(None),
    doctor_name: Optional[str] = Form(None),
    doctor_license: Optional[str] = Form(None),
    prescription_date: date = Form(...),
    notes: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # Save image and perform OCR if uploaded
    image_url = None
    ocr_text = None
    
    if image:
        # Save uploaded file
        upload_dir = "static/uploads/prescriptions"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = f"{upload_dir}/{datetime.now().timestamp()}_{image.filename}"
        
        with open(file_path, "wb") as f:
            content = await image.read()
            f.write(content)
        
        image_url = f"/{file_path}"
        
        # Perform OCR using OpenAI Vision
        ocr_text = await openai_service.extract_text_from_image(file_path)
    
    prescription_data = {
        "customer_id": customer_id if customer_id else None,
        "doctor_name": doctor_name,
        "doctor_license": doctor_license,
        "prescription_date": prescription_date,
        "image_url": image_url,
        "ocr_text": ocr_text,
        "notes": notes,
        "status": "pending",
    }
    
    crud.create_prescription(db, prescription_data)
    return RedirectResponse(url="/prescriptions", status_code=303)

# ==================== AI ASSISTANT ====================
@app.get("/ai-assistant", response_class=HTMLResponse)
async def ai_assistant(request: Request, session_id: Optional[str] = None, db: Session = Depends(get_db)):
    messages = []
    if session_id:
        messages = crud.get_chat_messages(db, session_id)
    
    return templates.TemplateResponse(
        "ai_assistant.html",
        get_template_context(request, session_id=session_id, messages=messages)
    )

@app.post("/api/ai/chat")
async def ai_chat(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    message = data.get("message")
    session_id = data.get("sessionId")
    
    # Create session if not exists
    if not session_id:
        session = crud.create_chat_session(db, {"title": message[:50]})
        session_id = session.id
    
    # Save user message
    crud.create_chat_message(db, {
        "session_id": session_id,
        "role": "user",
        "content": message
    })
    
    # Get AI response
    ai_response = await openai_service.get_drug_information(message)
    
    # Save AI message
    crud.create_chat_message(db, {
        "session_id": session_id,
        "role": "assistant",
        "content": ai_response
    })
    
    return JSONResponse({
        "sessionId": session_id,
        "response": ai_response
    })

# ==================== SUPPLIERS ====================
@app.get("/suppliers", response_class=HTMLResponse)
async def suppliers_list(request: Request, db: Session = Depends(get_db)):
    suppliers = crud.get_suppliers(db)
    
    return templates.TemplateResponse(
        "suppliers/list.html",
        get_template_context(request, suppliers=suppliers)
    )

# ==================== ANALYTICS ====================
@app.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request, db: Session = Depends(get_db)):
    revenue_stats = crud.get_revenue_stats(db)
    top_drugs = crud.get_top_selling_drugs(db, limit=10)
    category_analytics = crud.get_sales_by_category(db)
    
    return templates.TemplateResponse(
        "analytics.html",
        get_template_context(
            request,
            revenue_stats=revenue_stats,
            top_drugs=top_drugs,
            category_analytics=category_analytics
        )
    )

# ==================== ALERTS ====================
@app.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request, db: Session = Depends(get_db)):
    alerts = crud.get_alerts(db)
    expiring_drugs = crud.get_expiring_drugs(db, days=30)
    low_stock_drugs = crud.get_low_stock_drugs(db)
    
    return templates.TemplateResponse(
        "alerts.html",
        get_template_context(
            request,
            alerts=alerts,
            expiring_drugs=expiring_drugs,
            low_stock_drugs=low_stock_drugs
        )
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
