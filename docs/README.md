# NICMAH AGROVET Documentation

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git
- pip

### Installation
```bash
# Clone and setup
git clone <repository-url>
cd NICMAH-E

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start server
python manage.py runserver
```

### Access Points
- **Main Site**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/
- **POS System**: http://localhost:8000/pos/
- **Analytics**: http://localhost:8000/analytics/

## 🏗️ Architecture

### App Structure
```
nichmah_agrovet/          # Project root
├── core/                 # Core settings, templates, static files
├── users/                # Authentication and user management
├── catalog/              # Product catalog and categories
├── orders/               # Shopping cart and order management
├── pos/                  # Point of Sale system
├── inventory/            # Stock management and tracking
├── analytics/            # Reporting and dashboards
└── educational/          # Content management system
```

### Key Features
- **E-commerce**: Product catalog, shopping cart, WhatsApp checkout
- **POS System**: In-shop sales, receipt generation, session management
- **Inventory**: Stock tracking, alerts, purchase orders
- **Analytics**: Sales reports, performance metrics, dashboards
- **User Management**: Role-based access (Customer, Seller, Manager, Admin)

## 🔧 Development

### Code Standards
- Follow PEP 8 style guidelines
- Use snake_case for variables and functions
- Use PascalCase for classes
- Maximum line length: 88 characters (Black formatter)

### Testing
```bash
# Run tests
python manage.py test

# Run linting
flake8 .

# Run security checks
pip-audit
```

### Database
- **Development**: SQLite (default)
- **Production**: PostgreSQL (recommended)
- **Migration**: `python manage.py migrate`

## 🔒 Security

### Environment Variables
All sensitive data uses environment variables:
```bash
# .env file
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```

### Protected Files
The following files are automatically ignored by git:
- `.env` (environment variables)
- `db.sqlite3` (database)
- `media/` (uploaded files)
- `staticfiles/` (collected static files)
- `logs/` (log files)
- `venv/` (virtual environment)

## 🚀 Deployment

### Production Setup
1. **Database**: Use PostgreSQL
2. **Environment**: Set `DEBUG=False`
3. **Static Files**: Run `python manage.py collectstatic`
4. **Security**: Enable HTTPS and secure cookies

### Docker Deployment
```bash
# Build and run
docker-compose up --build
```

## 📊 Features

### User Management
- Custom user model with role-based permissions
- User authentication (login, signup, logout)
- User profiles with extended information
- Role-based access control

### E-commerce
- Product catalog with categories
- Product management (CRUD operations)
- Shopping cart functionality
- Order management system
- WhatsApp integration for checkout

### POS System
- Comprehensive POS dashboard
- Session management
- Receipt generation (PDF)
- Payment method tracking
- Stock updates on sales

### Inventory Management
- Stock movement tracking
- Stock alerts and notifications
- Purchase order system
- Stock level monitoring

### Analytics
- Real-time key performance indicators
- Interactive charts using Chart.js
- Sales distribution analysis
- Top performing products
- Customer segmentation

## 🛠️ Troubleshooting

### Common Issues
- **Port 8000 in use**: Use `python manage.py runserver 8001`
- **Database errors**: Run `python manage.py migrate --run-syncdb`
- **Static files**: Run `python manage.py collectstatic`

### Getting Help
- Check the troubleshooting guide
- Create an issue in the repository
- Contact the development team

---

**Version**: 1.0.0  
**Last Updated**: September 4, 2025  
**Maintainer**: Development Team
