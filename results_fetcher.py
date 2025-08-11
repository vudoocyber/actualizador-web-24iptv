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

# --- 2. FUNCIONES AUXILIARES (LÓGICA MEJORADA) ---

def extraer_hora_centro(horario_str):
    """
    Busca y extrae específicamente la hora que precede a la palabra 'Centro'.
    """
    match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:a\.m\.|p\.m\.|am|pm))\s+Centro', horario_str, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def convertir_hora_a_24h(hora_str):
    if not hora_str: return None
    hora_str = hora_str.lower().replace('.', '')
    match = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)', hora_str)
    if not match: return None
    
    hora, minuto, periodo = match.groups()
    hora = int(hora)
    minuto = int(minuto) if minuto else 0
    
    if periodo == 'pm' and hora != 12: hora += 12
    if periodo == 'am' and hora == 12: hora = 0
        
    return hora + (minuto / 60.0)

def obtener_resultado_gemini(descripcion_partido):
    if not GEMINI_API_KEY:
        print("ADVERTENCIA: API Key de Gemini no encontrada.")
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Actúa como un asistente de resultados deportivos EN TIEMPO REAL. Quiero saber el resultado final del siguiente partido que se jugó hoy: "{descripcion_partido}". Responde ÚNICAMENTE con el marcador final (ej. "2-1", "27-14"). Si no puedes encontrar el resultado, responde exactamente con "Resultado no encontrado"."""
        
        response = model.generate_content(prompt, request_options={'timeout': 90})
        resultado = response.text.strip()
        print(f"  > Resultado de Gemini para '{descripcion_partido}': {resultado}")
        return resultado if "no encontrado" not in resultado.lower() else None

    except Exception as e:
        print(f"  > ERROR al contactar con Gemini para '{descripcion_partido}': {e}")
        return None

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    print(f"Iniciando proceso de búsqueda de resultados...")
    
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

    print("2. Identificando partidos finalizados y buscando resultados...")
    resultados_finales = []
    
    cst_offset = timezone(timedelta(hours=-6))
    hora_actual_cst = datetime.now(cst_offset)
    hora_actual_float = hora_actual_cst.hour + (hora_actual_cst.minute / 60.0)
    print(f"Hora actual (Centro de México): {hora_actual_cst.strftime('%I:%M %p CST')}")

    for evento in lista_eventos_original:
        if "partido_relevante" in evento: continue
            
        for partido in evento.get("partidos", []):
            horario_str = partido.get("horarios", "")
            
            hora_centro_str = extraer_hora_centro(horario_str)
            if not hora_centro_str:
                continue

            hora_ct_24 = convertir_hora_a_24h(hora_centro_str)
            if hora_ct_24 is None:
                continue
            
            # Si la hora actual es 90 minutos o más después de la hora de inicio, busca el resultado.
            if hora_actual_float > hora_ct_24 + 1.5:
                print(f"- Partido finalizado detectado: {partido['descripcion']} (Inició a las {hora_ct_24:.2f}h)")
                resultado = obtener_resultado_gemini(partido['descripcion'])
                if resultado:
                    resultados_finales.append({
                        "evento_principal": evento["evento_principal"],
                        "descripcion": partido["descripcion"],
                        "resultado": resultado,
                        "estado": "Finalizado"
                    })

    json_salida = {"fecha_actualizacion": datetime.now().isoformat(), "resultados": resultados_finales}

    print(f"3. Guardando archivo local '{NOMBRE_ARCHIVO_SALIDA}'...")
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
