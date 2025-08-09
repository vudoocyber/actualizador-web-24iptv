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
NOMBRE_ARCHIVO_PROGRAMACION = os.getenv('NOMBRE_ARCHIVO_PROGRAMACION', 'programacion.html')
NOMBRE_ARCHIVO_MENSAJE = os.getenv('NOMBRE_ARCHIVO_MENSAJE', 'mensaje_whatsapp.html')
NOMBRE_ARCHIVO_SITEMAP = 'sitemap.xml'
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
    
    mensaje_texto_plano = f"""🎯 ¡Guía de Eventos Deportivos y Especiales para día de Hoy! 🏆🔥

Consulta los horarios y canales de transmisión aquí:

👉 https://24hometv.xyz/#horarios


📅 *{fecha_formateada}*

{lista_de_titulos}

📱 ¿Listo para no perderte ni un segundo de acción?

Dale clic al enlace y entérate de todo en segundos 👇

👉 https://24hometv.xyz/#horarios

⭐ 24IPTV & HomeTV – Tu Mejor Elección en Entretenimiento Deportivo ⭐"""
    
    mensaje_html_final = f"""<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <title>Mensaje para WhatsApp</title>\n</head>\n<body>\n    <pre>{mensaje_texto_plano}</pre>\n</body>\n</html>"""
    return mensaje_html_final

# --- 4. NUEVA FUNCIÓN PARA COMUNICARSE CON GEMINI ---
def obtener_ranking_eventos(texto_crudo):
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: No se encontró la API Key de Gemini. Omitiendo el ranking de eventos.")
        return []

    print("Contactando a la IA de Gemini para obtener el ranking de relevancia...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')

        lineas = texto_crudo.strip().split('\n')
        REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
        titulos_eventos = []
        for linea in lineas:
            linea = linea.strip()
            if "WWE Wrestling" in linea or REGEX_EMOJI.search(linea) or "Evento BOX" in linea:
                 if "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳" not in linea:
                    titulos_eventos.append(linea)
        
        lista_texto_plano = "\n".join(titulos_eventos)

        prompt = f"""
        Actúa como un analista experto en tendencias deportivas. A continuación, te proporciono una lista de títulos de eventos deportivos para el día de hoy.
        Basándote en la relevancia global, popularidad en búsquedas web y चर्चा en redes sociales, identifica los 3 eventos más importantes o relevantes de esta lista.

        Devuelve ÚNICAMENTE los nombres exactos de los 3 eventos que identificaste, en orden del más relevante al menos relevante. Cada nombre de evento debe estar en una nueva línea. No añadas introducciones, explicaciones, numeración, ni asteriscos.

        LISTA DE EVENTOS:
        {lista_texto_plano}
        """

        response = model.generate_content(prompt)
        ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        
        print(f"Ranking de Gemini recibido: {ranking_limpio}")
        return ranking_limpio

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return []

# --- 5. FUNCIÓN JSON (ACTUALIZADA PARA REORDENAR) ---
def crear_json_eventos(texto_crudo, ranking_relevancia):
    # (La primera parte de la función parsea todos los eventos como siempre)
    datos_json = {"fecha_actualizacion": datetime.now().isoformat(), "titulo_guia": "", "eventos": []}
    lineas = [l.strip() for l in texto_crudo.strip().split('\n') if l.strip()]
    REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las"]
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
        if ("WWE Wrestling" in linea or REGEX_EMOJI.search(linea) or "Evento BOX" in linea) and bloque_actual:
            bloques_evento.append(bloque_actual)
            bloque_actual = [linea]
        else:
            bloque_actual.append(linea)
    if bloque_actual: bloques_evento.append(bloque_actual)

    for bloque in bloques_evento:
        if not bloque: continue
        evento_principal = bloque[0]
        evento_json = {"evento_principal": evento_principal, "detalle_evento": "", "partidos": []}
        contenido = bloque[1:]
        grupos_partido = []
        grupo_actual = []
        for linea in contenido:
            grupo_actual.append(linea)
            if any(keyword in linea for keyword in PALABRAS_CLAVE_HORARIOS):
                grupos_partido.append(grupo_actual)
                grupo_actual = []
        if grupo_actual: evento_json["detalle_evento"] = " ".join(grupo_actual).strip()
        for grupo in grupos_partido:
            linea_horario = grupo.pop()
            detalles_previos = grupo
            partido = {"detalle_partido": " ".join(detalles_previos).strip(), "descripcion": "", "horarios": "", "canales": [], "competidores": [], "organizador": evento_principal}
            frases_split = r'\s+a las\s+|\s+a partir de las\s+'
            descripcion_raw = linea_horario
            horarios_raw = ""
            if re.search(frases_split, linea_horario, re.IGNORECASE):
                partes = re.split(frases_split, linea_horario, 1, re.IGNORECASE)
                descripcion_raw, horarios_raw = partes[0], partes[1]
            elif re.search(r'\d.*(am|pm|AM|PM)', linea_horario):
                match_horario = re.search(r'\d.*(am|pm|AM|PM)', linea_horario)
                if match_horario:
                    pos_inicio = match_horario.start()
                    descripcion_raw = linea_horario[:pos_inicio].strip()
                    horarios_raw = linea_horario[pos_inicio:]
            partido["descripcion"] = descripcion_raw.strip()
            if " vs " in partido["descripcion"]:
                partido["competidores"] = [c.strip() for c in partido["descripcion"].split(" vs ")]
            if " por " in horarios_raw:
                horarios, canales_texto = horarios_raw.split(" por ", 1)
                partido["horarios"] = horarios.strip()
                canales_texto = canales_texto.replace(" y ", ", ")
                partido["canales"] = [c.strip() for c in canales_texto.split(',')]
            else:
                partido["horarios"] = horarios_raw.strip()
            evento_json["partidos"].append(partido)
        if evento_json["partidos"]: datos_json["eventos"].append(evento_json)
            
    # --- LÓGICA DE REORDENAMIENTO ---
    if ranking_relevancia:
        print("Reordenando eventos según el ranking de relevancia...")
        eventos_originales = datos_json["eventos"]
        eventos_relevantes_ordenados = []
        eventos_restantes = []
        
        mapa_original = {evento["evento_principal"]: evento for evento in eventos_originales}

        # Separamos los eventos en dos grupos
        for nombre_relevante in ranking_relevancia:
            if nombre_relevante in mapa_original:
                eventos_relevantes_ordenados.append(mapa_original[nombre_relevante])
        
        nombres_relevantes_set = set(ranking_relevancia)
        for evento in eventos_originales:
            if evento["evento_principal"] not in nombres_relevantes_set:
                eventos_restantes.append(evento)
        
        datos_json["eventos"] = eventos_relevantes_ordenados + eventos_restantes
        print("Eventos reordenados exitosamente.")
    else:
        print("No se recibió ranking, se mantiene el orden original.")

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

# --- 7. FUNCIÓN PRINCIPAL (ACTUALIZADA) ---
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

    # NUEVO PASO: OBTENER RANKING DE GEMINI
    ranking = obtener_ranking_eventos(texto_extraido_filtrado)

    print("2. Generando contenido para los 4 archivos...")
    # Pasamos el ranking a la función que crea el JSON
    contenido_json = crear_json_eventos(texto_extraido_filtrado, ranking)
    contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    contenido_mensaje_whatsapp = crear_mensaje_whatsapp(texto_extraido_filtrado)
    crear_sitemap()
    print("Contenido generado.")
    
    # El resto de la función para guardar y subir los archivos no cambia
    print("3. Guardando archivos locales...")
    try:
        with open(NOMBRE_ARCHIVO_JSON, 'w', encoding='utf-8') as f: f.write(contenido_json)
        with open(NOMBRE_ARCHIVO_PROGRAMACION, 'w', encoding='utf-8') as f: f.write(contenido_html_programacion)
        with open(NOMBRE_ARCHIVO_MENSAJE, 'w', encoding='utf-8') as f: f.write(contenido_mensaje_whatsapp)
        print(f"Archivos locales guardados: {NOMBRE_ARCHIVO_JSON}, {NOMBRE_ARCHIVO_PROGRAMACION}, {NOMBRE_ARCHIVO_MENSAJE}, {NOMBRE_ARCHIVO_SITEMAP}.")
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
            for nombre_archivo in [NOMBRE_ARCHIVO_JSON, NOMBRE_ARCHIVO_PROGRAMACION, NOMBRE_ARCHIVO_MENSAJE, NOMBRE_ARCHIVO_SITEMAP]:
                with open(nombre_archivo, 'rb') as file:
                    print(f"Subiendo '{nombre_archivo}'...")
                    ftp.storbinary(f'STOR {nombre_archivo}', file)
            print("¡Subida de todos los archivos completada exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")
