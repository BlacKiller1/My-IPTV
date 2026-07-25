import urllib.request
import concurrent.futures
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVOS      = ["13-6.txt", "4-6.txt", "19-5.txt"]   # todas las fuentes, la más fresca primero
ARCHIVO_LISTA = "canales_tv.m3u"
CACHE         = ".cache_candidatos.json"
EPG_URL       = "https://epgshare01.online/epgshare01/epg_ripper_CL1.xml.gz"

# ---------- Detección por grupo ----------
# Los proveedores a veces anteponen el país: "CL: TVN HD", "CHI | Mega FHD".
P = r"(?i)^\s*(?:(?:CL|CHI|CHILE)\s*[-:|]+\s*)?"

TARGETS = [
    # === CHILE NOTICIAS === (antes que Chile: "Mega Noticias" no debe caer en "Mega")
    (re.compile(P + r"T13\b"),                                         "Chile Noticias"),
    (re.compile(P + r"24\s*Horas\b"),                                  "Chile Noticias"),
    (re.compile(P + r"CNN\s*Chile\b"),                                 "Chile Noticias"),
    (re.compile(P + r"Mega\s*noticias\b"),                             "Chile Noticias"),
    (re.compile(P + r"CHV\s*Noticias\b"),                              "Chile Noticias"),
    (re.compile(P + r"Cooperativa\b"),                                 "Chile Noticias"),
    # === CHILE ABIERTO ===
    (re.compile(P + r"TVN\b"),                                         "Chile"),
    (re.compile(P + r"Canal\s*13\b"),                                  "Chile"),
    (re.compile(P + r"13\s*Rec\b"),                                    "Chile"),
    (re.compile(P + r"Mega\b"),                                        "Chile"),
    (re.compile(P + r"(CHV|Chilevisio?n)\b"),                          "Chile"),
    (re.compile(P + r"Telecanal\b"),                                   "Chile"),
    (re.compile(P + r"La\s*Red\b"),                                    "Chile"),
    (re.compile(P + r"TV\+"),                                          "Chile"),
    (re.compile(P + r"Zona\s*Latina\b"),                               "Chile"),
    (re.compile(P + r"VIAX?\b"),                                       "Chile"),
    (re.compile(P + r"ETC\b"),                                         "Chile"),
    (re.compile(P + r"13\s*C\b"),                                      "Chile"),
    # === TNT SPORTS === (los feeds numerados llevan " 1/2/3" tras el nombre)
    (re.compile(r"(?i)\bTNT\s*Sports?\b"),                             "TNT Sports"),
    # === ESPN (post-filtrado idioma luego) ===
    (re.compile(r"(?i)^\s*ESPN\b"),                                    "ESPN"),
    # === UFC ===
    (re.compile(r"(?i)UFC"),                                           "UFC"),
    (re.compile(r"(?i)^\s*Paramount.*UFC"),                            "UFC"),
    # === NBA === (solo NBA explícito; ABC genérico trae cientos de canales locales US)
    (re.compile(r"(?i)\bNBA\b"),                                       "NBA"),
]

EXCLUIR = re.compile(
    r"(?i)(S\d{1,2}[xEe]\d{1,2}|\(\d{4}\)|iVBORw|base64|"
    r"\.(mkv|mp4|avi)|/series/|/movie/|karaoke|dragon\s*ball|telenovela)"
)

# Prefijo de país/idioma al inicio del nombre: "TR: ", "DE: ", "US | ", "CA-S: "...
PREFIJO_PAIS = re.compile(
    r"(?i)^\s*(TR|DE|PL|FR|IT|RO|NL|SE|NO|DK|FI|GR|BG|CZ|HU|RU|UK|EN|BR|PT|CA|CA-S|US|USA|AR|MX|CO|PE|VE|EC|IN|AL|EX|YU)\s*[-:|]"
)
# Idiomas/regiones que NO queremos (queremos español)
NO_ES = re.compile(
    r"(?i)(portugu[eê]s|legendado|brasil|t[uü]rk|deutsch|english|fran[çc]ais|italiano|"
    r"\bTR\b|\bBR\b|\bPT\b|\bEN\b|\bDE\b|\bPL\b|\bIT\b|\bFR\b|\bUK\b|\bRO\b|\bNL\b)"
)
# Contenido que no es el evento en sí
NO_EVENTO = re.compile(r"(?i)(weigh|pesaje|countdown|embedded|press\s*conf|conferencia|replay|prelim.*replay)")

EQUIPOS_NBA = [
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", "Chicago Bulls",
    "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", "Detroit Pistons",
    "Golden State Warriors", "Houston Rockets", "Indiana Pacers", "Los Angeles Clippers",
    "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat", "Milwaukee Bucks",
    "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks", "Oklahoma City Thunder",
    "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns", "Portland Trail Blazers",
    "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", "Utah Jazz", "Washington Wizards",
]


def calidad_score(nombre):
    """FHD primero: es lo que se ve mejor sin exigir tanto ancho de banda como 4K."""
    n = nombre.upper()
    if 'FHD' in n or '1080' in n: return 4
    if 'HD' in n:                 return 3
    if '4K' in n or 'UHD' in n:   return 2
    return 1


def detectar(nombre):
    if EXCLUIR.search(nombre):
        return None
    for patron, grupo in TARGETS:
        if patron.search(nombre):
            return grupo
    return None


# ---------- Nombre canónico: 1 entrada por canal real ----------

# Lo que puede sobrar tras el nombre del canal sin que deje de ser ese canal:
# etiquetas de calidad, país, códec, señal alternativa. Si sobra otra cosa
# ("Mega Series", "TVN Novelas"), no es el canal que buscamos.
SUFIJO_OK = re.compile(
    r"(?i)^[\s\-\|\*\(\)\[\]\.:,/²³¹⁴⁵⁶#]*"
    r"(?:(?:FHD|UHD|HD|SD|4K|8K|1080|720|CL|CHILE|CHI|TV|EN\s*VIVO|SE[NÑ]AL|"
    r"H\.?26[45]|HEVC|ALT|BACKUP|OPC?\d*|\d{1,3})"
    r"[\s\-\|\*\(\)\[\]\.:,/²³¹⁴⁵⁶#]*)*$"
)


def _canonico(nombre, reglas):
    """Primera regla cuyo patrón calza y cuyo sobrante son solo etiquetas."""
    for patron, canonico in reglas:
        m = re.match(patron, nombre)
        if m and SUFIJO_OK.match(nombre[m.end():]):
            return canonico
    return None


REGLAS_CHILE = [
    (re.compile(P + r"13\s*Rec\b"),               "13 REC"),
    (re.compile(P + r"13\s*C\b"),                 "13C"),
    (re.compile(P + r"Canal\s*13\b"),             "Canal 13"),
    (re.compile(P + r"Mega\s*2\b"),               "Mega 2"),
    (re.compile(P + r"Mega\b"),                   "Mega"),
    (re.compile(P + r"(?:CHV|Chilevisio?n)\b"),   "Chilevisión"),
    (re.compile(P + r"TVN\b"),                    "TVN"),
    (re.compile(P + r"Telecanal\b"),              "Telecanal"),
    (re.compile(P + r"La\s*Red\b"),               "La Red"),
    (re.compile(P + r"TV\+"),                     "TV+"),
    (re.compile(P + r"Zona\s*Latina\b"),          "Zona Latina"),
    (re.compile(P + r"VIAX?\b"),                  "ViaX"),
    (re.compile(P + r"ETC\b"),                    "ETC"),
]

REGLAS_NOTICIAS = [
    (re.compile(P + r"T13\b"),                    "T13"),
    (re.compile(P + r"24\s*Horas\b"),             "24 Horas"),
    (re.compile(P + r"CNN\s*Chile\b"),            "CNN Chile"),
    (re.compile(P + r"CHV\s*Noticias\b"),         "CHV Noticias"),
    (re.compile(P + r"Mega\s*noticias\b"),        "Meganoticias"),
    (re.compile(P + r"Cooperativa\b"),            "Cooperativa"),
]


def canonico_chile(n):
    return _canonico(n, REGLAS_CHILE)


def canonico_noticias(n):
    return _canonico(n, REGLAS_NOTICIAS)


def canonico_espn(n):
    if NO_ES.search(n):                       return None
    if re.search(r"(?i)ESPN\s*EXTRA", n):     return "ESPN Extra"
    if re.search(r"(?i)ESPN\s*Premium", n):   return "ESPN Premium"
    m = re.search(r"(?i)ESPN\s*([1-7])\b", n)
    if m:                                     return f"ESPN {m.group(1)}"
    if re.search(r"(?i)^\s*ESPN\s*(HD|FHD|$|\|)", n): return "ESPN 1"
    return None


def canonico_tnt(n):
    # Solo familia chilena: los feeds ARG/BR los descartó explícitamente
    if re.search(r"(?i)\b(ARG?|argentina|BR|brasil)\b", n):
        return None
    m = re.match(P + r"TNT\s*Sports?\s*(Premium\s*2|Premium|[1-3])?\b", n)
    if not m or not SUFIJO_OK.match(n[m.end():]):
        return None
    sufijo = re.sub(r"\s+", " ", (m.group(1) or "")).strip().title()
    return f"TNT Sports {sufijo}".strip()


def canonico_ufc(n):
    if NO_EVENTO.search(n):  return None
    if NO_ES.search(n) and not re.search(r"(?i)espa[nñ]ol|latino", n): return None
    m = re.search(r"(?i)UFC\s*PARAMOUNT\+?\s*([1-4])\b", n)
    if m:                                      return f"UFC Paramount+ {m.group(1)}"
    if re.search(r"(?i)UFC\s*Fight\s*Pass", n): return "UFC Fight Pass"
    if re.search(r"(?i)^\s*Paramount\s*Network", n): return "Paramount Network"
    if re.search(r"(?i)UFC", n):               return "UFC Evento"   # peleas del día
    return None


def canonico_nba(n):
    # Feeds en español por equipo (ES- NBA <equipo>) + NBA TV genérico
    m = re.search(r"(?i)ES\s*-?\s*NBA\s+(.+?)\s*$", n)
    if m:
        equipo = m.group(1).strip().lower()
        for e in EQUIPOS_NBA:
            # por apodo: "Los Angeles Lakers" y "Los Angeles Clippers" comparten ciudad
            if e.split()[-1].lower() in equipo:
                return f"NBA {e}"
        if re.search(r"(?i)^USA?$", equipo):
            return "NBA USA (ES)"
    if PREFIJO_PAIS.match(n) or NO_ES.search(n):
        return None
    if re.search(r"(?i)NBA\s*TV", n):
        return "NBA TV"
    if re.search(r"(?i)espa[nñ]ol", n) and re.search(r"(?i)\bvs\b", n):
        return "NBA Partido (ES)"
    return None


CANONICOS = {
    "Chile":          canonico_chile,
    "Chile Noticias": canonico_noticias,
    "ESPN":           canonico_espn,
    "TNT Sports":     canonico_tnt,
    "UFC":            canonico_ufc,
    "NBA":            canonico_nba,
}

ORDEN_GRUPOS = ["Chile", "Chile Noticias", "ESPN", "TNT Sports", "UFC", "NBA"]


def buscar(url):
    """Devuelve lista de (grupo, nombre, stream_url, extinf, score)."""
    res = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            extinf = ""
            n_lineas = 0
            for lb in resp:
                n_lineas += 1
                if n_lineas > 60000:   # cortar: los canales en vivo están al inicio, el resto es VOD
                    break
                linea = lb.decode('utf-8', errors='ignore').strip()
                if linea.startswith('#EXTINF'):
                    extinf = linea
                elif linea.startswith('http') and extinf:
                    partes = extinf.split(',', 1)
                    nombre = partes[1].strip() if len(partes) > 1 else ""
                    grupo = detectar(nombre)
                    if grupo:
                        res.append((grupo, nombre, linea, extinf, calidad_score(nombre)))
                    extinf = ""
    except Exception:
        pass
    return res


def cargar_urls(archivo):
    try:
        with open(archivo, encoding='utf-8') as f:
            return [l.strip() for l in f if l.strip().startswith('http')]
    except FileNotFoundError:
        print(f"  [!] No encontrado: {archivo}")
        return []


def verificar(url, timeout=6):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-1024'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(256)
            return r.getcode() in (200, 206)
    except Exception:
        return False


def fase_busqueda():
    """Descarga todas las listas y junta candidatos. Cachea para poder reajustar sin re-descargar."""
    if '--cache' in sys.argv and os.path.exists(CACHE):
        with open(CACHE, encoding='utf-8') as f:
            candidatos = json.load(f)
        print(f"Usando caché {CACHE}")
        return candidatos

    urls, vistas = [], set()
    for archivo in ARCHIVOS:
        for u in cargar_urls(archivo):
            if u not in vistas:
                vistas.add(u)
                urls.append(u)

    print(f"Buscando en {len(ARCHIVOS)} fuentes ({len(urls)} listas únicas)...")
    candidatos = {}
    completadas = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
        futuros = {executor.submit(buscar, url): url for url in urls}
        for futuro in concurrent.futures.as_completed(futuros):
            for grupo, nombre, surl, extinf, score in futuro.result():
                candidatos.setdefault(grupo, {})
                if surl not in candidatos[grupo]:
                    candidatos[grupo][surl] = (nombre, extinf, score)
            completadas += 1
            if completadas % 200 == 0:
                tot = sum(len(v) for v in candidatos.values())
                print(f"  ... {completadas}/{len(urls)} | candidatos: {tot}")

    with open(CACHE, 'w', encoding='utf-8') as f:
        json.dump(candidatos, f)
    return candidatos


CALIDAD = re.compile(r"(?i)\b(FHD|UHD|HD|SD|4K|8K|1080|720|H\.?26[45]|HEVC|OPC?\d*|CL|CHILE|CHI|TV)\b")


def es_senal_secundaria(nombre, canonico):
    """"TVN 2" no es TVN, "Telecanal 12" tampoco: número que el canal canónico no tiene."""
    limpio = CALIDAD.sub(" ", nombre)
    return bool(set(re.findall(r"\d{1,3}", limpio)) - set(re.findall(r"\d{1,3}", canonico)))


def agrupar_por_canal(candidatos):
    """{grupo: {nombre_canonico: [(score, nombre, extinf, surl), ...]}} ordenado por preferencia."""
    por_canal = {}
    for grupo in ORDEN_GRUPOS:
        fn = CANONICOS[grupo]
        for surl, (nombre, extinf, score) in candidatos.get(grupo, {}).items():
            clave = fn(nombre)
            if not clave:
                continue
            por_canal.setdefault(grupo, {}).setdefault(clave, []).append((score, nombre, extinf, surl))
    for grupo in por_canal:
        for clave, opciones in por_canal[grupo].items():
            # señal principal antes que secundaria, luego mejor calidad, luego nombre más limpio
            opciones.sort(key=lambda x: (es_senal_secundaria(x[1], clave), -x[0], len(x[1])))
    return por_canal


def primer_vivo(opciones, max_total=300, lote=50):
    """Verifica por tandas en orden de preferencia; corta apenas encuentra uno vivo."""
    for i in range(0, min(len(opciones), max_total), lote):
        tanda = opciones[i:i + lote]
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(40, len(tanda))) as ex:
            vivos = list(ex.map(lambda o: verificar(o[3]), tanda))
        for (score, nombre, extinf, surl), vivo in zip(tanda, vivos):
            if vivo:
                return (nombre, extinf, surl)
    return None


def limpiar_extinf(extinf, nombre_final, grupo):
    """Deja el EXTINF con el nombre canónico y el grupo correcto, conservando el logo."""
    atributos = extinf.split(',', 1)[0]
    atributos = re.sub(r'\s*group-title="[^"]*"', '', atributos)
    atributos = re.sub(r'\s*tvg-name="[^"]*"', '', atributos)
    atributos = re.sub(r'\s*xui-id="[^"]*"', '', atributos)
    atributos = atributos.rstrip()
    return f'{atributos} tvg-name="{nombre_final}" group-title="{grupo}",{nombre_final}'


def principal():
    candidatos = fase_busqueda()
    for g, v in candidatos.items():
        print(f"  {g}: {len(v)} candidatos")

    por_canal = agrupar_por_canal(candidatos)
    print("\nVerificando 1 stream vivo por canal...\n")

    seleccion = {}
    for grupo in ORDEN_GRUPOS:
        canales = por_canal.get(grupo, {})
        vivos = []
        for clave in sorted(canales):
            elegido = primer_vivo(canales[clave])
            if elegido:
                vivos.append((clave, elegido))
                print(f"  [VIVO] {grupo:15} {clave:32} <- {elegido[0][:45]}")
            else:
                print(f"  [ --- ] {grupo:15} {clave:32} sin stream activo")
        seleccion[grupo] = vivos

    print(f"\nEscribiendo {ARCHIVO_LISTA}...")
    total = 0
    with open(ARCHIVO_LISTA, 'w', encoding='utf-8') as f:
        f.write(f'#EXTM3U url-tvg="{EPG_URL}" x-tvg-url="{EPG_URL}"\n')
        for grupo in ORDEN_GRUPOS:
            vivos = seleccion.get(grupo, [])
            if not vivos:
                continue
            f.write("\n")
            for clave, (nombre, extinf, surl) in vivos:
                f.write(limpiar_extinf(extinf, clave, grupo) + "\n")
                f.write(surl + "\n")
            total += len(vivos)
            print(f"  {grupo}: {len(vivos)} canales")

    print(f"\nListo! {total} canales en total. EPG: {EPG_URL}")


if __name__ == "__main__":
    principal()
