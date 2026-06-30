// Keycloak configuration
const keycloak = new Keycloak({
    url: 'http://localhost:8080',
    realm: 'rag-realm',
    clientId: 'hr-app'
});

// Sample employee data (in-memory for demo)
let employees = [
    { id: 1, name: 'John Smith', position: 'Senior Developer', department: 'Engineering', email: 'john.smith@company.com' },
    { id: 2, name: 'Sarah Johnson', position: 'HR Manager', department: 'HR', email: 'sarah.j@company.com' },
    { id: 3, name: 'Mike Davis', position: 'Sales Lead', department: 'Sales', email: 'mike.d@company.com' },
    { id: 4, name: 'Emily Chen', position: 'Marketing Director', department: 'Marketing', email: 'emily.c@company.com' },
    { id: 5, name: 'Robert Taylor', position: 'Finance Analyst', department: 'Finance', email: 'robert.t@company.com' }
];

let nextEmployeeId = 6;
let currentUser = null;
let isHrAdmin = false;

// Show login page
function showLoginPage() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('loginPage').style.display = 'flex';
    document.getElementById('app').style.display = 'none';
}

// Show main app
function showMainApp() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('loginPage').style.display = 'none';
    document.getElementById('app').style.display = 'flex';
}

// Login with Keycloak
function loginWithKeycloak() {
    keycloak.login({
        redirectUri: window.location.href,
        prompt: 'login' // force explicit user auth for this client
    }).catch(error => {
        console.error('Login failed:', error);
        alert('Login failed. Please try again.');
    });
}

// Initialize Keycloak
keycloak.init({
    onLoad: 'none',  // Do not auto-check SSO on load — require explicit login
    checkLoginIframe: false,
    pkceMethod: 'S256'
}).then(authenticated => {
    if (authenticated) {
        // User is logged in - show main app
        keycloak.loadUserProfile().then(profile => {
            currentUser = profile;
            
            // Extract roles
            const roles = keycloak.tokenParsed?.realm_access?.roles || [];
            isHrAdmin = roles.includes('hr_admin');

            // Enforce application-level authorization: only users with 'hr_user' or 'hr_admin' may use this app
            const hasHrAccess = roles.includes('hr_user') || roles.includes('hr_admin');
            if (!hasHrAccess) {
                // Show login page with access denied message (do not log user out of Keycloak)
                showLoginPage();
                const errorEl = document.getElementById('loginError');
                if (errorEl) {
                    errorEl.textContent = 'Access denied: your account does not have permission to access the HR app.';
                    errorEl.style.display = 'block';
                } else {
                    alert('Access denied: your account does not have permission to access the HR app.');
                }
                return;
            }
            
            // Show main app
            showMainApp();
            
            // Update UI
            updateUserInfo(profile, roles);
            renderEmployees();
            setupEventListeners();
            
            // Auto-refresh token
            setInterval(() => {
                keycloak.updateToken(70).catch(() => {
                    console.log('Failed to refresh token');
                });
            }, 60000);
        });
    } else {
        // User is not logged in - show login page
        showLoginPage();
    }
}).catch(error => {
    console.error('Keycloak initialization failed:', error);
    showLoginPage();
    const errorEl = document.getElementById('loginError');
    if (errorEl) {
        errorEl.textContent = 'Failed to connect to authentication server. Please try again.';
        errorEl.style.display = 'block';
    }
});

// Logout handler
keycloak.onAuthLogout = () => {
    console.log('User logged out from another tab');
    window.location.reload();
};

function updateUserInfo(profile, roles) {
    const username = profile.username || profile.email || 'User';
    const roleText = isHrAdmin ? 'HR Admin' : 'HR User';
    
    document.getElementById('username').textContent = username;
    document.getElementById('userRole').textContent = roleText;
    document.getElementById('userRole').className = isHrAdmin ? 'user-role badge-admin' : 'user-role badge-user';
    
    // Show add employee button only for admins
    if (isHrAdmin) {
        document.getElementById('addEmployeeBtn').style.display = 'block';
    }
}

function renderEmployees() {
    const employeeList = document.getElementById('employeeList');
    
    if (employees.length === 0) {
        employeeList.innerHTML = `
            <div class="empty-state">
                <p>📋 No employees found</p>
                <p style="font-size: 0.875rem;">Add your first employee to get started</p>
            </div>
        `;
        return;
    }
    
    employeeList.innerHTML = employees.map(emp => `
        <div class="employee-card" data-id="${emp.id}">
            <div class="employee-info">
                <h3>${emp.name}</h3>
                <div class="employee-details">
                    <span>📍 ${emp.position}</span>
                    <span>🏢 ${emp.department}</span>
                    <span>📧 ${emp.email}</span>
                </div>
            </div>
            <div class="employee-actions">
                ${isHrAdmin ? `
                    <button class="btn btn-secondary btn-edit" data-id="${emp.id}">Edit</button>
                    <button class="btn btn-danger btn-delete" data-id="${emp.id}">Delete</button>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // Attach delete event listeners
    if (isHrAdmin) {
        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                deleteEmployee(id);
            });
        });
    }
}

function setupEventListeners() {
    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', () => {
        keycloak.logout({
            redirectUri: window.location.origin + '/'
        });
    });
    
    // Add employee button (admin only)
    if (isHrAdmin) {
        document.getElementById('addEmployeeBtn').addEventListener('click', () => {
            document.getElementById('addEmployeeForm').style.display = 'block';
            document.getElementById('employeeForm').reset();
        });
        
        // Cancel button
        document.getElementById('cancelBtn').addEventListener('click', () => {
            document.getElementById('addEmployeeForm').style.display = 'none';
        });
        
        // Form submission
        document.getElementById('employeeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            addEmployee();
        });
    }
}

function addEmployee() {
    const name = document.getElementById('empName').value;
    const position = document.getElementById('empPosition').value;
    const department = document.getElementById('empDepartment').value;
    const email = document.getElementById('empEmail').value;
    
    const newEmployee = {
        id: nextEmployeeId++,
        name,
        position,
        department,
        email
    };
    
    employees.push(newEmployee);
    renderEmployees();
    
    // Hide form
    document.getElementById('addEmployeeForm').style.display = 'none';
    
    // Show success message
    alert(`✅ Employee "${name}" added successfully!`);
}

function deleteEmployee(id) {
    const employee = employees.find(emp => emp.id === id);
    if (!employee) return;
    
    if (confirm(`Are you sure you want to delete employee "${employee.name}"?`)) {
        employees = employees.filter(emp => emp.id !== id);
        renderEmployees();
        alert(`✅ Employee "${employee.name}" deleted successfully!`);
    }
}

// Refresh token periodically
setInterval(() => {
    keycloak.updateToken(70).then(refreshed => {
        if (refreshed) {
            console.log('Token refreshed');
        }
    }).catch(() => {
        console.error('Failed to refresh token');
        keycloak.logout();
    });
}, 60000); // Every minute
