import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO = "lista_chile_final.m3u"
ARCHIVO_LIMPIO = "lista_chile_final.m3u"

# Nombres de canales UFC reales (deben coincidir como palabra al inicio o exactamente)
PATRON_UFC_REAL = re.compile(
    r"(?i)^(UFC\s*(1|2|3|4|fight\s*pass|network|tv|channel|figth|01|02|\*|\²|\¹|fight)|\bufc\b\s*$|combate\s*(hd|fhd)?$|undefined\s*ufc|ufc\s*fight\s*pass)",
    re.IGNORECASE
)

# Patrones que claramente NO son canales UFC
PATRON_FALSO = re.compile(
    r"(?i)(karaoke|pelicula|serie|s0[0-9]\s*e[0-9]|iVBORw|base64|tmdb|group-title=.*cine|yellowstone|chicago|jack ryan|rocky|marvel|sector)",
    re.IGNORECASE
)

def es_ufc_real(nombre):
    nombre = nombre.strip()
    if PATRON_FALSO.search(nombre):
        return False
    return PATRON_UFC_REAL.search(nombre) is not None

with open(ARCHIVO, "r", encoding="utf-8", errors="ignore") as f:
    lineas = f.readlines()

salida = []
i = 0
ufc_guardados = 0
ufc_descartados = 0

while i < len(lineas):
    linea = lineas[i].strip()

    if linea.startswith("#EXTINF"):
        partes = linea.split(',', 1)
        nombre = partes[1].strip() if len(partes) > 1 else ""

        url = lineas[i+1].strip() if i+1 < len(lineas) else ""

        # Si es un canal UFC falso, lo saltamos
        if "ufc" in nombre.lower() and not es_ufc_real(nombre):
            ufc_descartados += 1
            i += 2
            continue

        salida.append(linea + "\n")
        if url:
            salida.append(url + "\n")
        i += 2
    else:
        salida.append(lineas[i])
        i += 1

with open(ARCHIVO_LIMPIO, "w", encoding="utf-8") as f:
    f.writelines(salida)

total = sum(1 for l in salida if l.startswith("#EXTINF"))
print(f"Canales UFC falsos eliminados: {ufc_descartados}")
print(f"Total canales en lista final:  {total}")
print(f"Archivo limpio guardado:       {ARCHIVO_LIMPIO}")
