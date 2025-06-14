# === INICIO DEL CÓDIGO FINAL CON CORRECCIÓN DE EMOJIS ===

import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP
from datetime import datetime

# --- 1. CONFIGURACIÓN GLOBAL ---
URL_FUENTE = "https://www.kaelustvsoporte.com/"
NOMBRE_ARCHIVO_PROGRAMACION = "programacion.html"
# Cambiamos el nombre del archivo a .html
NOMBRE_ARCHIVO_MENSAJE = "mensaje_whatsapp.html"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"

# --- 2. FUNCIÓN DE TRANSFORMACIÓN HTML (sin cambios) ---
def aplicar_reglas_html(texto_crudo):
    # (Esta función se queda exactamente igual que en la versión anterior)
    resultado_html = ""
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE = ["Este", "Centro", "Pacífico"]
    lineas = texto_crudo.strip().split('\n')
    year_actual = datetime.now().year
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith("Eventos Deportivos"):
            fecha_texto = linea.replace("Eventos Deportivos ", "").strip()
            resultado_html += f"<h2>Eventos Deportivos, {year_actual} <br /><br />\n{fecha_texto} <br /><br /><br />\n"
        elif "WWE Wrestling" in linea or REGEX_EMOJI.search(linea):
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
    return resultado_html

# --- 3. FUNCIÓN PARA CREAR MENSAJE (ACTUALIZADA PARA GENERAR HTML) ---
def crear_mensaje_whatsapp(texto_crudo):
    print("Generando mensaje para WhatsApp en formato HTML...")
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    lineas = texto_crudo.strip().split('\n')
    
    titulos_con_emoji = []
    fecha_del_dia = ""
    
    for linea in lineas:
        linea = linea.strip()
        if linea.startswith("Eventos Deportivos"):
            fecha_del_dia = linea.replace("Eventos Deportivos ", "").strip()
        elif "WWE Wrestling" in linea or REGEX_EMOJI.search(linea):
            titulos_con_emoji.append(linea)

    year_actual = datetime.now().year
    fecha_formateada = f"{fecha_del_dia} de {year_actual}"
    lista_de_titulos = "\n".join(titulos_con_emoji)

    # Primero creamos el texto plano del mensaje
    mensaje_texto_plano = f"""🎯 ¡Guía de Eventos Deportivos en Vivo de Hoy! 🏆🔥

Consulta los horarios y canales de transmisión aquí:

👉 https://24hometv.xyz/#horarios


📅 *{fecha_formateada}*

{lista_de_titulos}

📱 ¿Listo para no perderte ni un segundo de acción?

Dale clic al enlace y entérate de todo en segundos 👇

👉 https://24hometv.xyz/#horarios

⭐ 24IPTV & HomeTV – Tu Mejor Elección en Entretenimiento Deportivo ⭐"""
    
    # Ahora envolvemos ese texto en una estructura HTML simple para forzar la codificación UTF-8
    mensaje_html_final = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mensaje para WhatsApp</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f0f2f5; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; font-size: 16px; margin: 20px auto; padding: 20px; max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <pre>{mensaje_texto_plano}</pre>
</body>
</html>"""
    
    print("Mensaje en formato HTML generado.")
    return mensaje_html_final

# --- 4. FUNCIÓN PRINCIPAL (el resto del código no cambia) ---
def main():
    # (Esta función se queda exactamente igual que en la versión anterior)
    print("Iniciando proceso de actualización automática...")
    try:
        print("1. Extrayendo datos...")
        respuesta = requests.get(URL_FUENTE, timeout=20)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        ancla = soup.find(string=lambda text: text and "⚽️" in text)
        if not ancla:
            raise ValueError("ERROR CRÍTICO: No se encontró el ancla (⚽️).")
        bloque_contenido = ancla.parent.parent.parent
        if not bloque_contenido or bloque_contenido.name != 'div':
             raise ValueError("ERROR: No se pudo aislar el bloque <div> contenedor.")
        texto_extraido_filtrado = bloque_contenido.get_text(separator='\n', strip=True)
        print("Datos extraídos correctamente.")
    except Exception as e:
        print(f"ERROR FATAL en la extracción: {e}")
        return

    contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    print(f"Guardando '{NOMBRE_ARCHIVO_PROGRAMACION}'...")
    with open(NOMBRE_ARCHIVO_PROGRAMACION, 'w', encoding='utf-8') as f:
        f.write(contenido_html_programacion)
    
    contenido_mensaje_whatsapp = crear_mensaje_whatsapp(texto_extraido_filtrado)
    print(f"Guardando '{NOMBRE_ARCHIVO_MENSAJE}'...")
    with open(NOMBRE_ARCHIVO_MENSAJE, 'w', encoding='utf-8') as f:
        f.write(contenido_mensaje_whatsapp)
    
    print("Archivos temporales creados.")

    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return

    try:
        print(f"Subiendo archivos al servidor FTP en {FTP_HOST}...")
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_PROGRAMACION, 'rb') as file:
                print(f"Subiendo '{NOMBRE_ARCHIVO_PROGRAMACION}'...")
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_PROGRAMACION}', file)
            with open(NOMBRE_ARCHIVO_MENSAJE, 'rb') as file:
                print(f"Subiendo '{NOMBRE_ARCHIVO_MENSAJE}'...")
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_MENSAJE}', file)
            print("¡Subida de todos los archivos completada exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")

# === FIN DEL CÓDIGO ===
