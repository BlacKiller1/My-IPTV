import urllib.request
import concurrent.futures
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO_URLS = "4-6.txt"
PATRON = "ufc"

def buscar_en_lista(url):
    url = url.strip()
    if not url.startswith("http"):
        return url, []

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    encontrados = []

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.getcode() != 200:
                return url, []

            linea_extinf = ""
            for linea_bytes in resp:
                linea = linea_bytes.decode('utf-8', errors='ignore').strip()

                if linea.startswith("#EXTINF"):
                    linea_extinf = linea
                elif linea.startswith("http") and linea_extinf:
                    if PATRON in linea_extinf.lower():
                        partes = linea_extinf.split(',', 1)
                        nombre = partes[1].strip() if len(partes) > 1 else linea_extinf
                        encontrados.append((nombre, linea))
                    linea_extinf = ""

    except Exception:
        pass

    return url, encontrados

def principal():
    with open(ARCHIVO_URLS, "r", encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip().startswith("http")]

    print(f"Buscando UFC en {len(urls)} listas...\n")

    resultados = []
    completadas = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futuros = {executor.submit(buscar_en_lista, url): url for url in urls}

        for futuro in concurrent.futures.as_completed(futuros):
            url, canales = futuro.result()
            completadas += 1

            if canales:
                resultados.append((url, canales))
                print(f"[ENCONTRADO] {url}")
                for nombre, stream in canales:
                    print(f"   -> {nombre}")
                    print(f"      {stream}")

            if completadas % 50 == 0:
                print(f"  ... Revisadas {completadas}/{len(urls)}")

    print(f"\n{'='*60}")
    print(f"Listas con UFC: {len(resultados)} de {len(urls)}")

    if not resultados:
        print("No se encontro UFC en ninguna lista.")

if __name__ == "__main__":
    principal()
