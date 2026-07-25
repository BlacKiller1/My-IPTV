import urllib.request
import concurrent.futures
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVOS = ["13-6.txt", "19-5.txt", "4-6.txt"]

# TNT Sports (todas las variantes: base, 2, 3, Premium, Estadio, HD/FHD)
PAT_TNT = re.compile(r"(?i)^\s*TNT\s*Sports?\b")
# Señales de que es el feed chileno
PAT_CL  = re.compile(r"(?i)(\bCL\b|chile|chi\b|\bcdf\b|estadio|premium)")
# Señales de otro país (para descartar/avisar)
PAT_OTRO = re.compile(r"(?i)(\bARG\b|argentina|\bBR\b|brasil|\bUS\b|\bUK\b|\bMX\b)")

EXCLUIR = re.compile(r"(?i)(S\d{1,2}[xEe]\d{1,2}|\(\d{4}\)|iVBORw|base64|\.(mkv|mp4|avi)|/series/|/movie/)")

def calidad(nombre):
    n = nombre.upper()
    if 'FHD' in n: return 3
    if '4K' in n or 'UHD' in n: return 4
    if 'HD' in n: return 2
    return 1

def buscar(url):
    res = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            extinf = ""; n_lineas = 0
            for lb in resp:
                n_lineas += 1
                if n_lineas > 60000:
                    break
                linea = lb.decode('utf-8', errors='ignore').strip()
                if linea.startswith('#EXTINF'):
                    extinf = linea
                elif linea.startswith('http') and extinf:
                    p = extinf.split(',', 1)
                    nombre = p[1].strip() if len(p) > 1 else ""
                    if PAT_TNT.search(nombre) and not EXCLUIR.search(nombre):
                        res.append((nombre, extinf, linea, calidad(nombre)))
                    extinf = ""
    except Exception:
        pass
    return res

def cargar_urls(a):
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
    # dedup por URL de stream
    cand = {}  # surl -> (nombre, extinf, score)
    for arch in ARCHIVOS:
        urls = cargar_urls(arch)
        if not urls: continue
        print(f"Buscando TNT Sports en {arch} ({len(urls)} listas)...")
        completadas = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as ex:
            fut = {ex.submit(buscar, u): u for u in urls}
            for f in concurrent.futures.as_completed(fut):
                for nombre, extinf, surl, score in f.result():
                    if surl not in cand:
                        cand[surl] = (nombre, extinf, score)
                completadas += 1
                if completadas % 100 == 0:
                    print(f"  ... {completadas}/{len(urls)} | candidatos: {len(cand)}")

    print(f"\nTNT Sports en bruto: {len(cand)} streams. Verificando activos...\n")

    activos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        fut = {ex.submit(verificar, surl): (surl, d) for surl, d in cand.items()}
        for f in concurrent.futures.as_completed(fut):
            surl, (nombre, extinf, score) = fut[f]
            if f.result():
                activos.append((nombre, extinf, surl, score))

    # Clasificar: Chile vs otros
    chile = []; otros = []
    for nombre, extinf, surl, score in activos:
        if PAT_OTRO.search(nombre) and not PAT_CL.search(nombre):
            otros.append((nombre, extinf, surl, score))
        else:
            chile.append((nombre, extinf, surl, score))

    # dedup por nombre normalizado, mejor calidad
    def dedup(lst):
        best = {}
        for nombre, extinf, surl, score in lst:
            k = re.sub(r'\s+', ' ', nombre.lower()).strip()
            if k not in best or score > best[k][3]:
                best[k] = (nombre, extinf, surl, score)
        return sorted(best.values(), key=lambda x: x[0].lower())

    chile_d = dedup(chile)
    otros_d = dedup(otros)

    print(f"=== TNT Sports CHILE / sin país ({len(chile_d)}) ===")
    for nombre, extinf, surl, score in chile_d:
        print(f"  {nombre}")
        print(f"    {surl}")
    print(f"\n=== TNT Sports otros países ({len(otros_d)}) ===")
    for nombre, extinf, surl, score in otros_d:
        print(f"  {nombre}")

if __name__ == "__main__":
    principal()
