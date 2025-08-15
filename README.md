# 🛒 My Any Cart - Backend

**My Any Cart - Backend** is the API developed with **Django REST Framework** to support the **My Any Cart** application, which helps organize and track your purchases in a practical and efficient way.

This service provides secure endpoints for **user registration, product management, purchase history, and price analysis**.  
The database used is **PostgreSQL**, ensuring scalability and reliability.

---

## ✨ Features

### ✅ Implemented
- REST API with **Django REST Framework**
- **JWT Authentication** (via `djangorestframework-simplejwt`)
- Models and endpoints for:
  - Products
  - Cart
  - Purchase history
- Configuration for **PostgreSQL**
- **CORS** configured for integration with **Next.js** frontend

### 🚧 Upcoming features
- Data filtering and pagination
- Excel export of history
- Price analysis by product
- Consumption control and automatic categories
- Webhooks for real-time updates

---

## 🛠 Technologies used

- **Python 3.12+**
- **Django 5+**
- **Django REST Framework**
- **PostgreSQL**
- **Simple JWT**
- **django-cors-headers**
- **psycopg2**

---

## 📂 Folder structure

```bash
my-any-cart-backend/
├── myanycart/           # Main Django configuration
├── apps/
│   ├── accounts/        # User management and authentication
│   ├── products/        # Products and cart
│   └── purchases/       # History and analytics
├── requirements.txt     # Project dependencies
├── manage.py
└── README.md
```

---

## 🚀 How to run the project locally

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/my-any-cart-backend.git
cd my-any-cart-backend
```

### 2️⃣ Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Configure environment variables
Create a `.env` file in the root with the variables:
```env
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://user:password@localhost:5432/myanycart
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### 5️⃣ Run migrations
```bash
python manage.py migrate
```

### 6️⃣ Create superuser
```bash
python manage.py createsuperuser
```

### 7️⃣ Run the server
```bash
python manage.py runserver
```

The API will be available at:  
👉 **http://localhost:8000**

---

## 🔑 Authentication

The API uses **JWT** for authentication.  
Basic flow:
1. Send email/password to `/api/token/` and receive **access** + **refresh**
2. Use `Authorization: Bearer <access>` in protected endpoints
3. Refresh token via `/api/token/refresh/`

---

## 📡 Main endpoints

| Method | Route                     | Description                | Authentication |
|--------|--------------------------|----------------------------|--------------|
| POST   | `/api/token/`            | Get JWT token              | ❌           |
| POST   | `/api/token/refresh/`    | Refresh JWT token          | ❌           |
| GET    | `/products/`             | List products              | ✅           |
| POST   | `/products/`             | Create product             | ✅           |
| GET    | `/purchases/`            | List history               | ✅           |

---

## 📜 License
This project is licensed under the [MIT License](LICENSE).

---

💡 **Tip:** This backend was designed to integrate perfectly with the [My Any Cart - Frontend](https://github.com/tiagodev96/my-any-cart) in **Next.js**.
