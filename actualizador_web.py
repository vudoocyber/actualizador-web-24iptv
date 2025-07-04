import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP
from datetime import datetime
import json

# --- 1. CONFIGURACIÓN ---
URL_FUENTE = os.getenv('URL_FUENTE', 'URL_POR_DEFECTO_SI_NO_HAY_SECRET') # Reemplaza con tu URL si no usas secrets
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"

# Nombres de los 3 archivos que se van a generar
NOMBRE_ARCHIVO_JSON = 'events.json'
NOMBRE_ARCHIVO_PROGRAMACION = 'programacion.html'
NOMBRE_ARCHIVO_MENSAJE = 'mensaje_wsp.html'


# --- 2. FUNCIÓN PARA GENERAR EL HTML ANTIGUO (CON CORRECCIÓN UTF-8) ---
def aplicar_reglas_html(texto_crudo):
    resultado_html = ""
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE = ["Este", "Centro", "Pacífico"]
    lineas = texto_crudo.strip().split('\n')
    year_actual = datetime.now().year
    fecha_texto = ""

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


# --- 3. FUNCIÓN PARA GENERAR EL MENSAJE DE WHATSAPP (CON CORRECCIÓN UTF-8) ---
def crear_mensaje_whatsapp(texto_crudo):
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


# --- 4. NUEVA FUNCIÓN MEJORADA PARA CREAR EL JSON ---
def crear_json_eventos(texto_crudo):
    datos_json = { "fecha_actualizacion": datetime.now().isoformat(), "titulo_guia": "", "eventos": [] }
    lineas = texto_crudo.strip().split('\n')
    evento_actual = None
    REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las"]

    for linea in lineas:
        linea = linea.strip()
        if not linea or "Eventos Deportivos," in linea:
            if "Eventos Deportivos," in linea:
                 fecha_texto = linea.split(",")[1].strip()
                 datos_json["titulo_guia"] = f"Guía de Eventos del {fecha_texto}"
            continue

        if REGEX_EMOJI.search(linea):
            if evento_actual: datos_json["eventos"].append(evento_actual)
            emoji_match = REGEX_EMOJI.search(linea)
            icono = emoji_match.group(0) if emoji_match else ""
            nombre_evento = REGEX_EMOJI.sub('', linea).strip()
            evento_actual = { "evento_principal": nombre_evento, "icono": icono, "detalle_evento": "", "partidos": [] }
        
        elif any(keyword in linea for keyword in PALABRAS_CLAVE_HORARIOS):
            if evento_actual and evento_actual["partidos"]:
                ultimo_partido = evento_actual["partidos"][-1]
                if ultimo_partido["horarios"]:
                    ultimo_partido["descripcion"] += f" {linea}"
                else:
                    ultimo_partido["horarios"] = linea
                    if " por " in linea:
                        partes = linea.split(" por ", 1)
                        ultimo_partido["horarios"] = partes[0]
                        ultimo_partido["canales"] = [c.strip() for c in partes[1].split(',')]
        else:
            if evento_actual:
                if not evento_actual["partidos"] and not evento_actual["detalle_evento"]:
                    evento_actual["detalle_evento"] += f"{linea} "
                else:
                    nuevo_partido = { "descripcion": linea, "horarios": "", "canales": [] }
                    evento_actual["partidos"].append(nuevo_partido)
    
    if evento_actual: datos_json["eventos"].append(evento_actual)
    return json.dumps(datos_json, indent=4, ensure_ascii=False)


#
