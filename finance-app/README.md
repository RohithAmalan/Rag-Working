# Finance Management System

## 🎯 Purpose
Demonstrates Keycloak SSO with role-based access control (RBAC) for expense management.

## 🔑 Keycloak Roles

### `finance_admin`
- View all expenses
- Approve pending expenses
- Reject pending expenses
- Submit new expenses

### `finance_user`
- View all expenses
- Submit new expenses
- No approval/rejection permissions

## 🚀 Running the App

### Option 1: Python HTTP Server
```bash
cd finance-app
python3 -m http.server 3002
```

### Option 2: Node.js HTTP Server
```bash
cd finance-app
npx http-server -p 3002
```

Then open: **http://localhost:3002**

## ✅ SSO Testing

1. **Login to Finance App** → Redirects to Keycloak
2. **Open HR App** (http://localhost:3001) → Automatically logged in
3. **Open RAG App** (http://localhost:5173) → Automatically logged in
4. **Logout from any app** → Logged out from all apps

## 👥 Test Users (Configure in Keycloak)

| User | Finance Role | HR Role | RAG Role |
|------|--------------|---------|----------|
| rohith | finance_admin | hr_admin | admin, user |
| alice | - | hr_admin | user |
| bob | - | hr_user | user |
| carol | finance_admin | - | user |
| dave | finance_user | - | user |

## 📋 Features

### Dashboard Stats
- **Total Expenses** - Sum of all expense amounts
- **Pending Count** - Expenses awaiting approval
- **Approved Count** - Approved expenses
- **Rejected Count** - Rejected expenses

### Expense Management
- **View Expenses** - All users can see expense list
- **Submit Expense** - All users can submit new expenses
- **Approve/Reject** (Admin only) - Review and approve/reject pending expenses
- **Status Tracking** - Pending, Approved, Rejected badges

### Expense Categories
- Travel
- Office Supplies
- Software
- Training
- Equipment
- Other

## 🔧 Keycloak Configuration

### Client Settings (finance-app)
- **Client ID**: `finance-app`
- **Root URL**: `http://localhost:3002`
- **Valid Redirect URIs**: `http://localhost:3002/*`
- **Web Origins**: `http://localhost:3002`
- **Access Type**: `public`

### Realm Roles
- `finance_admin`
- `finance_user`

## 🎨 Tech Stack

- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Authentication**: Keycloak JavaScript Adapter 24.0
- **Port**: 3002
- **Data**: In-memory (demo purposes)

## 💡 Workflow Example

### Finance User Workflow
1. Login to app
2. View expense dashboard
3. Submit new expense
4. Wait for admin approval

### Finance Admin Workflow
1. Login to app
2. View all pending expenses
3. Review expense details
4. Approve or reject expenses
5. Track expense statistics

## 📝 Notes

- Data is stored in-memory and resets on page refresh
- For production, connect to a backend API
- Keycloak must be running on port 8080
- Realm must be configured with `finance-app` client
- Expenses default to "pending" status when submitted
