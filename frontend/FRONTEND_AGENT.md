# Frontend AI Agent Instructions

You are working on the **frontend** of a production-style RAG application.

==================================================
🎯 PROJECT PURPOSE
==================================================

Build a modern, responsive React frontend for a Retrieval-Augmented Generation (RAG) system.

The frontend must support:
- User authentication via Keycloak SSO
- File uploads (CSV, Excel, PDF)
- Interactive RAG queries with chat interface
- Document management
- Role-based UI rendering
- Real-time response streaming (future)

==================================================
🧠 TECH STACK
==================================================

Frontend:
- React 18+
- Vite (build tool)
- Tailwind CSS (styling)
- Keycloak JS (authentication)
- React Router (navigation)
- Axios (HTTP client)
- Lucide React (icons)
- shadcn/ui (component library - optional)

==================================================
📂 ARCHITECTURE RULES
==================================================

Follow component-based architecture.

Preferred structure:

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── main.jsx                # App entry point
│   ├── App.jsx                 # Root component
│   ├── pages/                  # Page components
│   │   ├── Login.jsx          # Login page
│   │   ├── Dashboard.jsx      # Main dashboard
│   │   ├── Upload.jsx         # File upload page
│   │   ├── Query.jsx          # RAG query page
│   │   └── Documents.jsx      # Document management
│   ├── components/             # Reusable components
│   │   ├── Navbar.jsx         # Navigation bar
│   │   ├── Sidebar.jsx        # Sidebar navigation
│   │   ├── FileUpload.jsx     # File upload component
│   │   ├── ChatInterface.jsx  # Chat UI
│   │   ├── MessageBubble.jsx  # Chat message
│   │   ├── DocumentCard.jsx   # Document display card
│   │   ├── UploadPanel.jsx    # Upload panel
│   │   └── ProtectedRoute.jsx # Route guard
│   ├── hooks/                  # Custom React hooks
│   │   ├── useAuth.jsx        # Authentication hook
│   │   ├── useUpload.jsx      # File upload hook
│   │   └── useQuery.jsx       # RAG query hook
│   ├── services/               # API services
│   │   ├── api.js             # API client configuration
│   │   ├── authService.js     # Auth API calls
│   │   ├── uploadService.js   # Upload API calls
│   │   └── queryService.js    # Query API calls
│   ├── utils/                  # Utility functions
│   │   ├── constants.js       # Constants
│   │   ├── helpers.js         # Helper functions
│   │   └── validators.js      # Input validation
│   ├── styles/                 # CSS files
│   │   └── index.css          # Global styles + Tailwind
│   └── config/                 # Configuration
│       └── keycloak.js        # Keycloak config
├── index.html                  # HTML template
├── vite.config.js             # Vite configuration
├── tailwind.config.js         # Tailwind configuration
├── postcss.config.js          # PostCSS configuration
├── package.json               # NPM dependencies
└── .env                       # Environment variables
```

Rules:
- Keep components small and focused (< 200 lines)
- One component per file
- Use functional components with hooks
- Separate business logic from UI
- Reuse components wherever possible
- Follow React best practices

==================================================
🎨 UI/UX REQUIREMENTS
==================================================

**Design Principles**:
- Clean and modern interface
- Responsive design (mobile-first)
- Intuitive navigation
- Clear visual hierarchy
- Accessible (WCAG 2.1 AA)
- Fast and performant

**Color Scheme** (customizable):
- Primary: Blue (#3B82F6)
- Secondary: Gray (#6B7280)
- Success: Green (#10B981)
- Error: Red (#EF4444)
- Warning: Yellow (#F59E0B)

**Layout**:
- Navbar (top) - Logo, navigation, user menu
- Sidebar (left) - Main navigation
- Content area (center) - Main content
- Footer (bottom) - Optional

**Key Pages**:

1. **Login Page**
   - Keycloak SSO button
   - Clean, centered design
   - Company logo/branding

2. **Dashboard**
   - Welcome message
   - Quick stats (files uploaded, queries made)
   - Recent activity

3. **Upload Page**
   - Drag-and-drop file upload
   - File type validation
   - Upload progress bar
   - Success/error messages

4. **Query Page**
   - Chat-style interface
   - Input field for questions
   - Message history
   - Source citations
   - Copy/share functionality

5. **Documents Page**
   - List of uploaded files
   - Search and filter
   - Delete functionality (admin only)
   - Download option

==================================================
🔐 AUTHENTICATION & AUTHORIZATION
==================================================

**Keycloak Integration**:

```javascript
// src/config/keycloak.js
import Keycloak from 'keycloak-js';

const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
};

const keycloak = new Keycloak(keycloakConfig);

export default keycloak;
```

**useAuth Hook**:
```javascript
// src/hooks/useAuth.jsx
import { useState, useEffect } from 'react';
import keycloak from '../config/keycloak';

export const useAuth = () => {
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    keycloak.init({ onLoad: 'login-required' })
      .then((auth) => {
        setAuthenticated(auth);
        if (auth) {
          setUser({
            username: keycloak.tokenParsed?.preferred_username,
            email: keycloak.tokenParsed?.email,
            roles: keycloak.tokenParsed?.realm_access?.roles || [],
          });
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const logout = () => {
    keycloak.logout();
  };

  return { authenticated, user, loading, logout, token: keycloak.token };
};
```

**Role-Based UI**:
```jsx
// Show upload button only for admins
{user?.roles?.includes('admin') && (
  <button onClick={handleUpload}>Upload File</button>
)}
```

==================================================
📡 API INTEGRATION
==================================================

**API Client Setup**:
```javascript
// src/services/api.js
import axios from 'axios';
import keycloak from '../config/keycloak';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    if (keycloak.token) {
      config.headers.Authorization = `Bearer ${keycloak.token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await keycloak.updateToken(30);
      error.config.headers.Authorization = `Bearer ${keycloak.token}`;
      return api.request(error.config);
    }
    return Promise.reject(error);
  }
);

export default api;
```

**API Services**:
```javascript
// src/services/uploadService.js
import api from './api';

export const uploadFile = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total
      );
      onProgress?.(percentCompleted);
    },
  });
};

export const getDocuments = async () => {
  const response = await api.get('/documents');
  return response.data;
};

export const deleteDocument = async (fileId) => {
  return api.delete(`/documents/${fileId}`);
};
```

```javascript
// src/services/queryService.js
import api from './api';

export const sendQuery = async (query, fileHints = []) => {
  const response = await api.post('/query', {
    query,
    file_hints: fileHints,
    top_k: 5,
  });
  return response.data;
};
```

==================================================
🎯 COMPONENT PATTERNS
==================================================

**File Upload Component**:
```jsx
// src/components/FileUpload.jsx
import { useState } from 'react';
import { Upload, CheckCircle, XCircle } from 'lucide-react';
import { uploadFile } from '../services/uploadService';

export default function FileUpload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    
    // Validate file type
    const validTypes = ['.csv', '.xlsx', '.xls', '.pdf'];
    const fileExt = selectedFile.name.substring(
      selectedFile.name.lastIndexOf('.')
    );
    
    if (!validTypes.includes(fileExt.toLowerCase())) {
      setError('Invalid file type. Please upload CSV, Excel, or PDF files.');
      return;
    }
    
    // Validate file size (max 10MB)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size must be less than 10MB');
      return;
    }
    
    setFile(selectedFile);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setError(null);
    setSuccess(false);
    
    try {
      await uploadFile(file, setProgress);
      setSuccess(true);
      setFile(null);
      setProgress(0);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow">
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <input
          type="file"
          onChange={handleFileChange}
          accept=".csv,.xlsx,.xls,.pdf"
          className="mt-4"
        />
      </div>
      
      {file && (
        <div className="mt-4">
          <p className="text-sm text-gray-600">
            Selected: {file.name}
          </p>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-2 w-full bg-blue-500 text-white py-2 rounded"
          >
            {uploading ? `Uploading... ${progress}%` : 'Upload'}
          </button>
        </div>
      )}
      
      {uploading && (
        <div className="mt-2 bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
      
      {success && (
        <div className="mt-4 flex items-center text-green-600">
          <CheckCircle className="mr-2" />
          File uploaded successfully!
        </div>
      )}
      
      {error && (
        <div className="mt-4 flex items-center text-red-600">
          <XCircle className="mr-2" />
          {error}
        </div>
      )}
    </div>
  );
}
```

**Chat Interface Component**:
```jsx
// src/components/ChatInterface.jsx
import { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import { sendQuery } from '../services/queryService';
import MessageBubble from './MessageBubble';

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendQuery(input);
      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))}
        {loading && (
          <div className="text-gray-500">Thinking...</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your data..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </form>
    </div>
  );
}
```

==================================================
🧹 CODING STANDARDS
==================================================

**React Best Practices**:
- Use functional components with hooks
- Keep components pure when possible
- Use PropTypes or TypeScript for type checking
- Destructure props
- Use meaningful variable names
- Add comments for complex logic
- Follow single responsibility principle

**Example Component**:
```jsx
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

/**
 * DocumentCard component displays uploaded document information
 * with actions (view, delete).
 */
export default function DocumentCard({ document, onDelete }) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm('Are you sure?')) return;
    
    setDeleting(true);
    try {
      await onDelete(document.id);
    } catch (error) {
      console.error('Delete failed:', error);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="p-4 border rounded-lg shadow-sm hover:shadow-md transition">
      <h3 className="font-semibold">{document.filename}</h3>
      <p className="text-sm text-gray-600">{document.file_type}</p>
      <button
        onClick={handleDelete}
        disabled={deleting}
        className="mt-2 text-red-500 hover:text-red-700"
      >
        {deleting ? 'Deleting...' : 'Delete'}
      </button>
    </div>
  );
}

DocumentCard.propTypes = {
  document: PropTypes.shape({
    id: PropTypes.string.isRequired,
    filename: PropTypes.string.isRequired,
    file_type: PropTypes.string.isRequired,
  }).isRequired,
  onDelete: PropTypes.func.isRequired,
};
```

==================================================
🎨 STYLING RULES
==================================================

**Tailwind CSS**:
- Use Tailwind utility classes
- Create custom components for repeated patterns
- Use responsive prefixes (sm:, md:, lg:)
- Follow mobile-first approach
- Extract common styles to components

**Common Patterns**:
```jsx
// Button
<button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 
                   transition disabled:opacity-50 disabled:cursor-not-allowed">
  Click Me
</button>

// Card
<div className="p-6 bg-white rounded-lg shadow-md hover:shadow-lg transition">
  Content
</div>

// Input
<input className="w-full px-4 py-2 border border-gray-300 rounded-lg 
                  focus:outline-none focus:ring-2 focus:ring-blue-500" />

// Container
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
  Content
</div>
```

==================================================
🚀 PERFORMANCE OPTIMIZATION
==================================================

**Best Practices**:
1. Use React.memo for expensive components
2. Use useMemo/useCallback appropriately
3. Lazy load routes with React.lazy
4. Optimize images (use WebP, lazy loading)
5. Code splitting with dynamic imports
6. Debounce search inputs
7. Virtual scrolling for long lists

**Example**:
```jsx
import { useMemo, useCallback } from 'react';

// Memoize expensive calculations
const filteredDocs = useMemo(() => {
  return documents.filter(doc => 
    doc.filename.toLowerCase().includes(search.toLowerCase())
  );
}, [documents, search]);

// Memoize callbacks
const handleDelete = useCallback((id) => {
  deleteDocument(id);
}, []);
```

==================================================
🧪 TESTING (Optional)
==================================================

Use Vitest or Jest for unit tests:
```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import FileUpload from './FileUpload';

describe('FileUpload', () => {
  it('renders upload button', () => {
    render(<FileUpload />);
    expect(screen.getByText(/upload/i)).toBeInTheDocument();
  });

  it('validates file type', () => {
    render(<FileUpload />);
    const input = screen.getByLabelText(/file/i);
    const invalidFile = new File(['content'], 'test.txt', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [invalidFile] } });
    expect(screen.getByText(/invalid file type/i)).toBeInTheDocument();
  });
});
```

==================================================
🎯 GOAL
==================================================

Generate clean, modern, production-ready frontend code for a RAG application with:

✅ Seamless Keycloak SSO authentication
✅ Intuitive file upload interface
✅ Interactive chat-style RAG queries
✅ Role-based UI rendering
✅ Responsive design (mobile-first)
✅ Clean and maintainable code
✅ Excellent user experience
✅ Performance optimization
✅ Accessibility compliance

Focus on user experience, code quality, and modern React patterns.
