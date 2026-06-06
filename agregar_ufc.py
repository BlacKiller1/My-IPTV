import urllib.request
import concurrent.futures
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARCHIVO_SALIDA = "lista_chile_final.m3u"

# Las 38 listas que confirmamos tienen UFC
URLS_CON_UFC = [
    "http://tentacyon.org:2096/get.php?username=Pedro74&password=Pedro74&type=m3u_plus",
    "http://tentacyon.org:2096/get.php?username=Cristian25&password=Cristian25&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=Cristianbe56&password=Benavente56&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=ClienteHenryC1A24n&password=NJMeWb8NaMST&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=jparodi&password=FE2rwz9p8KLP&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=ClienteAnpacu240224&password=7pahj62ajgh&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=VinicioGranda&password=099880VG&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=ANWRtU64Wd&password=7yQ4ngDkVm&type=m3u_plus",
    "http://rlatinop.com:8880/get.php?username=Jhonatan2.tv&password=x9428sVkss7T&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=52ure776th&password=52ure776th&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=DanielSpi&password=Nhtre98jgZvvR5&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=AbigailQuintuna&password=LV9z2EEPrmGE&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=usuariocanales234&password=KxgqUWyS9R&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=cliente617&password=654321&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=usuariocanales259&password=eVySVC6vv5&type=m3u_plus",
    "http://xstr.cyou:8080/get.php?username=Manuelmogrovejo&password=m9L3jQtewZFs&type=m3u_plus",
    "http://redworld.pro:8880//get.php?username=xpnkjqoezi&password=bM3Ey6pmL3a9&type=m3u_plus",
    "http://rlatinop.com:8880/get.php?username=Jessika11&password=GAB8b3ZqUV3a&type=m3u_plus",
    "http://rlatinop.com:8880/get.php?username=61717117&password=qTWrKTLgrw4a&type=m3u_plus",
    "http://redworld.pro:8880//get.php?username=Gangalee&password=Lq8CeHefNV6k&type=m3u_plus",
    "http://rlatinop.com:8880/get.php?username=JoseD24&password=3zQgMyUmzvuw&type=m3u_plus",
    "http://resplaytvofc.vip:80/get.php?username=7109212&password=710472267&type=m3u_plus",
    "http://xstr.cyou:8080/get.php?username=Sofy_chavez_211&password=m2tXPw9QFFxd&type=m3u_plus",
    "http://elpapanatas.space:8080/get.php?username=eder7378&password=8388eder&type=m3u_plus",
    "http://elpapanatas.space:8080/get.php?username=JavierRenderos&password=xakRfkrgDJ&type=m3u_plus",
    "http://elpapanatas.space:8080/get.php?username=12meses21890310&password=12meses21890310&type=m3u_plus",
    "http://elpapanatas.space:8080/get.php?username=3mauric1206&password=XJQ7mmhZFf&type=m3u_plus",
    "http://xstr.cyou:8080/get.php?username=JUF297LUY0&password=cta27playec&type=m3u_plus",
    "http://infinitisurl.com:8080/get.php?username=JARED34&password=675GTd&type=m3u_plus",
    "http://xstr.cyou:8080/get.php?username=eromero2121&password=s1stemas13579&type=m3u_plus",
    "http://xstr.cyou:8080/get.php?username=antonioosejos&password=Antonio02122022&type=m3u_plus",
    "http://xstr.cyou:8080/get.php?username=IsaacB0013&password=B4qJCJN47tBQ&type=m3u_plus",
    "http://xstr.cyou:8080/get.php?username=Arce3682&password=cEGuVWH9dcMQ&type=m3u_plus",
]

def extraer_ufc(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    encontrados = []
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            linea_extinf = ""
            for linea_bytes in resp:
                linea = linea_bytes.decode('utf-8', errors='ignore').strip()
                if linea.startswith("#EXTINF"):
                    linea_extinf = linea
                elif linea.startswith("http") and linea_extinf:
                    if "ufc" in linea_extinf.lower():
                        partes = linea_extinf.split(',', 1)
                        nombre = partes[1].strip() if len(partes) > 1 else "UFC"
                        encontrados.append((nombre, linea))
                    linea_extinf = ""
    except Exception:
        pass
    return encontrados

def verificar_url(url, timeout=8):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-1024'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(512)
            return r.getcode() in (200, 206)
    except Exception:
        return False

def principal():
    print(f"Extrayendo UFC de {len(URLS_CON_UFC)} listas confirmadas...\n")

    todos = {}  # url_stream -> nombre (deduplicar por URL)

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futuros = [executor.submit(extraer_ufc, url) for url in URLS_CON_UFC]
        for futuro in concurrent.futures.as_completed(futuros):
            for nombre, stream in futuro.result():
                if stream not in todos:
                    todos[stream] = nombre

    print(f"Canales UFC únicos encontrados: {len(todos)}")
    print("Verificando cuales están en línea...\n")

    activos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futuros = {executor.submit(verificar_url, url): (nombre, url) for url, nombre in todos.items()}
        for futuro in concurrent.futures.as_completed(futuros):
            nombre, url = futuros[futuro]
            if futuro.result():
                activos.append((nombre, url))
                print(f"  [VIVO] {nombre}")

    activos.sort(key=lambda x: x[0].lower())

    print(f"\nAgregando {len(activos)} canales UFC activos a {ARCHIVO_SALIDA}...")

    with open(ARCHIVO_SALIDA, "a", encoding="utf-8") as f:
        for nombre, url in activos:
            f.write(f"#EXTINF:-1,{nombre}\n{url}\n")

    print(f"\n{'='*50}")
    print(f"LISTO - UFC agregado a {ARCHIVO_SALIDA}")
    print(f"Canales UFC activos añadidos: {len(activos)}")
    for nombre, _ in activos:
        print(f"  - {nombre}")

if __name__ == "__main__":
    principal()
