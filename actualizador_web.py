import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP
from datetime import datetime
import json
import google.generativeai as genai # <-- Nueva importación

# --- 1. CONFIGURACIÓN ---
URL_FUENTE = os.getenv('URL_FUENTE')
FTP_HOST = os.getenv('FTP_HOST')
# ... (el resto de la configuración se mantiene igual)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') # <-- Nueva variable

# --- (Las funciones aplicar_reglas_html y crear_mensaje_whatsapp no cambian) ---
def aplicar_reglas_html(texto_crudo):
    # ... (código sin cambios)
def crear_mensaje_whatsapp(texto_crudo):
    # ... (código sin cambios)

# --- ¡NUEVA FUNCIÓN! PARA COMUNICARSE CON GEMINI ---
def obtener_ranking_eventos(texto_crudo):
    """
    Toma el texto crudo, extrae los títulos de los eventos,
    y le pide a Gemini que los clasifique por relevancia.
    """
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: No se encontró la API Key de Gemini. Omitiendo el ranking de eventos.")
        return []

    print("Contactando a la IA de Gemini para obtener el ranking de relevancia...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Extraemos solo los títulos para enviar a la IA, para ser más eficientes
        lineas = texto_crudo.strip().split('\n')
        REGEX_EMOJI = re.compile(r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
        titulos_eventos = []
        for linea in lineas:
            linea = linea.strip()
            if "WWE Wrestling" in linea or REGEX_EMOJI.search(linea) or "Evento BOX" in linea:
                 if "⚽️🏈🏀⚾️🏐🎾🥊🏒⛳️🎳" not in linea: # Excluimos la barra separadora
                    titulos_eventos.append(linea)
        
        lista_texto_plano = "\n".join(titulos_eventos)

        prompt = f"""
        Actúa como un analista experto en tendencias deportivas. A continuación, te proporciono una lista de títulos de eventos deportivos para el día de hoy.
        Basándote en la relevancia global, popularidad en búsquedas web y चर्चा en redes sociales, identifica los 3 eventos más importantes o relevantes de esta lista.

        Devuelve ÚNICAMENTE los nombres de los 3 eventos que identificaste, en orden del más relevante al menos relevante. Cada nombre de evento debe estar en una nueva línea. No añadas introducciones, explicaciones, ni numeración.

        LISTA DE EVENTOS:
        {lista_texto_plano}
        """

        response = model.generate_content(prompt)
        # Limpiamos la respuesta para obtener una lista limpia
        ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        
        print(f"Ranking de Gemini recibido: {ranking_limpio}")
        return ranking_limpio

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return []

# --- FUNCIÓN JSON (ACTUALIZADA PARA REORDENAR) ---
def crear_json_eventos(texto_crudo, ranking_relevancia):
    """
    Genera el archivo JSON, reordenando los eventos para poner
    los más relevantes al principio.
    """
    # (La primera parte de la función es igual, extrayendo todos los eventos)
    datos_json = {"fecha_actualizacion": datetime.now().isoformat(), "titulo_guia": "", "eventos": []}
    lineas = [l.strip() for l in texto_crudo.strip().split('\n') if l.strip()]
    # ... (el resto del código de parsing de bloques y partidos se mantiene igual)

    # --- NUEVA LÓGICA DE REORDENAMIENTO ---
    print("Reordenando eventos según el ranking de relevancia...")
    
    eventos_relevantes_ordenados = []
    eventos_restantes = []

    # 1. Separamos los eventos en dos grupos: relevantes y el resto
    for evento_obj in datos_json["eventos"]:
        if evento_obj["evento_principal"] in ranking_relevancia:
            eventos_relevantes_ordenados.append(evento_obj)
        else:
            eventos_restantes.append(evento_obj)
            
    # 2. Ordenamos la lista de relevantes para que coincida con el orden de Gemini
    # Usamos un diccionario para mapear el nombre al objeto para una búsqueda rápida
    mapa_relevantes = {evento["evento_principal"]: evento for evento in eventos_relevantes_ordenados}
    eventos_relevantes_final = [mapa_relevantes[nombre] for nombre in ranking_relevancia if nombre in mapa_relevantes]

    # 3. Unimos las listas: los relevantes ordenados primero, seguidos por el resto
    datos_json["eventos"] = eventos_relevantes_final + eventos_restantes
    
    print("Eventos reordenados exitosamente.")
    return json.dumps(datos_json, indent=4, ensure_ascii=False)

# --- (La función crear_sitemap no cambia) ---
def crear_sitemap():
    # ... (código sin cambios)

# --- FUNCIÓN PRINCIPAL (ACTUALIZADA) ---
def main():
    print("Iniciando proceso de actualización de todos los archivos...")
    # ... (La extracción de datos inicial se mantiene igual)

    # --- NUEVO PASO: LLAMAR A GEMINI ---
    ranking = obtener_ranking_eventos(texto_extraido_filtrado)

    print("2. Generando contenido para los 4 archivos...")
    # Pasamos el ranking a la función que crea el JSON
    contenido_json = crear_json_eventos(texto_extraido_filtrado, ranking)
    contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    contenido_mensaje_whatsapp = crear_mensaje_whatsapp(texto_extraido_filtrado)
    crear_sitemap()
    print("Contenido generado.")

    # ... (El resto de la función para guardar y subir archivos se mantiene igual)
