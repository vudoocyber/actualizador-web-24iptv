# Importamos todas las librerías necesarias al principio del archivo.
import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP

# --- 1. CONFIGURACIÓN GLOBAL ---
# Variables que el script usará.
URL_FUENTE = "https://www.kaelustvsoporte.com/"
NOMBRE_ARCHIVO_HTML = "programacion.html" # El archivo que generamos es solo el fragmento de contenido.

# Leemos los datos de FTP desde los "Secrets" de GitHub, que se configuran como variables de entorno.
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"  # ¡IMPORTANTE! Ajusta si tu ruta es diferente (ej. /www/ o solo /)


# --- 2. FUNCIÓN DE TRANSFORMACIÓN ---
# Esta función toma el texto crudo y le aplica las reglas de formato HTML.
def aplicar_reglas_html(texto_crudo):
    """
    Toma una cadena de texto con saltos de línea y aplica las reglas de formato HTML
    para generar el fragmento de código final.
    """
    resultado_html = ""
    # Expresión regular para detectar la mayoría de los emojis.
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE = ["Este", "Centro", "Pacífico"]
    
    lineas = texto_crudo.strip().split('\n')
    
    for linea in lineas:
        linea = linea.strip()
        if not linea:  # Ignorar líneas completamente vacías.
            continue

        # Aplica las reglas en el orden de prioridad definido.
        if REGEX_EMOJI.search(linea):
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
            
    return resultado_html


# --- 3. FUNCIÓN PRINCIPAL ---
# Esta es la función que orquesta todo el proceso.
def main():
    """
    Función principal que ejecuta los pasos de extracción, transformación y subida.
    """
    print("Iniciando proceso de actualización automática...")

    # PASO A: EXTRACCIÓN Y FILTRADO PRECISO
    try:
        print(f"1. Extrayendo datos de {URL_FUENTE}...")
        respuesta = requests.get(URL_FUENTE, timeout=20)
        respuesta.raise_for_status()  # Lanza un error si la petición HTTP falla.
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        
        marcador_texto = "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳"
        marcadores = soup.find_all(string=lambda t: t and marcador_texto in t)

        if len(marcadores) < 2:
            raise ValueError(f"ERROR CRÍTICO: No se encontraron los dos marcadores de emojis necesarios. Hallados: {len(marcadores)}")

        # --- LA CORRECCIÓN FINAL Y MÁS IMPORTANTE ---
        # Subimos dos niveles en el árbol HTML para encontrar el contenedor <p> correcto
        # y poder buscar a sus "hermanos".
        nodo_de_partida = marcadores[0].parent.parent
        print("Punto de partida correcto encontrado. Empezando a recopilar contenido...")
        
        lineas_deseadas = []
        for elemento in nodo_de_partida.find_next_siblings():
            if marcador_texto in elemento.get_text():
                print("Marcador de fin encontrado. Deteniendo la recopilación.")
                break
            
            texto_elemento = elemento.get_text(separator='\n', strip=True)
            if texto_elemento:
                lineas_deseadas.append(texto_elemento)

        if not lineas_deseadas:
            raise ValueError("ERROR: No se encontró contenido entre los marcadores, incluso con la lógica corregida.")
        
        texto_extraido_filtrado = "\n".join(lineas_deseadas)
        print("Datos extraídos y filtrados correctamente.")

    except Exception as e:
        print(f"ERROR FATAL en la extracción: {e}")
        return # Detiene la ejecución si la extracción falla.

    # PASO B: TRANSFORMACIÓN
    print("2. Transformando datos al formato HTML requerido...")
    contenido_html_final = aplicar_reglas_html(texto_extraido_filtrado)
    
    # PASO C: GUARDADO LOCAL (en la máquina virtual de GitHub)
    print(f"3. Guardando el resultado en el archivo temporal '{NOMBRE_ARCHIVO_HTML}'...")
    with open(NOMBRE_ARCHIVO_HTML, 'w', encoding='utf-8') as f:
        f.write(contenido_html_final)
    print("Archivo temporal creado exitosamente.")

    # PASO D: SUBIDA POR FTP
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan una o más variables de entorno para el FTP. Omitiendo la subida.")
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
# Esta construcción estándar de Python asegura que la función main() se llame
# solo cuando el archivo se ejecuta directamente.
if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")
