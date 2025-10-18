import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP
from datetime import datetime
import json
# Se mantiene el import de google.generativeai, aunque no se use en este script
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_FUENTE = os.getenv('URL_FUENTE')
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
NOMBRE_ARCHIVO_JSON = 'events.json'
NOMBRE_ARCHIVO_PROGRAMACION = os.getenv('NOMBRE_ARCHIVO_PROGRAMACION', 'programacion.html')
NOMBRE_ARCHIVO_MENSAJE = os.getenv('NOMBRE_ARCHIVO_MENSAJE', 'mensaje_whatsapp.html')
NOMBRE_ARCHIVO_SITEMAP = 'sitemap.xml'
NOMBRE_ARCHIVO_TELEGRAM = 'telegram_message.txt' # NUEVA CONSTANTE: Archivo de Texto Puro para Telegram
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- 2. FUNCIÓN PARA GENERAR EL HTML DE LA PÁGINA ---
def aplicar_reglas_html(texto_crudo):
    resultado_html = ""
    REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE = ["Este", "Centro", "Pacífico"]
    lineas = texto_crudo.strip().split('\n')
    year_actual = datetime.now().year
    
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        if linea.startswith("Eventos Deportivos"):
            fecha_texto = linea.replace("Eventos Deportivos ", "").strip()
            resultado_html += f"<h2>Eventos Deportivos y Especiales, {year_actual} <br /><br />\n{fecha_texto} <br /><br /><br />\n"
        elif "WWE Wrestling" in linea or REGEX_EMOJI.search(linea) or "Evento BOX" in linea:
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
    return resultado_html

# --- 3. FUNCIÓN PARA GENERAR EL MENSAJE DE WHATSAPP (MODIFICADA) ---
def crear_mensaje_whatsapp(texto_crudo):
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    lineas = texto_crudo.strip().split('\n')
    titulos_con_emoji = []
    fecha_del_dia = ""
    separador_emojis = "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳"
    separador_count = 0

    for linea in lineas:
        linea = linea.strip()
        if linea.startswith("Eventos Deportivos"):
            fecha_del_dia = linea.replace("Eventos Deportivos ", "").strip()
        elif separador_emojis in linea:
            separador_count += 1
            if separador_count == 1:
                titulos_con_emoji.append(f"{linea}\n")
            else:
                titulos_con_emoji.append(f"\n{linea}")
        elif "WWE Wrestling" in linea or REGEX_EMOJI.search(linea) or "Evento BOX" in linea:
            titulos_con_emoji.append(linea)
    
    year_actual = datetime.now().year
    fecha_formateada = f"{fecha_del_dia} de {year_actual}" if fecha_del_dia else f"Hoy, {datetime.now().strftime('%d de %B')}"
    lista_de_titulos = "\n".join(titulos_con_emoji)
    
    # Este es el texto puro que necesitamos para Telegram
    mensaje_texto_puro = f"""🎯 ¡Guía de Eventos Deportivos y Especiales para día de Hoy! 🏆🔥

Consulta los horarios y canales de transmisión aquí:

👉 https://24hometv.xyz/#horarios


📅 *{fecha_formateada}*

{lista_de_titulos}

📱 ¿Listo para no perderte ni un segundo de acción?

Dale clic al enlace y entérate de todo en segundos 👇

👉 https://24hometv.xyz/#horarios

⭐ 24IPTV & HomeTV – Tu Mejor Elección en Entretenimiento Deportivo ⭐"""
    
    # Este es el HTML que se sube al servidor (mensaje_whatsapp.html)
    mensaje_html_final = f"""<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <title>Mensaje para WhatsApp</title>\n</head>\n<body>\n    <pre>{mensaje_texto_plano}</pre>\n</body>\n</html>"""
    
    # DEVOLVEMOS AMBOS: HTML para la web y Texto Puro para Telegram
    return mensaje_html_final, mensaje_texto_plano


# --- 4. FUNCIÓN PARA GENERAR ARCHIVO TXT PURO PARA TELEGRAM (NUEVA) ---
def generar_archivo_telegram_txt(mensaje_texto_puro):
    """
    Genera un archivo de texto plano con codificación UTF-8 para evitar errores de Telegram.
    """
    try:
        # Escribimos el mensaje con codificación UTF-8 explícita
        with open(NOMBRE_ARCHIVO_TELEGRAM, 'w', encoding='utf-8') as f:
            f.write(mensaje_texto_puro)
        print(f"Archivo de texto plano '{NOMBRE_ARCHIVO_TELEGRAM}' generado para Telegram.")
    except Exception as e:
        print(f"Error al generar el archivo de texto plano para Telegram: {e}")
        raise # Propagamos el error si no se puede generar el archivo
    return NOMBRE_ARCHIVO_TELEGRAM


# --- 5. FUNCIÓN PARA COMUNICARSE CON GEMINI (ELIMINADA LA LÓGICA DE RANKING DE AQUÍ) ---
def obtener_ranking_eventos(texto_crudo):
    # NOTA: Esta función no debe usarse para el ranking; su lógica se ha movido a scripts externos.
    # El código se mantiene solo para satisfacer la llamada en 'main'.
    if 'GEMINI_API_KEY' in globals() and globals()['GEMINI_API_KEY']:
        # Si la API Key existe, intentamos simular el ranking
        # Pero en este proyecto, se asume que scripts externos hacen esto.
        print("ADVERTENCIA: La lógica de ranking ha sido delegada a scripts externos.")
        return []
    else:
        print("ADVERTENCIA: No se encontró la API Key de Gemini. Omitiendo el ranking de eventos.")
        return []

# --- 6. FUNCIÓN PARA CREAR JSON DE EVENTOS ---
def crear_json_eventos(texto_crudo, ranking):
    # Adaptación de la función original para que devuelva el contenido JSON
    data = {
        "fecha_extraccion": datetime.now().isoformat(),
        "contenido_texto_crudo": texto_crudo,
        # Si el ranking se usa, se incluiría aquí. Por ahora, queda fuera de este script.
    }
    
    try:
        # ensure_ascii=False es crucial para guardar emojis y tildes correctamente
        contenido_json = json.dumps(data, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error al serializar el JSON: {e}")
        return "{}"

    return contenido_json


# --- 7. FUNCIÓN PARA CREAR SITEMAP ---
def crear_sitemap():
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    contenido_sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://24hometv.xyz/</loc>
    <lastmod>{fecha_actual}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    with open(NOMBRE_ARCHIVO_SITEMAP, 'w', encoding='utf-8') as f:
        f.write(contenido_sitemap)
    print("Archivo sitemap.xml generado con la fecha de hoy.")


# --- 8. FUNCIÓN PRINCIPAL (AJUSTADA) ---
def main():
    print("Iniciando proceso de actualización de todos los archivos...")
    if not URL_FUENTE:
        print("ERROR CRÍTICO: El secret URL_FUENTE no está configurado.")
        return
    try:
        print("1. Extrayendo datos de la fuente...")
        respuesta = requests.get(URL_FUENTE, timeout=20)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        bloque_contenido = soup.find('div', {'id': 'comp-khhybsn1'})
        if not bloque_contenido:
            raise ValueError("No se encontró el contenedor de eventos con ID 'comp-khhybsn1'.")
        texto_extraido_filtrado = bloque_contenido.get_text(separator='\n', strip=True)
        print("Datos extraídos correctamente.")
    except Exception as e:
        print(f"ERROR FATAL en la extracción: {e}")
        return

    ranking = [] # Se usa ranking vacío para satisfacer la llamada a crear_json_eventos
    
    print("2. Generando contenido para todos los archivos...")
    # MODIFICADO: Ahora obtenemos HTML y el Texto Puro para Telegram
    contenido_html_mensaje, contenido_texto_puro_telegram = crear_mensaje_whatsapp(texto_extraido_filtrado)
    
    contenido_json = crear_json_eventos(texto_extraido_filtrado, ranking) 
    
    contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    nombre_archivo_telegram_txt = generar_archivo_telegram_txt(contenido_texto_puro_telegram)
    crear_sitemap()
    print("Contenido generado.")

    print("3. Guardando archivos locales...")
    archivos_a_subir = []
    try:
        with open(NOMBRE_ARCHIVO_JSON, 'w', encoding='utf-8') as f: f.write(contenido_json)
        archivos_a_subir.append(NOMBRE_ARCHIVO_JSON)

        with open(NOMBRE_ARCHIVO_PROGRAMACION, 'w', encoding='utf-8') as f: f.write(contenido_html_programacion)
        archivos_a_subir.append(NOMBRE_ARCHIVO_PROGRAMACION)
        
        with open(NOMBRE_ARCHIVO_MENSAJE, 'w', encoding='utf-8') as f: f.write(contenido_html_mensaje)
        archivos_a_subir.append(NOMBRE_ARCHIVO_MENSAJE)

        archivos_a_subir.append(NOMBRE_ARCHIVO_SITEMAP)
        archivos_a_subir.append(nombre_archivo_telegram_txt) 
        
        print(f"Archivos locales guardados: {', '.join(archivos_a_subir)}.")
    except Exception as e:
        print(f"Error al guardar archivos locales: {e}")
        return

    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return
    
    print("4. Subiendo archivos al servidor FTP...")
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            for nombre_archivo in [NOMBRE_ARCHIVO_JSON, NOMBRE_ARCHIVO_PROGRAMACION, NOMBRE_ARCHIVO_MENSAJE, NOMBRE_ARCHIVO_SITEMAP, nombre_archivo_telegram_txt]:
                with open(nombre_archivo, 'rb') as file:
                    print(f"Subiendo '{nombre_archivo}'...")
                    ftp.storbinary(f'STOR {nombre_archivo}', file)
            print("¡Subida de todos los archivos completada exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")
