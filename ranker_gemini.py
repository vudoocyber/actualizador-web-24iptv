import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import pytz
import re
from google import genai
from google.genai import types
import copy  # Necesario para crear copias independientes de los objetos

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA_LEGACY = "eventos-relevantes.json"    # Top 3 con emojis
NOMBRE_ARCHIVO_SALIDA_ROKU = "eventos-destacados-roku.json" # Top 6 limpio
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MEXICO_TZ = pytz.timezone('America/Mexico_City')

# --- FUNCIÓN DE LIMPIEZA PARA ROKU ---
def limpiar_texto_roku(texto):
    if not texto:
        return ""
    # 1. Regex para eliminar emojis (Rangos Unicode comunes de emojis y símbolos gráficos)
    emoji_pattern = re.compile(
        r'[\U0001F000-\U0001F9FF]'  # Rangos principales de emojis
        r'|[\U00002600-\U000027BF]' # Símbolos misceláneos (sol, nubes, aviones, etc.)
        r'|[\U0001F300-\U0001F5FF]' # Símbolos y pictogramas diversos
        r'|[\U0001F680-\U0001F6FF]' # Transportes y mapas
        r'|[\U0001F1E0-\U0001F1FF]' # Banderas
        r'|[\u2700-\u27BF]',         # Dingbats
        flags=re.UNICODE
    )
    # Reemplazar emojis por vacío
    texto_limpio = emoji_pattern.sub('', texto)
    # 2. Limpieza adicional de espacios dobles que puedan quedar
    return re.sub(r'\s+', ' ', texto_limpio).strip()

# --- 2. FUNCIÓN PARA LLAMAR A GEMINI ---
def obtener_ranking_eventos(lista_eventos):
    if not GEMINI_API_KEY:
        print("ERROR: No se encontró la API Key de Gemini. No se puede continuar.")
        return None

    print("Contactando a la IA de Gemini para obtener top 10 (para filtrar 6)...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        cst_offset = timezone(timedelta(hours=-6))
        hora_actual_cst = datetime.now(cst_offset)
        hora_formateada_cst = hora_actual_cst.strftime('%A, %d de %B de %Y - %I:%M %p CST')
        
        eventos_para_analizar = []
        for evento in lista_eventos:
            for partido in evento.get("partidos", []):
                eventos_para_analizar.append(f"{partido.get('descripcion', '')} {partido.get('horarios', '')}".strip())
        
        lista_texto_plano = "\n".join(filter(None, set(eventos_para_analizar)))
        if not lista_texto_plano:
            print("No se encontraron eventos para analizar.")
            return []

        # SOLICITAMOS 10 EVENTOS PARA ASEGURAR QUE TRAS FILTROS QUEDEN AL MENOS 6
        prompt = f"""
        Actúa como un curador de contenido experto y analista de tendencias EN TIEMPO REAL para una audiencia de México y Estados Unidos (USA).
        La fecha y hora actual en el Centro de México es: {hora_formateada_cst}.
        Tu tarea es analizar la siguiente lista de eventos y determinar los 10 más relevantes para esta audiencia.

        Reglas de Ranking:
        1.  **REGLA DE TIEMPO:** Ignora eventos que ya hayan finalizado.
        2.  **REGLA DE INTERÉS:** Prioriza eventos de alto interés como Liga MX, NFL, MLB, NBA, Boxeo/UFC y partidos de equipos populares (América, Chivas, Real Madrid, Barcelona, Cowboys, Lakers, Yankees, etc.).

        Formato de Salida:
        - Devuelve ÚNICAMENTE la descripción exacta de los 10 eventos que seleccionaste, en orden del más al menos relevante.
        - Cada descripción debe estar en una nueva línea.
        - NO incluyas números, viñetas, comillas, explicaciones o texto introductorio.

        LISTA DE EVENTOS PARA ANALIZAR:
        {lista_texto_plano}
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2 
            )
        )
        
        if response.text:
            ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
            print(f"Ranking de Gemini (Top 10 crudo) recibido: {ranking_limpio}")
            return ranking_limpio
        else:
            print("Gemini devolvió una respuesta vacía.")
            return []

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return None

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    print(f"Iniciando proceso de ranking de eventos...")
    
    fecha_actualizacion_iso = datetime.now(MEXICO_TZ).isoformat()
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        respuesta = requests.get(URL_JSON_FUENTE, headers=headers, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        fecha_guia_str = datos.get("fecha_guia")
        if not fecha_guia_str:
            print("ERROR: No se encontró la etiqueta 'fecha_guia' en events.json. Proceso detenido.")
            return

        hoy_mexico_str = datetime.now(MEXICO_TZ).strftime('%Y-%m-%d')
        if fecha_guia_str != hoy_mexico_str:
            print(f"ADVERTENCIA: La fecha de la guía ({fecha_guia_str}) no coincide con la fecha de hoy ({hoy_mexico_str}).")
            print("El ranking de eventos no se actualizará para evitar mostrar datos incorrectos.")
            return
        
        print(f"Fecha de la guía ({fecha_guia_str}) confirmada. Continuando con el ranking.")
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original:
            raise ValueError("El archivo events.json está vacío.")
        
    except Exception as e:
        print(f"ERROR FATAL al leer o validar el archivo JSON: {e}")
        return

    ranking_crudo = obtener_ranking_eventos(lista_eventos_original)

    # Lista maestra de 6 eventos
    eventos_relevantes_maestra = []

    if ranking_crudo is None:
        print("Fallo en la API de Gemini. Se generará una lista vacía.")
    else:
        print("2. Aplicando filtro de exclusión por código y construyendo Top 6...")
        palabras_prohibidas = ["Femenil", "WNBA", "NWSL", "Femenino"]
        
        eventos_rankeados_completos = []
        descripciones_rankeadas_unicas = set()

        for desc_relevante in ranking_crudo:
            encontrado = False
            for evento in lista_eventos_original:
                for partido in evento.get("partidos", []):
                    descripcion_corta = partido.get("descripcion", "")
                    if descripcion_corta and (descripcion_corta in desc_relevante or desc_relevante in descripcion_corta) and descripcion_corta not in descripciones_rankeadas_unicas:
                        eventos_rankeados_completos.append((evento, partido))
                        descripciones_rankeadas_unicas.add(descripcion_corta)
                        encontrado = True
                        break
                if encontrado:
                    break
        
        for evento, partido in eventos_rankeados_completos:
            # AHORA BUSCAMOS 6 EVENTOS
            if len(eventos_relevantes_maestra) >= 6:
                break
            
            evento_principal = evento.get("evento_principal", "")
            if not any(keyword in evento_principal for keyword in palabras_prohibidas):
                evento_relevante = {
                    "evento_principal": evento_principal,
                    "detalle_evento": evento.get("detalle_evento", ""),
                    "partidos": [partido]
                }
                eventos_relevantes_maestra.append(evento_relevante)
        
        print(f"Ranking Maestro (Top 6) obtenido: {[ev['partidos'][0]['descripcion'] for ev in eventos_relevantes_maestra]}")

    # --- 3. GENERACIÓN DE ARCHIVOS ---

    # A. Archivo Legacy (Top 3, con Emojis)
    eventos_legacy = eventos_relevantes_maestra[:3]
    json_legacy = {
        "fecha_actualizacion": fecha_actualizacion_iso,
        "fecha_guia": fecha_guia_str,
        "eventos_relevantes": eventos_legacy
    }

    # B. Archivo Roku (Top 6, SIN Emojis)
    # Usamos deepcopy para no modificar la lista original si fuera necesario, 
    # aunque aquí reconstruiremos diccionarios nuevos para estar seguros.
    eventos_roku_limpios = []
    
    for evento in eventos_relevantes_maestra:
        # Creamos una copia limpia de la estructura
        partido_orig = evento["partidos"][0]
        
        # Limpiamos cada campo de texto
        evt_principal_clean = limpiar_texto_roku(evento["evento_principal"])
        det_evento_clean = limpiar_texto_roku(evento["detalle_evento"])
        
        partido_clean = {
            "detalle_partido": limpiar_texto_roku(partido_orig.get("detalle_partido", "")),
            "descripcion": limpiar_texto_roku(partido_orig.get("descripcion", "")),
            "horarios": limpiar_texto_roku(partido_orig.get("horarios", "")),
            "canales": [limpiar_texto_roku(c) for c in partido_orig.get("canales", [])],
            "competidores": [limpiar_texto_roku(c) for c in partido_orig.get("competidores", [])]
        }
        
        evento_nuevo = {
            "evento_principal": evt_principal_clean,
            "detalle_evento": det_evento_clean,
            "partidos": [partido_clean]
        }
        eventos_roku_limpios.append(evento_nuevo)

    json_roku = {
        "fecha_actualizacion": fecha_actualizacion_iso,
        "fecha_guia": fecha_guia_str,
        "eventos_relevantes": eventos_roku_limpios
    }

    # --- 4. GUARDADO Y SUBIDA ---
    
    # Guardar Localmente
    print(f"Guardando {NOMBRE_ARCHIVO_SALIDA_LEGACY} (Top 3)...")
    with open(NOMBRE_ARCHIVO_SALIDA_LEGACY, 'w', encoding='utf-8') as f:
        json.dump(json_legacy, f, indent=4, ensure_ascii=False)

    print(f"Guardando {NOMBRE_ARCHIVO_SALIDA_ROKU} (Top 6 Limpio)...")
    with open(NOMBRE_ARCHIVO_SALIDA_ROKU, 'w', encoding='utf-8') as f:
        json.dump(json_roku, f, indent=4, ensure_ascii=False)

    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return
    
    print("5. Subiendo archivos al servidor FTP...")
    archivos_a_subir = [NOMBRE_ARCHIVO_SALIDA_LEGACY, NOMBRE_ARCHIVO_SALIDA_ROKU]
    
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            
            for archivo in archivos_a_subir:
                with open(archivo, 'rb') as file:
                    print(f"Subiendo '{archivo}'...")
                    ftp.storbinary(f'STOR {archivo}', file)
            
            print("¡Todos los archivos han sido subidos exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso de ranking finalizado ---")
