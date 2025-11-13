from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Optional, List
import os
from datetime import datetime, date
from decimal import Decimal

from database import engine, get_db, Base
import models
from openai_service import OpenAIService

#Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PharmaSaaS - Pharmacy Management System")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "your-secret-key-here"))

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize OpenAI service
openai_service = OpenAIService()

# Helper function to get current user
def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    
    user = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.is_active == True
    ).first()
    return user

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

# ==================== LANDING PAGE ====================
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page for pharmacy sign-up"""
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>PharmaSaaS - Pharmacy Management System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 80px 20px; text-align: center; }
        .hero h1 { font-size: 3em; margin-bottom: 20px; }
        .hero p { font-size: 1.3em; margin-bottom: 30px; opacity: 0.95; }
        .cta-btn { background: white; color: #667eea; padding: 15px 40px; border-radius: 50px; text-decoration: none; font-size: 1.1em; font-weight: bold; display: inline-block; transition: transform 0.3s; }
        .cta-btn:hover { transform: scale(1.05); }
        .features { padding: 60px 20px; max-width: 1200px; margin: 0 auto; }
        .features h2 { text-align: center; font-size: 2.5em; margin-bottom: 50px; color: #333; }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; }
        .feature-card { background: #f8f9fa; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .feature-card h3 { color: #667eea; margin-bottom: 15px; font-size: 1.5em; }
        .feature-card p { color: #666; line-height: 1.6; }
        .pricing { background: #f8f9fa; padding: 60px 20px; }
        .pricing h2 { text-align: center; font-size: 2.5em; margin-bottom: 50px; color: #333; }
        .pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 30px; max-width: 1000px; margin: 0 auto; }
        .pricing-card { background: white; padding: 40px; border-radius: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .pricing-card.featured { border: 3px solid #667eea; transform: scale(1.05); }
        .price { font-size: 3em; color: #667eea; margin: 20px 0; }
        .price span { font-size: 0.4em; color: #999; }
        .login-link { text-align: center; margin-top: 30px; }
        .login-link a { color: #667eea; text-decoration: none; font-size: 1.1em; }
        footer { background: #333; color: white; text-align: center; padding: 40px 20px; }
    </style>
</head>
<body>
    <div class="hero">
        <h1>🏥 PharmaSaaS</h1>
        <p>Complete Pharmacy Management System for Modern Pharmacies</p>
        <a href="/login" class="cta-btn">Get Started - Login</a>
    </div>
    
    <div class="features">
        <h2>Powerful Features</h2>
        <div class="feature-grid">
            <div class="feature-card">
                <h3>📱 Barcode Scanning</h3>
                <p>Use your phone camera to scan product barcodes for instant inventory management and quick sales processing.</p>
            </div>
            <div class="feature-card">
                <h3>👥 Multi-User Support</h3>
                <p>Admin and Pharmacist roles with custom permissions. Admins control everything, pharmacists handle daily operations.</p>
            </div>
            <div class="feature-card">
                <h3>💳 Credit Management</h3>
                <p>Comprehensive CRM for managing clients with credit accounts, payment tracking, and purchase history.</p>
            </div>
            <div class="feature-card">
                <h3>🤖 AI Assistant</h3>
                <p>Built-in AI chat to help with drug information, dosage queries, and inventory recommendations.</p>
            </div>
            <div class="feature-card">
                <h3>📊 Analytics Dashboard</h3>
                <p>Real-time sales analytics, inventory alerts, and comprehensive reporting for data-driven decisions.</p>
            </div>
            <div class="feature-card">
                <h3>🏪 Point of Sale</h3>
                <p>Fast, intuitive POS system with barcode scanning, multiple payment methods, and receipt generation.</p>
            </div>
        </div>
    </div>
    
    <div class="pricing">
        <h2>Simple Pricing</h2>
        <div class="pricing-grid">
            <div class="pricing-card">
                <h3>Starter</h3>
                <div class="price">$29<span>/month</span></div>
                <p>Perfect for small pharmacies</p>
                <ul style="text-align: left; margin-top: 20px; color: #666;">
                    <li>✓ 1 Admin + 2 Pharmacists</li>
                    <li>✓ Up to 500 products</li>
                    <li>✓ Basic reporting</li>
                    <li>✓ Email support</li>
                </ul>
            </div>
            <div class="pricing-card featured">
                <h3>Professional</h3>
                <div class="price">$79<span>/month</span></div>
                <p>Most popular choice</p>
                <ul style="text-align: left; margin-top: 20px; color: #666;">
                    <li>✓ Unlimited users</li>
                    <li>✓ Unlimited products</li>
                    <li>✓ Advanced analytics</li>
                    <li>✓ AI assistant</li>
                    <li>✓ Priority support</li>
                </ul>
            </div>
            <div class="pricing-card">
                <h3>Enterprise</h3>
                <div class="price">$199<span>/month</span></div>
                <p>For pharmacy chains</p>
                <ul style="text-align: left; margin-top: 20px; color: #666;">
                    <li>✓ Multiple locations</li>
                    <li>✓ Custom integrations</li>
                    <li>✓ Dedicated account manager</li>
                    <li>✓ 24/7 phone support</li>
                </ul>
            </div>
        </div>
        <div class="login-link">
            <p>Already have an account? <a href="/login">Login here</a></p>
        </div>
    </div>
    
    <footer>
        <p>&copy; 2025 PharmaSaaS. All rights reserved.</p>
        <p>Transform your pharmacy with intelligent management.</p>
    </footer>
</body>
</html>
    """)

# ==================== AUTHENTICATION ====================
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=303)
    
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>Login - PharmaSaaS</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-container { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); width: 100%; max-width: 400px; }
        h1 { color: #667eea; margin-bottom: 10px; text-align: center; }
        p { text-align: center; color: #666; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #333; font-weight: 500; }
        input { width: 100%; padding: 12px; border: 2px solid #e1e8ed; border-radius: 8px; font-size: 16px; }
        input:focus { outline: none; border-color: #667eea; }
        button { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
        button:hover { background: #5568d3; }
        .demo-creds { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 14px; }
        .demo-creds strong { color: #667eea; }
        .back-link { text-align: center; margin-top: 20px; }
        .back-link a { color: #667eea; text-decoration: none; }
        .error { color: red; margin-bottom: 15px; padding: 10px; background: #fee; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🏥 PharmaSaaS</h1>
        <p>Login to your pharmacy</p>
        
        <form method="POST" action="/login">
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" required placeholder="your@email.com">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required placeholder="••••••••">
            </div>
            <button type="submit">Login</button>
        </form>
        
        <div class="demo-creds">
            <strong>Demo Credentials:</strong><br>
            Admin: admin@demo.com / admin123<br>
            Pharmacist: pharmacist@demo.com / pharmacist123 (needs approval)
        </div>
        
        <div class="back-link">
            <a href="/">← Back to home</a>
        </div>
    </div>
</body>
</html>
    """)

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user or not pwd_context.verify(password, user.password_hash):
        return HTMLResponse(content="""
            <script>alert('Invalid credentials'); window.location.href='/login';</script>
        """)
    
    if not user.is_active:
        return HTMLResponse(content="""
            <script>alert('Your account is pending approval by your pharmacy admin'); window.location.href='/login';</script>
        """)
    
    request.session["user_id"] = user.id
    request.session["role"] = user.role.value
    request.session["org_id"] = user.organization_id
    
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# ==================== DASHBOARD ====================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    org_id = request.session.get("org_id")
    
    # Get statistics
    total_products = db.query(models.Drug).filter(models.Drug.organization_id == org_id).count()
    total_customers = db.query(models.Customer).filter(models.Customer.organization_id == org_id).count()
    total_sales = db.query(models.SalesOrder).filter(models.SalesOrder.organization_id == org_id).count()
    
    # Get pending credit
    pending_credit = db.query(func.sum(models.Customer.current_balance)).filter(
        models.Customer.organization_id == org_id
    ).scalar() or 0
    
    # Get low stock products
    low_stock = db.query(models.Drug).filter(
        models.Drug.organization_id == org_id
    ).all()
    
    low_stock_items = []
    for drug in low_stock:
        total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
            models.InventoryBatch.drug_id == drug.id
        ).scalar() or 0
        if total_stock < drug.reorder_level:
            low_stock_items.append({"name": drug.name, "stock": total_stock, "reorder": drug.reorder_level})
    
    return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - PharmaSaaS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }}
        .header-content {{ max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }}
        .nav {{ display: flex; gap: 20px; }}
        .nav a {{ color: white; text-decoration: none; padding: 8px 16px; border-radius: 5px; }}
        .nav a:hover {{ background: rgba(255,255,255,0.2); }}
        .container {{ max-width: 1200px; margin: 30px auto; padding: 0 20px; }}
        .welcome {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; color: #667eea; margin: 10px 0; }}
        .stat-label {{ color: #666; font-size: 0.9em; }}
        .alerts {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .alert-item {{ padding: 10px; background: #fff3cd; border-left: 4px solid #ffc107; margin-bottom: 10px; }}
        .ai-chat {{ position: fixed; bottom: 20px; right: 20px; }}
        .ai-btn {{ background: #667eea; color: white; border: none; padding: 15px 25px; border-radius: 50px; cursor: pointer; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }}
        .ai-btn:hover {{ background: #5568d3; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>🏥 PharmaSaaS</h1>
            <div class="nav">
                <a href="/dashboard">Dashboard</a>
                <a href="/inventory">Inventory</a>
                <a href="/sales">POS</a>
                <a href="/customers">Customers</a>
                {"<a href='/staff'>Staff</a>" if user.role.value == "admin" else ""}
                <a href="/logout">Logout</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="welcome">
            <h2>Welcome, {user.full_name}!</h2>
            <p>Role: {user.role.value.title()} | Organization: {user.organization.name}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Products</div>
                <div class="stat-value">{total_products}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Customers</div>
                <div class="stat-value">{total_customers}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Sales</div>
                <div class="stat-value">{total_sales}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pending Credit</div>
                <div class="stat-value">${float(pending_credit):.2f}</div>
            </div>
        </div>
        
        <div class="alerts">
            <h3>⚠️ Low Stock Alerts</h3>
            {"".join([f'<div class="alert-item">📦 {item["name"]}: {item["stock"]} units (reorder at {item["reorder"]})</div>' for item in low_stock_items])}
            {("<p>No low stock items</p>" if not low_stock_items else "")}
        </div>
    </div>
    
    <div class="ai-chat">
        <button class="ai-btn" onclick="window.location.href='/ai-chat'">💬 AI Assistant</button>
    </div>
</body>
</html>
    """)

# ==================== API ENDPOINTS ====================
@app.get("/api/product_by_barcode")
async def get_product_by_barcode(code: str, request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    """Get product by barcode for scanner integration"""
    org_id = request.session.get("org_id")
    
    product = db.query(models.Drug).filter(
        models.Drug.barcode == code,
        models.Drug.organization_id == org_id
    ).first()
    
    if not product:
        return JSONResponse({"error": "Product not found"}, status_code=404)
    
    # Get total stock
    total_stock = db.query(func.sum(models.InventoryBatch.quantity_on_hand)).filter(
        models.InventoryBatch.drug_id == product.id
    ).scalar() or 0
    
    return {
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "barcode": product.barcode,
        "stock": int(total_stock)
    }

@app.post("/api/sales")
async def create_sale(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    """Create new sale"""
    data = await request.json()
    org_id = request.session.get("org_id")
    
    # Create sale order
    sale = models.SalesOrder(
        organization_id=org_id,
        customer_id=data.get("customerId"),
        subtotal=data["subtotal"],
        tax=data.get("tax", 0),
        discount=data.get("discount", 0),
        total=data["total"],
        payment_method=models.PaymentMethodEnum(data["paymentMethod"]),
        amount_paid=data.get("amountPaid", data["total"]),
        balance=data.get("balance", 0),
        sale_number=f"SALE-{org_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    db.add(sale)
    db.flush()
    
    # Add line items and update inventory
    for item in data["lineItems"]:
        line_item = models.SalesLineItem(
            sales_order_id=sale.id,
            drug_id=item["productId"],
            quantity=item["quantity"],
            unit_price=item["unitPrice"],
            line_total=item["lineTotal"]
        )
        db.add(line_item)
        
        # Update inventory
        batch = db.query(models.InventoryBatch).filter(
            models.InventoryBatch.drug_id == item["productId"]
        ).first()
        if batch:
            batch.quantity_on_hand -= item["quantity"]
    
    # Update customer credit balance if credit sale
    if data["paymentMethod"] == "credit" and data.get("customerId"):
        customer = db.query(models.Customer).filter(models.Customer.id == data["customerId"]).first()
        if customer:
            customer.current_balance += data.get("balance", 0)
    
    db.commit()
    
    return {"success": True, "sale_id": sale.id, "sale_number": sale.sale_number}

@app.post("/api/ai/chat")
async def ai_chat(request: Request, user: models.User = Depends(require_auth), db: Session = Depends(get_db)):
    """AI chat endpoint"""
    data = await request.json()
    message = data.get("message")
    session_id = data.get("sessionId")
    
    # Create or get session
    if not session_id:
        chat_session = models.AIChatSession(user_id=user.id, title=message[:50])
        db.add(chat_session)
        db.flush()
        session_id = chat_session.id
    
    # Save user message
    user_msg = models.AIChatMessage(
        session_id=session_id,
        role="user",
        content=message
    )
    db.add(user_msg)
    
    # Get AI response
    response = await openai_service.get_drug_information(message)
    
    # Save AI response
    ai_msg = models.AIChatMessage(
        session_id=session_id,
        role="assistant",
        content=response
    )
    db.add(ai_msg)
    db.commit()
    
    return {"sessionId": session_id, "response": response}

# ==================== SIMPLE PAGES ====================
@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("inventory.html", {"request": request, "user": user})

@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("pos.html", {"request": request, "user": user})

@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("customers.html", {"request": request, "user": user})

@app.get("/staff", response_class=HTMLResponse)
async def staff_page(request: Request, user: models.User = Depends(require_auth)):
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return templates.TemplateResponse("staff.html", {"request": request, "user": user})

@app.get("/ai-chat", response_class=HTMLResponse)
async def ai_chat_page(request: Request, user: models.User = Depends(require_auth)):
    return templates.TemplateResponse("ai_chat.html", {"request": request, "user": user})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
