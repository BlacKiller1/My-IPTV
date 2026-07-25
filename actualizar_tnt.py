import urllib.request
import concurrent.futures
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO = "canales_tv.m3u"

# Selección TNT Sports Chile (transmiten Primera División chilena)
SELECCION = [
    ("TNT Sports 1",       "http://live.iptv.wtf:80/live/awvtgznv/w2xqZb086E/15718.ts"),
    ("TNT Sports 2",       "http://jumangis.cloud:2082/JairoVargas/5T5wLJjTbu/117755"),
    ("TNT Sports 3",       "http://live.iptv.wtf:80/live/awvtgznv/w2xqZb086E/14886.ts"),
    ("TNT Sports Premium", "http://alltvmx.com:80/Maria2402marq/FDEYQhzmSq/712753.ts"),
    ("TNT Sports Premium 2","http://live.iptv.wtf:80/live/awvtgznv/w2xqZb086E/15923.ts"),
    ("TNT Sports (Eventos)","http://jumangis.cloud:2082/JairoVargas/5T5wLJjTbu/384352"),
]

def verificar(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-1024'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(256)
            return r.getcode() in (200, 206)
    except Exception:
        return False

print("Verificando TNT Sports Chile...\n")
activos = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    fut = {ex.submit(verificar, u): (n, u) for n, u in SELECCION}
    for f in concurrent.futures.as_completed(fut):
        n, u = fut[f]
        estado = "[VIVO]" if f.result() else "[OFFLINE]"
        print(f"  {estado} {n}")
        if f.result():
            activos.append((n, u))

activos.sort(key=lambda x: x[0].lower())

# Leer lista y reemplazar grupo TNT Sports
lineas = open(ARCHIVO, encoding='utf-8', errors='ignore').readlines()
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
        if g != 'TNT Sports':
            grupos.setdefault(g, []).append((nom, l, url))
        i += 2
    else:
        i += 1

grupos['TNT Sports'] = [(n, f'#EXTINF:-1 group-title="TNT Sports",{n}', u) for n, u in activos]

orden = ['Chile', 'Chile Noticias', 'ESPN', 'TNT Sports', 'UFC', 'NBA']
total = 0
with open(ARCHIVO, 'w', encoding='utf-8') as f:
    f.write(header)
    for g in orden:
        cards = grupos.get(g, [])
        if not cards: continue
        f.write("\n")
        for nom, ext, url in sorted(cards, key=lambda x: x[0].lower()):
            f.write(ext + "\n" + url + "\n")
        total += len(cards)
        print(f"  {g}: {len(cards)}")

print(f"\nTNT Sports actualizado: {len(activos)} canales chilenos. Total lista: {total}")
