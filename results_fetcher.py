import requests
import json
import os
from ftplib import FTP
from datetime import datetime, timezone, timedelta
import re
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
URL_JSON_FUENTE = "https://24hometv.xyz/events.json"
NOMBRE_ARCHIVO_SALIDA = "results.json"
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- 2. FUNCIONES AUXILIARES ---

def extraer_hora_centro(horario_str):
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:a\.m\.|p\.m\.|am|pm))\s+Centro', horario_str, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def convertir_hora_a_24h(hora_str):
    if not hora_str: return None
    hora_str = hora_str.lower().replace('.', '')
    # --- LÍNEA CORREGIDA ---
    # Se eliminó un paréntesis extra que causaba el error de sintaxis.
    match = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)', hora_str)
    if not match: return None
    
    hora, minuto, periodo = match.groups()
    hora = int(hora)
    minuto = int(minuto) if minuto else 0
    
    if periodo == 'pm' and hora != 12: hora += 12
    if periodo == 'am' and hora == 12: hora = 0
        
    return hora + (minuto / 60.0)

def obtener_resultados_en_lote(partidos_finalizados):
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: API Key de Gemini no encontrada.")
        return []
    if not partidos_finalizados:
        print("No hay partidos finalizados para buscar resultados.")
        return []

    print(f"Contactando a Gemini para buscar resultados de {len(partidos_finalizados)} partidos en una sola llamada...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        lista_para_prompt = "\n".join(partidos_finalizados)

        prompt = f"""
        Actúa como un asistente de resultados deportivos. Te daré una lista de partidos que ya finalizaron. Para cada partido en la lista, busca el resultado final.

        Devuelve tu respuesta como un array JSON válido y nada más. Cada objeto en el array debe tener dos claves: "partido" (con el nombre exacto que te di) y "resultado" (con el marcador).
        Si no encuentras el resultado para un partido, simplemente omítelo del array JSON en tu respuesta.

        Ejemplo de respuesta JSON válida:
        [
          {{
            "partido": "Estoril vs Estrela",
            "resultado": "1-0"
          }},
          {{
            "partido": "Porto vs Vitoria Guimaraes",
            "resultado": "2-2"
          }}
        ]

        LISTA DE PARTIDOS A BUSCAR:
        {lista_para_prompt}
        """
        
        response = model.generate_content(prompt, request_options={'timeout': 180})
        respuesta_limpia = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        print(f"Respuesta JSON de Gemini recibida:\n{respuesta_limpia}")
        
        resultados = json.loads(respuesta_limpia)
        return resultados

    except Exception as e:
        print(f"ERROR al contactar o procesar la respuesta de Gemini: {e}")
        return []

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    print(f"Iniciando proceso de búsqueda de resultados...")
    
    try:
        print(f"1. Descargando {URL_JSON_FUENTE}...")
        respuesta = requests.get(URL_JSON_FUENTE, params={'v': datetime.now().timestamp()}, timeout=20)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lista_eventos_original = datos.get("eventos", [])
        if not lista_eventos_original: raise ValueError("El archivo events.json está vacío.")
        print("Archivo events.json leído correctamente.")
    except Exception as e:
        print(f"ERROR FATAL al leer el archivo JSON: {e}")
        return

    print("2. Identificando todos los partidos finalizados...")
    partidos_a_consultar = []
    
    cst_offset = timezone(timedelta(hours=-6))
    hora_actual_cst = datetime.now(cst_offset)
    hora_actual_float = hora_actual_cst.hour + (hora_actual_cst.minute / 60.0)
    print(f"Hora actual (Centro de México): {hora_actual_cst.strftime('%I:%M %p CST')}")

    for evento in lista_eventos_original:
        if "partido_relevante" in evento: continue
        for partido in evento.get("partidos", []):
            horario_str = partido.get("horarios", "")
            hora_centro_str = extraer_hora_centro(horario_str)
            if not hora_centro_str: continue
            
            hora_ct_24 = convertir_hora_a_24h(hora_centro_str)
            if hora_ct_24 is None: continue
            
            if hora_actual_float > hora_ct_24 + 1.5:
                partidos_a_consultar.append(partido['descripcion'])

    print(f"Se encontraron {len(partidos_a_consultar)} partidos finalizados para consultar.")

    resultados_de_gemini = obtener_resultados_en_lote(partidos_a_consultar)

    mapa_resultados = {res["partido"]: res["resultado"] for res in resultados_de_gemini}
    
    resultados_finales = []
    for descripcion, resultado in mapa_resultados.items():
        resultados_finales.append({
            "descripcion": descripcion,
            "resultado": resultado,
            "estado": "Finalizado"
        })

    json_salida = {"fecha_actualizacion": datetime.now().isoformat(), "resultados": resultados_finales}

    print(f"3. Guardando archivo local '{NOMBRE_ARCHIVO_SALIDA}' con {len(resultados_finales)} resultados...")
    with open(NOMBRE_ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
        json.dump(json_salida, f, indent=4, ensure_ascii=False)
    print("Archivo local guardado.")
    
    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return
    
    print(f"4. Subiendo '{NOMBRE_ARCHIVO_SALIDA}' al servidor FTP...")
    try:
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.set_pasv(True)
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_SALIDA, 'rb') as file:
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_SALIDA}', file)
            print("¡Archivo de resultados subido exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso de búsqueda de resultados finalizado ---")
