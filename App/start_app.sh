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
ngrok http 5001 --log=stdout > ngrok.log 2>&1 &
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
