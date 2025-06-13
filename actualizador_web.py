# === INICIO DEL CÓDIGO COMPLETO Y CORREGIDO para actualizador_web.py ===

import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP

# --- 1. CONFIGURACIÓN GLOBAL ---
URL_FUENTE = "https://www.kaelustvsoporte.com/"
NOMBRE_ARCHIVO_HTML = "programacion.html"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"

# --- 2. FUNCIÓN DE TRANSFORMACIÓN HTML ---
def aplicar_reglas_html(texto_crudo):
    resultado_html = ""
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE = ["Este", "Centro", "Pacífico"]
    lineas = texto_crudo.strip().split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        if REGEX_EMOJI.search(linea):
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
    return resultado_html

# --- 3. FUNCIÓN PRINCIPAL QUE ORQUESTA TODO ---
def main():
    print("Iniciando proceso de actualización automática...")

    # --- INICIO DEL PRIMER BLOQUE TRY/EXCEPT: EXTRACCIÓN ---
    # Este bloque intenta extraer los datos y maneja cualquier error en el proceso.
    try:
        print(f"1. Extrayendo datos de {URL_FUENTE}...")
        respuesta = requests.get(URL_FUENTE, timeout=20)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        
        marcador_texto = "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳"
        marcadores = soup.find_all(string=lambda t: t and marcador_texto in t)
        if len(marcadores) < 2:
            raise ValueError(f"ERROR CRÍTICO: No se encontraron los dos marcadores de emojis. Hallados: {len(marcadores)}")

        nodo_de_partida = marcadores[0].parent.parent
        print("Punto de partida correcto encontrado. Recopilando contenido...")
        lineas_deseadas = []
        for elemento in nodo_de_partida.find_next_siblings():
            if marcador_texto in elemento.get_text():
                print("Marcador de fin encontrado. Deteniendo recopilación.")
                break
            texto_elemento = elemento.get_text(separator='\n', strip=True)
            if texto_elemento:
                lineas_deseadas.append(texto_elemento)
        if not lineas_deseadas:
            raise ValueError("ERROR: No se encontró contenido entre los marcadores con la lógica corregida.")
        texto_extraido_filtrado = "\n".join(lineas_deseadas)
        print("Datos extraídos y filtrados correctamente.")
    except Exception as e:
        # Si algo en el bloque 'try' de arriba falla, se ejecuta este código.
        print(f"ERROR FATAL en la extracción: {e}")
        return # Detiene la ejecución del script.
    # --- FIN DEL PRIMER BLOQUE TRY/EXCEPT ---

    print("2. Transformando datos al formato HTML requerido...")
    contenido_html_final = aplicar_reglas_html(texto_extraido_filtrado)
    
    print(f"3. Guardando resultado en el archivo temporal '{NOMBRE_ARCHIVO_HTML}'...")
    with open(NOMBRE_ARCHIVO_HTML, 'w', encoding='utf-8') as f:
        f.write(contenido_html_final)
    print("Archivo temporal creado exitosamente.")

    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return

    # --- INICIO DEL SEGUNDO BLOQUE TRY/EXCEPT: FTP ---
    # Este bloque intenta subir el archivo y maneja cualquier error de conexión o subida.
    try:
        print(f"4. Conectando al servidor FTP en {FTP_HOST}...")
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_HTML, 'rb') as file:
                print(f"Subiendo '{NOMBRE_ARCHIVO_HTML}' a la carpeta '{RUTA_REMOTA_FTP}'...")
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_HTML}', file)
            print("¡Subida por FTP completada exitosamente!")
    except Exception as e:
        # Si algo en el bloque 'try' de FTP falla, se ejecuta este código.
        print(f"ERROR FATAL durante la subida por FTP: {e}")
    # --- FIN DEL SEGUNDO BLOQUE TRY/EXCEPT ---

# --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")

# === FIN DEL CÓDIGO COMPLETO Y CORREGIDO para actualizador_web.py ===
