# PharmaSaaS - Multi-Tenant Pharmacy Management System

## Overview
PharmaSaaS is a comprehensive, multi-tenant pharmacy management system built with FastAPI and Python. It allows multiple pharmacies to manage their operations independently with features like barcode scanning, credit management, AI assistance, and role-based access control.

## Project Status
**Status**: Fully Functional ✅
**Deployment**: Running on port 5000
**Database**: PostgreSQL (Replit-hosted)

## Features Implemented

### 1. Multi-Tenant Architecture
- Each pharmacy (organization) has isolated data
- Organization-scoped queries ensure data privacy
- Support for unlimited pharmacies on single deployment

### 2. Authentication & Authorization
- Custom authentication system with session management
- Password hashing using bcrypt via passlib
- Two user roles:
  - **Admin**: Full access to all features, can manage staff
  - **Pharmacist**: Limited access, requires admin approval

### 3. Barcode Scanning
- Camera-based barcode scanning for inventory and POS
- Uses native BarcodeDetector API when available
- Falls back to QuaggaJS for broader browser support
- Manual barcode entry option
- Auto-add-to-cart in POS on successful scan

### 4. Point of Sale (POS)
- Real-time barcode scanning with camera
- Shopping cart with quantity management
- Multiple payment methods: Cash, Card, Mobile Payment, Credit
- Credit sales with customer account tracking
- Automatic inventory updates on sale completion

### 5. Inventory Management
- Add products via camera barcode scanning
- Track stock levels with low-stock alerts
- Product details: name, barcode, price, manufacturer, category
- Batch tracking with expiry dates

### 6. Customer Relationship Management (CRM)
- Customer profiles with contact information
- Credit account management
- Credit limit and current balance tracking
- Payment history for credit customers

### 7. AI Chat Assistant
- OpenAI-powered pharmacy assistant
- Drug information and dosage queries
- Side effects and interaction warnings
- Inventory recommendations
- Gracefully handles missing API key

### 8. Staff Management (Admin Only)
- Add pharmacist accounts
- Approve/reject pharmacist access
- View all staff members and their status

### 9. Analytics Dashboard
- Total products, customers, and sales counts
- Pending credit balance summary
- Low stock alerts
- Role-specific views

### 10. Landing Page
- Professional SaaS landing page
- Feature showcase
- Pricing tiers (Starter, Professional, Enterprise)
- Call-to-action for sign-up/login

## Technical Stack

**Backend:**
- FastAPI 0.121.1
- SQLAlchemy 2.0.44 (ORM)
- PostgreSQL (via DATABASE_URL)
- Passlib[bcrypt] (password hashing)
- Python 3.11

**Frontend:**
- Jinja2 templates (server-side rendering)
- Vanilla JavaScript
- QuaggaJS (barcode scanning fallback)
- BarcodeDetector API (native scanning)
- Responsive CSS with gradient designs

**AI Integration:**
- OpenAI Python SDK
- GPT-5 model for chat assistant

## Database Schema

### Core Tables:
- **organizations**: Pharmacies (name, slug, subscription plan)
- **users**: Staff members (email, password_hash, role, organization_id)
- **drugs**: Products (name, barcode, price, quantity, organization_id)
- **inventory_batches**: Stock batches (quantity, expiry, lot number)
- **customers**: Clients (name, credit settings, balance, organization_id)
- **sales_orders**: Sales transactions (total, payment method, organization_id)
- **sales_line_items**: Sale details (product, quantity, price)
- **credit_payments**: Credit payment records
- **ai_chat_sessions**: AI conversation sessions
- **ai_chat_messages**: Chat message history

## Demo Credentials

**Organization**: Demo Pharmacy

**Admin Account:**
- Email: admin@demo.com
- Password: admin123
- Access: Full system access

**Pharmacist Account:**
- Email: pharmacist@demo.com
- Password: pharmacist123
- Status: Pending approval (admin must activate)

## Demo Data
The system comes pre-seeded with:
- 1 demo organization (Demo Pharmacy)
- 2 users (1 admin, 1 pharmacist)
- 3 sample products with barcodes
- 2 customer accounts with credit enabled
- Sample inventory batches

## API Endpoints

### Authentication
- `GET /` - Landing page
- `GET /login` - Login page
- `POST /login` - Login handler
- `GET /logout` - Logout

### Dashboard & Pages
- `GET /dashboard` - Main dashboard (requires auth)
- `GET /inventory` - Inventory management with barcode scanning
- `GET /sales` - Point of Sale with scanner
- `GET /customers` - CRM interface
- `GET /staff` - Staff management (admin only)
- `GET /ai-chat` - AI chat assistant

### API Endpoints
- `GET /api/product_by_barcode?code={barcode}` - Lookup product by barcode
- `POST /api/sales` - Create sale transaction
- `POST /api/ai/chat` - AI chat endpoint

## Environment Variables

**Required:**
- `DATABASE_URL` - PostgreSQL connection string (auto-configured by Replit)
- `SESSION_SECRET` - Session encryption key (auto-generated)

**Optional:**
- `OPENAI_API_KEY` - For AI chat assistant feature

## Running the Application

The application runs automatically via the configured workflow:
```bash
python app.py
```

Access the application at: `http://0.0.0.0:5000` or your Replit webview URL

## File Structure

```
.
├── app.py                 # Main FastAPI application
├── models.py              # SQLAlchemy database models
├── database.py            # Database configuration
├── init_db.py             # Database initialization script
├── openai_service.py      # OpenAI integration
├── templates/             # Jinja2 HTML templates
│   ├── pos.html          # Point of Sale interface
│   ├── inventory.html    # Inventory management
│   ├── customers.html    # CRM interface
│   ├── staff.html        # Staff management
│   └── ai_chat.html      # AI chat interface
├── static/                # Static assets (CSS, JS, images)
└── replit.md             # This file
```

## User Workflows

### Admin Workflow:
1. Login with admin credentials
2. View dashboard with pharmacy statistics
3. Manage products via inventory page
4. Approve pharmacist accounts in staff management
5. Process sales in POS
6. Manage customer credit accounts
7. Chat with AI assistant for queries

### Pharmacist Workflow:
1. Login (after admin approval)
2. View dashboard (limited access)
3. Process sales with barcode scanner
4. Add inventory via barcode scanning
5. View customer information
6. Use AI assistant for drug information

## Security Features

- Bcrypt password hashing
- Session-based authentication
- Organization-scoped data queries
- Role-based access control
- CSRF protection via FastAPI middleware
- No passwords stored in plain text
- Inactive users cannot login

## Recent Changes (November 13, 2025)

1. ✅ Implemented multi-tenant database schema
2. ✅ Built custom authentication system
3. ✅ Created professional landing page
4. ✅ Added barcode scanning to POS and inventory
5. ✅ Implemented credit management
6. ✅ Integrated OpenAI chat assistant
7. ✅ Added role-based access control
8. ✅ Created comprehensive UI templates
9. ✅ Fixed OpenAI API parameter issues
10. ✅ Seeded demo data for testing

## Next Steps (Future Enhancements)

- Organization registration flow for new pharmacies
- Email notifications for low stock
- Advanced reporting and analytics
- Receipt printing functionality
- Prescription management module
- Multi-location support for pharmacy chains
- Mobile app version
- Offline mode support
- Automated reordering based on AI recommendations

## Support & Maintenance

For issues or questions, contact the development team or refer to the codebase documentation.

## License

Proprietary - PharmaSaaS © 2025
