from flask import Flask, render_template,request
import folium
from folium import Element
# Removed heavy imports for performance:
import requests  # Needed for satellite API calls
# import geopandas as gpd  # Heavy geospatial library - disabled
# from shapely.geometry import Point  # Not used with land checking disabled
import time
import json
import re
import math
import heapq
import ast  # Safe way to parse Python literal structures
def get_distances(max_distance, hour, jack_enabled):
    def distance_3d(point1,point2):
        def to_xyz(lat, lon, alt_km):
            R = 6371 + alt_km  # Earth radius + altitude
            lat_rad = math.radians(lat)
            lon_rad = math.radians(lon)
            x = R * math.cos(lat_rad) * math.cos(lon_rad)
            y = R * math.cos(lat_rad) * math.sin(lon_rad)
            z = R * math.sin(lat_rad)
            return x, y, z

        x1, y1, z1 = to_xyz(point1[0],point1[1], point1[2])
        x2, y2, z2 = to_xyz(point2[0],point2[1], point2[2])
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2 + (z1 - z2)**2)

    # Skip land checking for performance - comment out for production use
    # land = gpd.read_file("natural_earth_land/ne_110m_land.shp") 

    def is_on_land(lat, lon):
        # Disabled for performance - always return True
        return True
        # point = Point(lon, lat)
        # return any(land.geometry.contains(point))




    def get_coordinates(hours = "00"):
        url = f'https://a.windbornesystems.com/treasure/{hours}.json'
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise error for bad status codes
            try:
                return response.json()
            except json.JSONDecodeError as e:
                print(f"[{hour}] JSON decode error: {e}")
                print("Attempting to sanitize and reformat...")

                lines = response.text.strip().splitlines()

                # Filter lines that look like [x, y, z]
                array_lines = [line.strip() for line in lines if line.strip().startswith('[') and line.strip().endswith(']')]

                # Replace NaN, Infinity with null
                array_lines = [re.sub(r'\b(NaN|Infinity|-Infinity)\b', 'null', line) for line in array_lines]

                # Join into a single JSON array
                fixed_json = "[\n" + ",\n".join(array_lines) + "\n]"

                try:
                    return json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    print(f"[{hour}] Still failed after fixing format: {e2}")
                    return []
        except requests.RequestException as e:
            print(f"HTTP error occurred: {e}")
            return []
        except ValueError:
            print("Error parsing JSON.")
            return []

    #points = get_coordinates()
    valid_hours = [f"{h:02}" for h in range(24)]
    points = get_coordinates(valid_hours[hour])

    if(len(points) == 0):
        return ([],[],0)
    palo_alto_office = [37.419,-122.106,0]
    points.insert(0,palo_alto_office)
    i = 0
    for point in points:
        point.append(i)
        # point.append(False)
        i += 1
    fcc_start = -1
    if(jack_enabled):
        with open("fcc_facilities.json", "r") as f:
            fcc_facilities = json.load(f)
        fcc_start = i
        for facility in fcc_facilities:
            lat = facility['lat']
            lon = facility['lon']
            alt = facility.get('height', 0) / 3.281  # Convert feet to meters for altitude
            points.append([lat, lon, alt, i])
            i += 1



    def calculate_distance(max_distance = 1000):
        res = [[] for point in points]
        for point1 in points:
            for point2 in points:
                if(point1[3] == point2[3]):
                    continue
                dis = distance_3d(point1, point2)
                if(dis < max_distance):
                    res[point1[3]].append((point2[3],dis))
        return res


    neighbor_arr = calculate_distance(max_distance)


    def djikstra(graph, start=0):
        distances = [([],float('inf')) for node in graph]
        distances[start] = ([],0)

        # Min-heap priority queue: (distance, node)
        priority_queue = [(0, start)]
        while(priority_queue):
            current_distance, current_node = heapq.heappop(priority_queue)
            # Skip if we already found a shorter path
            if current_distance > distances[current_node][1]:
                #print(current_distance, distances[current_node][1])
                continue

            for neighbor, weight in graph[current_node]:
                distance = current_distance + weight
                if distance < distances[neighbor][1]:
                    distances[neighbor] = (distances[current_node][0] + [current_node],distance)
                    heapq.heappush(priority_queue, (distance, neighbor))
        return distances
    return (points, djikstra(neighbor_arr), fcc_start)

















def add_markers(points, distances, fcc_start, only_land = True):
    # Create minimal map with no markers initially
    m = folium.Map(location=[points[0][0], points[0][1]], tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://carto.com/">CartoDB</a>', zoom_start=4, min_zoom=3, max_zoom=10)
    
    # Prepare marker data for JavaScript instead of adding to Folium
    marker_data = []
    for lat, lon, alt, id in points:
        if math.isnan(lat) or math.isnan(lon):
            continue
        fcc_relay = (fcc_start >= 0 and id >= fcc_start)
        reachable = True if id == 0 else (id < len(distances) and len(distances[id][0]) > 0)
        
        marker_info = {
            'id': id,
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'fcc_relay': fcc_relay,
            'reachable': reachable,
            'is_hq': (id == 0),
            'distance': distances[id][1] if id < len(distances) and len(distances[id]) > 1 else 0
        }
        marker_data.append(marker_info)
    
    m.get_root().html.add_child(folium.Element(f"""
    <script>
        var markerData = {json.dumps(marker_data)};
        var pathData = {{}};
        var activePaths = {{}};
        var pathDataLoaded = false;
        var markersAdded = false;
        
        document.addEventListener("DOMContentLoaded", function() {{
            window.myMap = {m.get_name()};
            
            // Load path data from API with better error handling
            fetch('/api/paths')
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error(`HTTP ${{response.status}}: Failed to load path data`);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    pathData = data;
                    pathDataLoaded = true;
                    console.log('Path data loaded:', Object.keys(pathData).length, 'paths');
                }})
                .catch(error => {{
                    console.error('Error loading path data:', error);
                    pathDataLoaded = false;
                    // Show user-friendly error
                    setTimeout(() => {{
                        if (typeof showMessage === 'function') {{
                            showMessage('Unable to load routing data. Path visualization may be limited.', 'error');
                        }}
                    }}, 1000);
                }});
            
            // Add markers via JavaScript instead of Folium
            function addMarkers() {{
                console.log('Adding', markerData.length, 'markers');
                var reachableCount = 0;
                markerData.forEach(function(marker) {{
                    var color = marker.reachable ? 'blue' : 'red';
                    var radius = marker.fcc_relay ? 3 : 5;
                    if (marker.reachable) reachableCount++;
                    
                    if (marker.is_hq) {{
                        // Add HQ marker with windborn.png icon
                        var hqIcon = L.icon({{
                            iconUrl: '/static/windborn.png',
                            iconSize: [30, 30],
                            iconAnchor: [15, 15],
                            popupAnchor: [0, -15]
                        }});
                        L.marker([marker.lat, marker.lon], {{icon: hqIcon}})
                         .bindPopup("Palo Alto HQ")
                         .addTo(window.myMap);
                    }} else {{
                        var circleMarker = L.circleMarker([marker.lat, marker.lon], {{
                            radius: radius,
                            fillColor: color,
                            color: 'black',
                            weight: 2,
                            fillOpacity: 0.8
                        }}).bindPopup("Node " + marker.id + (marker.reachable ? " - Distance: " + marker.distance.toFixed(2) + " km" : ""))
                          .bindTooltip(marker.lat + "," + marker.lon + "," + marker.alt + (marker.reachable && !marker.fcc_relay ? " - Click to show path" : ""))
                          .addTo(window.myMap);
                        
                        if (marker.reachable && !marker.fcc_relay) {{
                            circleMarker.on('click', function() {{
                                if (pathDataLoaded) {{
                                    window.togglePath(marker.id);
                                }}
                            }});
                        }}
                    }}
                }});
                console.log('Added markers:', reachableCount, 'reachable out of', markerData.length);
                markersAdded = true;
            }}
            
            window.togglePath = function(nodeId) {{
                if (!pathDataLoaded) {{
                    console.log('Path data not loaded yet');
                    return;
                }}
                
                if (activePaths[nodeId]) {{
                    window.myMap.removeLayer(activePaths[nodeId]);
                    delete activePaths[nodeId];
                }} else {{
                    var data = pathData[nodeId];
                    if (data) {{
                        var pathLine = L.polyline(data.coords, {{
                            color: 'green',
                            weight: 4,
                            opacity: 0.8,
                        }}).bindTooltip("Node " + nodeId + "<br>Distance: " + data.distance.toFixed(2) + " km<br>Path: " + data.path_str, {{sticky: true}});
                        pathLine.addTo(window.myMap);
                        activePaths[nodeId] = pathLine;
                    }}
                }}
            }};
            
            // Add markers after map loads
            setTimeout(addMarkers, 100);
        }});
    </script>
    """))

    return m







app = Flask(__name__)

# Global variables to store current session data
current_path_data = {}
current_points = []

@app.route("/api/paths")
def get_paths():
    """API endpoint to return path data as JSON"""
    return current_path_data

@app.route("/")
def index():
    global current_path_data, current_points
    
    max_range = int(request.args.get("value", 500))
    hour_value = int(request.args.get("hour", 0))
    jack_enabled = request.args.get("jack", "0") == "1"

    points, distances, fcc_start = get_distances(max_range, hour_value, jack_enabled)
    if(len(points) == 0):
         return render_template("index.html",
                               map_html="",
                               initial_value=max_range,
                               initial_hour=hour_value,
                               error_message="Error in loading JSON data for specified hour, try again later or try with different hour.",
                               jack_enabled=jack_enabled)
    
    # Store data globally for API access
    current_points = points
    current_path_data = {}
    
    # Load FCC facility names for better path descriptions
    fcc_facility_names = {}
    if fcc_start >= 0:
        with open("fcc_facilities.json", "r") as f:
            fcc_facilities = json.load(f)
        for i, facility in enumerate(fcc_facilities):
            facility_id = fcc_start + i
            # Extract short name from location
            short_name = facility['name'].split(' - ')[0]  # e.g. "New York, NY"
            fcc_facility_names[facility_id] = f"{facility['type']} ({short_name})"
    
    for i, (lat, lon, alt, id) in enumerate(points):
        if id == 0 or len(distances[id][0]) == 0:
            continue
        path_coords = [[points[n][0], points[n][1]] for n in distances[id][0] + [id]]
        path_nodes = distances[id][0] + [id]
        
        # Create descriptive path string
        path_labels = []
        for n in path_nodes:
            if n == 0:
                path_labels.append("HQ")
            elif n in fcc_facility_names:
                path_labels.append(fcc_facility_names[n])
            else:
                path_labels.append(f"Satellite {n}")
        
        path_str = " > ".join(path_labels)
        current_path_data[id] = {
            'coords': path_coords,
            'distance': distances[id][1],
            'path_str': path_str,
            'lat': lat,
            'lon': lon
        }
    
    m = add_markers(points, distances, fcc_start)

    # Save or display
    map_html = m._repr_html_()
    
    # Calculate network performance metrics
    total_satellites = len([p for p in points if p[3] != 0 and (fcc_start == -1 or p[3] < fcc_start)])
    total_fcc_relays = len([p for p in points if fcc_start != -1 and p[3] >= fcc_start])
    reachable_satellites = len([id for id in current_path_data.keys() if id != 0 and (fcc_start == -1 or id < fcc_start)])
    
    # Calculate average hop count
    if current_path_data:
        hop_counts = [len(data['coords']) - 1 for data in current_path_data.values()]
        avg_hops = sum(hop_counts) / len(hop_counts)
        max_hops = max(hop_counts) if hop_counts else 0
        min_hops = min(hop_counts) if hop_counts else 0
    else:
        avg_hops = max_hops = min_hops = 0
    
    # Calculate network coverage percentage
    coverage_percent = (reachable_satellites / total_satellites * 100) if total_satellites > 0 else 0
    
    # Find longest and shortest distances
    if current_path_data:
        distances_km = [data['distance'] for data in current_path_data.values()]
        max_distance = max(distances_km) if distances_km else 0
        min_distance = min(distances_km) if distances_km else 0
        avg_distance = sum(distances_km) / len(distances_km) if distances_km else 0
    else:
        max_distance = min_distance = avg_distance = 0
    
    network_metrics = {
        'total_satellites': total_satellites,
        'total_fcc_relays': total_fcc_relays,
        'reachable_satellites': reachable_satellites,
        'coverage_percent': round(coverage_percent, 1),
        'avg_hops': round(avg_hops, 1),
        'max_hops': max_hops,
        'min_hops': min_hops,
        'max_distance': round(max_distance, 1),
        'min_distance': round(min_distance, 1),
        'avg_distance': round(avg_distance, 1)
    }
    
    # Debug: Check HTML size and distances
    html_lines = len(map_html.split('\n'))
    print(f"Generated HTML has {html_lines} lines, {total_satellites} satellites, {reachable_satellites} reachable")
    
    return render_template("index.html", map_html=map_html, initial_value=max_range, initial_hour=hour_value, error_message=None, jack_enabled=jack_enabled, metrics=network_metrics)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
