import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO = "lista_chile_final.m3u"

# Eliminar VOD (series/películas sueltas con S01E01, años, etc.)
PATRON_VOD = re.compile(
    r"(?i)(S\d{1,2}\s*E\d{1,2}|"           # S01 E01
    r"\(\d{4}\)|"                             # (2021)
    r"\b\d{4}\b.*(p|bluray|bdrip|hdtv)|"    # 1080p, bluray
    r"Karaoke\s|"
    r"temporada|episodio|capitulo|"
    r"coraz.n\s*valiente|"                    # telenovela específica
    r"\.mkv|\.mp4|\.avi)"
)

# Prioridad de calidad para elegir el mejor stream
def calidad(nombre, url):
    n = nombre.upper()
    if "FHD" in n or "FULL" in n: return 4
    if "4K" in n or "UHD" in n:   return 3
    if "HD" in n:                  return 2
    return 1

def normalizar(nombre):
    """Nombre limpio para agrupar duplicados."""
    n = nombre.strip()
    # Quitar calidad al final
    n = re.sub(r"\s*(FHD|HD|SD|4K|UHD|HDÂ²|FHDÂ²|HD\²|FHD\²)[\s\*\²\¹\|opc\-\d]*$", "", n, flags=re.IGNORECASE)
    # Quitar sufijos de opción
    n = re.sub(r"\s*(OP\s*\d+|OPC[\s\-]\d+|\|opc.*|\*+|\²|\¹|\d+)$", "", n, flags=re.IGNORECASE)
    # Quitar espacios extra y caracteres raros al final
    n = re.sub(r"[\s\|\/\-\*]+$", "", n)
    n = re.sub(r"\s{2,}", " ", n)
    return n.strip().lower()

# Leer archivo
with open(ARCHIVO, "r", encoding="utf-8", errors="ignore") as f:
    lineas = f.readlines()

# Parsear canales
canales = []
i = 0
while i < len(lineas):
    linea = lineas[i].strip()
    if linea.startswith("#EXTINF"):
        url = lineas[i+1].strip() if i+1 < len(lineas) else ""
        partes = linea.split(',', 1)
        nombre = partes[1].strip() if len(partes) > 1 else ""

        # Filtrar VOD / telenovelas / karaokes
        if not PATRON_VOD.search(nombre):
            canales.append((nombre, url, linea))
        i += 2
    else:
        i += 1

vod_eliminados = 0
# Contar VOD eliminados
i = 0
total_orig = 0
while i < len(lineas):
    if lineas[i].strip().startswith("#EXTINF"):
        total_orig += 1
        i += 2
    else:
        i += 1
vod_eliminados = total_orig - len(canales)

# Agrupar por nombre normalizado y quedarse con el mejor stream
grupos = defaultdict(list)
for nombre, url, extinf in canales:
    clave = normalizar(nombre)
    grupos[clave].append((nombre, url, extinf))

# Elegir el mejor de cada grupo (mayor calidad, y si hay empate el primero)
canales_finales = []
for clave, opciones in grupos.items():
    mejor = max(opciones, key=lambda x: calidad(x[0], x[1]))
    canales_finales.append(mejor)

# Extraer grupo del extinf para re-ordenar
def extraer_grupo(extinf):
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else "Otros"

ORDEN_GRUPOS = ["UFC","ESPN","TNT Sports","Fox Sports","Chile","HBO","TNT / Turner","Fox","Warner","Peliculas","Otros"]

canales_finales.sort(key=lambda x: (
    ORDEN_GRUPOS.index(extraer_grupo(x[2])) if extraer_grupo(x[2]) in ORDEN_GRUPOS else 99,
    x[0].lower()
))

# Escribir archivo final
with open(ARCHIVO, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    grupo_actual = None
    for nombre, url, extinf in canales_finales:
        grupo = extraer_grupo(extinf)
        if grupo != grupo_actual:
            f.write("\n")
            grupo_actual = grupo
        f.write(extinf + "\n")
        f.write(url + "\n")

from collections import Counter
conteo = Counter(extraer_grupo(e) for _,_,e in canales_finales)

print(f"VOD/series eliminados:  {vod_eliminados}")
print(f"Duplicados eliminados:  {len(canales) - len(canales_finales)}")
print(f"\nCanales finales por grupo:")
for g in ORDEN_GRUPOS:
    if conteo[g]:
        print(f"  {g:<15} {conteo[g]}")
print(f"\nTotal final: {len(canales_finales)} canales")
