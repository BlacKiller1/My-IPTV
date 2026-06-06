import urllib.request
import concurrent.futures
import threading
import os

archivo_entrada = "4-6.txt"
archivo_salida = "super_lista_limpia.m3u"
archivo_caidos = "enlaces_caidos.txt"

# Candado para evitar que los múltiples hilos escriban en el archivo a la vez
lock_escritura = threading.Lock()

def procesar_lista(url):
    """Procesa el enlace en streaming y escribe directamente a disco para ahorrar RAM."""
    url = url.strip()
    if not url.startswith("http"):
        return url, False, 0
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    canales_procesados = 0
    
    try:
        with urllib.request.urlopen(req, timeout=15) as respuesta:
            if respuesta.getcode() != 200:
                return url, False, 0
            
            linea_extinf = ""
            bloque_escritura = []
            
            # Iteramos sobre la respuesta directamente (streaming) sin cargarla en RAM
            for linea_bytes in respuesta:
                linea = linea_bytes.decode('utf-8', errors='ignore').strip()
                
                if not linea:
                    continue
                
                if linea.startswith("#EXTINF"):
                    # Limpiamos para dejar solo el nombre
                    partes = linea.split(',', 1)
                    if len(partes) > 1:
                        nombre_canal = partes[1].strip()
                        linea_extinf = f"#EXTINF:-1,{nombre_canal}"
                    else:
                        linea_extinf = "#EXTINF:-1,Canal sin nombre"
                        
                elif linea.startswith("http") and linea_extinf:
                    # Preparamos el canal para escribirlo
                    bloque_escritura.append(f"{linea_extinf}\n{linea}\n")
                    linea_extinf = "" 
                    canales_procesados += 1
                    
                    # Cada 2000 canales, vaciamos el bloque al disco duro y liberamos RAM
                    if len(bloque_escritura) >= 2000:
                        with lock_escritura:
                            with open(archivo_salida, "a", encoding="utf-8") as f_out:
                                f_out.writelines(bloque_escritura)
                        bloque_escritura.clear() # Vaciamos la memoria
            
            # Escribir los canales que hayan quedado rezagados
            if bloque_escritura:
                with lock_escritura:
                    with open(archivo_salida, "a", encoding="utf-8") as f_out:
                        f_out.writelines(bloque_escritura)
                        
        return url, True, canales_procesados
        
    except Exception:
        return url, False, 0

def principal():
    try:
        with open(archivo_entrada, "r", encoding="utf-8") as f:
            urls = [linea.strip() for linea in f if linea.strip().startswith("http")]
    except FileNotFoundError:
        print(f"Error: No se encontró '{archivo_entrada}'.")
        return

    print(f"Iniciando descarga optimizada (Low RAM) de {len(urls)} listas...\n")
    
    # Preparamos los archivos (borramos versiones anteriores si existen)
    with open(archivo_salida, "w", encoding="utf-8") as f_out:
        f_out.write("#EXTM3U\n")
    if os.path.exists(archivo_caidos):
        os.remove(archivo_caidos)
    
    enlaces_inactivos = []
    listas_exitosas = 0
    total_canales_extraidos = 0
    
    # Reducido a 3 hilos para asegurar estabilidad
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        resultados = executor.map(procesar_lista, urls)
        
        for url, exito, cantidad_canales in resultados:
            if exito:
                if cantidad_canales > 0:
                    listas_exitosas += 1
                    total_canales_extraidos += cantidad_canales
                    print(f"[✔ DESCARGADA] {url} -> {cantidad_canales} canales.")
                else:
                    enlaces_inactivos.append(url)
                    print(f"[⚠ VACÍA]      {url}")
            else:
                enlaces_inactivos.append(url)
                print(f"[✖ CAÍDA]      {url}")

    # Guardar registro de los enlaces caídos
    if enlaces_inactivos:
        with open(archivo_caidos, "w", encoding="utf-8") as f_out:
            for url in enlaces_inactivos:
                f_out.write(f"{url}\n")

    print("\n" + "="*50)
    print("PROCESO FINALIZADO")
    print("="*50)
    print(f"Listas procesadas con éxito: {listas_exitosas} de {len(urls)}")
    print(f"Total de canales en disco:   {total_canales_extraidos}")
    print(f"Archivo generado:            {archivo_salida}")

if __name__ == "__main__":
    principal()