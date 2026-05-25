"""Application-wide constants."""

# ============================================================================
# Role Constants
# ============================================================================

class Roles:
    """User role constants for RBAC."""
    
    ADMIN = "admin"
    USER = "user"
    
    @classmethod
    def all_roles(cls) -> list[str]:
        """Return list of all defined roles."""
        return [cls.ADMIN, cls.USER]
    
    @classmethod
    def is_valid_role(cls, role: str) -> bool:
        """Check if a role name is valid."""
        return role in cls.all_roles()


# ============================================================================
# API Constants
# ============================================================================

class APIMessages:
    """Standard API response messages."""
    
    UNAUTHORIZED = "Authentication required"
    FORBIDDEN_ADMIN = "Admin access required. Only administrators can perform this action."
    FORBIDDEN_USER = "User authentication required"
    INVALID_CREDENTIALS = "Invalid username or password"
    LOGIN_SUCCESS = "Login successful"
    LOGOUT_SUCCESS = "Logout successful"
