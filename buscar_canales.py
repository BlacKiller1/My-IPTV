import urllib.request
import concurrent.futures
import re

ARCHIVO_URLS = "4-6.txt"
ARCHIVO_RESULTADO = "resultado_busqueda.txt"

# Patrones a buscar (ESPN o TNT para Chile)
PATRONES = [
    re.compile(r"(?i)espn.{0,10}(cl\b|chile)", re.IGNORECASE),
    re.compile(r"(?i)tnt.{0,10}(cl\b|chile)", re.IGNORECASE),
    re.compile(r"(?i)(cl|chile).{0,10}espn", re.IGNORECASE),
    re.compile(r"(?i)(cl|chile).{0,10}tnt", re.IGNORECASE),
]

def buscar_en_lista(url):
    url = url.strip()
    if not url.startswith("http"):
        return url, []

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    canales_encontrados = []

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
                    for patron in PATRONES:
                        if patron.search(linea_extinf):
                            # Extraer nombre del canal
                            partes = linea_extinf.split(',', 1)
                            nombre = partes[1].strip() if len(partes) > 1 else linea_extinf
                            canales_encontrados.append((nombre, linea))
                            break
                    linea_extinf = ""

    except Exception:
        pass

    return url, canales_encontrados

def principal():
    with open(ARCHIVO_URLS, "r", encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip().startswith("http")]

    print(f"Buscando ESPN/TNT Chile en {len(urls)} listas (esto puede tardar varios minutos)...\n")

    listas_con_canales = []
    completadas = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futuros = {executor.submit(buscar_en_lista, url): url for url in urls}

        for futuro in concurrent.futures.as_completed(futuros):
            url, canales = futuro.result()
            completadas += 1

            if canales:
                listas_con_canales.append((url, canales))
                print(f"[ENCONTRADO] {url}")
                for nombre, stream in canales:
                    print(f"   -> {nombre}")

            if completadas % 20 == 0:
                print(f"  ... Revisadas {completadas}/{len(urls)} listas")

    print(f"\n{'='*60}")
    print(f"BUSQUEDA COMPLETA")
    print(f"{'='*60}")
    print(f"Listas con ESPN/TNT Chile: {len(listas_con_canales)} de {len(urls)}\n")

    with open(ARCHIVO_RESULTADO, "w", encoding="utf-8") as f:
        f.write(f"Busqueda: ESPN y TNT Sport Chile\n")
        f.write(f"Total listas revisadas: {len(urls)}\n")
        f.write(f"Listas con coincidencias: {len(listas_con_canales)}\n")
        f.write("="*60 + "\n\n")

        for url, canales in listas_con_canales:
            f.write(f"URL: {url}\n")
            for nombre, stream in canales:
                f.write(f"  Canal: {nombre}\n")
                f.write(f"  Stream: {stream}\n")
            f.write("\n")

    if listas_con_canales:
        print("Resultados guardados en: resultado_busqueda.txt")
        for url, canales in listas_con_canales:
            print(f"\nLista: {url}")
            for nombre, _ in canales:
                print(f"  - {nombre}")
    else:
        print("No se encontraron canales ESPN o TNT Sport para Chile en ninguna lista.")

if __name__ == "__main__":
    principal()
