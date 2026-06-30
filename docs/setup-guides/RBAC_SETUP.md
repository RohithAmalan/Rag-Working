# Role-Based Access Control (RBAC) Setup Guide

## 🎯 Overview

This RAG application implements Role-Based Access Control (RBAC) to restrict certain operations based on user roles.

### Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full access - Upload, Delete, Query, View documents, Analytics |
| **user** | Limited access - Query and View documents only (read-only) |

## 🔐 Backend Implementation

### Protected Endpoints

#### Admin Only (403 if not admin):
- `POST /upload` - Upload documents
- `DELETE /documents/{document_id}` - Delete document by ID
- `DELETE /documents/by-name/{file_name}` - Delete document by filename

#### Authenticated Users (401 if not logged in):
- `POST /query` - Query documents  
- `GET /documents` - List all documents
- `GET /documents/preview/{file_name}` - Preview file data
- `GET /documents/analytics/{file_name}` - View analytics

### Dependencies

```python
from app.utils.dependencies import require_admin, require_user, get_current_user

# Admin only
async def upload_documents(
    files: list[UploadFile],
    current_user: dict = Depends(require_admin)  # ✅ Admin check
):
    ...

# Any authenticated user
async def query_documents(
    payload: QueryRequest,
    current_user: dict = Depends(require_user)  # ✅ Auth check
):
    ...
```

## 🔧 Keycloak Role Setup

### Step 1: Create Realm Roles

1. Go to Keycloak Admin: http://localhost:8080/admin
2. Select **rag-realm**
3. Go to **Realm roles** (left sidebar)
4. Click **Create role**
5. Create two roles:
   - **Role name**: `admin`  
     **Description**: Administrator with full access
   - **Role name**: `user`  
     **Description**: Standard user with read-only access

### Step 2: Assign Roles to Users

1. Go to **Users** (left sidebar)
2. Click on a user (e.g., `admin`)
3. Go to **Role mapping** tab
4. Click **Assign role**
5. Select **Filter by realm roles**
6. Assign appropriate roles:
   - For admin users: Select both `admin` and `user` roles
   - For regular users: Select only `user` role
7. Click **Assign**

### Step 3: Include Roles in Token

Roles are automatically included in the JWT token under:
```json
{
  "realm_access": {
    "roles": ["admin", "user", "offline_access"]
  }
}
```

The backend extracts these roles during token verification.

## 🎨 Frontend Role Handling

### Store Roles in App State

After login, store user roles:

```javascript
// In App.jsx
const [userRoles, setUserRoles] = useState([]);

const handleLogin = async (credentials) => {
  const response = await loginUser(credentials);
  
  // Store roles from login response
  setUserRoles(response.roles || []);
  localStorage.setItem('user_roles', JSON.stringify(response.roles));
  
  setIsAuthenticated(true);
  setUsername(response.username);
};
```

### Conditional UI Rendering

```javascript
// Check if user is admin
const isAdmin = userRoles.includes('admin');

// Hide upload button for non-admins
{isAdmin && (
  <button onClick={handleUpload}>
    Upload Documents
  </button>
)}

// Hide delete buttons for non-admins
{isAdmin && (
  <button onClick={() => handleDelete(doc.id)}>
    Delete
  </button>
)}
```

### Handle 403 Errors

```javascript
try {
  await uploadFiles(files);
} catch (error) {
  if (error.response?.status === 403) {
    toast.error("Admin access required");
  }
}
```

## 📝 Testing RBAC

### Test 1: Admin User
```bash
# Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Response includes roles:
{
  "access_token": "...",
  "roles": ["admin", "user"],
  "username": "admin"
}

# Try admin action (should work)
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer <token>" \
  -F "files=@test.csv"
# ✅ Success
```

### Test 2: Regular User
```bash
# Login as regular user
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"user123"}'

# Response:
{
  "access_token": "...",
  "roles": ["user"],
  "username": "user"
}

# Try admin action (should fail)
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer <token>" \
  -F "files=@test.csv"
# ❌ 403 Forbidden: "Admin access required"

# Try user action (should work)
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the total sales?"}'
# ✅ Success
```

## 🚨 Error Responses

### 401 Unauthorized
User is not authenticated (missing or invalid token):
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
User is authenticated but lacks required role:
```json
{
  "detail": "Admin access required. You do not have permission to perform this action."
}
```

## 🔍 Checking User Roles

### Via API
```bash
# Verify token and get user info including roles
curl -X GET http://localhost:8000/auth/verify \
  -H "Authorization: Bearer <your_token>"

# Response:
{
  "username": "admin",
  "roles": ["admin", "user"],
  "is_active": true
}
```

### Via Keycloak Admin
1. Go to **Users** → Select user
2. Go to **Role mapping** tab
3. View **Assigned roles**

## 📦 Legacy Auth (No Keycloak)

When Keycloak is disabled, roles are assigned based on username:

- Username `admin` → roles: `["admin", "user"]`
- Any other username → roles: `["user"]`

This ensures RBAC works even without Keycloak!

## ✅ Quick Setup Checklist

- [ ] Create `admin` and `user` roles in Keycloak
- [ ] Assign roles to users in Keycloak
- [ ] Backend returns roles in login response
- [ ] Frontend stores roles in state/localStorage
- [ ] Frontend conditionally renders admin UI elements
- [ ] Backend protects admin endpoints with `require_admin`
- [ ] Test with both admin and non-admin users

---

**Now you have full RBAC! 🎉**

Admins can upload and delete, users can only query and view!
