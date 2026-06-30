# HR Management System

## 🎯 Purpose
Demonstrates Keycloak SSO with role-based access control (RBAC) for HR operations.

## 🔑 Keycloak Roles

### `hr_admin`
- View all employees
- Add new employees
- Edit employee information
- Delete employees

### `hr_user`
- View all employees only
- No modification permissions

## 🚀 Running the App

### Option 1: Python HTTP Server
```bash
cd hr-app
python3 -m http.server 3001
```

### Option 2: Node.js HTTP Server
```bash
cd hr-app
npx http-server -p 3001
```

Then open: **http://localhost:3001**

## ✅ SSO Testing

1. **Login to HR App** → Redirects to Keycloak
2. **Open Finance App** (http://localhost:3002) → Automatically logged in
3. **Open RAG App** (http://localhost:5173) → Automatically logged in
4. **Logout from any app** → Logged out from all apps

## 👥 Test Users (Configure in Keycloak)

| User | HR Role | Finance Role | RAG Role |
|------|---------|--------------|----------|
| rohith | hr_admin | finance_admin | admin, user |
| alice | hr_admin | - | user |
| bob | hr_user | - | user |
| carol | - | finance_admin | user |
| dave | - | finance_user | user |

## 📋 Features

- **Employee Directory** - View all employees with position, department, email
- **Add Employee** (Admin only) - Form to add new employees
- **Edit Employee** (Admin only) - Modify employee information
- **Delete Employee** (Admin only) - Remove employees from directory
- **Session Monitoring** - Auto-logout when session expires
- **Cross-App SSO** - Single login for all apps

## 🔧 Keycloak Configuration

### Client Settings (hr-app)
- **Client ID**: `hr-app`
- **Root URL**: `http://localhost:3001`
- **Valid Redirect URIs**: `http://localhost:3001/*`
- **Web Origins**: `http://localhost:3001`
- **Access Type**: `public`

### Realm Roles
- `hr_admin`
- `hr_user`

## 🎨 Tech Stack

- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Authentication**: Keycloak JavaScript Adapter 24.0
- **Port**: 3001
- **Data**: In-memory (demo purposes)

## 📝 Notes

- Data is stored in-memory and resets on page refresh
- For production, connect to a backend API
- Keycloak must be running on port 8080
- Realm must be configured with `hr-app` client
