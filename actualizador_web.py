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

# --- (Las funciones aplicar_reglas_html y crear_mensaje_whatsapp no cambian) ---
def aplicar_reglas_html(texto_crudo):
    # ... (código sin cambios)
def crear_mensaje_whatsapp(texto_crudo):
    # ... (código sin cambios)

# --- FUNCIÓN DE IA ACTUALIZADA ---
def obtener_ranking_eventos(texto_crudo):
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: No se encontró la API Key de Gemini. Omitiendo el ranking de eventos.")
        return []
    print("Contactando a la IA de Gemini para obtener el ranking de relevancia...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Extraemos una lista limpia de partidos para enviar a la IA
        lineas = texto_crudo.strip().split('\n')
        PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las"]
        partidos_para_analizar = []
        for linea in lineas:
            linea_limpia = linea.strip()
            if any(keyword in linea_limpia for keyword in PALABRAS_CLAVE_HORARIOS):
                # Extraemos solo la parte de la descripción del partido
                try:
                    descripcion = re.split(r'\s+a las\s+|\s+a partir de las\s+', linea_limpia, 1, re.IGNORECASE)[0]
                    partidos_para_analizar.append(descripcion.strip())
                except:
                    partidos_para_analizar.append(linea_limpia)

        lista_texto_plano = "\n".join(partidos_para_analizar)

        prompt = f"""
        Actúa como un analista experto en tendencias deportivas globales. A continuación te doy una lista de partidos, peleas y eventos deportivos del día.
        Basándote en la relevancia global, popularidad en búsquedas web y चर्चा en redes sociales, identifica los 3 eventos más importantes.

        Devuelve ÚNICAMENTE la descripción exacta de los 3 eventos que identificaste, en orden del más relevante al menos relevante. Por ejemplo: 'Bills vs Giants' o 'Pelea Estelar Dolidze vs Hernandez'.
        Cada descripción debe estar en una nueva línea. No añadas introducciones, explicaciones, numeración, ni ningún otro texto.

        LISTA DE EVENTOS:
        {lista_texto_plano}
        """

        response = model.generate_content(prompt, request_options={'timeout': 120})
        ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        
        print(f"Ranking de Gemini recibido: {ranking_limpio}")
        return ranking_limpio

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return []

# --- FUNCIÓN JSON REFACTORIZADA Y CORREGIDA ---
def crear_json_eventos(texto_crudo, ranking_relevancia):
    
    # --- Sub-función para parsear una línea de partido ---
    def parsear_linea_partido(linea_partido):
        partido = {"descripcion": "", "horarios": "", "canales": [], "competidores": []}
        
        linea_limpia = linea_partido.strip()
        
        # Dividir por canales
        descripcion_y_horarios = linea_limpia
        if " por " in linea_limpia:
            partes = linea_limpia.split(" por ", 1)
            descripcion_y_horarios = partes[0]
            canales_texto = partes[1].replace(" y ", ", ")
            partido["canales"] = [c.strip() for c in canales_texto.split(',')]

        # Dividir descripción y horarios
        frases_split = r'\s+a las\s+|\s+a partir de las\s+'
        if re.search(frases_split, descripcion_y_horarios, re.IGNORECASE):
            partes = re.split(frases_split, descripcion_y_horarios, 1, re.IGNORECASE)
            partido["descripcion"], partido["horarios"] = partes[0].strip(), partes[1].strip()
        else:
            # Si no hay "a las", buscamos el primer número para separar
            match_horario = re.search(r'\d', descripcion_y_horarios)
            if match_horario:
                pos_inicio = match_horario.start()
                partido["descripcion"] = descripcion_y_horarios[:pos_inicio].strip()
                partido["horarios"] = descripcion_y_horarios[pos_inicio:].strip()
            else:
                partido["descripcion"] = descripcion_y_horarios

        # Extraer competidores
        if " vs " in partido["descripcion"]:
            partido["competidores"] = [c.strip() for c in partido["descripcion"].split(" vs ")]
        elif " va " in partido["descripcion"]: # Caso especial como "Cardinals va Chiefs"
            partido["competidores"] = [c.strip() for c in partido["descripcion"].split(" va ")]
            
        return partido

    # --- Lógica principal de crear_json_eventos ---
    datos_json = {"fecha_actualizacion": datetime.now().isoformat(), "titulo_guia": "", "eventos": []}
    lineas = [l.strip() for l in texto_crudo.strip().split('\n') if l.strip()]
    
    REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    
    # --- 1. Agrupación de eventos (lógica mejorada) ---
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
        
        # Una línea es un título si tiene emoji Y NO parece un horario
        es_titulo = (REGEX_EMOJI.search(linea) or "Evento BOX" in linea) and " a las " not in linea and " pm " not in linea and " am " not in linea
        
        if es_titulo and bloque_actual:
            bloques_evento.append(bloque_actual)
            bloque_actual = [linea]
        else:
            bloque_actual.append(linea)
    if bloque_actual: bloques_evento.append(bloque_actual)

    # --- 2. Procesamiento de cada bloque para crear la lista original ---
    lista_eventos_original = []
    for bloque in bloques_evento:
        if not bloque: continue
        evento_principal = bloque[0]
        evento_json = {"evento_principal": evento_principal, "detalle_evento": "", "partidos": []}
        contenido = bloque[1:]
        
        partido_actual = {}
        detalles_previos = []
        for linea in contenido:
            if any(keyword in linea for keyword in ["Este", "Centro", "Pacífico", "partir de las"]):
                # Es una línea de horario, procesamos el partido
                partido_info = parsear_linea_partido(linea)
                partido_info["detalle_partido"] = " ".join(detalles_previos).strip()
                # Si la descripción principal estaba vacía, la llenamos
                if not partido_info["descripcion"] and detalles_previos:
                    partido_info["descripcion"] = detalles_previos[-1]
                
                partido_info["organizador"] = evento_principal
                evento_json["partidos"].append(partido_info)
                detalles_previos = []
            else:
                # Es una línea de detalle (nombre de estadio, jornada, etc.)
                detalles_previos.append(linea)
        
        # Si quedó algún detalle sin partido (ej. "Pelea Estelar...")
        if detalles_previos:
             # Creamos un "partido" sin horarios/canales para este detalle
            partido_info = parsear_linea_partido(detalles_previos[-1])
            partido_info["detalle_partido"] = " ".join(detalles_previos[:-1]).strip()
            partido_info["organizador"] = evento_principal
            evento_json["partidos"].append(partido_info)
        
        if evento_json["partidos"]:
            lista_eventos_original.append(evento_json)

    # --- 3. Creación de las tarjetas especiales de eventos relevantes ---
    eventos_relevantes_especiales = []
    if ranking_relevancia:
        print("Creando tarjetas especiales para eventos relevantes...")
        for desc_relevante in ranking_relevancia:
            # Buscamos el partido relevante en toda la estructura original
            for evento in lista_eventos_original:
                for partido in evento["partidos"]:
                    if desc_relevante in partido["descripcion"]:
                        # Encontramos el partido, ahora creamos la tarjeta especial
                        tarjeta_especial = {
                            "evento_principal": evento["evento_principal"],
                            # Nuevo campo para identificar esta tarjeta
                            "partido_relevante": {
                                "descripcion": partido["descripcion"],
                                "detalle_partido": partido["detalle_partido"],
                                "horarios": partido["horarios"],
                                "canales": partido["canales"],
                                "competidores": partido["competidores"],
                                "organizador": evento["evento_principal"]
                            }
                        }
                        eventos_relevantes_especiales.append(tarjeta_especial)
                        break # Pasamos al siguiente de la lista de ranking
                else:
                    continue
                break
    
    # --- 4. Ensamblaje final del JSON ---
    datos_json["eventos"] = eventos_relevantes_especiales + lista_eventos_original
    return json.dumps(datos_json, indent=4, ensure_ascii=False)


# --- (Las funciones crear_sitemap y main no cambian en su estructura principal) ---
# ... (El resto del código se mantiene igual, solo asegúrate de que `main` llame a 
# `crear_json_eventos` con los dos argumentos: texto y ranking)

# --- FUNCIÓN PRINCIPAL COMPLETA ---
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

    ranking = obtener_ranking_eventos(texto_extraido_filtrado)

    print("2. Generando contenido para los 4 archivos...")
    contenido_json = crear_json_eventos(texto_extraido_filtrado, ranking)
    contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    contenido_mensaje_whatsapp = crear_mensaje_whatsapp(texto_extraido_filtrado)
    crear_sitemap()
    print("Contenido generado.")

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
