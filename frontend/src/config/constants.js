// API and application constants
const ENV = import.meta.env;

export const API_CONFIG = {
  baseURL: ENV.VITE_API_BASE_URL || 'http://localhost:8001',
  timeout: parseInt(ENV.VITE_API_TIMEOUT) || 300000, // 5 minutes for embedding model loading on first upload
};

export const AUTH_CONFIG = {
  tokenKey: 'access_token',
  usernameKey: 'username',
  tokenType: 'bearer',
};

export const ROLES = {
  ADMIN: 'admin',
  USER: 'user',
};

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  USERNAME: 'username',
  REFRESH_TOKEN: 'refresh_token',
  USER_ROLES: 'user_roles',
};

export const UPLOAD_CONFIG = {
  maxFileSize: parseInt(ENV.VITE_MAX_FILE_SIZE) || 50 * 1024 * 1024, // 50MB
  allowedTypes: ['.csv', '.xlsx', '.xls', '.pdf'],
  allowedMimeTypes: [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/pdf',
  ],
};

export const QUERY_CONFIG = {
  defaultTopK: 6,
  maxTopK: 20,
  minTopK: 1,
  debounceMs: 300,
};

export const PAGINATION_CONFIG = {
  defaultPageSize: 100,
  pageSizes: [25, 50, 100, 200],
};

export const TOAST_CONFIG = {
  position: 'top-right',
  duration: 3000,
  style: {
    borderRadius: '12px',
    padding: '12px 16px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
  },
  success: {
    iconTheme: {
      primary: '#10b981',
      secondary: '#ffffff',
    },
  },
  error: {
    iconTheme: {
      primary: '#ef4444',
      secondary: '#ffffff',
    },
  },
};

export const REFRESH_INTERVALS = {
  documents: 10000,    // 10 seconds
  storage: 30000,      // 30 seconds
  health: 60000,       // 60 seconds
};

export const ROUTES = {
  home: '/',
  login: '/login',
  dataDashboard: '/data-dashboard',
  analyticsDashboard: '/analytics-dashboard',
};

export const DEMO_CREDENTIALS = [
  { username: 'admin', password: 'admin123' },
  { username: 'demo', password: 'demo123' },
  { username: 'user', password: 'user123' },
];

export default {
  API_CONFIG,
  AUTH_CONFIG,
  UPLOAD_CONFIG,
  QUERY_CONFIG,
  PAGINATION_CONFIG,
  TOAST_CONFIG,
  REFRESH_INTERVALS,
  ROUTES,
  DEMO_CREDENTIALS,
};
