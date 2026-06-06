import urllib.request
import concurrent.futures
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO_URLS   = "4-6.txt"
ARCHIVO_SALIDA = "peliculas_disponibles.txt"

# Película: tiene año entre paréntesis, sin patrón de serie
PATRON_AÑO    = re.compile(r'\((\d{4})\)')
PATRON_SERIE  = re.compile(r'(?i)S\d{1,2}\s*[xEe]\d{1,2}')
PATRON_CALIDAD = re.compile(r'(?i)(1080p|720p|4K|BluRay|BDRip|WEB-DL|HDTV|BRRip|DVDRip|HDRip)')
PATRON_BASURA = re.compile(r'(?i)(iVBORw|base64|\.jpg|\.png|karaoke|#EXTINF.*group-title="(?:CANALES|DEPORTES|NEWS|NOTICIAS)")')
PATRON_CANAL  = re.compile(r'(?i)^(CL\s*\||ESPN|TNT|FOX|HBO|UFC|CNN|BBC|MTV|VH1|CANAL\s*\d|TV\s*\d|\d+\s*HD)')

def es_pelicula(nombre):
    if PATRON_SERIE.search(nombre):
        return False
    if PATRON_CANAL.search(nombre.strip()):
        return False
    if PATRON_AÑO.search(nombre):
        return True
    if PATRON_CALIDAD.search(nombre):
        return True
    return False

def extraer_titulo(nombre):
    # Quitar calidad y año del final para normalizar
    titulo = PATRON_CALIDAD.sub('', nombre)
    titulo = re.sub(r'\((\d{4})\)', r'(\1)', titulo)  # conservar año limpio
    titulo = re.sub(r'[\.\[\]_]+', ' ', titulo)
    titulo = re.sub(r'\s{2,}', ' ', titulo)
    return titulo.strip()

def extraer_año(nombre):
    m = PATRON_AÑO.search(nombre)
    return int(m.group(1)) if m else 0

def buscar_peliculas_en_lista(url):
    peliculas = {}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            linea_extinf = ""
            for linea_bytes in resp:
                linea = linea_bytes.decode('utf-8', errors='ignore').strip()
                if linea.startswith('#EXTINF'):
                    linea_extinf = linea
                elif linea.startswith('http') and linea_extinf:
                    if PATRON_BASURA.search(linea_extinf):
                        linea_extinf = ""
                        continue
                    partes = linea_extinf.split(',', 1)
                    nombre = partes[1].strip() if len(partes) > 1 else ""
                    if es_pelicula(nombre):
                        titulo = extraer_titulo(nombre)
                        año = extraer_año(nombre)
                        clave = titulo.lower()
                        if clave not in peliculas:
                            peliculas[clave] = (titulo, año)
                    linea_extinf = ""
    except Exception:
        pass
    return peliculas

def principal():
    with open(ARCHIVO_URLS, encoding='utf-8') as f:
        urls = [l.strip() for l in f if l.strip().startswith('http')]

    print(f"Buscando películas en {len(urls)} listas...\n")

    todas = {}
    completadas = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futuros = {executor.submit(buscar_peliculas_en_lista, url): url for url in urls}
        for futuro in concurrent.futures.as_completed(futuros):
            for clave, (titulo, año) in futuro.result().items():
                if clave not in todas:
                    todas[clave] = (titulo, año)
            completadas += 1
            if completadas % 50 == 0:
                print(f"  ... {completadas}/{len(urls)} listas | Películas: {len(todas)}")

    # Ordenar por año descendente, luego por título
    peliculas_ord = sorted(todas.values(), key=lambda x: (-x[1], x[0].lower()))

    print(f"\n{'='*60}")
    print(f"TOTAL PELÍCULAS ENCONTRADAS: {len(peliculas_ord)}")
    print(f"{'='*60}\n")

    # Agrupar por década
    decadas = defaultdict(list)
    sin_año = []
    for titulo, año in peliculas_ord:
        if año >= 2020:
            decadas["2020s (Recientes)"].append((titulo, año))
        elif año >= 2010:
            decadas["2010s"].append((titulo, año))
        elif año >= 2000:
            decadas["2000s"].append((titulo, año))
        elif año >= 1990:
            decadas["1990s"].append((titulo, año))
        elif año > 0:
            decadas["Clásicas (antes 1990)"].append((titulo, año))
        else:
            sin_año.append((titulo, año))

    with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        f.write(f"PELÍCULAS DISPONIBLES EN LAS LISTAS\n")
        f.write(f"Total: {len(peliculas_ord)}\n")
        f.write("="*60 + "\n\n")

        for decada in ["2020s (Recientes)", "2010s", "2000s", "1990s", "Clásicas (antes 1990)"]:
            if decada in decadas:
                f.write(f"\n--- {decada} ({len(decadas[decada])}) ---\n")
                print(f"\n--- {decada} ({len(decadas[decada])}) ---")
                for titulo, año in decadas[decada]:
                    linea = f"  {titulo}" + (f" ({año})" if año else "")
                    f.write(linea + "\n")
                    print(linea)

        if sin_año:
            f.write(f"\n--- Sin año ({len(sin_año)}) ---\n")
            print(f"\n--- Sin año ({len(sin_año)}) ---")
            for titulo, año in sin_año:
                f.write(f"  {titulo}\n")
                print(f"  {titulo}")

    print(f"\nGuardado en: {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    principal()
