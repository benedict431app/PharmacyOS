# Pharmacy Management System - Design Guidelines

## Design Approach
**System Selected**: Material Design principles adapted for healthcare
**Rationale**: Information-dense, data-heavy dashboard application requiring clear hierarchy, efficient workflows, and professional presentation. Healthcare context demands clarity and reliability over visual experimentation.

## Core Design Principles
1. **Data-First Design**: Information accessibility and scannability are paramount
2. **Workflow Efficiency**: Minimize clicks for common pharmacist tasks
3. **Visual Hierarchy**: Critical alerts (low stock, expiring drugs) must stand out immediately
4. **Professional Healthcare Aesthetic**: Clean, trustworthy, clinical presentation

---

## Typography System

**Primary Font**: Inter (via Google Fonts)
**Secondary Font**: Roboto Mono (for data tables, codes, quantities)

**Hierarchy**:
- Dashboard Headers: text-2xl, font-semibold
- Section Titles: text-xl, font-semibold
- Card Headers: text-lg, font-medium
- Body Text: text-base, font-normal
- Data Tables: text-sm, font-mono for numbers
- Labels/Meta: text-sm, font-medium
- Alerts/Badges: text-xs, font-semibold uppercase

---

## Layout System

**Spacing Units**: Tailwind spacing of 3, 4, 6, 8, 12 (e.g., p-4, gap-6, mb-8, py-12)
- Tight spacing (3) for inline elements, badges
- Standard spacing (4, 6) for cards, form fields
- Generous spacing (8, 12) for section breaks, dashboard modules

**Dashboard Grid**: 
- Sidebar: 16rem fixed width (w-64)
- Main content: Flexible with max-w-7xl container
- Card grids: grid-cols-1 md:grid-cols-2 lg:grid-cols-3 for stats/metrics
- Data tables: Full-width within container

**Responsive Breakpoints**:
- Mobile: Single column, collapsible sidebar
- Tablet (md): 2-column layouts for cards
- Desktop (lg+): Full multi-column dashboard layouts

---

## Component Library

### Navigation
- **Sidebar Navigation**: Fixed left sidebar with icon + label navigation items, grouped by category (Inventory, Sales, Analytics, Settings)
- **Top Bar**: Logo, search bar (prominent), notification bell with badge, user profile dropdown
- **Active States**: Highlighted background for current section

### Dashboard Modules
- **Stats Cards**: Grid of metric cards (Total Stock Value, Low Stock Items, Expiring Soon, Today's Sales) with large numbers, trend indicators (↑↓), and icons
- **Data Tables**: Striped rows for readability, sortable headers, search/filter bar above table, pagination below
- **Charts**: Clean line/bar charts for sales trends, donut charts for category breakdowns using Chart.js or similar

### Inventory Management
- **Drug Cards**: Compact cards showing drug name, quantity, expiry date, supplier, with quick action buttons (Edit, Reorder, View Details)
- **Stock Level Indicators**: Visual bars or badges (High Stock, Normal, Low, Critical) with distinct styling
- **Filters Panel**: Multi-select dropdowns for category, supplier, expiry range

### Forms & Input
- **Standard Forms**: Clear labels above inputs, generous padding, validation messages below fields
- **Search Bars**: Prominent with search icon, autocomplete dropdown for drug names
- **Barcode Scanner**: Camera viewfinder UI with overlay guides, instant drug lookup results
- **Prescription Upload**: Drag-and-drop zone with camera capture button, preview of uploaded image, OCR results displayed in editable form

### AI Chatbot Interface
- **Chat Window**: Fixed bottom-right bubble launcher, expandable panel with conversation history
- **Messages**: User messages right-aligned, AI responses left-aligned with avatar icon
- **Quick Actions**: Preset question chips (e.g., "Drug interactions", "Dosage for adults", "Side effects")

### CRM & Patient Records
- **Patient Cards**: Avatar/initials, name, contact info, last visit date, prescription count
- **Prescription History**: Timeline view with expandable drug details
- **Contact Forms**: Phone, email, address fields with validation

### Alerts & Notifications
- **Alert Banners**: Top-of-section warnings for critical inventory issues (red for critical low stock, orange for expiring soon)
- **Notification Dropdown**: List of recent alerts, timestamps, "Mark all read" action
- **Toast Notifications**: Bottom-right corner for success/error feedback after actions

### Analytics Dashboard
- **Time Period Selector**: Tabs or dropdown (Last 7 days, 30 days, 3 months, Custom range)
- **KPI Grid**: 4-column grid of key metrics with comparison to previous period
- **Forecast Visualization**: Line chart showing historical data + predicted trends (different line style for forecast)

### Nearby Pharmacies
- **Map View**: Embedded map with markers for nearby locations
- **List View**: Cards showing pharmacy name, distance, hours, contact button
- **Toggle**: Switch between map and list views

---

## Visual Elements

### Icons
Use **Heroicons** (outline style) via CDN for consistency
- Inventory: cube, archive-box
- Sales: shopping-cart, currency-dollar
- Analytics: chart-bar, presentation-chart-line
- Users: users, user-circle
- Alerts: exclamation-triangle, bell
- Actions: plus, pencil, trash

### Badges & Status
- Stock Status: Pill-shaped badges with text-xs font
- Expiry Warnings: Bordered badges with icon
- Role Tags: Subtle background badges in user listings

### Data Visualization
- Clean, minimal chart styling with grid lines
- Single accent for primary data series
- Use contrasting shades for comparisons
- Include legends and axis labels clearly

---

## Interactions

**Minimal Animations**:
- Smooth sidebar collapse/expand (200ms transition)
- Dropdown menus fade in (150ms)
- Modal overlays with backdrop blur
- Button hover states with subtle scale (hover:scale-105)
- Loading spinners for async operations (OCR, AI responses)

**No**: Unnecessary scroll animations, parallax effects, or decorative transitions

---

## Accessibility

- ARIA labels for icon-only buttons
- Keyboard navigation for all interactive elements
- Focus indicators (ring-2 ring-offset-2) on all inputs
- Color is never the only indicator (use icons + text for status)
- Sufficient contrast ratios for all text (WCAG AA minimum)

---

## Images

**No large hero images** - This is a dashboard application, not a marketing site.

**Functional Images**:
- Drug product photos in inventory cards (small thumbnails)
- Prescription uploads (user-provided images with OCR preview)
- User avatars in CRM and profile areas
- Empty state illustrations for no data scenarios (simple, minimalist SVGs)