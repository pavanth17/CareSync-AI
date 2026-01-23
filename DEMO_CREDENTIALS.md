# CareSync AI - Demo Credentials Guide

## Quick Access URLs

| Portal | URL | Purpose |
|--------|-----|---------|
| **Staff Login** | `http://localhost:5000/login` | Login for Admin, Doctors, Nurses |
| **Credentials** | `http://localhost:5000/credentials` | View all demo credentials |
| **Patient Portal** | `http://localhost:5000/discharged-portal` | Discharged patients (chat with AI) |
| **Home** | `http://localhost:5000/` | Landing page |

---

## 🔐 Staff Credentials

### Administrator Account
| Field | Value |
|-------|-------|
| **Staff ID** | ADM0001 |
| **Name** | Pavanth Kumar |
| **Password** | admin123 |
| **Login URL** | http://localhost:5000/login |
| **Dashboard** | Admin dashboard with all controls |

### Doctor Accounts
| Staff ID | Name | Password | Role |
|----------|------|----------|------|
| DOC0001 | Ishaan Desai | doctor1 | Doctor |
| DOC0002 | Rajesh Ghosh | doctor2 | Doctor |

**Access**: http://localhost:5000/login

### Nurse Accounts
| Staff ID | Name | Password | Role |
|----------|------|----------|------|
| NRS0001 | Ila Sharma | nurse1 | Nurse |
| NRS0002 | Ritika Rao | nurse2 | Nurse |
| NRS0003 | Sneha Dutta | nurse3 | Nurse |

**Access**: http://localhost:5000/login

### Ward Login (Department Nurses)
| Staff ID | Name | Password | Department |
|----------|------|----------|------------|
| NRS_ICU | Priya ICU | nurse123 | ICU |
| NRS_ER | Rahul Emergency | nurse123 | Emergency |

**Access**: http://localhost:5000/login (Redirects to Ward Dashboard)

---

## 👥 Patient Portal (Discharged Patients)

**URL**: http://localhost:5000/discharged-portal

### Available Patients
| Patient ID | Name | Phone | Features |
|-----------|------|-------|----------|
| PAT000001 | Priya Prasad | 555-935-4604 | Chat with AI, View records |
| PAT000005 | Aditya Nambiar | 555-709-3888 | Chat with AI, View records |

**Login Requirements**:
- Enter Patient ID (e.g., `PAT000001`)
- Enter Phone Number (e.g., `555-935-4604`)
- Access discharged patient dashboard with AI chat