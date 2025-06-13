import os
import requests
from bs4 import BeautifulSoup
from ftplib import FTP
import re
import os

# --- 1. CONFIGURACIÓN (MODIFICA ESTAS VARIABLES) ---
URL_FUENTE = "https://www.kaelustvsoporte.com/"
# Debes encontrar el selector CSS correcto. Haz clic derecho en la página y selecciona "Inspeccionar".
# Busca el contenedor principal de la programación. Puede ser un <div> con una clase o ID específico.
# Ejemplo: si el contenido está en <div class="schedule">, el selector sería 'div.schedule'
SELECTOR_CSS_CONTENIDO = "div.sqs-block-content" # ¡ESTE ES UN EJEMPLO, DEBES AJUSTARLO!

# Datos de tu servidor FTP
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/" # Ruta en el servidor donde va el archivo

# Nombre del archivo de contenido local y remoto
NOMBRE_ARCHIVO_HTML = "programacion.html"

# --- 2. LÓGICA DE TRANSFORMACIÓN (TUS REGLAS) ---
def aplicar_reglas_html(texto_crudo):
    """Aplica las reglas de etiquetado al texto extraído."""
    resultado_html = ""
    # Regex para detectar emojis (Unicode)
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE = ["Este", "Centro", "Pacífico"]
    
    lineas = texto_crudo.strip().split('\n')
    
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue # Ignorar líneas vacías

        if REGEX_EMOJI.search(linea):
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
            
    return resultado_html

# ... (las importaciones y la función aplicar_reglas_html() se mantienen igual)

def main():
    print("Iniciando proceso de actualización...")

    # --- PASO A: EXTRAER DATOS (WEB SCRAPING) ---
    try:
        print(f"1. Extrayendo datos de {URL_FUENTE}...")
        respuesta = requests.get(URL_FUENTE, timeout=15)
        respuesta.raise_for_status()
        
        soup = BeautifulSoup(respuesta.content, 'html.parser')

        # --- ¡NUEVA LÓGICA DE FILTRADO PRECISO! ---
        print("Buscando los marcadores de inicio y fin...")
        
        # El texto exacto que actúa como nuestro delimitador
        marcador_texto = "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳"

        # Buscamos TODOS los elementos que contengan exactamente esa cadena de emojis.
        # Esto es más fiable que buscar por clase, que podría cambiar.
        marcadores = soup.find_all(string=lambda t: t and marcador_texto in t)

        if len(marcadores) < 2:
            print(f"ERROR: No se encontraron los dos marcadores de emojis necesarios para delimitar el contenido. Se encontraron {len(marcadores)}.")
            return

        # El nodo de inicio es el elemento padre del primer marcador de texto
        nodo_inicio = marcadores[0].parent
        print("Marcador de inicio encontrado.")

        lineas_deseadas = []
        # Iteramos a través de todos los elementos 'hermanos' que vienen DESPUÉS del nodo de inicio
        for elemento_siguiente in nodo_inicio.find_next_siblings():
            # Condición de parada: Si encontramos el siguiente marcador de fin, salimos del bucle.
            if marcador_texto in elemento_siguiente.get_text():
                print("Marcador de fin encontrado. Deteniendo la recopilación.")
                break
            
            # Si no es el marcador de fin, extraemos su texto si tiene contenido visible.
            texto_elemento = elemento_siguiente.get_text(separator='\n', strip=True)
            if texto_elemento:
                lineas_deseadas.append(texto_elemento)

        if not lineas_deseadas:
            print("ADVERTENCIA: No se encontró contenido entre los dos marcadores.")
            return

        # Unimos todo el texto recopilado en una sola variable
        texto_extraido_filtrado = "\n".join(lineas_deseadas)
        print("Contenido entre marcadores extraído y filtrado correctamente.")

    except requests.exceptions.RequestException as e:
        print(f"ERROR al acceder a la URL: {e}")
        return
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la extracción: {e}")
        return

    # --- PASO B: TRANSFORMAR A HTML ---
    print("2. Transformando datos con las reglas HTML...")
    contenido_html_final = aplicar_reglas_html(texto_extraido_filtrado)

    # --- PASO C: GUARDAR ARCHIVO LOCALMENTE (En la máquina virtual de GitHub) ---
    print(f"3. Guardando el resultado en {NOMBRE_ARCHIVO_HTML}...")
    with open(NOMBRE_ARCHIVO_HTML, 'w', encoding='utf-8') as f:
        f.write(contenido_html_final)
    print("Archivo local actualizado.")
    
    # --- PASO D: SUBIR ARCHIVO POR FTP ---
    # (Esta parte no cambia, usa los Secrets de GitHub como ya lo configuramos)
    try:
        print(f"4. Conectando a FTP en {FTP_HOST}...")
        # ... El resto del código FTP se mantiene exactamente igual ...
        # (código para conectar, subir el archivo y cerrar la conexión)
    except Exception as e:
        print(f"ERROR durante la subida por FTP: {e}")
        return

    print("--- Proceso completado ---")


    # --- PASO B: TRANSFORMAR A HTML ---
    print("2. Transformando datos con las reglas HTML...")
    contenido_html_final = aplicar_reglas_html(texto_extraido)
    
    # Aquí puedes opcionalmente envolver el contenido en una plantilla HTML completa
    # html_completo = f"""
    # <!DOCTYPE html>
    # <html>
    # <head><title>Mi Página</title></head>
    # <body>
    # {contenido_html_final}
    # </body>
    # </html>"""
    
    # --- PASO C: GUARDAR ARCHIVO LOCALMENTE ---
    print(f"3. Guardando el resultado en {NOMBRE_ARCHIVO_HTML}...")
    with open(NOMBRE_ARCHIVO_HTML, 'w', encoding='utf-8') as f:
        f.write(contenido_html_final) # o `f.write(html_completo)` si usas plantilla
    print("Archivo local actualizado.")
    
    # --- PASO D: SUBIR ARCHIVO POR FTP ---
    try:
        print(f"4. Conectando a FTP en {FTP_HOST}...")
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.cwd(RUTA_REMOTA_FTP) # Cambiar al directorio correcto
            
            with open(NOMBRE_ARCHIVO_HTML, 'rb') as file:
                print(f"Subiendo {NOMBRE_ARCHIVO_HTML} al servidor...")
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_HTML}', file)
            
            print("¡Archivo subido exitosamente!")

    except Exception as e:
        print(f"ERROR durante la subida por FTP: {e}")
        return

    print("--- Proceso completado ---")


if __name__ == "__main__":
    main()
