#!/bin/bash

# Quick Start Script for HR and Finance Apps
# Usage: ./start-sso-apps.sh

echo "🚀 Starting Keycloak SSO Demo Apps..."
echo ""

# Check if ports are available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $1 is already in use!"
        return 1
    fi
    return 0
}

# Check required ports
echo "📡 Checking ports..."
check_port 3001 || exit 1
check_port 3002 || exit 1
echo "✅ Ports 3001 and 3002 are available"
echo ""

# Check if Keycloak is running
echo "🔍 Checking Keycloak..."
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "⚠️  Keycloak is not running on port 8080"
    echo "   Start it with: docker-compose up keycloak"
    echo ""
    read -p "Do you want to start Keycloak now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose up -d keycloak
        echo "⏳ Waiting for Keycloak to start..."
        sleep 15
    else
        exit 1
    fi
fi
echo "✅ Keycloak is running"
echo ""

# Function to start app in new terminal
start_app() {
    app_name=$1
    port=$2
    app_dir=$3
    
    echo "🚀 Starting $app_name on port $port..."
    
    # macOS specific - open new Terminal tab
    if [[ "$OSTYPE" == "darwin"* ]]; then
        osascript -e "tell application \"Terminal\" to do script \"cd '$PWD/$app_dir' && python3 -m http.server $port\"" > /dev/null 2>&1
    else
        # Linux - use gnome-terminal or xterm
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "cd '$PWD/$app_dir' && python3 -m http.server $port; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "cd '$PWD/$app_dir' && python3 -m http.server $port; exec bash" &
        else
            echo "⚠️  Please start manually: cd $app_dir && python3 -m http.server $port"
        fi
    fi
}

# Start HR App
start_app "HR App" 3001 "hr-app"
sleep 2

# Start Finance App
start_app "Finance App" 3002 "finance-app"
sleep 2

echo ""
echo "✅ Both apps are starting!"
echo ""
echo "📋 Access URLs:"
echo "   HR App:      http://localhost:3001"
echo "   Finance App: http://localhost:3002"
echo "   RAG App:     http://localhost:5173 (if running)"
echo "   Keycloak:    http://localhost:8080"
echo ""
echo "👥 Test Users:"
echo "   rohith - Super Admin (all apps)"
echo "   alice  - HR Admin + RAG User"
echo "   bob    - HR User + RAG User"
echo "   carol  - Finance Admin + RAG User"
echo "   dave   - Finance User + RAG User"
echo ""
echo "🔑 Default Password: password"
echo ""
echo "📖 See KEYCLOAK_SSO_SETUP.md for detailed setup instructions"
echo ""
echo "🛑 To stop: Close the terminal tabs or press Ctrl+C in each"
echo ""
