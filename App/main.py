from flask import Flask, render_template,request
import folium
import requests
from folium import IFrame
from folium import Element
import geopandas as gpd
from shapely.geometry import Point
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

    # Load land polygons from Natural Earth
    land = gpd.read_file("natural_earth_land/ne_110m_land.shp")

    def is_on_land(lat, lon):
        point = Point(lon, lat)
        return any(land.geometry.contains(point))




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
    jack_start = -1
    if(jack_enabled):
        with open("jack_locations.json", "r") as f:
            jack_locations = json.load(f)
        jack_start = i
        for loc in jack_locations:
            lat = loc['lat']
            lon = loc['lon']
            alt = 0  # default altitude if not available
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
    return (points, djikstra(neighbor_arr), jack_start)

















def add_markers(points, distances, jack_start, only_land = True):
    m = folium.Map(location=[points[0][0], points[0][1]], tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://carto.com/">CartoDB</a>', zoom_start=4, min_zoom=3, max_zoom=10)
    m.get_root().html.add_child(folium.Element(f"""
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            window.myMap = {m.get_name()};
        }});
    </script>
    """))

    icon = folium.CustomIcon(
        icon_image='windborn.png',  # or local path: 'my_icon.png'
        icon_size=(30, 30),  # width, height in pixels
        icon_anchor=(15, 15)  # anchor point, optional
    )
    for lat, lon, alt, id in points:
        if math.isnan(lat) or math.isnan(lon):
            continue
        if(jack_start >= 0 and id >= jack_start):
            jack = True
        else:
            jack = False
        reachable = True
        if len(distances[id][0]) == 0:
            reachable = False
        if(id == 0):
            folium.Marker(
            location=[lat, lon],
            icon=icon,
            fill=True,
            fill_color='blue' if reachable else 'red',
            color="black",
            fill_opacity=0.8,
            popup="Palo Alto HQ"
            ).add_to(m)
            continue
        path_coords = [[points[n][0], points[n][1]] for n in distances[id][0] + [id]]
        path_json = json.dumps(path_coords)

        # Add visible marker
        folium.CircleMarker(
            location=[lat, lon],
            radius=1 if jack else 5,
            fill=True,
            fill_color='blue' if reachable else 'red',
            color='black',
            thickness=2,
            fill_opacity=0.8,
            popup=f"Node {id}",
            tooltip=f"{lat},{lon},{alt}"
        ).add_to(m)
        if(reachable):
        # Inject JS for path toggle on click
            path_nodes = distances[id][0] + [id]
            path_str = " > ".join([f"Node {n}" for n in path_nodes])
            js = f"""
            <script>
            setTimeout(function() {{
                var pathLine_{id} = L.polyline({path_json}, {{
                    color: 'green',
                    weight: 4,
                    opacity: 0.8,
                }}).bindTooltip("Node {id}<br>Distance: {distances[id][1]:.2f} km<br>Path: {path_str}", {{sticky: true}});
                var trigger = L.circleMarker({json.dumps([lat, lon])}, {{
                    radius: 10,
                    opacity: 0,
                    fillOpacity: 0
                }}).addTo(window.myMap);
                trigger.on('click', function () {{
                    if (window.myMap.hasLayer(pathLine_{id})) {{
                        window.myMap.removeLayer(pathLine_{id});
                    }} else {{
                        pathLine_{id}.addTo(window.myMap);
                    }}
                }});
            }}, 100);
            </script>
            """
            m.get_root().html.add_child(Element(js))
    return m







app = Flask(__name__)

@app.route("/")
def index():
    max_range = int(request.args.get("value", 500))
    hour_value = int(request.args.get("hour", 0))
    jack_enabled = request.args.get("jack", "0") == "1"

    points, distances,jack_start = get_distances(max_range, hour_value, jack_enabled)
    if(len(points) == 0):
         return render_template("index.html",
                               map_html="",
                               initial_value=max_range,
                               initial_hour=hour_value,
                               error_message="Error in loading JSON data for specified hour, try again later or try with different hour.",
                               jack_enabled=jack_enabled)
    m = add_markers(points, distances,jack_start)


    # Save or display
    map_html = m._repr_html_()
    return render_template("index.html", map_html=map_html, initial_value=max_range, initial_hour=hour_value, error_message=None,jack_enabled=jack_enabled)

if __name__ == "__main__":
    app.run(debug=True)