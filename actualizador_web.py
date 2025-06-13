# === INICIO DEL CÓDIGO PARA actualizador_web.py ===

# 1. Importaciones necesarias
import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP

# 2. Configuración Global
URL_FUENTE = "https://www.kaelustvsoporte.com/"
NOMBRE_ARCHIVO_HTML = "programacion.html"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/" # ¡IMPORTANTE! Ajusta si tu ruta es diferente (ej. /www/)

# 3. Función de Transformación HTML
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

# 4. Función Principal que orquesta todo
def main():
    print("Iniciando proceso de actualización automática...")
    try:
        print(f"1. Extrayendo datos de {URL_FUENTE}...")
        respuesta = requests.get(URL_FUENTE, timeout=20)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        marcador_texto = "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳"
        marcadores = soup.find_all(string=lambda t: t and marcador_texto in t)
        if len(marcadores) < 2:
            raise ValueError(f"ERROR CRÍTICO: No se encontraron los dos marcadores de emojis. Hallados: {len(marcadores)}")

        # La corrección clave: subimos dos niveles para encontrar el <p> contenedor
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
        print
