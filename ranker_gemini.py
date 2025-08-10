import requests
import json
import os
from ftplib import FTP
from datetime import datetime  # <-- LÍNEA AÑADIDA Y CORREGIDA
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "eventos-relevantes.json"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- 2. FUNCIÓN PARA LLAMAR A GEMINI ---
def obtener_ranking_eventos(lista_eventos):
    if not GEMINI_API_KEY:
        print("ERROR: No se encontró la API Key de Gemini. No se puede continuar.")
        return []

    print("Contactando a la IA de Gemini para obtener el ranking de relevancia...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        descripciones_partidos = []
        for evento in lista_eventos:
            for partido in evento.get("partidos", []):
                descripciones_partidos.append(partido.get("descripcion", ""))
        
        lista_texto_plano = "\n".join(filter(None, set(descripciones_partidos)))

        if not lista_texto_plano:
            print("No se encontraron descripciones de partidos para analizar.")
            return []

        prompt = f"""
        Actúa como un analista experto en tendencias de entretenimiento para una audiencia de México y Estados Unidos (USA).
        Tu tarea es analizar la siguiente lista de descripciones de eventos y determinar los 3 más relevantes para esta audiencia específica.

        Para determinar la relevancia, prioriza de la siguiente manera:
        1.  **Alto Interés Regional:** Da máxima prioridad a eventos de la Liga MX, NFL, MLB, NBA y peleas de boxeo importantes (especialmente con peleadores mexicanos o de alto perfil en USA).
        2.  **Relevancia Cultural General:** Considera conciertos de artistas populares en la región, estrenos de series o películas muy esperadas y eventos de la cultura pop.
        3.  **Popularidad en Búsquedas y Redes Sociales:** Evalúa qué eventos están generando más conversación y búsquedas en México y USA.

        La salida debe ser exclusivamente el texto de la descripción de los 3 eventos, cada uno en una línea nueva, en orden del más al menos relevante.
        Asegúrate de que la descripción que devuelves coincida EXACTAMENTE con una de las líneas que te proporcioné.
        NO incluyas números, viñetas, comillas, explicaciones, o cualquier texto introductorio.

        LISTA DE EVENTOS PARA ANALIZAR:
        {lista_texto_plano}
        """

        response = model.generate_content(prompt, request_options={'timeout': 120})
        ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        
        print(f"Ranking de Gemini recibido: {ranking_limpio}")
        return ranking_limpio

    except Exception as e:
        print(f"ERROR al contactar con Gemini: {e}. Omitiendo el ranking.")
        return []

# --- 3. FUNCIÓN PRINCIPAL ---
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
    for desc_relevante in ranking:
        encontrado = False
        for evento in lista_eventos_original:
            # Hacemos una copia para no modificar la lista original mientras iteramos
            for partido in evento.get("partidos", []):
                if desc_relevante == partido.get("descripcion"):
                    evento_relevante = {
                        "evento_principal": evento["evento_principal"],
                        "detalle_evento": evento.get("detalle_evento", ""),
                        "partidos": [partido]
                    }
                    eventos_relevantes.append(evento_relevante)
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
