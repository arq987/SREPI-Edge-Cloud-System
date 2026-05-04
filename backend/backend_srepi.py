from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import pymssql
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import uuid
import urllib.parse
# 1. Cargar las variables de entorno desde el archivo .env
load_dotenv()

app = FastAPI(title="SREPI Backend Core - Seguridad Implementada")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción se pone la IP del kiosco
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Obtener las credenciales de forma segura

DB_SERVER = os.getenv("DB_SERVER") 
DB_USER = os.getenv("DB_USER")     
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")  
SECRET_KEY = os.getenv("SECRET_KEY_JWT")   

def obtener_conexion():
    try:
        # pymssql se conecta de forma nativa sin necesitar drivers externos
        conn = pymssql.connect(
            server=DB_SERVER,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except Exception as e:
        print(f"❌ Error conectando a Azure SQL: {e}")
        return None

# --- CONFIGURACIÓN DE META (WHATSAPP) ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN_META")
META_TOKEN = os.getenv("META_ACCESS_TOKEN")
PHONE_ID = os.getenv("META_PHONE_ID")

def enviar_mensaje_whatsapp(telefono_destino: str, texto: str):
    """Función para disparar respuestas reales a través de la API de Meta"""
    url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono_destino,
        "type": "text",
        "text": {"body": texto}
    }
    
    if META_TOKEN and META_TOKEN != "tu_token_de_acceso_de_meta":
        # Hacemos la petición y guardamos la respuesta
        respuesta = requests.post(url, headers=headers, json=payload)
        
        # Imprimimos en consola qué nos dijo Meta
        if respuesta.status_code == 200:
            print(f"✅ Mensaje entregado a Meta para el número {telefono_destino}")
        else:
            print(f"❌ Error de Meta al enviar: {respuesta.status_code}")
            print(f"Detalle del error: {respuesta.text}")
    else:
        print(f"\n[SIMULACIÓN WHATSAPP a {telefono_destino}]:\n{texto}\n")

def enviar_qr_whatsapp(telefono_destino: str, token_jwt: str, texto_caption: str):
    """Genera un QR al vuelo y lo envía como imagen por WhatsApp"""
    
    # 1. Codificamos el token (que tiene caracteres especiales) para que sea seguro en una URL
    token_seguro = urllib.parse.quote(token_jwt)
    
    # 2. Usamos una API gratuita y rápida que convierte textos en imágenes QR
    url_imagen_qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&margin=10&data={token_seguro}"
    
    url_meta = f"https://graph.facebook.com/v17.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 3. Armamos el payload tipo "image" con el link y el pie de foto (caption)
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono_destino,
        "type": "image",
        "image": {
            "link": url_imagen_qr,
            "caption": texto_caption
        }
    }
    
    if META_TOKEN and META_TOKEN != "tu_token_de_acceso_de_meta":
        respuesta = requests.post(url_meta, headers=headers, json=payload)
        if respuesta.status_code == 200:
            print(f"✅ Código QR enviado como imagen a {telefono_destino}")
        else:
            print(f"❌ Error de Meta al enviar QR: {respuesta.status_code}")
            print(f"Detalle: {respuesta.text}")
    else:
        print(f"\n[SIMULACIÓN QR a {telefono_destino}]:\nImagen: {url_imagen_qr}\nTexto: {texto_caption}\n")
# ====================================================================
# FASE 2: WEBHOOK DE WHATSAPP (META CLOUD API)
# ====================================================================

@app.get("/webhook")
def verificar_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Meta llama a este endpoint una sola vez para verificar que tu servidor existe"""
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print("✅ Webhook verificado exitosamente por Meta.")
        # Meta exige que le devolvamos el challenge como un número entero
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Error de autenticación del Webhook")

@app.post("/webhook")
async def recibir_mensaje_whatsapp(request: Request):
    """Este endpoint recibe todos los mensajes de texto que envían los clientes"""
    payload = await request.json()
    
    try:
        # Navegamos por la estructura JSON oficial que envía Meta
        if "object" in payload and payload["object"] == "whatsapp_business_account":
            entry = payload["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]
            
            if "messages" in value:
                mensaje_info = value["messages"][0]
                telefono_cliente = mensaje_info["from"]
                texto_mensaje = mensaje_info["text"]["body"].lower().strip()
                
                print(f"📩 Mensaje recibido de {telefono_cliente}: {texto_mensaje}")
                
                # --- MÁQUINA DE ESTADOS DEL BOT ---
                if "hola" in texto_mensaje or "oferta" in texto_mensaje:
                    # 1. El cliente saluda, consultamos la base de datos SQL
                    ofertas = consultar_ofertas_disponibles()["ofertas_activas"]
                    
                    # --- NUEVA LÓGICA: LIMITAR A TOP 10 ---
                    top_ofertas = ofertas[:10] 
                    
                    respuesta = "🤖 *SREPI Bot:*\n¡Hola! Encontré estas Cajas Sorpresa más urgentes para ti hoy:\n\n"
                    for item in top_ofertas:
                        respuesta += f"🟢 Envía *{item['id_lote']}* para rescatar: {item['producto']}\n"
                        respuesta += f"💵 {item['precio_original']} -> *{item['precio_oferta']}*\n"
                        respuesta += f"⏳ Vence en {item['vence_en_horas']}h | Ganas {item['recompensa_xp']} XP\n---\n"
                    
                    # Si hay más productos, le avisamos al usuario
                    if len(ofertas) > 10:
                        respuesta += f"\n*(Hay {len(ofertas) - 10} productos más en riesgo. ¡Escribe el ID para reservar!)*"
                    
                    enviar_mensaje_whatsapp(telefono_cliente, respuesta)
                
                elif texto_mensaje.isdigit():
                    # 2. El cliente envía un número (ID de Lote), procesamos la reserva
                    resultado = confirmar_reserva(int(texto_mensaje), telefono_cliente)
                    
                    if "error" in resultado:
                        enviar_mensaje_whatsapp(telefono_cliente, f"🤖 *Error:* {resultado['error']}")
                    else:
                        respuesta_qr = f"✅ *{resultado['mensaje']}*\n{resultado['instrucciones']}\n\n"
                        respuesta_qr += f"Tu Código de Retiro es:\n```{resultado['codigo_qr_jwt']}```"
                        enviar_mensaje_whatsapp(telefono_cliente, respuesta_qr)
                
                else:
                    enviar_mensaje_whatsapp(telefono_cliente, "🤖 Escribe *ofertas* para ver el catálogo o el *número* del producto que deseas.")
                    
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ Error procesando el Webhook: {e}")
        return {"status": "error"}

# --- MOTOR DDA Y GAMIFICACIÓN ---
def calcular_dda_y_gamificacion(precio_base, horas, multiplicador_xp):
    """Calcula el descuento según las horas y aplica el multiplicador de la categoría"""
    if horas <= 3:
        descuento, xp_base = 0.70, 100  # Zona Roja Crítica
    elif horas <= 6:
        descuento, xp_base = 0.50, 50   # Zona Amarilla
    else:
        descuento, xp_base = 0.20, 20   # Zona Verde/Preventiva
        
    precio_final = int(precio_base * (1 - descuento))
    
    # Aquí multiplicamos la XP base por el factor que viene de la base de datos
    xp_total = int(xp_base * multiplicador_xp) 
    
    return precio_final, xp_total

# --- ENDPOINT: CATÁLOGO DE OFERTAS ---
@app.get("/api/ofertas")
def consultar_ofertas_disponibles():
    ofertas_procesadas = []
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # Ejecutamos el Stored Procedure que creamos en SQL Server
        cursor.execute("EXEC sp_ObtenerLotesEnRiesgo")
        filas = cursor.fetchall()
        
        for fila in filas:
            # Mapeamos los resultados que nos devuelve SQL
            id_lote = fila[0]
            sku = fila[1]
            nombre = fila[2]
            categoria = fila[3]
            precio_base = float(fila[4])
            multiplicador_xp = float(fila[5])
            cantidad = fila[6]
            horas = fila[7]
            
            # Pasamos los datos por el motor DDA
            precio_descuento, puntos_xp = calcular_dda_y_gamificacion(precio_base, horas, multiplicador_xp)
            
            ofertas_procesadas.append({
                "id_lote": id_lote,
                "sku": sku,
                "producto": f"{nombre} ({categoria})",
                "unidades_disponibles": cantidad,
                "vence_en_horas": horas,
                "precio_original": f"${precio_base:,.0f}",
                "precio_oferta": f"${precio_descuento:,.0f}",
                "recompensa_xp": puntos_xp
            })
            
        conn.close()
        return {"ofertas_activas": ofertas_procesadas}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando al ERP (SQL Server): {str(e)}")

# --- ENDPOINT: GENERACIÓN DE RESERVA Y CÓDIGO QR ---
@app.post("/api/reservar/{id_lote}")
def confirmar_reserva(id_lote: int, telefono_usuario: str):
    """
    En un entorno de producción, aquí haríamos un UPDATE a SREPI_Reservas en SQL.
    Por ahora, generamos el Token JWT garantizando la validez offline.
    """
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
# Validamos que el lote exista y tenga stock
        cursor.execute("""
            SELECT P.Nombre, P.Precio_Base, DATEDIFF(hour, GETUTCDATE(), L.Fecha_Vencimiento)
            FROM Inventario_Lotes L
            INNER JOIN Productos P ON L.SKU = P.SKU
            WHERE L.ID_Lote = %s AND L.Cantidad_Disponible > 0
        """, id_lote)
        
        producto_db = cursor.fetchone()
        conn.close()
        
        if not producto_db:
            return {"error": "El lote ya no está disponible o fue retirado."}

        nombre_prod = producto_db[0]
        precio_base = float(producto_db[1])
        horas = producto_db[2]
        
        # Calculamos el precio final para meterlo en el QR (Asumimos multiplicador 1.0 por rapidez)
        precio_pagado, xp_ganados = calcular_dda_y_gamificacion(precio_base, horas, 1.0)

# Generamos el payload para el Kiosco Edge
        payload_qr = {
            "id_transaccion": str(uuid.uuid4()),  # <--- SELLO DE SEGURIDAD ÚNICO
            "id_lote": id_lote,
            "usuario": telefono_usuario,
            "producto": nombre_prod,
            "pagado": precio_pagado,
            "xp": xp_ganados,
            "exp": datetime.utcnow() + timedelta(hours=2)
        }
# Generamos el Token Criptográfico (JWT)
        token_reserva = jwt.encode(payload_qr, SECRET_KEY, algorithm="HS256")
        
        # Armamos el pie de foto (caption) que acompañará al Código QR
        mensaje_pie_foto = (
            f"🎉 *¡Reserva Exitosa!*\n\n"
            f"📦 {nombre_prod}\n"
            f"💵 Pagas: ${precio_pagado:,.0f}\n"
            f"⭐ Ganas: {xp_ganados} XP\n\n"
            f"Acércate al Punto Express SREPI y muestra este Código QR a la cámara para retirar tu producto. "
            f"Tienes 2 horas antes de que la reserva expire."
        )
        
        # ¡Magia! Enviamos la imagen directamente al WhatsApp del cliente
        enviar_qr_whatsapp(telefono_usuario, token_reserva, mensaje_pie_foto)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la reserva: {str(e)}")
    
    # --- MODELO PARA RECIBIR LOS DATOS DEL KIOSCO ---
# --- MODELO PARA RECIBIR LOS DATOS DEL KIOSCO ---
class DatosRetiro(BaseModel):
    id_transaccion: str   # <--- Requerimos el UUID
    id_lote: int
    usuario: str
    xp_ganada: int

# --- ENDPOINT: CONFIRMACIÓN DESDE EL KIOSCO EDGE ---
@app.post("/api/kiosco/confirmar-retiro")
def procesar_retiro(datos: DatosRetiro):
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        
        # 1. VERIFICACIÓN DE SEGURIDAD: ¿Ya existe esta transacción?
        cursor.execute("SELECT ID_Transaccion FROM Registro_Retiros WHERE ID_Transaccion = %s", datos.id_transaccion)
        if cursor.fetchone():
            conn.close()
            # Devolvemos error 400 si el QR ya fue usado
            raise HTTPException(status_code=400, detail="Este Código QR ya fue canjeado anteriormente.")
        
        # 2. Si no existe, registramos la transacción para quemar el QR
        cursor.execute("INSERT INTO Registro_Retiros (ID_Transaccion, Telefono_Usuario) VALUES (%s, %s)", 
                    datos.id_transaccion, datos.usuario)
        
        # 3. Descontamos 1 unidad del lote
        cursor.execute("""
            UPDATE Inventario_Lotes 
            SET Cantidad_Disponible = Cantidad_Disponible - 1 
            WHERE ID_Lote = %s AND Cantidad_Disponible > 0
        """, datos.id_lote)
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "mensaje": "Inventario descontado exitosamente."}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")