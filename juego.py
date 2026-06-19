import folium
import json
import http.server
import socketserver
import webbrowser
import threading
import time
import random
from urllib.parse import urlparse, parse_qs

# Forzar una nueva semilla aleatoria basada en tiempo real
random.seed(time.time())

def generar_juego(categoria):
    with open("preguntas.json", "r", encoding="utf-8") as f:
        categorias = json.load(f)
    
    # Si la categoría no existe en el JSON, cargamos la primera por defecto para evitar cuelgues
    if categoria not in categorias:
        categoria = list(categorias.keys())[0]
        
    lugares = categorias[categoria]
    objetivo = random.choice(lugares)
    
    m = folium.Map(
        location=[20, 0], zoom_start=3,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri"
    )

    css_styles = """
    <style>
        #hud {
            position: absolute; top: 20px; left: 50%; transform: translateX(-50%);
            z-index: 1000; background: green;
            padding: 20px 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            color: white; text-align: center; min-width: 350px; font-family: sans-serif;
        }
        #hud h2 { margin: 0 0 15px 0; font-size: 1.3rem; font-weight: 600; }
        .botones-hud { display: flex; justify-content: center; gap: 10px; }
        .btn-hud {
            background: white; color: #667eea; border: none; padding: 10px 20px;
            border-radius: 25px; font-weight: 600; cursor: pointer; transition: all 0.3s ease;
        }
        .btn-hud:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .map-clickable { cursor: crosshair !important; }
    </style>
    """
    
    js_code = f"""
    document.addEventListener("DOMContentLoaded", function() {{
        var lat_obj = {objetivo['lat']};
        var lon_obj = {objetivo['lon']};
        var nombre_obj = "{objetivo['nombre']}";
        var cat_actual = "{categoria}";
        
        var hud = document.createElement('div');
        hud.id = 'hud';
        hud.innerHTML = '<h2>' + nombre_obj + ' </h2>' +
                        '<div class="botones-hud">' + 
                        '<button id="menu-btn" class="btn-hud">Menú</button>' +
                        '<button id="next-btn" class="btn-hud">Siguiente</button>' +
                        '</div>';
        document.body.appendChild(hud);

        // El botón siguiente debe mantener la misma categoría actual
        document.getElementById('next-btn').addEventListener('click', function() {{
            window.location.href = '/juego?cat=' + encodeURIComponent(cat_actual) + '&t=' + Date.now();
        }});
        
        document.getElementById('menu-btn').addEventListener('click', function() {{
            window.location.href = '/';
        }});

        var mapContainer = document.querySelector('.leaflet-container');
        if (mapContainer) {{ mapContainer.classList.add('map-clickable'); }}

        var map_id = Object.keys(window).find(key => key.startsWith('map_'));
        var map = window[map_id];

        map.on('click', function(e) {{
            var dist = L.latLng(e.latlng.lat, e.latlng.lng).distanceTo(L.latLng(lat_obj, lon_obj)) / 1000;
            alert("Objetivo: " + nombre_obj + "\\nError: " + dist.toFixed(2) + " km");
            L.marker([e.latlng.lat, e.latlng.lng]).addTo(map).bindPopup("Tu fallo: " + dist.toFixed(2) + " km").openPopup();
            L.marker([lat_obj, lon_obj]).addTo(map).bindPopup(nombre_obj).openPopup();
        }});
    }});
    """
    
    m.get_root().html.add_child(folium.Element(css_styles))
    m.get_root().html.add_child(folium.Element(f'<script>{js_code}</script>'))
    
    # Renderizamos el mapa en formato texto (HTML) en lugar de guardarlo como archivo
    return m.get_root().render()

def generar_menu():
    """Lee el JSON y crea un menú HTML dinámico con botones para cada categoría"""
    with open("preguntas.json", "r", encoding="utf-8") as f:
        categorias = json.load(f)
    
    botones = ""
    for cat in categorias.keys():
        botones += f'<a href="/juego?cat={cat}" class="btn">{cat}</a>\n'
    
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Maptap practice</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; 
                   align-items: center; justify-content: center; height: 100vh; margin: 0; 
                   background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; }}
            h1 {{ font-size: 3rem; margin-bottom: 40px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
            .menu {{ display: flex; flex-direction: column; gap: 20px; min-width: 250px; }}
            .btn {{ text-decoration: none; background: rgba(255, 255, 255, 0.1); color: white; 
                    padding: 15px 30px; border-radius: 50px; text-align: center; font-size: 1.2rem; 
                    font-weight: bold; border: 2px solid white; transition: all 0.3s; backdrop-filter: blur(5px); }}
            .btn:hover {{ background: white; color: #1e3c72; transform: scale(1.05); }}
        </style>
    </head>
    <body>
        <h1>Maptap practice</h1>
        <div class="menu">{botones}</div>
    </body>
    </html>
    """
    return html

class GameHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # Si entra a la raíz (/), devolvemos el menú
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(generar_menu().encode('utf-8'))
            return
            
        # Si entra a /juego, capturamos la categoría y devolvemos el mapa
        elif parsed_path.path == '/juego':
            query_params = parse_qs(parsed_path.query)
            # Extraemos la categoría de la URL (Ej: /juego?cat=Europa). Si no hay, ponemos "Mundo"
            categoria = query_params.get('cat', ['Mundo'])[0]
            
            html_content = generar_juego(categoria)
            
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            return
            
        # Para evitar bucles con la petición de favicon y otros recursos por defecto
        elif parsed_path.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
            
        # Comportamiento por defecto
        return super().do_GET()

PORT = 8000
with socketserver.TCPServer(("", PORT), GameHandler) as httpd:
    print(f"🌍 Juego disponible en http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}/")
    httpd.serve_forever()