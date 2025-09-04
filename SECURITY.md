# Security

## 🔒 Security Measures

### Environment Variables
- All sensitive data uses environment variables
- No hardcoded secrets in source code
- `.env` file is gitignored

### Protected Files
- `.env` (environment variables)
- `db.sqlite3` (database)
- `media/` (uploaded files)
- `staticfiles/` (collected static files)
- `logs/` (log files)
- `venv/` (virtual environment)

### Database Security
- Development: SQLite (local only)
- Production: PostgreSQL (recommended)
- All credentials externalized

### Code Security
- No API keys in source code
- No passwords hardcoded
- No internal URLs exposed

## 🚨 Reporting Security Issues

If you discover a security vulnerability, please:
1. **DO NOT** create a public issue
2. Email: [your-email@domain.com]
3. Include detailed description of the issue
4. Provide steps to reproduce

## 🔐 Security Checklist

- [x] Environment variables used for all secrets
- [x] No hardcoded credentials
- [x] Database file gitignored
- [x] Media files gitignored
- [x] Log files gitignored
- [x] Virtual environment gitignored

**Status**: ✅ Secure for GitHub deployment

