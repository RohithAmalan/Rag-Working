#!/bin/bash

# Keycloak Configuration Helper
# This script helps configure Keycloak environment variables

set -e  # Exit on any error

echo "🔐 Keycloak Configuration Helper"
echo "================================"
echo ""

# Resolve paths relative to script location (cross-platform, not hardcoded)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ENV="$SCRIPT_DIR/backend/.env"
FRONTEND_ENV="$SCRIPT_DIR/frontend/.env"

# Check if Keycloak is running
echo "Checking Keycloak status..."
if docker ps | grep -q keycloak; then
    echo "✅ Keycloak container is running"
else
    echo "❌ Keycloak container is not running"
    echo "Start it with: docker-compose up -d keycloak"
    exit 1
fi

echo ""
echo "Configuring backend .env file..."

# Check if .env exists, if not create from example
if [ ! -f "$BACKEND_ENV" ]; then
    if [ -f "$SCRIPT_DIR/backend/.env.example" ]; then
        echo "Creating .env from .env.example..."
        cp "$SCRIPT_DIR/backend/.env.example" "$BACKEND_ENV"
    else
        echo "Creating new .env file..."
        touch "$BACKEND_ENV"
    fi
fi

# Add or update Keycloak settings
echo ""
echo "Adding Keycloak configuration to backend/.env..."

# Remove old Keycloak lines if they exist
# Use portable sed syntax (works on both macOS and Linux)
sed -i'' -e '/KEYCLOAK_URL/d' "$BACKEND_ENV"
sed -i'' -e '/KEYCLOAK_REALM/d' "$BACKEND_ENV"
sed -i'' -e '/KEYCLOAK_CLIENT_ID/d' "$BACKEND_ENV"

# Add new Keycloak settings
cat >> "$BACKEND_ENV" << 'ENVEOF'

# Keycloak SSO Configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=rag-realm
KEYCLOAK_CLIENT_ID=rag-app
ENVEOF

echo "✅ Backend .env configured"

# Frontend .env
echo ""
echo "Configuring frontend .env file..."

if [ ! -f "$FRONTEND_ENV" ]; then
    echo "Creating frontend .env..."
    touch "$FRONTEND_ENV"
fi

# Remove old settings — portable sed
sed -i'' -e '/VITE_KEYCLOAK/d' "$FRONTEND_ENV"

# Add frontend Keycloak settings
cat >> "$FRONTEND_ENV" << 'FRONTEOF'
VITE_KEYCLOAK_URL=http://localhost:8080
VITE_KEYCLOAK_REALM=rag-realm
VITE_KEYCLOAK_CLIENT_ID=rag-app
FRONTEOF

echo "✅ Frontend .env configured"

echo ""
echo "📋 Configuration Summary:"
echo "========================"
echo "Backend (.env):"
echo "  KEYCLOAK_URL=http://localhost:8080"
echo "  KEYCLOAK_REALM=rag-realm"
echo "  KEYCLOAK_CLIENT_ID=rag-app"
echo ""
echo "Frontend (.env):"
echo "  VITE_KEYCLOAK_URL=http://localhost:8080"
echo "  VITE_KEYCLOAK_REALM=rag-realm"
echo "  VITE_KEYCLOAK_CLIENT_ID=rag-app"
echo ""
echo "✅ Configuration complete!"
echo ""
echo "Next steps:"
echo "1. Import keycloak/realm-export.json via Keycloak Admin Console → Import"
echo "2. Log in with the temporary credentials from realm-export.json"
echo "3. You will be prompted to set a permanent password on first login"
echo "4. See docs/setup-guides/ for full RBAC and deployment guides"
echo "5. Restart backend and frontend to apply changes"
