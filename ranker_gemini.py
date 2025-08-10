import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "eventos-relevantes.json"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- 2. FUNCIÓN PARA LLAMAR A GEMINI (PROMPT ACTUALIZADO) ---
def obtener_ranking_eventos(lista_eventos):
    if not GEMINI_API_KEY:
        print("ERROR: No se encontró la API Key de Gemini. No se puede continuar.")
        return []

    print("Contactando a la IA de Gemini con nueva regla de exclusión...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        cst_offset = timezone(timedelta(hours=-6))
        hora_actual_cst = datetime.now(cst_offset)
        hora_formateada_cst = hora_actual_cst.strftime('%A, %d de %B de %Y - %I:%M %p CST')
        print(f"Hora actual para el análisis: {hora_formateada_cst}")

        eventos_para_analizar = []
        for evento in lista_eventos:
            for partido in evento.get("partidos", []):
                linea_completa = f"{partido.get('descripcion', '')} {partido.get('horarios', '')}"
                eventos_para_analizar.append(linea_completa.strip())
        
        lista_texto_plano = "\n".join(filter(None, set(eventos_para_analizar)))

        if not lista_texto_plano:
            print("No se encontraron eventos para analizar.")
            return []

        # --- PROMPT MEJORADO CON REGLA DE EXCLUSIÓN ---
        prompt = f"""
        Actúa como un curador de contenido experto y analista de tendencias EN TIEMPO REAL para una audiencia de México y Estados Unidos (USA).

        La fecha y hora actual en el Centro de México es: {hora_formateada_cst}.

        Tu tarea es analizar la siguiente lista de eventos y determinar los 3 más relevantes para esta audiencia específica, siguiendo estas reglas en orden estricto:

        1.  **REGLA CRÍTICA DE TIEMPO:** Ignora por completo cualquier evento cuya hora de inicio ya haya pasado considerablemente. Prioriza eventos que están por iniciar o en curso.
        2.  **REGLA CRÍTICA DE EXCLUSIÓN:** Los partidos de ligas o torneos femeninos (ej. Liga MX Femenil, NWSL, Copa América Femenil, Tour de Francia Femenil) NO deben ser considerados para el top 3, a menos que se trate de un evento de magnitud excepcional como la final de una Copa del Mundo.
        3.  **Alto Interés Regional:** De los eventos restantes, da máxima prioridad a los de Liga MX, NFL, MLB, NBA y peleas de boxeo importantes.
        4.  **Relevancia Cultural General:** Considera también conciertos, estrenos de TV o eventos de cultura pop muy esperados.

        La salida debe ser exclusivamente el texto de la descripción de los 3 eventos seleccionados (sin la parte del horario), cada uno en una nueva línea, en orden del más al menos relevante.
        Asegúrate de que la descripción que devuelves coincida EXACTAMENTE con la descripción de uno de los eventos en la lista.
        NO incluyas números, viñetas, comillas, explicaciones, o cualquier texto introductorio.

        LISTA DE EVENTOS PARA ANALIZAR:
        {lista_texto_plano}
        """

        response = model.generate_content(prompt, request_options={'timeout': 120})
        ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        
        print(f"Ranking de Gemini (con exclusión) recibido: {ranking_limpio}")
        return ranking_limpio

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return []

# --- 3. FUNCIÓN PRINCIPAL (sin cambios) ---
def main():
    print(f"Iniciando proceso de ranking de eventos...")
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original:
            raise ValueError("El archivo events.json está vacío o no tiene la clave 'eventos'.")
        print("Archivo events.json leído correctamente.")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    ranking = obtener_ranking_eventos(lista_eventos_original)

    if not ranking:
        print("No se recibió ranking de Gemini. El archivo de eventos relevantes no se actualizará.")
        return

    print("3. Filtrando los eventos relevantes de la lista original...")
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
