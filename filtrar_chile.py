import urllib.request
import concurrent.futures
import re
import os
import sys

# Forzar UTF-8 en consola Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVOS_ENTRADA = ["super_lista_limpia.m3u", "lista_redworld.m3u"]
ARCHIVO_SALIDA = "lista_chile_final.m3u"

# --- PATRONES DE FILTRO ---
PATRONES_CANAL = [
    # Chile (canales generales)
    re.compile(r"(?i)\bCL\b"),
    re.compile(r"(?i)chile"),
    re.compile(r"(?i)\bCHI\b"),

    # ESPN (cualquier versión)
    re.compile(r"(?i)\bespn\b"),

    # TNT Sports
    re.compile(r"(?i)tnt.{0,5}sport"),
    re.compile(r"(?i)tnt.{0,5}deport"),

    # UFC
    re.compile(r"(?i)\bufc\b"),

    # Canales de películas / entretenimiento
    re.compile(r"(?i)\btnt\b"),
    re.compile(r"(?i)\bfox\b"),
    re.compile(r"(?i)\bwarner\b"),
    re.compile(r"(?i)\bspace\b"),
    re.compile(r"(?i)\bhbo\b"),
    re.compile(r"(?i)\bcinemax\b"),
    re.compile(r"(?i)\bparamount\b"),
    re.compile(r"(?i)\buniversal\b"),
    re.compile(r"(?i)\bsony.{0,8}(movie|cine|ent)"),
    re.compile(r"(?i)\baxn\b"),
    re.compile(r"(?i)\bfx\b"),
    re.compile(r"(?i)\bsyfy\b"),
    re.compile(r"(?i)\bcinecanal\b"),
    re.compile(r"(?i)\bcine\b"),
    re.compile(r"(?i)pelicula"),
    re.compile(r"(?i)\bmovie\b"),
    re.compile(r"(?i)\bfilm\b"),
    re.compile(r"(?i)\bstar.{0,5}(movie|cine|channel)"),
]

# Solo queremos HD
PATRON_HD = re.compile(r"(?i)(HD|FHD|4K|UHD)")

# Excluir contenido adulto / no deseado
PATRON_EXCLUIR = re.compile(r"(?i)(xxx|xnxx|porn|adult|sex|erotic|xxx)", re.IGNORECASE)

def es_canal_deseado(linea_extinf):
    if not PATRON_HD.search(linea_extinf):
        return False
    if PATRON_EXCLUIR.search(linea_extinf):
        return False
    for patron in PATRONES_CANAL:
        if patron.search(linea_extinf):
            return True
    return False

def verificar_url(url, timeout=8):
    """Verifica si el stream responde (conexión real)."""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Range': 'bytes=0-1024'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.getcode()
            r.read(512)  # leer un poco para confirmar que transmite
            return code in (200, 206)
    except Exception:
        return False

def extraer_canales(archivo):
    """Lee el M3U y devuelve lista de (nombre, url) que coinciden con los filtros."""
    canales = []
    try:
        with open(archivo, "r", encoding="utf-8", errors="ignore") as f:
            linea_extinf = ""
            for linea in f:
                linea = linea.strip()
                if linea.startswith("#EXTINF"):
                    linea_extinf = linea
                elif linea.startswith("http") and linea_extinf:
                    if es_canal_deseado(linea_extinf):
                        partes = linea_extinf.split(',', 1)
                        nombre = partes[1].strip() if len(partes) > 1 else "Canal"
                        canales.append((nombre, linea, linea_extinf))
                    linea_extinf = ""
    except FileNotFoundError:
        pass
    return canales

def principal():
    print("Extrayendo canales de los archivos M3U...")

    todos = []
    vistos = set()
    for archivo in ARCHIVOS_ENTRADA:
        canales = extraer_canales(archivo)
        for nombre, url, extinf in canales:
            if url not in vistos:
                vistos.add(url)
                todos.append((nombre, url, extinf))
        print(f"  {archivo}: {len(canales)} canales candidatos")

    print(f"\nTotal candidatos (sin duplicados): {len(todos)}")
    print("Verificando cuales estan en linea (esto toma unos minutos)...\n")

    activos = []
    verificados = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futuros = {executor.submit(verificar_url, url): (nombre, url, extinf) for nombre, url, extinf in todos}

        for futuro in concurrent.futures.as_completed(futuros):
            nombre, url, extinf = futuros[futuro]
            verificados += 1
            ok = futuro.result()

            if ok:
                activos.append((nombre, url, extinf))
                print(f"  [VIVO] {nombre}")

            if verificados % 50 == 0:
                print(f"  ... Verificados {verificados}/{len(todos)} | Activos hasta ahora: {len(activos)}")

    print(f"\n{'='*60}")
    print(f"PROCESO FINALIZADO")
    print(f"{'='*60}")
    print(f"Candidatos encontrados: {len(todos)}")
    print(f"Canales activos y HD:   {len(activos)}")

    activos.sort(key=lambda x: x[0].lower())

    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for nombre, url, extinf in activos:
            f.write(f"#EXTINF:-1,{nombre}\n{url}\n")

    print(f"Archivo generado: {ARCHIVO_SALIDA}")
    print(f"\nCanales incluidos:")
    for nombre, _, _ in activos:
        print(f"  - {nombre}")

if __name__ == "__main__":
    principal()
