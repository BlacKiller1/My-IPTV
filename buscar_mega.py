import urllib.request
import concurrent.futures
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVOS = ["13-6.txt", "19-5.txt"]
ARCHIVO_LISTA = "canales_tv.m3u"

# Mega principal (canal abierto chileno). Excluir Mega 2, Plus, Go, Series, etc. y otros países
PAT_MEGA = re.compile(r"(?i)^\s*Mega(visi[oó]n)?\s*(HD|FHD|CL|Chile|$|\|)")
PAT_EXCL = re.compile(r"(?i)(mega\s*2|mega\s*plus|mega\s*go|mega\s*series|mega\s*hits|"
                      r"mega\s*noticias|mega\s*pack|mega\s*flix|mega\s*cine|mega\s*kids|"
                      r"\bAR\b|argentina|\bBR\b|brasil|\bMX\b|peru|colombia|S\d{1,2}[xEe]\d{1,2}|"
                      r"\(\d{4}\)|\.mkv|\.mp4|/series/|/movie/)")

def calidad(n):
    n = n.upper()
    if 'FHD' in n: return 3
    if '4K' in n or 'UHD' in n: return 4
    if 'HD' in n: return 2
    return 1

def buscar(url):
    res = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            extinf = ""; nl = 0
            for lb in resp:
                nl += 1
                if nl > 60000: break
                linea = lb.decode('utf-8', errors='ignore').strip()
                if linea.startswith('#EXTINF'):
                    extinf = linea
                elif linea.startswith('http') and extinf:
                    p = extinf.split(',', 1)
                    nombre = p[1].strip() if len(p) > 1 else ""
                    if PAT_MEGA.search(nombre) and not PAT_EXCL.search(nombre):
                        res.append((nombre, linea, calidad(nombre)))
                    extinf = ""
    except Exception:
        pass
    return res

def cargar(a):
    try:
        with open(a, encoding='utf-8') as f:
            return [l.strip() for l in f if l.strip().startswith('http')]
    except FileNotFoundError:
        return []

def verificar(url, timeout=6):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-1024'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(256)
            return r.getcode() in (200, 206)
    except Exception:
        return False

def principal():
    cand = {}
    for arch in ARCHIVOS:
        urls = cargar(arch)
        if not urls: continue
        print(f"Buscando Mega en {arch} ({len(urls)} listas)...")
        comp = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
            fut = {ex.submit(buscar, u): u for u in urls}
            for f in concurrent.futures.as_completed(fut):
                for nombre, surl, score in f.result():
                    if surl not in cand:
                        cand[surl] = (nombre, score)
                comp += 1
                if comp % 150 == 0:
                    print(f"  ... {comp}/{len(urls)} | candidatos: {len(cand)}")
        if len(cand) >= 15:   # suficientes, no seguir a la fuente lenta
            print("  (suficientes candidatos, paro)")
            break

    print(f"\nMega en bruto: {len(cand)}. Verificando...\n")
    activos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        fut = {ex.submit(verificar, s): (s, d) for s, d in cand.items()}
        for f in concurrent.futures.as_completed(fut):
            s, (nombre, score) = fut[f]
            if f.result():
                activos.append((nombre, s, score))

    # dedup por nombre, mejor calidad
    best = {}
    for nombre, surl, score in activos:
        k = re.sub(r'\s+', ' ', nombre.lower()).strip()
        if k not in best or score > best[k][2]:
            best[k] = (nombre, surl, score)
    activos = sorted(best.values(), key=lambda x: (-x[2], x[0].lower()))

    print(f"=== Mega principal activos ({len(activos)}) ===")
    for nombre, surl, score in activos:
        print(f"  {nombre}")
        print(f"    {surl}")

    if not activos:
        print("No se encontró Mega principal activo.")
        return

    # Agregar el mejor como "Mega" al grupo Chile (reemplazar MEGA FHD viejo si existe)
    mejor_nombre, mejor_url, _ = activos[0]
    lineas = open(ARCHIVO_LISTA, encoding='utf-8', errors='ignore').readlines()
    header = lineas[0]
    grupos = {}
    i = 1
    while i < len(lineas):
        l = lineas[i].strip()
        if l.startswith('#EXTINF') and i+1 < len(lineas):
            url = lineas[i+1].strip()
            m = re.search(r'group-title="([^"]*)"', l)
            g = m.group(1) if m else ''
            p = l.split(',', 1); nom = p[1].strip() if len(p) > 1 else ''
            grupos.setdefault(g, []).append((nom, l, url))
            i += 2
        else:
            i += 1

    # Quitar cualquier "Mega" principal viejo del grupo Chile (no Mega 2)
    chile = grupos.get('Chile', [])
    chile = [(n, e, u) for (n, e, u) in chile
             if not (re.match(r'(?i)^\s*mega(visi[oó]n)?\s*(hd|fhd|$|\|)', n) and 'mega 2' not in n.lower())]
    # Agregar Mega principal
    chile.append(("Mega", '#EXTINF:-1 group-title="Chile",Mega', mejor_url))
    grupos['Chile'] = chile

    orden = ['Chile', 'Chile Noticias', 'ESPN', 'TNT Sports', 'UFC', 'NBA']
    total = 0
    with open(ARCHIVO_LISTA, 'w', encoding='utf-8') as f:
        f.write(header)
        for g in orden:
            cards = grupos.get(g, [])
            if not cards: continue
            f.write("\n")
            for nom, ext, url in sorted(cards, key=lambda x: x[0].lower()):
                f.write(ext + "\n" + url + "\n")
            total += len(cards)

    print(f"\n>> Agregado 'Mega' principal: {mejor_nombre}")
    print(f"   {mejor_url}")
    print(f"   Grupo Chile ahora: {len(grupos['Chile'])} canales. Total: {total}")

if __name__ == "__main__":
    principal()
