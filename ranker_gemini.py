import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import re
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "eventos-relevantes.json"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- 2. FUNCIÓN PARA LLAMAR A GEMINI (PROMPT SIMPLIFICADO) ---
def obtener_ranking_eventos(lista_eventos_filtrada):
    if not GEMINI_API_KEY:
        print("ERROR: No se encontró la API Key de Gemini. No se puede continuar.")
        return []

    print("Contactando a la IA de Gemini con lista pre-filtrada...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        cst_offset = timezone(timedelta(hours=-6))
        hora_actual_cst = datetime.now(cst_offset)
        hora_formateada_cst = hora_actual_cst.strftime('%A, %d de %B de %Y - %I:%M %p CST')
        
        # El prompt ahora recibe una lista que ya ha sido filtrada por nuestro código
        lista_texto_plano = "\n".join(filter(None, set(lista_eventos_filtrada)))

        if not lista_texto_plano:
            print("No se encontraron eventos válidos para analizar después del filtro.")
            return []

        # El prompt ya no necesita la regla de exclusión, la hacemos nosotros en el código.
        prompt = f"""
        Actúa como un curador de contenido experto y analista de tendencias EN TIEMPO REAL para una audiencia de México y Estados Unidos (USA).
        La fecha y hora actual en el Centro de México es: {hora_formateada_cst}.
        Tu tarea es analizar la siguiente lista de eventos y determinar los 3 más relevantes.

        Reglas de Ranking:
        1.  **REGLA DE TIEMPO:** Ignora eventos que ya hayan finalizado.
        2.  **REGLA DE INTERÉS:** Prioriza eventos de alto interés como Liga MX, NFL, MLB, NBA, Boxeo/UFC y partidos de equipos populares (América, Chivas, Real Madrid, Barcelona, Cowboys, Lakers, Yankees, etc.).

        Formato de Salida:
        - Devuelve ÚNICAMENTE la descripción exacta de los 3 eventos que seleccionaste, en orden del más al menos relevante.
        - Cada descripción debe estar en una nueva línea.
        - NO incluyas números, viñetas, comillas, explicaciones o texto introductorio.

        LISTA DE EVENTOS PARA ANALIZAR:
        {lista_texto_plano}
        """

        response = model.generate_content(prompt, request_options={'timeout': 120})
        ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        
        print(f"Ranking de Gemini (pre-filtrado) recibido: {ranking_limpio}")
        return ranking_limpio

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return []

# --- 3. FUNCIÓN PRINCIPAL (CON LÓGICA DE FILTRADO PRIMERO) ---
def main():
    print(f"Iniciando proceso de ranking de eventos...")
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original:
            raise ValueError("El archivo events.json está vacío.")
        print("Archivo events.json leído correctamente.")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    # --- INICIO DE LA NUEVA LÓGICA DE FILTRADO ---
    print("2. Filtrando eventos de ligas femeninas ANTES de enviar a la IA...")
    palabras_prohibidas = ["Femenil", "WNBA", "NWSL"]
    eventos_para_analizar = []
    
    for evento in lista_eventos_original:
        # Si ninguna palabra prohibida está en el título de la liga, procesamos sus partidos
        if not any(keyword in evento.get("evento_principal", "") for keyword in palabras_prohibidas):
            for partido in evento.get("partidos", []):
                linea_completa = f"{partido.get('descripcion', '')} {partido.get('horarios', '')}"
                eventos_para_analizar.append(linea_completa.strip())
    
    print(f"Se enviarán {len(eventos_para_analizar)} eventos a la IA para su análisis.")
    # --- FIN DE LA NUEVA LÓGICA DE FILTRADO ---

    ranking = obtener_ranking_eventos(eventos_para_analizar)

    if not ranking:
        print("No se recibió ranking de Gemini. El archivo de eventos relevantes se creará vacío.")
        json_salida = {"eventos_relevantes": []}
    else:
        print("3. Construyendo el JSON de eventos relevantes...")
        eventos_relevantes = []
        descripciones_ya_anadidas = set()
        for desc_relevante in ranking:
            encontrado = False
            for evento in lista_eventos_original:
                for partido in evento.get("partidos", []):
                    if desc_relevante in partido.get("descripcion", "") and partido.get("descripcion") not in descripciones_ya_anadidas:
                        evento_relevante = {
                            "evento_principal": evento["evento_principal"],
                            "detalle_evento": evento.get("detalle_evento", ""),
                            "partidos": [partido]
                        }
                        eventos_relevantes.append(evento_relevante)
                        descripciones_ya_anadidas.add(partido.get("descripcion"))
                        encontrado = True
                        break
                if encontrado:
                    break
        json_salida = {"eventos_relevantes": eventos_relevantes}

    print(f"4. Guardando archivo local '{NOMBRE_ARCHIVO_SALIDA}'...")
    with open(NOMBRE_ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(json_salida, f, indent=4, ensure_ascii=False)
    print("Archivo local guardado.")
    
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return
    
    print(f"5. Subiendo '{NOMBRE_ARCHIVO_SALIDA}' al servidor FTP...")
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_SALIDA, 'rb') as file:
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_SALIDA}', file)
            print("¡Archivo de eventos relevantes subido exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso de ranking finalizado ---")
