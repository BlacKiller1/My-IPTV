import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO_ENTRADA = "lista_chile_final.m3u"
ARCHIVO_SALIDA  = "lista_chile_final.m3u"

# Grupos en orden de prioridad (el primero que coincida gana)
GRUPOS = [
    ("UFC",          [re.compile(r"(?i)\bufc\b|combate")]),
    ("ESPN",         [re.compile(r"(?i)\bespn\b")]),
    ("TNT Sports",   [re.compile(r"(?i)tnt.{0,8}sport|tnt.{0,8}deport|\*T\*N\*T")]),
    ("Fox Sports",   [re.compile(r"(?i)fox.{0,8}sport|fox.{0,8}deport")]),
    ("Chile",        [re.compile(r"(?i)\bCL\s*\||chile|\bCHI\b|chilevision|mega\b|tvn\b|canal.?13|24.?horas|la.?red|ucv|ntv|via.?x|teletrak|cnn.?chile|premier.?chi|fut.?basic")]),
    ("HBO",          [re.compile(r"(?i)\bhbo\b|hbo.?max|hbo.?pop|hbo.?family|hbo.?plus|hbo.?xtreme")]),
    ("TNT / Turner", [re.compile(r"(?i)\btnt\b|tbs\b|turner")]),
    ("Fox",          [re.compile(r"(?i)\bfox\b")]),
    ("Warner",       [re.compile(r"(?i)\bwarner\b")]),
    ("Peliculas",    [re.compile(r"(?i)\baxn\b|axn.?movies|\bspace\b|cinemax|\bparamount\b|\buniversal\b|\bsony\b|\bfx\b|\bsyfy\b|cinecanal|\btcm\b|\bamc\b|\bgolden\b|star.?channel|\bcine\b|pelicula|\bfilm\b|\bmovie\b|bom.?cine|runtime.?cine|m\+cine")]),
    ("Otros",        [re.compile(r".*")]),  # catch-all
]

def detectar_grupo(nombre):
    for grupo, patrones in GRUPOS:
        for patron in patrones:
            if patron.search(nombre):
                return grupo
    return "Otros"

def limpiar_extinf(linea):
    """Elimina group-title existente para no duplicar."""
    linea = re.sub(r'\s*group-title="[^"]*"', '', linea)
    return linea

# Leer el archivo
with open(ARCHIVO_ENTRADA, "r", encoding="utf-8", errors="ignore") as f:
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
        grupo = detectar_grupo(nombre)
        canales.append((grupo, nombre, linea, url))
        i += 2
    else:
        i += 1

# Deduplicar por URL dentro de cada grupo
vistos = set()
canales_unicos = []
for grupo, nombre, extinf, url in canales:
    clave = url.strip()
    if clave not in vistos:
        vistos.add(clave)
        canales_unicos.append((grupo, nombre, extinf, url))

# Ordenar: primero por grupo (en el orden de GRUPOS), luego por nombre
orden_grupos = [g for g, _ in GRUPOS]
canales_unicos.sort(key=lambda x: (orden_grupos.index(x[0]), x[1].lower()))

# Escribir el archivo ordenado
with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    grupo_actual = None
    for grupo, nombre, extinf, url in canales_unicos:
        if grupo != grupo_actual:
            f.write(f"\n")
            grupo_actual = grupo

        # Limpiar group-title anterior e insertar el nuevo
        extinf_limpio = limpiar_extinf(extinf)
        # Insertar group-title justo antes del nombre (después de la última coma)
        partes = extinf_limpio.split(',', 1)
        base = partes[0]  # "#EXTINF:-1" o similar
        canal_nombre = partes[1] if len(partes) > 1 else nombre
        nueva_linea = f'{base} group-title="{grupo}",{canal_nombre}'

        f.write(nueva_linea + "\n")
        f.write(url + "\n")

# Contar por grupo
from collections import Counter
conteo = Counter(g for g, *_ in canales_unicos)

print("Lista organizada por grupos:")
for grupo in orden_grupos:
    if conteo[grupo]:
        print(f"  {grupo:<15} {conteo[grupo]} canales")
print(f"\nTotal: {len(canales_unicos)} canales")
print(f"Archivo guardado: {ARCHIVO_SALIDA}")
