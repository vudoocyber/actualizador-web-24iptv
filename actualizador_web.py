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

# Nombres de los archivos a generar, leídos desde los Secrets de GitHub
NOMBRE_ARCHIVO_JSON = 'events.json'
NOMBRE_ARCHIVO_PROGRAMACION = os.getenv('NOMBRE_ARCHIVO_PROGRAMACION', 'programacion.html')
NOMBRE_ARCHIVO_MENSAJE = os.getenv('NOMBRE_ARCHIVO_MENSAJE', 'mensaje_whatsapp.html')
NOMBRE_ARCHIVO_SITEMAP = 'sitemap.xml'


# --- 2. FUNCIÓN PARA GENERAR EL HTML ANTIGUO ---
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
        elif REGEX_EMOJI.search(linea) or "Evento BOX" in linea:
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
    return resultado_html

# --- 3. FUNCIÓN PARA GENERAR EL MENSAJE DE WHATSAPP ---
def crear_mensaje_whatsapp(texto_crudo):
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    lineas = texto_crudo.strip().split('\n')
    titulos_con_emoji = []
    fecha_del_dia = ""
    for linea in lineas:
        linea = linea.strip()
        if linea.startswith("Eventos Deportivos"):
            fecha_del_dia = linea.replace("Eventos Deportivos ", "").strip()
        elif "WWE Wrestling" in linea or REGEX_EMOJI.search(linea) or "Evento BOX" in linea:
            titulos_con_emoji.append(linea)
    
    year_actual = datetime.now().year
    fecha_formateada = f"{fecha_del_dia} de {year_actual}" if fecha_del_dia else f"Hoy, {datetime.now().strftime('%d de %B')}"
    lista_de_titulos = "\n".join(titulos_con_emoji)
    
    mensaje_texto_plano = f"""🎯 ¡Guía de Eventos Deportivos en Vivo de Hoy! 🏆🔥\n\nConsulta los horarios y canales de transmisión aquí:\n\n👉 https://24hometv.xyz/#horarios\n\n\n📅 *{fecha_formateada}*\n\n{lista_de_titulos}\n\n📱 ¿Listo para no perderte ni un segundo de acción?\n\nDale clic al enlace y entérate de todo en segundos 👇\n\n👉 https://24hometv.xyz/#horarios\n\n⭐ 24IPTV & HomeTV – Tu Mejor Elección en Entretenimiento Deportivo ⭐"""
    mensaje_html_final = f"""<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <title>Mensaje para WhatsApp</title>\n</head>\n<body>\n    <pre>{mensaje_texto_plano}</pre>\n</body>\n</html>"""
    return mensaje_html_final

# --- 4. FUNCIÓN FINAL PARA CREAR EL JSON ---
def crear_json_eventos(texto_crudo):
    datos_json = {"fecha_actualizacion": datetime.now().isoformat(), "titulo_guia": "", "eventos": []}
    lineas = [l.strip() for l in texto_crudo.strip().split('\n') if l.strip()]

    REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las"]

    # Paso 1: Agrupar líneas por evento principal
    bloques_evento = []
    bloque_actual = []
    for linea in lineas:
        if "Eventos Deportivos" in linea:
            if "Julio" in linea or "Agosto" in linea: # Filtro para asegurar que es la línea de fecha
                datos_json["titulo_guia"] = linea
            continue
        if "Kaelus Soporte" in linea or "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳" in linea:
            continue
        
        if (REGEX_EMOJI.search(linea) or "Evento BOX" in linea) and bloque_actual:
            bloques_evento.append(bloque_actual)
            bloque_actual = [linea]
        else:
            bloque_actual.append(linea)
    if bloque_actual: bloques_evento.append(bloque_actual)

    # Paso 2: Procesar cada bloque de evento
    for bloque in bloques_evento:
        if not bloque: continue
        evento_json = {"evento_principal": bloque[0], "detalle_evento": "", "partidos": []}
        contenido = bloque[1:]
        
        grupos_partido = []
        grupo_actual = []
        for linea in contenido:
            grupo_actual.append(linea)
            if any(keyword in linea for keyword in PALABRAS_CLAVE_HORARIOS):
                grupos_partido.append(grupo_actual)
                grupo_actual = []
        
        if grupo_actual: evento_json["detalle_evento"] = " ".join(grupo_actual).strip()
            
        # Paso 3: Parsear cada grupo de partido
        for grupo in grupos_partido:
            partido = {"detalle_partido": "", "descripcion": "", "horarios": "", "canales": []}
            linea_horario = grupo.pop()
            detalles_previos = grupo

            frases_split = r'\s+a las\s+|\s+a partir de las\s+'
            descripcion_raw = linea_horario
            horarios_raw = ""

            partes_frase = re.split(frases_split, linea_horario, 1, re.IGNORECASE)
            if len(partes_frase) > 1:
                descripcion_raw, horarios_raw = partes_frase[0], partes_frase[1]
            else:
                match_horario = re.search(r'\d.*(am|pm|AM|PM)', linea_horario)
                if match_horario:
                    pos_inicio = match_horario.start()
                    descripcion_raw = linea_horario[:pos_inicio].strip()
                    horarios_raw = linea_horario[pos_inicio:]

            partido["descripcion"] = descripcion_raw.strip()
            partido["detalle_partido"] = " ".join(detalles_previos).strip()
            
            if " por " in horarios_raw:
                horarios, canales_texto = horarios_raw.split(" por ", 1)
                partido["horarios"] = horarios.strip()
                canales_texto = canales_texto.replace(" y ", ", ")
                partido["canales"] = [c.strip() for c in canales_texto.split(',')]
            else:
                partido["horarios"] = horarios_raw.strip()
            
            evento_json["partidos"].append(partido)
        
        if evento_json["partidos"]: datos_json["eventos"].append(evento_json)
            
    return json.dumps(datos_json, indent=4, ensure_ascii=False)


# --- 5. FUNCIÓN PARA GENERAR EL SITEMAP ---
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


# --- 6. FUNCIÓN PRINCIPAL ---
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

    print("2. Generando contenido para los 4 archivos...")
    contenido_json = crear_json_eventos(texto_extraido_filtrado)
    contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    contenido_mensaje_whatsapp = crear_mensaje_whatsapp(texto_extraido_filtrado)
    crear_sitemap()
    print("Contenido generado.")

    print("3. Guard
