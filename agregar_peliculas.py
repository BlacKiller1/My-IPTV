import urllib.request
import concurrent.futures
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO_URLS   = "4-6.txt"
ARCHIVO_LISTA  = "lista_chile_final.m3u"

PATRON_AÑO     = re.compile(r'\((\d{4})\)')
PATRON_SERIE   = re.compile(r'(?i)S\d{1,2}\s*[xEe]\d{1,2}')
PATRON_CALIDAD = re.compile(r'(?i)(1080p|720p|4K|BluRay|BDRip|WEB-DL|HDTV|BRRip|DVDRip|HDRip)')
PATRON_BASURA  = re.compile(r'(?i)(iVBORw|base64|\.jpg|\.png|karaoke|xnxx|xxx|porn)')
PATRON_CANAL   = re.compile(r'(?i)^(CL\s*\||ESPN|TNT|FOX|HBO|UFC|CNN|BBC|MTV|VH1|CANAL\s*\d|TV\s*\d|\d+\s*HD\b)')

def es_pelicula(nombre):
    if PATRON_SERIE.search(nombre):   return False
    if PATRON_CANAL.search(nombre.strip()): return False
    if PATRON_BASURA.search(nombre):  return False
    if PATRON_AÑO.search(nombre):     return True
    if PATRON_CALIDAD.search(nombre): return True
    return False

def normalizar_titulo(nombre):
    t = PATRON_CALIDAD.sub('', nombre)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'[\.\[\]_]+', ' ', t)
    t = re.sub(r'\|.*$', '', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip().lower()

def calidad_score(nombre):
    n = nombre.upper()
    if 'FHD' in n or 'FULL' in n: return 4
    if '4K' in n or 'UHD' in n:   return 3
    if 'HD' in n or '1080' in n:   return 2
    return 1

def descargar_peliculas(url):
    encontradas = {}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            linea_extinf = ""
            for lb in resp:
                linea = lb.decode('utf-8', errors='ignore').strip()
                if linea.startswith('#EXTINF'):
                    linea_extinf = linea
                elif linea.startswith('http') and linea_extinf:
                    partes = linea_extinf.split(',', 1)
                    nombre = partes[1].strip() if len(partes) > 1 else ""
                    if es_pelicula(nombre):
                        clave = normalizar_titulo(nombre)
                        score = calidad_score(nombre)
                        if clave not in encontradas or score > encontradas[clave][2]:
                            encontradas[clave] = (nombre, linea, score)
                    linea_extinf = ""
    except Exception:
        pass
    return encontradas

def principal():
    with open(ARCHIVO_URLS, encoding='utf-8') as f:
        urls = [l.strip() for l in f if l.strip().startswith('http')]

    print(f"Descargando películas de {len(urls)} listas...\n")

    todas = {}
    completadas = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futuros = {executor.submit(descargar_peliculas, url): url for url in urls}
        for futuro in concurrent.futures.as_completed(futuros):
            for clave, (nombre, stream_url, score) in futuro.result().items():
                if clave not in todas or score > todas[clave][2]:
                    todas[clave] = (nombre, stream_url, score)
            completadas += 1
            if completadas % 50 == 0:
                print(f"  ... {completadas}/{len(urls)} listas | Películas únicas: {len(todas)}")

    # Ordenar por año desc, luego título
    def sort_key(item):
        nombre = item[0]
        m = PATRON_AÑO.search(nombre)
        año = int(m.group(1)) if m else 0
        return (-año, nombre.lower())

    peliculas = sorted(todas.values(), key=sort_key)

    print(f"\nTotal películas únicas encontradas: {len(peliculas)}")
    print(f"Agregando a {ARCHIVO_LISTA}...\n")

    # Renombrar grupo viejo "Peliculas" a "Canales Cine" en el archivo existente
    with open(ARCHIVO_LISTA, 'r', encoding='utf-8', errors='ignore') as f:
        contenido = f.read()
    contenido = contenido.replace('group-title="Peliculas"', 'group-title="Canales Cine"')

    # Agregar sección de películas
    bloque = '\n'
    for nombre, stream_url, _ in peliculas:
        bloque += f'#EXTINF:-1 group-title="Peliculas",{nombre}\n{stream_url}\n'

    with open(ARCHIVO_LISTA, 'w', encoding='utf-8') as f:
        f.write(contenido + bloque)

    print(f"Listo. {len(peliculas)} películas agregadas en el grupo 'Peliculas'.")
    print(f"El grupo anterior de canales de cine ahora se llama 'Canales Cine'.")

if __name__ == "__main__":
    principal()
