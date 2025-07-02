import requests
from bs4 import BeautifulSoup
import re
import os
from ftplib import FTP
from datetime import datetime
import json ### NUEVO ###

# --- 1. CONFIGURACIÓN GLOBAL (Leída desde los Secrets de GitHub) ---
URL_FUENTE = os.getenv('URL_FUENTE')
NOMBRE_ARCHIVO_PROGRAMACION = os.getenv('NOMBRE_ARCHIVO_PROGRAMACION')
NOMBRE_ARCHIVO_MENSAJE = os.getenv('NOMBRE_ARCHIVO_MENSAJE')
NOMBRE_ARCHIVO_JSON = 'events.json' ### NUEVO ###
FTP_HOST = os.getenv('FTP_HOST')
FTP_USUARIO = os.getenv('FTP_USUARIO')
FTP_CONTRASENA = os.getenv('FTP_CONTRASENA')
RUTA_REMOTA_FTP = "/public_html/"

# --- 2. FUNCIÓN DE TRANSFORMACIÓN HTML (sin cambios) ---
def aplicar_reglas_html(texto_crudo):
    # (Esta función se queda exactamente igual)
    resultado_html = ""
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE = ["Este", "Centro", "Pacífico"]
    lineas = texto_crudo.strip().split('\n')
    year_actual = datetime.now().year
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith("Eventos Deportivos"):
            fecha_texto = linea.replace("Eventos Deportivos ", "").strip()
            resultado_html += f"<h2>Eventos Deportivos, {year_actual} <br /><br />\n{fecha_texto} <br /><br /><br />\n"
        elif "WWE Wrestling" in linea or REGEX_EMOJI.search(linea):
            resultado_html += f"<h3>{linea}</h3><br /><br />\n"
        elif any(keyword in linea for keyword in PALABRAS_CLAVE):
            resultado_html += f"<p>{linea}</p><br /><br />\n"
        else:
            resultado_html += f"<p><strong>{linea}</strong></p><br /><br />\n"
    return resultado_html

# --- 3. FUNCIÓN PARA CREAR MENSAJE (sin cambios) ---
def crear_mensaje_whatsapp(texto_crudo):
    # (Esta función se queda exactamente igual)
    print("Generando mensaje para WhatsApp en formato HTML...")
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    lineas = texto_crudo.strip().split('\n')
    titulos_con_emoji = []
    fecha_del_dia = ""
    for linea in lineas:
        linea = linea.strip()
        if linea.startswith("Eventos Deportivos"):
            fecha_del_dia = linea.replace("Eventos Deportivos ", "").strip()
        elif "WWE Wrestling" in linea or REGEX_EMOJI.search(linea):
            titulos_con_emoji.append(linea)
    year_actual = datetime.now().year
    fecha_formateada = f"{fecha_del_dia} de {year_actual}"
    lista_de_titulos = "\n".join(titulos_con_emoji)
    mensaje_texto_plano = f"""🎯 ¡Guía de Eventos Deportivos en Vivo de Hoy! 🏆🔥\n\nConsulta los horarios y canales de transmisión aquí:\n\n👉 https://24hometv.xyz/#horarios\n\n\n📅 *{fecha_formateada}*\n\n{lista_de_titulos}\n\n📱 ¿Listo para no perderte ni un segundo de acción?\n\nDale clic al enlace y entérate de todo en segundos 👇\n\n👉 https://24hometv.xyz/#horarios\n\n⭐ 24IPTV & HomeTV – Tu Mejor Elección en Entretenimiento Deportivo ⭐"""
    mensaje_html_final = f"""<!DOCTYPE html>\n<html lang="es">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Mensaje para WhatsApp</title>\n    <style>\n        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f0f2f5; }}\n        pre {{ white-space: pre-wrap; word-wrap: break-word; font-size: 16px; margin: 20px auto; padding: 20px; max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}\n    </style>\n</head>\n<body>\n    <pre>{mensaje_texto_plano}</pre>\n</body>\n</html>"""
    print("Mensaje en formato HTML generado.")
    return mensaje_html_final

### NUEVA FUNCIÓN ###
# --- 4. FUNCIÓN PARA CREAR EL JSON DE EVENTOS ---
def crear_json_eventos(texto_crudo):
    print("Generando archivo JSON para el nuevo diseño web...")
    datos_json = {
        "fecha_actualizacion": datetime.now().isoformat(),
        "guia": []
    }
    evento_actual = None
    partido_actual = None
    lineas = texto_crudo.strip().split('\n')
    
    REGEX_EMOJI = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]+', re.UNICODE)
    PALABRAS_CLAVE_HORARIOS = ["Este", "Centro", "Pacífico", "partir de las"]

    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith("Eventos Deportivos"):
            continue

        if REGEX_EMOJI.search(linea):
            if evento_actual:
                datos_json["guia"].append(evento_actual)
            
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
                # Asumimos que los canales son la última parte que se añade
                if " y Categoria " in linea:
                    horarios_raw, canales_raw = linea.split(" por ", 1)
                    canales_full, categoria = canales_raw.rsplit(" y Categoria ", 1)
                    partido_actual["horarios"] = horarios_raw
                    partido_actual["canales"] = [c.strip() for c in canales_full.split(',')]
                    partido_actual["categoria"] = categoria.strip()
                elif " por " in linea:
                    horarios_raw, canales_raw = linea.split(" por ", 1)
                    partido_actual["horarios"] = horarios_raw
                    partido_actual["canales"] = [c.strip() for c in canales_raw.split(',')]
        else:
            if evento_actual:
                # Si no es un horario, puede ser un detalle del evento o un nuevo partido
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
        datos_json["guia"].append(evento_actual)
    
    print("Archivo JSON generado correctamente.")
    return json.dumps(datos_json, indent=2, ensure_ascii=False)


# --- 5. FUNCIÓN PRINCIPAL (MODIFICADA) ---
def main():
    print("Iniciando proceso de actualización automática...")
    if not all([URL_FUENTE, NOMBRE_ARCHIVO_PROGRAMACION, NOMBRE_ARCHIVO_MENSAJE]):
        print("ERROR CRÍTICO: Faltan una o más variables de configuración (URL_FUENTE, NOMBRES DE ARCHIVOS). Revisa los Secrets de GitHub.")
        return

    try:
        print(f"1. Extrayendo datos de la fuente configurada...")
        respuesta = requests.get(URL_FUENTE, timeout=20)
        respuesta.raise_for_status()
        soup = BeautifulSoup(respuesta.content, 'html.parser')
        ancla = soup.find(string=lambda text: text and "⚽️" in text)
        if not ancla:
            raise ValueError("ERROR CRÍTICO: No se encontró el ancla (⚽️).")
        bloque_contenido = ancla.parent.parent.parent
        if not bloque_contenido or bloque_contenido.name != 'div':
             raise ValueError("ERROR: No se pudo aislar el bloque <div> contenedor.")
        texto_extraido_filtrado = bloque_contenido.get_text(separator='\n', strip=True)
        print("Datos extraídos correctamente.")
    except Exception as e:
        print(f"ERROR FATAL en la extracción: {e}")
        return

    # --- Lógica original (sin cambios) ---
    contenido_html_programacion = aplicar_reglas_html(texto_extraido_filtrado)
    print(f"Guardando '{NOMBRE_ARCHIVO_PROGRAMACION}'...")
    with open(NOMBRE_ARCHIVO_PROGRAMACION, 'w', encoding='utf-8') as f:
        f.write(contenido_html_programacion)
    
    contenido_mensaje_whatsapp = crear_mensaje_whatsapp(texto_extraido_filtrado)
    print(f"Guardando '{NOMBRE_ARCHIVO_MENSAJE}'...")
    with open(NOMBRE_ARCHIVO_MENSAJE, 'w', encoding='utf-8') as f:
        f.write(contenido_mensaje_whatsapp)

    # --- Nueva lógica para JSON (se ejecuta en paralelo) ---
    contenido_json = crear_json_eventos(texto_extraido_filtrado)
    print(f"Guardando '{NOMBRE_ARCHIVO_JSON}'...")
    with open(NOMBRE_ARCHIVO_JSON, 'w', encoding='utf-8') as f:
        f.write(contenido_json)
    
    print("Archivos temporales creados (HTML y JSON).")

    if not all([FTP_HOST, FTP_USUARIO, FTP_CONTRASENA]):
        print("ADVERTENCIA: Faltan variables de FTP. Omitiendo la subida.")
        return

    try:
        print(f"Subiendo archivos al servidor FTP en {FTP_HOST}...")
        with FTP(FTP_HOST, FTP_USUARIO, FTP_CONTRASENA) as ftp:
            ftp.cwd(RUTA_REMOTA_FTP)
            
            # Subida de archivos originales
            with open(NOMBRE_ARCHIVO_PROGRAMACION, 'rb') as file:
                print(f"Subiendo '{NOMBRE_ARCHIVO_PROGRAMACION}'...")
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_PROGRAMACION}', file)
            with open(NOMBRE_ARCHIVO_MENSAJE, 'rb') as file:
                print(f"Subiendo '{NOMBRE_ARCHIVO_MENSAJE}'...")
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_MENSAJE}', file)
            
            # ### NUEVO: Subida del archivo JSON ###
            with open(NOMBRE_ARCHIVO_JSON, 'rb') as file:
                print(f"Subiendo '{NOMBRE_ARCHIVO_JSON}'...")
                ftp.storbinary(f'STOR {NOMBRE_ARCHIVO_JSON}', file)
                
            print("¡Subida de todos los archivos completada exitosamente!")
    except Exception as e:
        print(f"ERROR FATAL durante la subida por FTP: {e}")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    main()
    print("--- Proceso finalizado ---")

# === FIN DEL CÓDIGO ===
