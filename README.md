# 🚚 AI Logistics Route Optimizer

<p align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![Render](https://img.shields.io/badge/Backend-Render-46E3B7)
![Vercel](https://img.shields.io/badge/Frontend-Vercel-black?logo=vercel)
![License](https://img.shields.io/badge/License-MIT-green)

</p>

An **AI-powered Smart Logistics Management Platform** that optimizes delivery routes using **Google OR-Tools Vehicle Routing Problem (VRP)** algorithms while providing a complete logistics management dashboard for drivers, vehicles, orders, analytics, and dispatch operations.

---

# 🌐 Live Demo

### 🚀 Frontend

**https://ai-logistics-umber.vercel.app**

### ⚡ Backend API

**https://ai-logistics-backend-zn50.onrender.com**

### 📚 API Documentation

**https://ai-logistics-backend-zn50.onrender.com/docs**

---

# ✨ Features

## Authentication

- JWT Authentication
- Secure Password Hashing
- Role-based Access
- Protected Routes

---

## Driver Management

- Create Drivers
- Assign Users
- Vehicle Assignment
- Driver Availability
- Capacity Management

---

## Vehicle Management

- Vehicle CRUD
- Capacity Tracking
- Active Status
- Availability Management

---

## Order Management

- Pickup & Delivery Locations
- Priority Levels
- Driver Assignment
- Vehicle Assignment
- Order Status Tracking

---

## AI Route Optimization

Powered by **Google OR-Tools**

- Vehicle Routing Problem (VRP)
- Capacity Constraints
- Multi-Vehicle Routing
- Route Distance Optimization
- Driver Assignment
- Estimated Delivery Routes

---

## Analytics Dashboard

- KPI Cards
- Driver Statistics
- Vehicle Statistics
- Order Analytics
- Interactive Charts

---

## Modern UI

- Responsive Design
- Dark Theme
- Search
- Pagination
- Loading States
- Validation
- Reusable Components

---

## 🧠 AI Route Optimization

```mermaid
flowchart LR

    Orders --> Optimizer
    Drivers --> Optimizer
    Vehicles --> Optimizer

    Optimizer --> ORTools

    ORTools --> Capacity
    Capacity --> Routes

    Routes --> Dashboard
```

## 🏗️ System Architecture

```mermaid
flowchart TB

    U[User]

    subgraph Frontend
        R[React + Vite]
        C[Context API]
        UI[Dashboard UI]
    end

    subgraph Backend
        F[FastAPI]
        A[JWT Authentication]
        S[Service Layer]
        Repo[Repository Layer]
        ORM[SQLAlchemy ORM]
    end

    subgraph Database
        DB[(Neon PostgreSQL)]
    end

    subgraph AI
        VRP[Google OR-Tools]
        OPT[Vehicle Routing Problem]
    end

    U --> R
    R --> C
    C --> UI

    UI --> F

    F --> A
    F --> S

    S --> Repo
    Repo --> ORM
    ORM --> DB

    S --> VRP
    VRP --> OPT

    OPT --> UI
```



# 📁 Project Structure

```
AI-Logistics
│
├── backend
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── db
│   │   ├── dependencies
│   │   ├── models
│   │   ├── repositories
│   │   ├── schemas
│   │   ├── services
│   │   └── main.py
│   │
│   └── requirements.txt
│
├── frontend
│   ├── src
│   │   ├── components
│   │   ├── context
│   │   ├── pages
│   │   ├── services
│   │   └── App.jsx
│
├── alembic
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

# ⚙ Tech Stack

## Frontend

- React
- Vite
- React Router
- Axios
- Context API
- Recharts

---

## Backend

- FastAPI
- SQLAlchemy 2.0
- Alembic
- JWT Authentication
- Passlib
- Pydantic v2

---

## Database

- PostgreSQL
- Neon Database

---

## AI

- Google OR-Tools
- Vehicle Routing Problem (VRP)

---

## Deployment

- Vercel
- Render
- Docker

---

# 🚀 Optimization Pipeline

```mermaid
sequenceDiagram

participant User
participant Frontend
participant Backend
participant ORTools
participant Database

User->>Frontend: Optimize Routes

Frontend->>Backend: POST /optimization

Backend->>Database: Fetch Drivers

Backend->>Database: Fetch Vehicles

Backend->>Database: Fetch Orders

Backend->>ORTools: Build VRP Model

ORTools-->>Backend: Optimized Routes

Backend-->>Frontend: Route Plan

Frontend-->>User: Visualization
```

---

# 🔐 Authentication Flow

```mermaid
flowchart LR

User

Login

JWT

ProtectedAPI

Database

User --> Login

Login --> JWT

JWT --> ProtectedAPI

ProtectedAPI --> Database
```

---

# 📊 API Modules

| Module | Description |
|---------|-------------|
| Authentication | Login & Registration |
| Users | User Management |
| Drivers | Driver CRUD |
| Vehicles | Vehicle CRUD |
| Orders | Order CRUD |
| Optimization | AI Route Optimization |
| Analytics | Dashboard Metrics |

---

# 📦 Local Installation

Clone the repository

```bash
git clone https://github.com/MainakDebnath6/AI-Logistics.git

cd AI-Logistics
```

Backend

```bash
python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

alembic upgrade head

uvicorn backend.app.main:app --reload
```

Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# 🌍 Environment Variables

Backend

```env
DATABASE_URL=
SECRET_KEY=
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_CORS_ORIGINS=
```

Frontend

```env
VITE_API_BASE_URL=
```

---

# 📸 Screenshots

> Add screenshots here

- Login
- Dashboard
- Drivers
- Vehicles
- Orders
- Route Optimization
- Analytics

---

# 🎯 Future Improvements

- Live GPS Tracking
- Real-Time Dispatch
- Driver Mobile App
- ETA Prediction
- Fuel Consumption Prediction
- ML-Based Demand Forecasting
- Google Maps Integration
- Notifications
- Multi-Warehouse Optimization

---

# 👨‍💻 Author

**Mainak Debnath**

- GitHub: https://github.com/MainakDebnath6
- LinkedIn: https://www.linkedin.com/in/mainak-debnath01/

---

# ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub!
