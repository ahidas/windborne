# Windborne Balloon Network Analyzer

Real-time balloon network visualization with optimal routing analysis using Dijkstra's algorithm and FCC communication infrastructure.

## 🚀 Quick Deploy (New Computer)

### One-Command Setup:
```bash
git clone <your-repo-url>
cd App/
./deploy.sh YOUR_NGROK_AUTH_TOKEN
```

### Get ngrok Auth Token:
1. Sign up: https://dashboard.ngrok.com/signup
2. Get token: https://dashboard.ngrok.com/get-started/your-authtoken

### Start Application:
```bash
./start_app.sh
```

### Stop Application:
```bash
./stop_app.sh
```

## ✨ Features

- **🎈 Real-time Balloon Tracking**: Live positions from Windborne treasure hunt API
- **📡 FCC Communication Relays**: 20+ real antenna structures for multi-hop routing  
- **🗺️ Interactive Network Map**: Click balloons to show optimal paths to HQ
- **📊 Performance Metrics**: Network coverage, hop counts, distances
- **⚡ Dijkstra Pathfinding**: Optimal routing with 3D distance calculations

## 🏗️ Architecture

**Backend:**
- Flask web framework
- 3D Haversine distance calculations  
- Dijkstra's shortest path algorithm
- FCC Antenna Structure Database integration

**Frontend:**
- Interactive Leaflet maps
- Real-time path visualization
- Network performance dashboard
- Mobile-responsive design

**Data Sources:**
- Windborne treasure hunt API (`a.windbornesystems.com/treasure/`)
- FCC Antenna Structure Database
- Natural Earth land boundaries

## 📱 Usage

1. **Adjust Range**: Set max communication distance (0-1000km)
2. **Select Time**: Historical positions (0-23 hours ago)  
3. **Toggle Relays**: Include FCC communication infrastructure
4. **Click Balloons**: View optimal routing paths to Palo Alto HQ
5. **View Metrics**: Real-time network performance statistics

## 🔧 Development

**Local Development:**
```bash
source venv/bin/activate
python app.py
# Visit: http://localhost:5001
```

**Requirements:**
- Python 3.8+
- Flask, Folium, Requests
- ngrok account (free)

## 📊 Network Metrics

The application provides real-time analysis of:
- Balloon coverage percentage
- Average communication hops
- Network routing efficiency  
- FCC relay utilization
- Distance optimization

Perfect for demonstrating balloon constellation management and network topology optimization.

---
*Built for Windborne Systems - Advanced balloon network analysis*