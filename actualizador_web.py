import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP
from datetime import datetime
import json
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_FUENTE = os.getenv('URL_FUENTE')
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
NOMBRE_ARCHIVO_JSON = 'events.json'
# NOMBRE_ARCHIVO_PROGRAMACION ELIMINADO
NOMBRE_ARCHIVO_MENSAJE = os.getenv('NOMBRE_ARCHIVO_MENSAJE', 'mensaje_whatsapp.html')
NOMBRE_ARCHIVO_SITEMAP = 'sitemap.xml'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- 2. FUNCIÓN PARA GENERAR EL HTML DE LA PÁGINA (ELIMINADA) ---
# Se eliminó aplicar_reglas_html

# --- 3. FUNCIÓN PARA GENERAR EL MENSAJE DE WHATSAPP ---
def crear_mensaje_whatsapp(texto_crudo):
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    lineas = texto_crudo.strip().split('\n')
    titulos_con_emoji = []
    fecha_del_dia = ""
    separador_emojis = "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳"
    separador_count = 0

    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
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
    
    mensaje_texto_puro = f"""🎯 ¡Guía de Eventos Deportivos y Especiales para día de Hoy! 🏆🔥

Consulta los horarios y canales de transmisión aquí:

👉 https://24hometv.xyz/#horarios


📅 *{fecha_formateada}*

{lista_de_titulos}

📱 ¿Listo para no perderte ni un segundo de acción?

Dale clic al enlace y entérate de todo en segundos 👇

👉 https://24hometv.xyz/#horarios

⭐ 24IPTV & HomeTV – Tu Mejor Elección en Entretenimiento Deportivo ⭐"""
    
    mensaje_html_final = f"""<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <title>Mensaje para WhatsApp</title>\n</head>\n<body>\n    <pre>{mensaje_texto_puro}</pre>\n</body>\n</html>"""
    return mensaje_html_final

# --- 4. FUNCIÓN PARA COMUNICARSE CON GEMINI ---
def obtener_ranking_eventos(texto_crudo):
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: No se encontró la API Key de Gemini. Omitiendo el ranking de eventos.")
        return []

    print("Contactando a la IA de Gemini con prompt optimizado para audiencia México/USA...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        lineas = texto_crudo.strip().split('\n')
        PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las", " por "]
        eventos_para_analizar = []
        for linea in lineas:
            linea_limpia = linea.strip()
            if any(keyword in linea_limpia for keyword in PALABRAS_CLAVE_HORARIOS):
                try:
                    descripcion = re.split(r'\s+a las\s+|\s+a partir de las\s+', linea_limpia, 1, re.IGNORECASE)[0]
                    descripcion = descripcion.split(" por ")[0]
                    eventos_para_analizar.append(descripcion.strip())
                except:
                    continue
            elif "Pelea Estelar" in linea_limpia:
                 eventos_para_analizar.append(linea_limpia)

        lista_texto_plano = "\n".join(set(eventos_para_analizar))

        prompt = f"""
        Actúa como un analista experto en tendencias de entretenimiento para una audiencia de México y Estados Unidos (USA).
        Tu tarea es analizar la siguiente lista de eventos y determinar los 3 más relevantes para esta audiencia específica.
        Para determinar la relevancia, prioriza de la siguiente manera:
        1.  **Alto Interés Regional:** Da máxima prioridad a eventos de la Liga MX, NFL, MLB, NBA y peleas de boxeo importantes.
        2.  **Relevancia Cultural General:** Considera conciertos, estrenos de TV o eventos de cultura pop muy esperados.
        3.  **Popularidad en Búsquedas y Redes Sociales:** Evalúa qué eventos están generando más conversación.
        La salida debe ser exclusivamente el texto de la descripción de los 3 eventos, cada uno en una línea nueva, en orden del más al menos relevante.
        Asegúrate de que la descripción que devuelves coincida EXACTAMENTE con una de las líneas que te proporcioné.
        NO incluyas números, viñetas, comillas, explicaciones, o cualquier texto introductorio.

        LISTA DE EVENTOS PARA ANALIZAR:
        {lista_texto_plano}
        """

        response = model.generate_content(prompt, request_options={'timeout': 120})
        ranking_limpio = [re.sub(r'^[*-]?\s*', '', linea).strip() for linea in response.text.strip().split('\n') if linea.strip()]
        
        print(f"Ranking de Gemini (optimizado) recibido: {ranking_limpio}")
        return ranking_limpio

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return []

# --- 5. FUNCIÓN JSON (CON LÓGICA DE SEPARACIÓN DE BLOQUES CORREGIDA) ---
def crear_json_eventos(texto_crudo, ranking_relevancia):
    
    REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)

    # --- FUNCIÓN INTERNA PARA IDENTIFICAR TÍTULOS ---
    def es_linea_de_titulo(linea):
        if "WWE Wrestling" in linea or "Evento BOX" in linea:
            return True
        if REGEX_EMOJI.search(linea):
            if not any(keyword in linea.lower() for keyword in ["vs", "va", " a las ", " pm ", " am ", "p.m."]):
                return True
        return False

    def parsear_linea_partido(linea_partido):
        partido = {"descripcion": "", "horarios": "", "canales": [], "competidores": []}
        linea_limpia = linea_partido.strip()
        
        descripcion_y_horarios = linea_limpia
        if " por " in linea_limpia:
            partes = linea_limpia.split(" por ", 1)
            descripcion_y_horarios = partes[0]
            canales_texto = partes[1].replace(" y ", ", ")
            partido["canales"] = [c.strip() for c in canales_texto.split(',')]

        frases_split = r'\s+a las\s+|\s+a partir de las\s+'
        if re.search(frases_split, descripcion_y_horarios, re.IGNORECASE):
            partes = re.split(frases_split, descripcion_y_horarios, 1, re.IGNORECASE)
            partido["descripcion"], partido["horarios"] = partes[0].strip(), partes[1].strip()
        else:
            match_horario = re.search(r'\d', descripcion_y_horarios)
            if match_horario:
                pos_inicio = match_horario.start()
                partido["descripcion"] = descripcion_y_horarios[:pos_inicio].strip()
                partido["horarios"] = descripcion_y_horarios[pos_inicio:].strip()
            else:
                partido["descripcion"] = descripcion_y_horarios

        if " vs " in partido["descripcion"]:
            partido["competidores"] = [c.strip() for c in partido["descripcion"].split(" vs ")]
        elif " va " in partido["descripcion"]:
            partido["competidores"] = [c.strip() for c in partido["descripcion"].split(" va ")]
            
        return partido

    datos_json = {"fecha_actualizacion": datetime.now().isoformat(), "titulo_guia": "", "eventos": []}
    lineas = [l.strip() for l in texto_crudo.strip().split('\n') if l.strip()]
    
    bloques_evento = []
    bloque_actual = []
    for linea in lineas:
        if "Eventos Deportivos" in linea:
            fecha_texto = linea.replace("Eventos Deportivos ", "").strip()
            year_actual = datetime.now().year
            titulo_completo_html = f"Eventos Deportivos y Especiales, {year_actual} <br /> {fecha_texto}"
            datos_json["titulo_guia"] = titulo_completo_html
            continue
        if "Kaelus Soporte" in linea or "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳" in linea:
            continue
        
        if es_linea_de_titulo(linea) and bloque_actual:
            bloques_evento.append(bloque_actual)
            bloque_actual = [linea]
        else:
            bloque_actual.append(linea)
    if bloque_actual: bloques_evento.append(bloque_actual)

    lista_eventos_original = []
    for bloque in bloques_evento:
        if not bloque: continue
        evento_principal = bloque[0]
        evento_json = {"evento_principal": evento_principal, "detalle_evento": "", "partidos": []}
        contenido = bloque[1:]
        
        detalles_previos = []
        for linea in contenido:
            if any(keyword in linea for keyword in ["Este", "Centro", "Pacífico", "partir de las"]):
                partido_info = parsear_linea_partido(linea)
                partido_info["detalle_partido"] = " ".join(detalles_previos).strip()
                if not partido_info["descripcion"] and detalles_previos:
                    partido_info["descripcion"] = detalles_previos[-1]
                partido_info["organizador"] = evento_principal
                evento_json["partidos"].append(partido_info)
                detalles_previos = []
            else:
                detalles_previos.append(linea)
        
        if detalles_previos:
            partido_info = parsear_linea_partido(detalles_previos[-1])
            partido_info["detalle_partido"] = " ".join(detalles_previos[:-1]).strip()
            partido_info["organizador"] = evento_principal
            evento_json["partidos"].append(partido_info)
        
        if evento_json["partidos"]:
            lista_eventos_original.append(evento_json)

    # El JSON solo contendrá la lista de eventos originales (sin ranking_relevancia)
    datos_json["eventos"] = lista_eventos_original
    return json.dumps(datos_json, indent=4, ensure_ascii=False)

# --- 6. FUNCIÓN PARA GENERAR EL SITEMAP ---
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

# --- 7. FUNCIÓN PRINCIPAL ---
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

    # El ranking es una lista vacía
    ranking = obtener_ranking_eventos(texto_extraido_filtrado)

    print("2. Generando contenido para los 3 archivos...")
    contenido_json = crear_json_eventos(texto_extraido_filtrado, ranking)
    # Se elimina contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    contenido_mensaje_whatsapp = crear_mensaje_whatsapp(texto_extraido_filtrado)
    crear_sitemap()
    print("Contenido generado.")

    print("3. Guardando archivos locales...")
    archivos_a_subir = []
    try:
        with open(NOMBRE_ARCHIVO_JSON, 'w', encoding='utf-8') as f: f.write(contenido_json)
        archivos_a_subir.append(NOMBRE_ARCHIVO_JSON)

        # Se elimina la subida de programacion.html
        
        with open(NOMBRE_ARCHIVO_MENSAJE, 'w', encoding='utf-8') as f: f.write(contenido_mensaje_whatsapp)
        archivos_a_subir.append(NOMBRE_ARCHIVO_MENSAJE)

        archivos_a_subir.append(NOMBRE_ARCHIVO_SITEMAP)
        
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
            for nombre_archivo in archivos_a_subir:
                with open(nombre_archivo, 'rb') as file:
                    print(f"Subiendo '{nombre_archivo}'...")
                    ftp.storbinary(f'STOR {nombre_archivo}', file)
            print("¡Subida de todos los archivos completada exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")
