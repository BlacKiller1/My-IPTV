import urllib.request
import concurrent.futures
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO_URLS = "4-6.txt"
BUSCAR = "nba"  # lo que buscamos (insensible a mayúsculas)

def buscar_en_lista(url):
    encontrados = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            linea_extinf = ""
            for lb in resp:
                linea = lb.decode('utf-8', errors='ignore').strip()
                if linea.startswith('#EXTINF'):
                    linea_extinf = linea
                elif linea.startswith('http') and linea_extinf:
                    if BUSCAR.lower() in linea_extinf.lower():
                        partes = linea_extinf.split(',', 1)
                        nombre = partes[1].strip() if len(partes) > 1 else linea_extinf
                        encontrados.append((nombre, linea))
                    linea_extinf = ""
    except Exception:
        pass
    return url, encontrados

def principal():
    with open(ARCHIVO_URLS, encoding='utf-8') as f:
        urls = [l.strip() for l in f if l.strip().startswith('http')]

    print(f'Buscando "{BUSCAR}" en {len(urls)} listas...\n')

    resultados = []
    completadas = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futuros = {executor.submit(buscar_en_lista, url): url for url in urls}
        for futuro in concurrent.futures.as_completed(futuros):
            url, encontrados = futuro.result()
            completadas += 1
            if encontrados:
                resultados.extend(encontrados)
                for nombre, stream in encontrados:
                    print(f"  [ENCONTRADO] {nombre}")
            if completadas % 80 == 0:
                print(f"  ... {completadas}/{len(urls)} listas revisadas")

    print(f"\n{'='*60}")
    if resultados:
        # Deduplicar por nombre normalizado
        vistos = set()
        unicos = []
        for nombre, stream in resultados:
            clave = nombre.lower().strip()
            if clave not in vistos:
                vistos.add(clave)
                unicos.append((nombre, stream))

        unicos.sort(key=lambda x: x[0].lower())
        print(f'Resultados únicos para "{BUSCAR}": {len(unicos)}')
        print()
        for nombre, stream in unicos:
            print(f"  {nombre}")
            print(f"    {stream}")
    else:
        print(f'No se encontró "{BUSCAR}" en ninguna lista.')

if __name__ == "__main__":
    principal()
