# === INICIO DEL CÓDIGO FINAL, DEFINITIVO Y CORREGIDO para actualizador_web.py ===

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
        
        # Ajuste para que "WWE Wrestling" también sea un título h3
        if "WWE Wrestling" in linea or REGEX_EMOJI.search(linea):
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
    return resultado_html

# --- 3. FUNCIÓN PRINCIPAL (Lógica del "Ancla y Contenedor") ---
def main():
    print("Iniciando proceso de actualización automática...")
    try:
        print(f"1. Extrayendo datos de {URL_FUENTE}...")
        respuesta = requests.get(URL_FUENTE, timeout=20)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        
        # --- LÓGICA FINAL BASADA EN ENCONTRAR EL BLOQUE CONTENEDOR ---
        print("Buscando el bloque de contenido usando el emoji de fútbol como ancla...")
        
        # 1. Buscamos el primer texto que contenga un emoji de fútbol para usarlo como 'ancla'.
        ancla = soup.find(string=lambda text: text and "⚽️" in text)
        
        if not ancla:
            raise ValueError("ERROR CRÍTICO: No se encontró el emoji ancla (⚽️) en la página para localizar el bloque.")
        
        # 2. Subimos en la jerarquía del HTML para encontrar el 'bloque' contenedor principal.
        # La estructura suele ser: ancla(texto) -> span -> p -> div (el bloque que queremos)
        bloque_contenido = ancla.parent.parent.parent
        
        # 3. Verificación de seguridad para asegurar que encontramos un bloque <div>
        if not bloque_contenido or bloque_contenido.name != 'div':
             raise ValueError("ERROR: No se pudo aislar el bloque <div> contenedor a partir del ancla. La estructura pudo cambiar.")

        print("Bloque de contenido principal aislado. Extrayendo todo el texto de este bloque.")
        
        # 4. Extraemos TODO el texto que está dentro de ese bloque, manteniendo saltos de línea.
        texto_extraido_filtrado = bloque_contenido.get_text(separator='\n', strip=True)

        if not texto_extraido_filtrado:
            raise ValueError("ERROR: El bloque de contenido aislado parece estar vacío.")

        print("Datos extraídos correctamente con el método de ancla y contenedor.")

    except Exception as e:
        print(f"ERROR FATAL en la extracción: {e}")
        return

    print("2. Transformando datos al formato HTML...")
    contenido_html_final = aplicar_reglas_html(texto_extraido_filtrado)
    
    print(f"3. Guardando resultado en el archivo temporal '{NOMBRE_ARCHIVO_HTML}'...")
    with open(NOMBRE_ARCHIVO_HTML, 'w', encoding='utf-8') as f:
        f.write(contenido_html_final)
    print("Archivo temporal creado.")

    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return

    try:
        print(f"4. Conectando al servidor FTP en {FTP_HOST}...")
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_HTML, 'rb') as file:
                print(f"Subiendo '{NOMBRE_ARCHIVO_HTML}' a la carpeta '{RUTA_REMOTA_FTP}'...")
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_HTML}', file)
            print("¡Subida por FTP completada exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

# --- PUNTO DE ENTRADA DEL SCRIPT ---
if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")

# === FIN DEL CÓDIGO FINAL, DEFINITIVO Y CORREGIDO para actualizador_web.py ===
