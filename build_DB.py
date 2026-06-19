import csv
import json
import requests

def obtener_ciudades_csv():
    ciudades = []
    # Leemos el archivo descargado de SimpleMaps
    try:
        with open('worldcities.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Filtramos las que no tengan datos de población para evitar errores
                if row['population']:
                    ciudades.append({
                        'nombre': f"{row['city']}, {row['country']}",
                        'lat': float(row['lat']),
                        'lon': float(row['lng']),
                        'pais': row['country'],
                        'iso2': row['iso2'], # Código del país (ej. US, ES, FR)
                        'poblacion': float(row['population'])
                    })
    except FileNotFoundError:
        print("❌ Error: No se encontró 'worldcities.csv'. Descárgalo de SimpleMaps y ponlo en esta carpeta.")
        return []
    
    # Ordenamos todas las ciudades de mayor a menor población
    ciudades.sort(key=lambda x: x['poblacion'], reverse=True)
    return ciudades

def obtener_monumentos_wikidata():
    print("Descargando Monumentos de Wikidata...")
    url = "https://query.wikidata.org/sparql"
    headers = {'User-Agent': 'GeoJuegoDataGenerator/3.0', 'Accept': 'application/json'}
    
    # La consulta que te funcionó bien
    query = """
        SELECT ?itemLabel (MAX(?lat) AS ?final_lat) (MAX(?lon) AS ?final_lon) WHERE {
          { ?item wdt:P1435 wd:Q9259 . } UNION { ?item wdt:P31 wd:Q570116 . } UNION { ?item wdt:P31 wd:Q41132 . }
          ?item wikibase:sitelinks ?sitelinks .
          FILTER(?sitelinks > 60)
          ?item p:P625/psv:P625 [ wikibase:geoLatitude ?lat ; wikibase:geoLongitude ?lon ] .
          FILTER NOT EXISTS { ?item wdt:P1082 ?poblacion . }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
        } GROUP BY ?item ?itemLabel ?sitelinks ORDER BY DESC(?sitelinks) LIMIT 60
    """
    try:
        respuesta = requests.get(url, headers=headers, params={'query': query})
        respuesta.raise_for_status()
        datos = respuesta.json()
        monumentos = []
        for r in datos['results']['bindings']:
            monumentos.append({
                "nombre": r['itemLabel']['value'],
                "lat": float(r['final_lat']['value']),
                "lon": float(r['final_lon']['value'])
            })
        print(f"✅ Monumentos: {len(monumentos)} obtenidos.")
        return monumentos
    except Exception as e:
        print(f"❌ Error con Wikidata: {e}")
        return []

def construir_base_datos():
    todas_las_ciudades = obtener_ciudades_csv()
    if not todas_las_ciudades:
        return

    # Códigos ISO de los principales países europeos para el filtro
    paises_europa = ['GB', 'FR', 'DE', 'IT', 'ES', 'PT', 'NL', 'BE', 'CH', 'AT', 'SE', 'NO', 'DK', 'FI', 'IE', 'GR', 'PL', 'CZ', 'RO', 'HU']

    base_datos = {
        # TOP 300 del mundo entero
        "Mundo": [{"nombre": c['nombre'], "lat": c['lat'], "lon": c['lon']} for c in todas_las_ciudades[:300]],
        
        # TOP 100 filtrando solo código US (Estados Unidos)
        "EEUU": [{"nombre": c['nombre'], "lat": c['lat'], "lon": c['lon']} for c in todas_las_ciudades if c['iso2'] == 'US'][:100],
        
        # TOP 200 filtrando por los códigos de la lista europea
        "Europa": [{"nombre": c['nombre'], "lat": c['lat'], "lon": c['lon']} for c in todas_las_ciudades if c['iso2'] in paises_europa][:200],
        
        # Traemos los monumentos directamente de internet
        "Monumentos": obtener_monumentos_wikidata()
    }

    with open("preguntas.json", "w", encoding="utf-8") as f:
        json.dump(base_datos, f, ensure_ascii=False, indent=2)
    
    print("\n🎉 Archivo 'preguntas.json' generado con éxito usando SimpleMaps + Wikidata.")

if __name__ == "__main__":
    construir_base_datos()