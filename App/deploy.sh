#!/bin/bash

# Windborne Satellite Network Analyzer - Auto Deploy Script
# Usage: ./deploy.sh YOUR_NGROK_AUTH_TOKEN

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if auth token provided
if [ $# -eq 0 ]; then
    print_error "Usage: $0 <NGROK_AUTH_TOKEN>"
    print_error "Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

NGROK_TOKEN="$1"
APP_PORT="5001"

print_status "🚀 Starting Windborne Satellite Network Analyzer deployment..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    print_error "app.py not found. Please run this script from the App/ directory."
    exit 1
fi

# Install system dependencies
print_status "📦 Installing system dependencies..."
sudo apt update -qq
sudo apt install -y python3-venv python3-pip wget curl

# Create virtual environment
print_status "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
print_status "📚 Installing Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# Generate FCC data
print_status "📡 Generating FCC facility data..."
python3 fetch_fcc_data.py

# Download and setup ngrok
print_status "🌐 Setting up ngrok tunnel..."
if [ ! -f "ngrok" ]; then
    wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
    tar xzf ngrok-v3-stable-linux-amd64.tgz
    rm ngrok-v3-stable-linux-amd64.tgz
    chmod +x ngrok
fi

# Configure ngrok with auth token
./ngrok config add-authtoken "$NGROK_TOKEN"
print_success "ngrok configured with auth token"

# Create startup script
print_status "📝 Creating startup script..."
cat > start_app.sh << 'EOF'
#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🛰️  Starting Windborne Satellite Network Analyzer...${NC}"

# Start Flask app in background
echo -e "${BLUE}[1/2]${NC} Starting Flask application on port 5001..."
source venv/bin/activate
python app.py &
FLASK_PID=$!

# Wait for Flask to start
sleep 3

# Start ngrok tunnel
echo -e "${BLUE}[2/2]${NC} Creating public tunnel with ngrok..."
./ngrok http 5001 --log=stdout > ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to initialize
sleep 5

# Get public URL
echo -e "${YELLOW}⏳ Fetching public URL...${NC}"
sleep 2
PUBLIC_URL=$(curl -s localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*"' | head -1 | sed 's/"public_url":"//;s/"//')

if [ ! -z "$PUBLIC_URL" ]; then
    echo -e "${GREEN}🎉 Deployment successful!${NC}"
    echo -e "${GREEN}📱 Public URL: $PUBLIC_URL${NC}"
    echo -e "${BLUE}💻 Local URL:  http://localhost:5001${NC}"
    echo ""
    echo -e "${YELLOW}📊 Features available:${NC}"
    echo "   • Real-time satellite network visualization"
    echo "   • FCC communication relay integration"
    echo "   • Network performance metrics"
    echo "   • Interactive path routing"
    echo ""
    echo -e "${YELLOW}⚡ To stop: Press Ctrl+C${NC}"
    echo ""
    
    # Save URLs to file for reference
    echo "PUBLIC_URL=$PUBLIC_URL" > .env
    echo "LOCAL_URL=http://localhost:5001" >> .env
    echo "FLASK_PID=$FLASK_PID" >> .env
    echo "NGROK_PID=$NGROK_PID" >> .env
    
    # Wait for user to stop
    trap 'echo -e "\n${YELLOW}🛑 Shutting down...${NC}"; kill $FLASK_PID $NGROK_PID 2>/dev/null; exit' INT
    wait
else
    echo -e "${RED}❌ Failed to get ngrok URL. Check ngrok.log for details.${NC}"
    kill $FLASK_PID $NGROK_PID 2>/dev/null
    exit 1
fi
EOF

chmod +x start_app.sh

# Create stop script
cat > stop_app.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping Windborne Satellite Network Analyzer..."

# Kill processes from .env if it exists
if [ -f ".env" ]; then
    source .env
    kill $FLASK_PID $NGROK_PID 2>/dev/null || true
fi

# Fallback: kill by process name
pkill -f "python app.py" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true

echo "✅ Stopped successfully"
EOF

chmod +x stop_app.sh

# Final setup
print_success "✅ Deployment setup complete!"
echo ""
print_status "🎯 Next steps:"
echo "   1. Run: ${GREEN}./start_app.sh${NC} to start the application"
echo "   2. Share the public URL with your team"
echo "   3. Run: ${GREEN}./stop_app.sh${NC} to stop when done"
echo ""
print_status "📁 Generated files:"
echo "   • start_app.sh - Start the application"
echo "   • stop_app.sh - Stop the application"  
echo "   • venv/ - Python virtual environment"
echo "   • ngrok - Tunnel executable"
echo "   • fcc_facilities.json - Communication relay data"
echo ""
print_warning "💡 Pro tip: The public URL changes each time you restart ngrok"
print_success "🚀 Ready for deployment!"