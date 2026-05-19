// Theme colors and constants
export const colors = {
  // Primary colors
  ink: '#1a1a1a',
  coral: '#ff6b6b',
  accent: '#4ecdc4',
  mint: '#95e1d3',
  sky: '#48dbfb',
  
  // Neutral colors
  white: '#ffffff',
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
  
  // Semantic colors
  success: '#10b981',
  error: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',
};

export const gradients = {
  background: 'radial-gradient(circle at top right, #fff1df, #dff8ff 40%, #f4f4f5 75%)',
  skyCard: 'linear-gradient(to bottom right, rgba(72, 219, 251, 0.1), transparent)',
  mintCard: 'linear-gradient(to bottom right, rgba(149, 225, 211, 0.1), transparent)',
  inkButton: 'linear-gradient(to right, #1a1a1a, rgba(26, 26, 26, 0.8))',
};

export const spacing = {
  xs: '0.25rem',    // 4px
  sm: '0.5rem',     // 8px
  md: '1rem',       // 16px
  lg: '1.5rem',     // 24px
  xl: '2rem',       // 32px
  '2xl': '3rem',    // 48px
};

export const borderRadius = {
  sm: '0.5rem',     // 8px
  md: '0.75rem',    // 12px
  lg: '1rem',       // 16px
  xl: '1.5rem',     // 24px
  '2xl': '2rem',    // 32px
  '3xl': '3rem',    // 48px
  full: '9999px',
};

export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
};

export const fontSizes = {
  xs: '0.75rem',    // 12px
  sm: '0.875rem',   // 14px
  base: '1rem',     // 16px
  lg: '1.125rem',   // 18px
  xl: '1.25rem',    // 20px
  '2xl': '1.5rem',  // 24px
  '3xl': '1.875rem',// 30px
  '4xl': '2.25rem', // 36px
};

export const transitions = {
  fast: 'all 0.15s ease',
  normal: 'all 0.2s ease',
  slow: 'all 0.3s ease',
};

export default {
  colors,
  gradients,
  spacing,
  borderRadius,
  shadows,
  fontSizes,
  transitions,
};
