# NICMAH AGROVET - E-commerce & POS System

A comprehensive Django-based web application for agricultural products, featuring e-commerce, POS system, inventory management, and analytics.

## 🚀 Project Status

**Current Status:** Core Development Phase - 80% Complete  
**Last Updated:** August 29, 2025  
**Version:** 1.0.0-beta

## ✨ Features

### 🏗️ **Project Foundation**
- Django 5.2.5 with modular app architecture
- Virtual environment and dependency management
- PostgreSQL/SQLite database configuration
- Environment variable management with python-decouple
- Git repository with proper branching strategy
- CI/CD pipeline with GitHub Actions
- Docker and Docker Compose configuration
- Code quality tools (flake8, black, pytest)

### 👥 **User Management System**
- Custom User model with role-based permissions
- User roles: Customer, Seller, Manager, Admin
- User authentication (login, signup, logout)
- User profiles with extended information
- Complete Seller Management System
- Role-based access control
- Beautiful authentication UI with Tailwind CSS
- User dashboard system

### 🛍️ **E-commerce Core**
- Product catalog with categories
- Product management (CRUD operations)
- Product images and media handling
- Stock management and tracking
- Shopping cart functionality
- Order management system
- WhatsApp integration for checkout
- Product search and filtering

### 💰 **POS (Point of Sale) System**
- Comprehensive POS dashboard with real-time metrics
- Session management (start/close sessions)
- Today's sales overview and statistics
- Quick actions for common POS tasks
- Product search functionality
- Receipt management system
- Sales list and detailed views
- Commission calculation system
- Receipt generation (PDF)
- Payment method tracking
- Stock updates on sales

### 📊 **Inventory Management**
- Stock movement tracking
- Stock alerts and notifications
- Inventory transactions
- Supplier management
- Purchase order system
- Stock level monitoring

### 📈 **Analytics & Reporting**
- Real-time key performance indicators
- Interactive charts using Chart.js
- Revenue and orders trend analysis
- Sales distribution by source
- Top performing products analysis
- Customer segmentation insights
- Customer lifetime value metrics
- Retention rate visualization
- Inventory analytics and stock turnover
- Quick report generation

### 📚 **Educational Hub**
- Article management system
- Article categories and tags
- Content publishing workflow
- Educational content structure

### 🎨 **Frontend & UI**
- Responsive design with Tailwind CSS
- Agro-themed color scheme and branding
- Modern animations and transitions
- Interactive JavaScript functionality

## 🏗️ Architecture

### **App Structure**
```
nichmah_agrovet/          # Project root
├── core/                 # Core settings, templates, static files, mixins
├── users/                # Authentication, roles, user management
├── catalog/              # Product catalog, categories, stock details
├── orders/               # Cart, WhatsApp checkout, order models
├── pos/                  # In-shop sales, receipt printing
├── inventory/            # Stock tracking, low-stock alerts
├── analytics/            # Reports, dashboards, insights
└── educational/          # Articles, blog system
```

### **Code Organization**
- **Mixins**: Common model, admin, and view mixins in `core/`
- **Utilities**: Shared utility functions in `core/utils.py`
- **Templates**: Base templates in `core/templates/`
- **Static Files**: CSS, JS, and images in `core/static/`

## 🚀 Quick Start

### **Prerequisites**
- Python 3.11+
- pip
- Git

### **Installation**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd NICMAH-E
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy .env.example to .env and configure
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main site: http://localhost:8000/
   - Admin panel: http://localhost:8000/admin/

## 🔧 Development

### **Code Quality**
```bash
# Run linting
flake8 .

# Run tests
python manage.py test

# Run security checks
pip-audit

# Format code
black .
```

### **Database**
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (development only)
python manage.py flush
```

### **Static Files**
```bash
# Collect static files
python manage.py collectstatic

# Clear static files cache
python manage.py collectstatic --clear
```

## 🐳 Docker

### **Development**
```bash
docker-compose up --build
```

### **Production**
```bash
docker build -t nichmah-agrovet .
docker run -p 8000:8000 nichmah-agrovet
```

## 📚 Documentation

- Setup: see `docs/SETUP.md`
- Architecture: see `docs/ARCHITECTURE.md`
- Cart: see `docs/CART.md`
- Security: see `docs/SECURITY.md`
- API: REST API documentation (coming soon)
- Deployment: Production deployment guide (coming soon)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## 🔄 Recent Updates

### **Codebase Cleanup (September 4, 2025)**
- ✅ Restructured documentation with comprehensive guides and architecture docs
- ✅ Removed unused test cleanup command
- ✅ Updated TODO comments with implementation placeholders
- ✅ Verified no duplicate code exists (utilities properly centralized)
- ✅ Created code standards and development guidelines
- ✅ Enhanced project documentation structure

### **Documentation Improvements**
- ✅ Created comprehensive documentation structure in `docs/`
- ✅ Added Quick Start Guide for new developers
- ✅ Created Architecture Overview documentation
- ✅ Established Code Standards and best practices
- ✅ Added cleanup summary and recommendations

### **Security Enhancements**
- ✅ Created comprehensive security documentation
- ✅ Implemented secure environment variable management
- ✅ Added security settings configuration
- ✅ Enhanced logging and monitoring setup

---

**Built with ❤️ for NICMAH AGROVET**
