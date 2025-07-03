import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP
from datetime import datetime
import json

# --- 1. CONFIGURACIÓN ---
URL_FUENTE = os.getenv('URL_FUENTE', 'URL_POR_DEFECTO_SI_NO_HAY_SECRET') # Reemplaza con tu URL si no usas secrets
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"
NOMBRE_ARCHIVO_JSON = 'events.json'

# --- 2. FUNCIÓN PARA CREAR EL JSON DE EVENTOS ---
def crear_json_eventos(texto_crudo):
    print("Generando archivo JSON para el nuevo diseño web...")
    # La estructura base del JSON, que empieza con {
    datos_json = {
        "fecha_actualizacion": datetime.now().isoformat(),
        "titulo_guia": "",
        "eventos": []
    }
    evento_actual = None
    partido_actual = None
    lineas = texto_crudo.strip().split('\n')
    
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las"]

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        
        if linea.startswith("Eventos Deportivos"):
            fecha_texto = linea.replace("Eventos Deportivos ", "").strip()
            # Asignamos el título de la guía a nuestro diccionario
            datos_json["titulo_guia"] = f"Guía de Eventos del {fecha_texto}, {datetime.now().year}"
            continue

        if REGEX_EMOJI.search(linea):
            if evento_actual:
                datos_json["eventos"].append(evento_actual)
            
            emoji_match = REGEX_EMOJI.search(linea)
            emoji = emoji_match.group(0) if emoji_match else ""
            nombre_evento = REGEX_EMOJI.sub('', linea).strip()
            
            evento_actual = {
                "evento_principal": nombre_evento,
                "icono": emoji,
                "detalle_evento": "",
                "partidos": []
            }
        elif any(keyword in linea for keyword in PALABRAS_CLAVE_HORARIOS):
            if partido_actual:
                partido_actual["horarios"] = linea
                if " por " in linea:
                    partes = linea.split(" por ", 1)
                    partido_actual["horarios"] = partes[0]
                    canales_raw = partes[1]
                    if " y Categoria " in canales_raw:
                        canales_full, categoria = canales_raw.rsplit(" y Categoria ", 1)
                        partido_actual["canales"] = [c.strip() for c in canales_full.split(',')]
                        partido_actual["categoria"] = categoria.strip()
                    else:
                        partido_actual["canales"] = [c.strip() for c in canales_raw.split(',')]
                        partido_actual["categoria"] = ""
                else:
                    partido_actual["canales"] = []
        else:
            if evento_actual:
                if not evento_actual["partidos"] and not evento_actual["detalle_evento"]:
                     evento_actual["detalle_evento"] = linea
                else:
                    partido_actual = {
                        "descripcion": linea,
                        "horarios": "",
                        "canales": [],
                        "categoria": ""
                    }
                    evento_actual["partidos"].append(partido_actual)
    
    if evento_actual:
        datos_json["eventos"].append(evento_actual)
    
    print("Estructura de datos creada. Convirtiendo a texto JSON...")
    # La función json.dumps es la que crea el texto que empieza con {
    return json.dumps(datos_json, indent=4, ensure_ascii=False)

# --- 3. FUNCIÓN PRINCIPAL ---
def main():
    print("Iniciando proceso de actualización de JSON...")
    if not URL_FUENTE or URL_FUENTE == 'URL_POR_DEFECTO_SI_NO_HAY_SECRET':
        print("ERROR CRÍTICO: No se ha configurado la URL_FUENTE.")
        return

    try:
        print(f"1. Extrayendo datos de la fuente...")
        respuesta = requests.get(URL_FUENTE, timeout=20)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        ancla = soup.find(string=lambda text: text and "⚽️" in text)
        if not ancla: raise ValueError("No se encontró el ancla (⚽️).")
        bloque_contenido = ancla.parent.parent.parent
        texto_extraido_filtrado = bloque_contenido.get_text(separator='\n', strip=True)
        print("Datos extraídos correctamente.")
    except Exception as e:
        print(f"ERROR FATAL en la extracción: {e}")
        return

    contenido_json = crear_json_eventos(texto_extraido_filtrado)
    
    print(f"Guardando '{NOMBRE_ARCHIVO_JSON}' localmente...")
    with open(NOMBRE_ARCHIVO_JSON, 'w', encoding='utf-8') as f:
        f.write(contenido_json)
    print("Archivo JSON local creado.")

    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return

    try:
        print(f"Subiendo '{NOMBRE_ARCHIVO_JSON}' al servidor FTP...")
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.cwd(RUTA_REMOTA_FTP)
            with open(NOMBRE_ARCHIVO_JSON, 'rb') as file:
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_JSON}', file)
            print("¡Subida completada exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")
