import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import pytz
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

# --- 2. FUNCIÓN PARA LLAMAR A GEMINI (MODELO ACTUALIZADO) ---
def obtener_ranking_eventos(lista_eventos):
    if not GEMINI_API_KEY:
        print("ERROR: No se encontró la API Key de Gemini. No se puede continuar.")
        return []
    print("Contactando a la IA de Gemini con modelo estable...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # --- CAMBIO IMPORTANTE: Usamos el modelo estable 'gemini-pro' ---
        model = genai.GenerativeModel('gemini-pro')
        # ... (el resto de la función no cambia) ...
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

        prompt = f"""
        Actúa como un curador de contenido experto para una audiencia de México y Estados Unidos (USA).
        La fecha y hora actual en el Centro de México es: {hora_formateada_cst}.
        Analiza la siguiente lista de eventos y determina los 3 más relevantes, siguiendo estas reglas en orden estricto:
        1. REGLA DE TIEMPO: Ignora eventos que ya hayan finalizado.
        2. REGLA DE EXCLUSIÓN: Descarta INMEDIATAMENTE cualquier partido de una liga o torneo femenino (palabras clave: "Femenil", "WNBA", "NWSL").
        3. REGLA DE INTERÉS: Prioriza eventos de alto interés como Liga MX, NFL, MLB, NBA, Boxeo/UFC y partidos de equipos populares (América, Chivas, Real Madrid, Barcelona, Cowboys, Lakers, Yankees, etc.).
        
        Formato de Salida: Devuelve ÚNICAMENTE la descripción exacta de los 3 eventos, cada uno en una nueva línea, en orden de relevancia. NO incluyas números, viñetas, o cualquier otro texto.

        LISTA DE EVENTOS:
        {lista_texto_plano}
        """

        response = model.generate_content(prompt, request_options={'timeout': 120})
        ranking_limpio = [linea.strip() for linea in response.text.strip().split('\n') if linea.strip()]
        
        print(f"Ranking de Gemini (modelo 'latest') recibido: {ranking_limpio}")
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
            raise ValueError("El archivo events.json está vacío.")
        print("Archivo events.json leído correctamente.")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    ranking_crudo = obtener_ranking_eventos(lista_eventos_original)

    if not ranking_crudo:
        print("No se recibió ranking de Gemini. El archivo de eventos relevantes se creará vacío.")
        json_salida = {"eventos_relevantes": []}
    else:
        print("2. Construyendo y filtrando la lista de eventos relevantes...")
        eventos_relevantes = []
        descripciones_ya_anadidas = set()
        palabras_prohibidas = ["Femenil", "WNBA", "NWSL"]

        for desc_relevante in ranking_crudo:
            if len(eventos_relevantes) >= 3: break
            encontrado = False
            for evento in lista_eventos_original:
                for partido in evento.get("partidos", []):
                    descripcion_corta = partido.get("descripcion", "")
                    if descripcion_corta and descripcion_corta in desc_relevante and descripcion_corta not in descripciones_ya_anadidas:
                        evento_principal = evento.get("evento_principal", "")
                        if any(keyword in evento_principal for keyword in palabras_prohibidas):
                            print(f"  [FILTRADO] Se omitió '{descripcion_corta}' de la liga '{evento_principal}'.")
                            encontrado = True
                            break 
                        print(f"  [ÉXITO] Coincidencia válida encontrada: '{descripcion_corta}'")
                        evento_relevante = {"evento_principal": evento_principal, "detalle_evento": evento.get("detalle_evento", ""), "partidos": [partido]}
                        eventos_relevantes.append(evento_relevante)
                        descripciones_ya_anadidas.add(descripcion_corta)
                        encontrado = True
                        break
                if encontrado: break
        print(f"Ranking final después de aplicar filtros: {[ev['partidos'][0]['descripcion'] for ev in eventos_relevantes]}")
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
