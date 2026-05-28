/**
 * Authentication hook for role-based access control
 * 
 * Provides utilities to check user roles from stored token
 */

import { useState, useEffect } from 'react';

export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get user info from localStorage (set during login)
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      try {
        const parsedUser = JSON.parse(userData);
        setUser(parsedUser);
      } catch (error) {
        console.error('Failed to parse user data:', error);
        setUser(null);
      }
    }
    
    setLoading(false);
  }, []);

  const hasRole = (role) => {
    if (!user || !user.roles) return false;
    return user.roles.includes(role);
  };

  const hasAnyRole = (roles) => {
    if (!user || !user.roles) return false;
    return roles.some(role => user.roles.includes(role));
  };

  const isAdmin = () => hasRole('admin');
  const isUser = () => hasRole('user');

  return {
    user,
    loading,
    hasRole,
    hasAnyRole,
    isAdmin,
    isUser,
    isAuthenticated: !!user
  };
};

/**
 * Role constants matching backend
 */
export const ROLES = {
  ADMIN: 'admin',
  USER: 'user',
  HR_ADMIN: 'hr_admin',
  HR_USER: 'hr_user',
  FINANCE_ADMIN: 'finance_admin',
  FINANCE_USER: 'finance_user'
};
