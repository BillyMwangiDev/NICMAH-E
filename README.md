# NICMAH - E-commerce & POS System

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive Django-based agricultural e-commerce platform with integrated Point of Sale (POS), inventory management, analytics, and educational hub.

## Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Security](#-security)
- [Contributing](#-contributing)
- [License](#-license)

## Features

### E-commerce
- Product catalog with categories and tags
- Advanced search and filtering
- Shopping cart with session persistence
- WhatsApp-based checkout integration
- Order management and tracking
- Product reviews and ratings

### Point of Sale (POS)
- Real-time sales processing
- Session management (opening/closing)
- Multiple payment methods (Cash, M-Pesa, Card, Mobile Money)
- Receipt generation (PDF) with company logo
- External receipt printer support (ESC/POS compatible)
- Commission tracking for sellers
- Offline mode support with sync
- Barcode scanning (manual and external scanner support)
- Auto-incrementing sale IDs

### Inventory Management
- Real-time stock tracking
- Low stock alerts
- Stock movement history
- Supplier management
- Purchase order system with preview
- Document generation (Receipts, Invoices, Quotations, Purchase Orders)
- Batch and expiry tracking
- Excel import/export functionality

### Analytics & Reporting
- Interactive dashboards with Chart.js
- Unified sales tracking (POS + E-commerce)
- Revenue and sales analytics
- Product performance metrics
- Customer insights
- Inventory turnover analysis
- Customizable date range reports (Daily, Weekly, Monthly, Annual)
- Export functionality (CSV, Excel, PDF)
- Growth percentage calculations
- Payment method breakdowns

### User Management
- Role-based access control (Customer, Seller, Manager, Admin)
- User profiles and authentication
- Seller performance tracking
- Customer segmentation

### Educational Hub
- Agricultural articles and guides
- Category-based content
- Search and filter functionality
- Content management system

### Modern UI/UX
- Responsive design with Tailwind CSS
- Agro-themed color palette
- Smooth animations and transitions
- Mobile-first approach
- Accessibility compliant (WCAG 2.1)

## Tech Stack

### Backend
- **Framework:** Django 5.2.5
- **Database:** PostgreSQL / SQLite (development)
- **Authentication:** Django built-in + Argon2 password hashing + JWT (djangorestframework-simplejwt)
- **API:** Django REST Framework with JWT authentication

### Frontend
- **CSS Framework:** Tailwind CSS 3.x (CDN)
- **JavaScript:** Vanilla JS with modern ES6+
- **Icons:** Font Awesome 6.6.0
- **Charts:** Chart.js

### DevOps & Tools
- **Version Control:** Git
- **CI/CD:** GitHub Actions
- **Containerization:** Docker & Docker Compose
- **Code Quality:** flake8, black, pylint
- **Testing:** pytest, coverage
- **Security:** pip-audit, django-csp-nonce

## Quick Start

### Prerequisites

- Python 3.11 or higher
- pip package manager
- Git
- PostgreSQL (for production)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/BillyMwangiDev/NICMAH-E.git
   cd NICMAH-E
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env with your configuration
   # Required variables:
   # - SECRET_KEY
   # - DEBUG
   # - DATABASE_URL
   # - ALLOWED_HOSTS
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Frontend: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin/
   - POS Dashboard: http://127.0.0.1:8000/pos/
   - Analytics: http://127.0.0.1:8000/analytics/

### Generate Sample Data (Optional)

To test the analytics dashboard with sample data:

```python
# Create a file: create_sample_data.py and run:
python manage.py shell < create_sample_data.py
```

## 📁 Project Structure

```
NICMAH-E/
├── nichmah_agrovet/          # Project settings
│   ├── settings.py           # Main settings
│   ├── security_settings.py  # Security configuration
│   ├── urls.py               # Root URL configuration
│   └── wsgi.py               # WSGI configuration
├── core/                     # Core app (base templates, mixins)
│   ├── templates/            # Base HTML templates
│   ├── static/               # CSS, JS, images
│   ├── mixins.py             # Reusable model/view mixins
│   └── utils.py              # Utility functions
├── users/                    # User management
│   ├── models.py             # Custom User model
│   ├── views.py              # Auth views
│   └── forms.py              # User forms
├── catalog/                  # Product catalog
│   ├── models.py             # Product, Category models
│   ├── views.py              # Catalog views
│   └── admin.py              # Admin configuration
├── pos/                      # Point of Sale
│   ├── models.py             # Sale, Session models
│   ├── views.py              # POS views
│   └── templates/            # POS templates
├── inventory/                # Inventory management
│   ├── models.py             # Stock models
│   └── views.py              # Inventory views
├── analytics/                # Analytics & reporting
│   ├── models.py             # Sales analytics models
│   ├── views.py              # Dashboard views
│   └── signals.py            # Sales tracking signals
├── orders/                   # Order management
│   ├── models.py             # Order models
│   └── views.py              # Order views
├── educational/              # Educational content
│   ├── models.py             # Article models
│   └── views.py              # Content views
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose setup
└── README.md                 # This file
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite for development)
DATABASE_URL=sqlite:///db.sqlite3

# Database (PostgreSQL for production)
# DATABASE_URL=postgresql://user:password@localhost:5432/nicmah_db

# Security
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Email Configuration (Optional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# WhatsApp Integration (Optional)
WHATSAPP_PHONE_NUMBER=+254700000000
```

### Security Settings

The project includes robust security configurations:

- **Content Security Policy (CSP)** - Protects against XSS attacks
- **Argon2 Password Hashing** - Industry-standard password security
- **Rate Limiting** - Prevents brute-force attacks
- **HTTPS Enforcement** - In production environments
- **Secure Headers** - X-Frame-Options, X-Content-Type-Options, etc.

## Development

### Code Quality

```bash
# Run linter
flake8 .

# Format code
black .

# Check for security issues
pip-audit

# Type checking (if using mypy)
mypy .

# Verify calculations and data integrity
python manage.py verify_calculations

# Check for unused imports (requires vulture)
vulture . --min-confidence 80
```

### Database Management

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (development only!)
python manage.py flush

# Create database backup
python manage.py dumpdata > backup.json

# Load database backup
python manage.py loaddata backup.json
```

### Static Files

```bash
# Collect static files
python manage.py collectstatic

# Clear static cache
python manage.py collectstatic --clear --noinput
```

### Custom Management Commands

```bash
# Check system configuration
python manage.py check --deploy

# Verify all calculations (sales, inventory, analytics)
python manage.py verify_calculations

# Fix calculation errors automatically
python manage.py verify_calculations --fix

# Update site settings
python manage.py update_site_name

# Create test data
python manage.py shell < create_sample_data.py
```

## Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test catalog

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report

# Run pytest (if configured)
pytest
pytest --cov=. --cov-report=html
```

### Test Structure

```
tests/
├── test_models.py
├── test_views.py
├── test_forms.py
└── test_integration.py
```

## Deployment

### Using Docker

#### Development Environment

```bash
# Using Docker Compose (includes PostgreSQL)
docker-compose up -d

# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Stop services
docker-compose down
```

#### Production Environment

```bash
# Using Production Docker Compose (includes PostgreSQL, Nginx, Redis)
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f web

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files (already done in Dockerfile.prod)
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Stop services
docker-compose -f docker-compose.prod.yml down
```

#### Docker Files Overview

- **`Dockerfile`** - Development Dockerfile (uses `requirements-dev.txt`)
- **`Dockerfile.prod`** - Production Dockerfile with multi-stage build (uses `requirements.txt`)
- **`docker-compose.yml`** - Development setup (PostgreSQL + Django)
- **`docker-compose.prod.yml`** - Production setup (PostgreSQL + Django + Nginx + Redis)

#### Requirements Files

- **`requirements.txt`** - Production dependencies only
- **`requirements-dev.txt`** - Includes production dependencies + development tools (testing, linting, etc.)

### Manual Deployment

1. **Prepare the server**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install dependencies
   sudo apt install python3-pip python3-venv postgresql nginx
   ```

2. **Set up the application**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd NICMAH-E

   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate

   # Install dependencies
   pip install -r requirements.txt

   # Configure environment
   cp .env.example .env
   # Edit .env for production
   ```

3. **Configure database**
   ```bash
   # Create PostgreSQL database
   sudo -u postgres psql
   CREATE DATABASE nicmah_db;
   CREATE USER nicmah_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE nicmah_db TO nicmah_user;
   \q

   # Run migrations
   python manage.py migrate
   ```

4. **Set up Gunicorn**
   ```bash
   pip install gunicorn
   gunicorn nichmah_agrovet.wsgi:application --bind 0.0.0.0:8000
   ```

5. **Configure Nginx**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location /static/ {
           alias /path/to/NICMAH-E/staticfiles/;
       }

       location /media/ {
           alias /path/to/NICMAH-E/media/;
       }

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### Environment-Specific Settings

- **Development:** `DEBUG=True`, SQLite database
- **Staging:** `DEBUG=False`, PostgreSQL, test data
- **Production:** `DEBUG=False`, PostgreSQL, SSL, monitoring

## Security

### Best Practices Implemented

- ✅ **Argon2 Password Hashing** - Industry-standard password security with fallback to PBKDF2
- ✅ **CSRF Protection** - Enabled on all forms and AJAX requests
- ✅ **Content Security Policy (CSP)** - Protects against XSS attacks via HTTP headers
- ✅ **SQL Injection Prevention** - Django ORM parameterized queries + custom middleware
- ✅ **XSS Protection** - Input sanitization and output escaping in templates
- ✅ **Secure Session Cookies** - HttpOnly, Secure flags in production
- ✅ **Rate Limiting** - Prevents brute-force attacks on authentication endpoints
- ✅ **Input Validation** - Server-side validation on all user inputs
- ✅ **Secure File Uploads** - File type validation, size limits, and secure storage
- ✅ **Environment Variable Management** - All secrets stored in `.env` file (never committed)
- ✅ **Security Headers** - X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security
- ✅ **Security Monitoring** - Logging of security events and suspicious activities

### Security Checklist

```bash
# Run Django security check
python manage.py check --deploy

# Audit dependencies for vulnerabilities
pip-audit

# Check for outdated packages
pip list --outdated

# Update dependencies safely
pip install --upgrade <package>

# Verify calculations and data integrity
python manage.py verify_calculations

# Check for code quality issues
flake8 .
black --check .
```

### Security Best Practices

1. **Never commit secrets** - Always use environment variables for sensitive data
2. **Keep dependencies updated** - Regularly run `pip-audit` and update packages
3. **Use HTTPS in production** - Configure SSL/TLS certificates
4. **Enable DEBUG=False in production** - Prevents information leakage
5. **Regular backups** - Backup database and media files regularly
6. **Monitor logs** - Review security logs for suspicious activities
7. **Strong passwords** - Enforce password complexity requirements
8. **Principle of least privilege** - Grant minimum necessary permissions
9. **Input validation** - Always validate and sanitize user inputs
10. **Output escaping** - Escape all user-generated content in templates

### Reporting Security Issues

Please report security vulnerabilities to: security@nicmahagrovet.com

**Responsible Disclosure:**
- Do not publicly disclose vulnerabilities
- Allow reasonable time for fixes before disclosure
- Provide detailed information about the vulnerability

## Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
   - Follow PEP 8 style guide
   - Add tests for new features
   - Update documentation
4. **Commit your changes**
   ```bash
   git commit -m "Add: amazing feature description"
   ```
5. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Commit Message Convention

```
Type: Brief description

Detailed explanation (optional)

Types:
- Add: New feature
- Fix: Bug fix
- Update: Changes to existing features
- Remove: Remove code/features
- Docs: Documentation changes
- Style: Code style changes
- Refactor: Code refactoring
- Test: Add or update tests
```

### Code Standards

- **Follow PEP 8** - Python code style guide
- **Type Hints** - Use type hints where appropriate for better code clarity
- **Docstrings** - Write docstrings for all functions, classes, and modules
- **Single Responsibility** - Keep functions small and single-purpose
- **Meaningful Names** - Use descriptive variable and function names
- **Comments** - Add comments for complex logic, not obvious code
- **DRY Principle** - Don't Repeat Yourself - extract common code to utilities
- **No Hardcoded Values** - Use constants or configuration for magic numbers/strings
- **Error Handling** - Always handle exceptions appropriately
- **Code Review** - All code must be reviewed before merging

### Code Cleanup Best Practices

1. **Remove Unused Code** - Delete unused imports, functions, and variables
2. **Eliminate Duplicates** - Extract common patterns to shared utilities (e.g., CSRF token functions in `core/static/js/main.js`)
3. **Consolidate Imports** - Group imports logically (standard library, third-party, local)
4. **Remove Dead Code** - Delete commented-out code and unused files
5. **Optimize Queries** - Use `select_related()` and `prefetch_related()` to reduce database queries
6. **Cache Expensive Operations** - Cache frequently accessed data
7. **Use Database Indexes** - Add indexes for frequently queried fields
8. **Validate Data Integrity** - Run `verify_calculations` command regularly
9. **Centralize Utilities** - Shared JavaScript functions in `window.NICMAH` namespace
10. **Database Consistency** - All data fetched from database, no mock data in production code

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

Need help? Here's how to get support:

- **Documentation:** Check this README and inline code documentation
- **Issues:** [Create an issue](https://github.com/BillyMwangiDev/NICMAH-E/issues)
- **Email:** support@nicmahagrovet.com
- **Community:** Join our discussions

## Acknowledgments

- Django community for the excellent framework
- Tailwind CSS for the beautiful UI components
- Chart.js for data visualization
- All contributors and supporters

## Recent Updates

### Database & Data Integrity
- ✅ All data operations use SQLite/PostgreSQL (no mock data)
- ✅ Unified Sales model for tracking all sales (POS + E-commerce)
- ✅ JSONField converted to TextField for SQLite compatibility
- ✅ Calculation verification command (`verify_calculations`)
- ✅ Data synchronization command (`sync_unified_sales`)

### UI/UX Improvements
- ✅ Modern Tailwind CSS design across all pages
- ✅ Responsive layouts for mobile and desktop
- ✅ Company logo integration in all documents
- ✅ Consistent branding (NICMAH) throughout
- ✅ Improved POS dashboard and analytics pages

### Code Quality
- ✅ Removed duplicate code (CSRF token utilities centralized)
- ✅ Removed unused imports and dead code
- ✅ Optimized database queries (select_related, prefetch_related)
- ✅ Consistent error handling
- ✅ Security best practices implemented

### Features Added
- ✅ JWT authentication with token rotation
- ✅ External receipt printer support
- ✅ Enhanced barcode scanner detection
- ✅ Purchase order preview functionality
- ✅ Sales report pagination and filtering

## Project Status

- ✅ Core functionality complete
- ✅ POS system operational with offline support
- ✅ Analytics dashboard functional with unified sales tracking
- ✅ Security hardening implemented (JWT, CSRF, rate limiting)
- ✅ Document generation (PDF) with company branding
- ✅ Database integrity verified
- ✅ Code cleanup and optimization complete
- 📅 Mobile app (in progress)
- 📅 API documentation (planned)
- 📅 Multi-language support (planned)

---

**Built for NICMAH**

*Empowering Kenyan Agriculture Through Technology*
