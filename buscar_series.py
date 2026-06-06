import urllib.request
import concurrent.futures
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO_URLS   = "4-6.txt"
ARCHIVO_SALIDA = "series_disponibles.txt"

PATRON_SERIE = re.compile(r'(?i)S(\d{1,2})\s*[xEe](\d{1,2})')
PATRON_BASURA = re.compile(r'(?i)(iVBORw|base64|tmdb\.org|group-title=.*\bkaraoke\b|\.jpg|\.png)')

def buscar_series_en_lista(url):
    url = url.strip()
    series_encontradas = defaultdict(set)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            for linea_bytes in resp:
                linea = linea_bytes.decode('utf-8', errors='ignore').strip()
                if not linea.startswith('#EXTINF'):
                    continue
                if PATRON_BASURA.search(linea):
                    continue
                partes = linea.split(',', 1)
                if len(partes) < 2:
                    continue
                nombre = partes[1].strip()
                m = PATRON_SERIE.search(nombre)
                if m:
                    titulo = PATRON_SERIE.split(nombre)[0].strip().rstrip('-( .')
                    titulo = re.sub(r'\s{2,}', ' ', titulo).strip()
                    if len(titulo) >= 3:
                        temporada = int(m.group(1))
                        series_encontradas[titulo].add(temporada)
    except Exception:
        pass
    return series_encontradas

def principal():
    with open(ARCHIVO_URLS, encoding='utf-8') as f:
        urls = [l.strip() for l in f if l.strip().startswith('http')]

    print(f"Buscando series en {len(urls)} listas (puede tardar varios minutos)...\n")

    todas_series = defaultdict(set)
    completadas = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futuros = {executor.submit(buscar_series_en_lista, url): url for url in urls}
        for futuro in concurrent.futures.as_completed(futuros):
            resultado = futuro.result()
            for titulo, temps in resultado.items():
                todas_series[titulo].update(temps)
            completadas += 1
            if completadas % 50 == 0:
                print(f"  ... Revisadas {completadas}/{len(urls)} listas | Series encontradas: {len(todas_series)}")

    series_ord = sorted(todas_series.items(), key=lambda x: x[0].lower())

    print(f"\n{'='*60}")
    print(f"TOTAL SERIES ENCONTRADAS: {len(series_ord)}")
    print(f"{'='*60}\n")

    with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        f.write(f"SERIES DISPONIBLES EN LAS LISTAS\n")
        f.write(f"Total: {len(series_ord)}\n")
        f.write("="*60 + "\n\n")
        for titulo, temps in series_ord:
            ts = sorted(temps)
            if len(ts) == 1:
                linea = f"{titulo}  (Temporada {ts[0]})"
            else:
                linea = f"{titulo}  (T{ts[0]} - T{ts[-1]}, {len(ts)} temporadas)"
            f.write(linea + "\n")
            print(linea)

    print(f"\nGuardado en: {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    principal()
