#!/bin/bash

# Keycloak Configuration Helper
# This script helps configure Keycloak environment variables

echo "🔐 Keycloak Configuration Helper"
echo "================================"
echo ""

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

# Backend .env
BACKEND_ENV="/Users/rohith/RAG/backend/.env"

# Check if .env exists, if not create from example
if [ ! -f "$BACKEND_ENV" ]; then
    if [ -f "/Users/rohith/RAG/backend/.env.example" ]; then
        echo "Creating .env from .env.example..."
        cp /Users/rohith/RAG/backend/.env.example "$BACKEND_ENV"
    else
        echo "Creating new .env file..."
        touch "$BACKEND_ENV"
    fi
fi

# Add or update Keycloak settings
echo ""
echo "Adding Keycloak configuration to backend/.env..."

# Remove old Keycloak lines if they exist
sed -i.bak '/KEYCLOAK_URL/d' "$BACKEND_ENV"
sed -i.bak '/KEYCLOAK_REALM/d' "$BACKEND_ENV"
sed -i.bak '/KEYCLOAK_CLIENT_ID/d' "$BACKEND_ENV"

# Add new Keycloak settings
cat >> "$BACKEND_ENV" << 'ENVEOF'

# Keycloak SSO Configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=rag-realm
KEYCLOAK_CLIENT_ID=rag-app
ENVEOF

echo "✅ Backend .env configured"

# Frontend .env
FRONTEND_ENV="/Users/rohith/RAG/frontend/.env"

echo ""
echo "Configuring frontend .env file..."

if [ ! -f "$FRONTEND_ENV" ]; then
    echo "Creating frontend .env..."
    touch "$FRONTEND_ENV"
fi

# Remove old settings
sed -i.bak '/VITE_KEYCLOAK/d' "$FRONTEND_ENV" 2>/dev/null || true

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
echo "1. Configure Keycloak (see KEYCLOAK_RBAC_GUIDE.md)"
echo "2. Create realm 'rag-realm' in Keycloak admin console"
echo "3. Create client 'rag-app' with proper settings"
echo "4. Create test users with roles (admin, user)"
echo "5. Restart backend and frontend to apply changes"
