import urllib.request

URL = "http://redworld.pro:8880//get.php?username=Carolina.castillo&password=59NwwY8vmRag&type=m3u_plus"
ARCHIVO_SALIDA = "lista_redworld.m3u"

def descargar_lista(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    canales = 0
    bloque = []

    print(f"Conectando a: {url}\n")

    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.getcode() != 200:
            print(f"Error HTTP: {resp.getcode()}")
            return

        with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f_out:
            f_out.write("#EXTM3U\n")

        linea_extinf = ""

        for linea_bytes in resp:
            linea = linea_bytes.decode('utf-8', errors='ignore').strip()

            if not linea:
                continue

            if linea.startswith("#EXTINF"):
                partes = linea.split(',', 1)
                nombre = partes[1].strip() if len(partes) > 1 else "Canal sin nombre"
                linea_extinf = f"#EXTINF:-1,{nombre}"

            elif linea.startswith("http") and linea_extinf:
                bloque.append(f"{linea_extinf}\n{linea}\n")
                linea_extinf = ""
                canales += 1

                if canales % 5000 == 0:
                    print(f"  Canales descargados: {canales}...")

                if len(bloque) >= 2000:
                    with open(ARCHIVO_SALIDA, "a", encoding="utf-8") as f_out:
                        f_out.writelines(bloque)
                    bloque.clear()

        if bloque:
            with open(ARCHIVO_SALIDA, "a", encoding="utf-8") as f_out:
                f_out.writelines(bloque)

    print(f"\n{'='*50}")
    print(f"DESCARGA COMPLETADA")
    print(f"{'='*50}")
    print(f"Total de canales: {canales}")
    print(f"Archivo guardado: {ARCHIVO_SALIDA}")

if __name__ == "__main__":
    try:
        descargar_lista(URL)
    except Exception as e:
        print(f"Error: {e}")
