import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP
from datetime import datetime
import json

# --- 1. CONFIGURACIÓN ---
URL_FUENTE = os.getenv('URL_FUENTE')
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
NOMBRE_ARCHIVO_JSON = 'events.json'
NOMBRE_ARCHIVO_PROGRAMACION = os.getenv('NOMBRE_ARCHIVO_PROGRAMACION', 'programacion.html')
NOMBRE_ARCHIVO_MENSAJE = os.getenv('NOMBRE_ARCHIVO_MENSAJE', 'mensaje_whatsapp.html')

# --- 2. FUNCIÓN PARA GENERAR EL HTML ANTIGUO (CORREGIDA) ---
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
            resultado_html += f"<h2>Eventos Deportivos, {year_actual} <br /><br />\n{fecha_texto} <br /><br /><br />\n"
        # CORRECCIÓN: Identifica correctamente las líneas de título de evento
        elif REGEX_EMOJI.search(linea) or "Evento BOX" in linea:
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
    return resultado_html

# --- 3. FUNCIÓN PARA GENERAR EL MENSAJE DE WHATSAPP ---
def crear_mensaje_whatsapp(texto_crudo):
    # Sin cambios necesarios aquí
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
    fecha_formateada = f"{fecha_del_dia} de {year_actual}" if fecha_del_dia else f"Hoy, {datetime.now().strftime('%d de %B')}"
    lista_de_titulos = "\n".join(titulos_con_emoji)
    
    mensaje_texto_plano = f"""🎯 ¡Guía de Eventos Deportivos en Vivo de Hoy! 🏆🔥\n\nConsulta los horarios y canales de transmisión aquí:\n\n👉 https://24hometv.xyz/#horarios\n\n\n📅 *{fecha_formateada}*\n\n{lista_de_titulos}\n\n📱 ¿Listo para no perderte ni un segundo de acción?\n\nDale clic al enlace y entérate de todo en segundos 👇\n\n👉 https://24hometv.xyz/#horarios\n\n⭐ 24IPTV & HomeTV – Tu Mejor Elección en Entretenimiento Deportivo ⭐"""
    mensaje_html_final = f"""<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <title>Mensaje para WhatsApp</title>\n</head>\n<body>\n    <pre>{mensaje_texto_plano}</pre>\n</body>\n</html>"""
    return mensaje_html_final

# --- 4. FUNCIÓN JSON CON LÓGICA DE PARSEO FINAL ---
def crear_json_eventos(texto_crudo):
    datos_json = { "fecha_actualizacion": datetime.now().isoformat(), "titulo_guia": "", "eventos": [] }
    lineas = texto_crudo.strip().split('\n')
    evento_actual = None
    detalle_partido_actual = "" # Variable para guardar detalles como el estadio
    
    REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las"]

    for linea in lineas:
        linea = linea.strip()
        if not linea or "Kaelus Soporte" in linea or "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳" in linea: continue
        
        if "Eventos Deportivos" in linea:
            datos_json["titulo_guia"] = linea
            continue

        if REGEX_EMOJI.search(linea) or "Evento BOX" in linea:
            if evento_actual: datos_json["eventos"].append(evento_actual)
            evento_actual = { "evento_principal": linea, "detalle_evento": "", "partidos": [] }
            detalle_partido_actual = ""
        
        elif any(keyword in linea for keyword in PALABRAS_CLAVE_HORARIOS):
            if evento_actual:
                partido = {}
                descripcion, horarios = "", ""
                canales = []

                # CORRECCIÓN: Separa la descripción de las frases de horario
                split_frases = r'\s+a las\s+|\s+apartir de las\s+'
                partes_descripcion = re.split(split_frases, linea, 1)
                
                descripcion_raw = partes_descripcion[0]
                horarios_raw = partes_descripcion[1] if len(partes_descripcion) > 1 else ''

                if " por " in horarios_raw:
                    horarios, canales_raw = horarios_raw.split(" por ", 1)
                    canales_raw = canales_raw.replace(" y ", ", ")
                    canales = [c.strip() for c in canales_raw.split(',')]
                else:
                    horarios = horarios_raw
                
                partido["descripcion"] = (detalle_partido_actual + " " + descripcion_raw).strip()
                partido["horarios"] = horarios.strip()
                partido["canales"] = canales
                
                evento_actual["partidos"].append(partido)
                detalle_partido_actual = "" # Limpiar el detalle después de usarlo

        else: # Si no tiene emoji ni horario, es un detalle de evento o de partido
            if evento_actual:
                if not evento_actual["partidos"]:
                    evento_actual["detalle_evento"] += f" {linea}".strip()
                else:
                    detalle_partido_actual += f" {linea}".strip()

    if evento_actual: datos_json["eventos"].append(evento_actual)
    datos_json["eventos"] = [e for e in datos_json["eventos"] if e.get("partidos")]
    
    return json.dumps(datos_json, indent=4, ensure_ascii=False)


# --- 5. FUNCIÓN PRINCIPAL ---
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

    print("2. Generando contenido para los 3 archivos...")
    contenido_json = crear_json_eventos(texto_extraido_filtrado)
    contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    contenido_mensaje_whatsapp = crear_mensaje_whatsapp(texto_extraido_filtrado)
    print("Contenido generado.")

    print("3. Guardando archivos locales...")
    try:
        with open(NOMBRE_ARCHIVO_JSON, 'w', encoding='utf-8') as f: f.write(contenido_json)
        with open(NOMBRE_ARCHIVO_PROGRAMACION, 'w', encoding='utf-8') as f: f.write(contenido_html_programacion)
        with open(NOMBRE_ARCHIVO_MENSAJE, 'w', encoding='utf-8') as f: f.write(contenido_mensaje_whatsapp)
        print(f"Archivos locales guardados: {NOMBRE_ARCHIVO_JSON}, {NOMBRE_ARCHIVO_PROGRAMACION}, {NOMBRE_ARCHIVO_MENSAJE}.")
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
            for nombre_archivo in [NOMBRE_ARCHIVO_JSON, NOMBRE_ARCHIVO_PROGRAMACION, NOMBRE_ARCHIVO_MENSAJE]:
                with open(nombre_archivo, 'rb') as file:
                    print(f"Subiendo '{nombre_archivo}'...")
                    ftp.storbinary(f'STOR {nombre_archivo}', file)
            print("¡Subida de todos los archivos completada exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")
