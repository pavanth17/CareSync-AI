# Design Guidelines: Hospital Patient Monitoring & Care Coordination System

## Design Approach
**System-Based Approach** - Healthcare applications prioritize clarity, efficiency, and reliability over visual trends. Drawing from Material Design principles and established medical dashboard patterns (Epic, Cerner, modern EHR systems), this design emphasizes information hierarchy, quick scannability, and fail-safe interactions.

## Core Design Principles
1. **Clinical Clarity**: Every element serves a functional purpose
2. **Scan Efficiency**: Information must be processable at a glance
3. **Alert Prominence**: Emergency notifications override all other UI elements
4. **Role Optimization**: Each dashboard tailored to user workflows

---

## Typography System

**Font Family**: Inter or Roboto (Google Fonts CDN)

**Hierarchy**:
- Dashboard Headers: text-2xl, font-semibold
- Section Titles: text-lg, font-medium
- Data Labels: text-sm, font-medium, uppercase tracking-wide
- Patient Names: text-base, font-semibold
- Vital Values: text-3xl, font-bold (large display numbers)
- Body Text: text-base, font-normal
- Timestamps: text-xs, font-normal
- Alert Text: text-lg, font-bold

---

## Layout System

**Spacing Primitives**: Use Tailwind units of 2, 4, 6, 8, 12, 16
- Component padding: p-4 or p-6
- Card spacing: gap-4 or gap-6
- Section margins: mb-8 or mb-12
- Table cell padding: p-3

**Grid Structure**:
- Admin Dashboard: 12-column grid for user management tables
- Doctor/Nurse Dashboards: 3-column patient card grid (lg:grid-cols-3 md:grid-cols-2)
- Patient Detail View: 2-column split (vitals chart + patient info)
- Sidebar Navigation: Fixed 64px width (collapsed) or 256px (expanded)

**Container Constraints**:
- Max width: max-w-7xl for main content
- Full viewport height layouts for dashboards
- Sticky headers for tables and dashboards

---

## Component Library

### Navigation
**Top Bar** (h-16, fixed):
- Logo/Hospital name (left)
- User role badge with name
- Emergency alert indicator (bell icon with pulse animation if active)
- Logout button (right)

**Side Navigation** (collapsible):
- Icons with labels (expanded) or icon-only (collapsed)
- Active state: border-l-4 accent
- Menu items: Dashboard, Patients, Alerts, Users (Admin only), Reports

### Dashboard Layouts

**Admin Dashboard**:
- Stats cards row: 4 cards (Total Patients, Active Doctors, Active Nurses, Critical Alerts)
- User management table: Full-width data table with search, filter, action columns
- Quick actions panel: "Register Doctor" and "Register Nurse" buttons

**Doctor/Nurse Dashboards**:
- Alert banner at top (if active emergencies)
- Patient cards grid: 3 columns on desktop, stacked on mobile
- Each card: Patient photo placeholder, name, room number, vital signs summary, status badge

### Patient Cards
**Compact View** (in grid):
- Border with status indicator (3px left border)
- Patient ID and Name (header)
- Vital signs: 4 metrics in 2x2 micro-grid (Heart Rate, BP, O2, Temp)
- Last updated timestamp
- "View Details" button

**Detailed View** (modal or full page):
- Patient header with photo, demographics
- Real-time vitals chart (line graphs, updates every 3 seconds)
- Vital history table
- Assigned doctor/nurse info
- Notes section

### Vital Signs Display
**Live Monitors**:
- Large numeric display (text-4xl or text-5xl)
- Unit label (text-sm, muted)
- Trend indicator (up/down arrow icon)
- Mini sparkline chart beneath value
- Status badge (Normal/Warning/Critical)

**Layout**: 
```
[Icon] Heart Rate        [Icon] Blood Pressure
  124 bpm ↑                 120/80 mmHg →
  [sparkline]               [sparkline]
  
[Icon] O2 Saturation    [Icon] Temperature  
  98% →                     98.6°F →
  [sparkline]               [sparkline]
```

### Emergency Alert System
**Alert Modal** (z-50, backdrop blur):
- Full-screen overlay with semi-transparent backdrop
- Centered alert card (max-w-lg)
- Pulsing border animation
- Alert icon (large, top center)
- Patient name and room number
- Critical vital reading
- "Acknowledge & Navigate" button (large, full width)
- Auto-dismiss timer (60s) with countdown

**Alert Banner** (sticky top):
- Full-width, h-12
- Scrolling text for multiple alerts
- Dismiss individual alerts with X button
- Click to view detail

### Data Tables
**User Management & Patient Lists**:
- Striped rows for readability
- Sticky header row
- Sortable columns (click header)
- Action column (right): Edit, Delete, View icons
- Pagination controls (bottom)
- Search bar (top right)
- Filter dropdowns (top left)

### Forms
**Login Screen**:
- Centered card (max-w-md)
- Hospital logo/name at top
- Role selector (dropdown): Admin, Doctor, Nurse
- ID field (text input)
- Password field (password input)
- "Login" button (full width)
- Subtle background pattern or medical imagery

**User Registration** (Admin):
- Multi-step form or single scrollable form
- Sections: Personal Info, Credentials, Role Assignment
- Input groups with labels above fields
- Required field indicators
- "Register" and "Cancel" buttons

### Status Indicators
**Patient Status Badges**:
- Pill shape (rounded-full px-3 py-1)
- Text labels: "Stable", "Monitoring", "Critical"
- Size: text-xs font-semibold

**Availability Indicators** (for doctors/nurses):
- Dot indicator (w-2 h-2 rounded-full)
- Positions: On-Duty, Off-Duty, In Emergency

---

## Real-Time Elements

**Update Animations**:
- Vital values: Gentle fade-in when updated (transition-opacity duration-300)
- New alerts: Slide-in from top (transform translate-y)
- Status changes: Pulse effect once (animate-pulse, then stop)

**Loading States**:
- Skeleton screens for tables/cards
- Spinner for vitals (if connection interrupted)
- Pulse animation on live data badges

---

## Responsive Behavior

**Desktop** (lg:):
- Side navigation expanded
- 3-column patient cards
- Multi-column forms

**Tablet** (md:):
- Side navigation collapsed (icon only)
- 2-column patient cards
- Stacked form sections

**Mobile** (base):
- Bottom navigation bar or hamburger menu
- Single column cards
- Full-width forms
- Larger touch targets (min-h-12)

---

## Accessibility

- Semantic HTML throughout (nav, main, aside, article)
- ARIA labels on all icons and icon-only buttons
- Focus visible states (ring-2 ring-offset-2)
- Keyboard navigation support
- Color is never the only indicator (use icons + text)
- High contrast ratios for all text
- Screen reader announcements for alerts and vital changes

---

## Icon Usage
Use **Heroicons** (outline for navigation, solid for alerts/status):
- Emergency: ExclamationTriangleIcon
- Vitals: HeartIcon, UserIcon
- Users: UserGroupIcon, ShieldCheckIcon
- Actions: PencilIcon, TrashIcon, EyeIcon
- Navigation: HomeIcon, ChartBarIcon, BellIcon