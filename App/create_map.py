import requests
import folium
from folium import IFrame
from folium import Element
import geopandas as gpd
from shapely.geometry import Point
import time
import json
import re
import math
import heapq

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
points = get_coordinates()
palo_alto_office = [37.419,-122.106,0]
points.insert(0,palo_alto_office)
i = 0
for point in points:
    point.append(i)
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


neighbor_arr = calculate_distance()


def djikstra(graph, start=0):
    distances = [([],float('inf')) for node in graph]
    distances[start] = ([start],0)

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

distances = djikstra(neighbor_arr)
for path,dist in distances:
    if(dist > 100000 and len(path) > 0):
        print(path,dist)














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


def add_markers(distances, only_land = True):
    for lat, lon, alt, id in points:
        reachable = True
        if(id == 0):
            folium.Marker(
            location=[lat, lon],
            icon=icon,
            fill=True,
            fill_color='blue' if reachable else 'red',
            color="black",
            fill_opacity=0.8,
            popup=f"Node {id}"
            ).add_to(m)
            continue
        if len(distances[id][0]) == 0:
            reachable = False
        path_coords = [[points[n][0], points[n][1]] for n in distances[id][0] + [id]]
        path_json = json.dumps(path_coords)

        # Add visible marker
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            fill=True,
            fill_color='blue' if reachable else 'red',
            color="black",
            thickness=3,
            fill_opacity=0.8,
            popup=f"Node {id}"
        ).add_to(m)
        if(reachable):
        # Inject JS for path toggle on click
            js = f"""
            <script>
            setTimeout(function() {{
                var pathLine_{id} = L.polyline({path_json}, {{
                    color: 'green',
                    weight: 4,
                    opacity: 0.8,
                }});
                var trigger = L.circleMarker({json.dumps([lat, lon])}, {{
                    radius: 15,
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
add_markers(distances)


# Save or display
m.save("templates/map.html")