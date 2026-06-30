// Keycloak configuration
const keycloak = new Keycloak({
    url: 'http://localhost:8080',
    realm: 'rag-realm',
    clientId: 'finance-app'
});

// Sample expense data (in-memory for demo)
let expenses = [
    { id: 1, title: 'Conference Trip', category: 'Travel', amount: 1250.00, description: 'Airfare and hotel for tech conference', submittedBy: 'Alice', status: 'pending', date: '2026-05-20' },
    { id: 2, title: 'Office Chairs', category: 'Office Supplies', amount: 450.00, description: 'Ergonomic chairs for new employees', submittedBy: 'Bob', status: 'approved', date: '2026-05-18' },
    { id: 3, title: 'Software License', category: 'Software', amount: 299.00, description: 'Annual IntelliJ IDEA license', submittedBy: 'Carol', status: 'approved', date: '2026-05-15' },
    { id: 4, title: 'Team Lunch', category: 'Other', amount: 180.00, description: 'Team building lunch event', submittedBy: 'Dave', status: 'rejected', date: '2026-05-12' },
    { id: 5, title: 'Cloud Services', category: 'Software', amount: 850.00, description: 'AWS hosting fees for Q2', submittedBy: 'Emily', status: 'pending', date: '2026-05-22' }
];

let nextExpenseId = 6;
let currentUser = null;
let isFinanceAdmin = false;

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

// Login with Keycloak (explicit login, do not use existing SSO session)
function loginWithKeycloak() {
    keycloak.login({
        redirectUri: window.location.href,
        prompt: 'login'
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
            isFinanceAdmin = roles.includes('finance_admin');

            // Enforce app-level authorization: require 'finance_user' or 'finance_admin'
            const hasFinanceAccess = roles.includes('finance_user') || roles.includes('finance_admin');
            if (!hasFinanceAccess) {
                showLoginPage();
                const errorEl = document.getElementById('loginError');
                if (errorEl) {
                    errorEl.textContent = 'Access denied: your account does not have permission to access the Finance app.';
                    errorEl.style.display = 'block';
                } else {
                    alert('Access denied: your account does not have permission to access the Finance app.');
                }
                return;
            }
            
            // Show main app
            showMainApp();
            
            // Update UI
            updateUserInfo(profile, roles);
            renderExpenses();
            updateStats();
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
    const roleText = isFinanceAdmin ? 'Finance Admin' : 'Finance User';
    
    document.getElementById('username').textContent = username;
    document.getElementById('userRole').textContent = roleText;
    document.getElementById('userRole').className = isFinanceAdmin ? 'user-role badge-admin' : 'user-role badge-user';
}

function updateStats() {
    const total = expenses.reduce((sum, exp) => sum + exp.amount, 0);
    const pending = expenses.filter(exp => exp.status === 'pending').length;
    const approved = expenses.filter(exp => exp.status === 'approved').length;
    const rejected = expenses.filter(exp => exp.status === 'rejected').length;
    
    document.getElementById('totalExpenses').textContent = `$${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('pendingCount').textContent = pending;
    document.getElementById('approvedCount').textContent = approved;
    document.getElementById('rejectedCount').textContent = rejected;
}

function renderExpenses() {
    const expenseList = document.getElementById('expenseList');
    
    if (expenses.length === 0) {
        expenseList.innerHTML = `
            <div class="empty-state">
                <p>💳 No expenses found</p>
                <p style="font-size: 0.875rem;">Submit your first expense to get started</p>
            </div>
        `;
        return;
    }
    
    // Sort by date (newest first)
    const sortedExpenses = [...expenses].sort((a, b) => new Date(b.date) - new Date(a.date));
    
    expenseList.innerHTML = sortedExpenses.map(exp => `
        <div class="expense-card" data-id="${exp.id}">
            <div class="expense-header">
                <div class="expense-info">
                    <h3>${exp.title}</h3>
                    <div class="expense-meta">
                        <span>📂 ${exp.category}</span>
                        <span>👤 ${exp.submittedBy}</span>
                        <span>📅 ${new Date(exp.date).toLocaleDateString()}</span>
                    </div>
                </div>
                <div>
                    <p class="amount">$${exp.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                    <span class="status-badge status-${exp.status}">${exp.status.toUpperCase()}</span>
                </div>
            </div>
            <p class="expense-description">${exp.description}</p>
            ${isFinanceAdmin && exp.status === 'pending' ? `
                <div class="expense-actions">
                    <button class="btn btn-success btn-approve" data-id="${exp.id}">✓ Approve</button>
                    <button class="btn btn-danger btn-reject" data-id="${exp.id}">✗ Reject</button>
                </div>
            ` : ''}
        </div>
    `).join('');
    
    // Attach event listeners for approve/reject (admin only)
    if (isFinanceAdmin) {
        document.querySelectorAll('.btn-approve').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                updateExpenseStatus(id, 'approved');
            });
        });
        
        document.querySelectorAll('.btn-reject').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.dataset.id);
                updateExpenseStatus(id, 'rejected');
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
    
    // Submit expense button (all users)
    document.getElementById('submitExpenseBtn').addEventListener('click', () => {
        document.getElementById('submitExpenseForm').style.display = 'block';
        document.getElementById('expenseForm').reset();
    });
    
    // Cancel button
    document.getElementById('cancelBtn').addEventListener('click', () => {
        document.getElementById('submitExpenseForm').style.display = 'none';
    });
    
    // Form submission
    document.getElementById('expenseForm').addEventListener('submit', (e) => {
        e.preventDefault();
        submitExpense();
    });
}

function submitExpense() {
    const title = document.getElementById('expTitle').value;
    const category = document.getElementById('expCategory').value;
    const amount = parseFloat(document.getElementById('expAmount').value);
    const description = document.getElementById('expDescription').value;
    
    const newExpense = {
        id: nextExpenseId++,
        title,
        category,
        amount,
        description,
        submittedBy: currentUser.username || currentUser.email || 'User',
        status: 'pending',
        date: new Date().toISOString().split('T')[0]
    };
    
    expenses.push(newExpense);
    renderExpenses();
    updateStats();
    
    // Hide form
    document.getElementById('submitExpenseForm').style.display = 'none';
    
    // Show success message
    alert(`✅ Expense "${title}" submitted successfully! It is now pending approval.`);
}

function updateExpenseStatus(id, status) {
    const expense = expenses.find(exp => exp.id === id);
    if (!expense) return;
    
    const action = status === 'approved' ? 'approve' : 'reject';
    if (confirm(`Are you sure you want to ${action} the expense "${expense.title}" ($${expense.amount})?`)) {
        expense.status = status;
        renderExpenses();
        updateStats();
        alert(`✅ Expense "${expense.title}" ${status === 'approved' ? 'approved' : 'rejected'} successfully!`);
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
