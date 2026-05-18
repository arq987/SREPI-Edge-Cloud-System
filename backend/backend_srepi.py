from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import pymssql
import jwt
from datetime import datetime, timedelta
from typing import Optional, List
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
DB_LOGIN_TIMEOUT_SECONDS = 60
DB_QUERY_TIMEOUT_SECONDS = 60
DEFAULT_RESERVA_VALOR = 2
DEFAULT_RESERVA_UNIDAD = "horas"

BOT_ESTADOS = {}
ESTADO_ESPERANDO_CATEGORIA = "esperando_categoria"
ESTADO_ESPERANDO_LOTE = "esperando_lote"
ESTADO_ESPERANDO_MAS = "esperando_mas"
ESTADO_ESPERANDO_CANTIDAD = "esperando_cantidad"
MAX_OFERTAS_POR_MENSAJE = 10
MAX_UNIDADES_POR_PRODUCTO = 5

def obtener_conexion():
    try:
        # pymssql se conecta de forma nativa sin necesitar drivers externos
        conn = pymssql.connect(
            server=DB_SERVER,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            login_timeout=DB_LOGIN_TIMEOUT_SECONDS,
            timeout=DB_QUERY_TIMEOUT_SECONDS
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

def obtener_categorias_por_id():
    resultado = listar_categorias()
    categorias = resultado.get("categorias", [])
    return {int(c["id"]): c["nombre"] for c in categorias}

def filtrar_ofertas_por_categoria(ofertas, categoria_nombre):
    marcador = f"({categoria_nombre})"
    return [item for item in ofertas if marcador in item.get("producto", "")]

def formatear_ofertas(ofertas):
    respuesta = ""
    for item in ofertas:
        respuesta += f"🟢 Envía *{item['id_lote']}* para rescatar: {item['producto']}\n"
        respuesta += f"📦 Disponibles: {item.get('unidades_disponibles', 0)} unidades\n"
        respuesta += f"💵 {item['precio_original']} -> *{item['precio_oferta']}*\n"
        respuesta += f"⏳ Vence en {item['vence_en_dias']} dias | Ganas {item['recompensa_xp']} XP\n---\n"
    return respuesta

def obtener_config_reserva():
    try:
        conn = obtener_conexion()
        if not conn:
            return {"valor": DEFAULT_RESERVA_VALOR, "unidad": DEFAULT_RESERVA_UNIDAD}
        cursor = conn.cursor()
        cursor.execute("SELECT Valor, Unidad FROM SREPI_Reserva_Config WHERE ID_Config = 1")
        fila = cursor.fetchone()
        conn.close()
        if not fila:
            return {"valor": DEFAULT_RESERVA_VALOR, "unidad": DEFAULT_RESERVA_UNIDAD}
        valor = int(fila[0])
        unidad = str(fila[1])
        if unidad not in ("horas", "dias"):
            unidad = DEFAULT_RESERVA_UNIDAD
        if valor <= 0:
            valor = DEFAULT_RESERVA_VALOR
        return {"valor": valor, "unidad": unidad}
    except Exception:
        return {"valor": DEFAULT_RESERVA_VALOR, "unidad": DEFAULT_RESERVA_UNIDAD}

class ReservaConfigPayload(BaseModel):
    valor: int
    unidad: str

DEFAULT_DDA_PARAMS = {
    "dias_roja": 2,
    "dias_amarilla": 3,
    "desc_roja": 70.0,
    "desc_amarilla": 50.0,
    "desc_verde": 20.0,
    "xp_roja": 100,
    "xp_amarilla": 50,
    "xp_verde": 20,
    "multiplicador_xp": 1.0
}

def obtener_params_dda():
    try:
        conn = obtener_conexion()
        if not conn:
            return dict(DEFAULT_DDA_PARAMS)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Dias_Roja, Dias_Amarilla, Desc_Roja, Desc_Amarilla, Desc_Verde,
                   XP_Roja, XP_Amarilla, XP_Verde, Multiplicador_XP
            FROM DDA_Params_Config WHERE ID_Config = 1
        """)
        fila = cursor.fetchone()
        conn.close()
        if not fila:
            return dict(DEFAULT_DDA_PARAMS)
        return {
            "dias_roja": int(fila[0]),
            "dias_amarilla": int(fila[1]),
            "desc_roja": float(fila[2]),
            "desc_amarilla": float(fila[3]),
            "desc_verde": float(fila[4]),
            "xp_roja": int(fila[5]),
            "xp_amarilla": int(fila[6]),
            "xp_verde": int(fila[7]),
            "multiplicador_xp": float(fila[8])
        }
    except Exception:
        return dict(DEFAULT_DDA_PARAMS)


class DDAParamsConfigModel(BaseModel):
    dias_roja: int = 2
    dias_amarilla: int = 3
    desc_roja: float = 70.0
    desc_amarilla: float = 50.0
    desc_verde: float = 20.0
    xp_roja: int = 100
    xp_amarilla: int = 50
    xp_verde: int = 20
    multiplicador_xp: float = 1.0


@app.get("/api/dda/params")
def leer_params_dda():
    return obtener_params_dda()


@app.post("/api/dda/params")
def guardar_params_dda(payload: DDAParamsConfigModel):
    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()
        cursor.execute("""
            IF EXISTS (SELECT 1 FROM DDA_Params_Config WHERE ID_Config = 1)
                UPDATE DDA_Params_Config
                SET Dias_Roja = %s, Dias_Amarilla = %s,
                    Desc_Roja = %s, Desc_Amarilla = %s, Desc_Verde = %s,
                    XP_Roja = %s, XP_Amarilla = %s, XP_Verde = %s,
                    Multiplicador_XP = %s, Fecha_Actualizacion = SYSUTCDATETIME()
                WHERE ID_Config = 1
            ELSE
                INSERT INTO DDA_Params_Config
                    (ID_Config, Dias_Roja, Dias_Amarilla, Desc_Roja, Desc_Amarilla, Desc_Verde, XP_Roja, XP_Amarilla, XP_Verde, Multiplicador_XP)
                VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            payload.dias_roja, payload.dias_amarilla,
            payload.desc_roja, payload.desc_amarilla, payload.desc_verde,
            payload.xp_roja, payload.xp_amarilla, payload.xp_verde,
            payload.multiplicador_xp,
            payload.dias_roja, payload.dias_amarilla,
            payload.desc_roja, payload.desc_amarilla, payload.desc_verde,
            payload.xp_roja, payload.xp_amarilla, payload.xp_verde,
            payload.multiplicador_xp
        ))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando parametros DDA: {str(e)}")


@app.get("/api/dda/reserva-config")
def leer_config_reserva():
    return obtener_config_reserva()

@app.post("/api/dda/reserva-config")
def guardar_config_reserva(payload: ReservaConfigPayload):
    unidad = payload.unidad.strip().lower()
    if unidad not in ("horas", "dias"):
        raise HTTPException(status_code=400, detail="Unidad invalida")
    if payload.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor invalido")

    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()
        cursor.execute("""
            IF EXISTS (SELECT 1 FROM SREPI_Reserva_Config WHERE ID_Config = 1)
                UPDATE SREPI_Reserva_Config
                SET Valor = %s, Unidad = %s, Fecha_Actualizacion = SYSUTCDATETIME()
                WHERE ID_Config = 1
            ELSE
                INSERT INTO SREPI_Reserva_Config (ID_Config, Valor, Unidad)
                VALUES (1, %s, %s)
        """, (payload.valor, unidad, payload.valor, unidad))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando configuracion reserva: {str(e)}")
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
                    # 1. El cliente saluda, listamos categorias antes de mostrar ofertas
                    enviar_mensaje_whatsapp(
                        telefono_cliente,
                        "🤖 *SREPI Bot:*\n¡Hola! Elige una categoria para ver sus ofertas."
                    )
                    try:
                        categorias_por_id = obtener_categorias_por_id()
                    except HTTPException as he:
                        if he.status_code == 503:
                            enviar_mensaje_whatsapp(
                                telefono_cliente,
                                "⚠️ No pudimos obtener las categorias en este momento. Intenta de nuevo en unos minutos."
                            )
                            return {"status": "success"}
                        raise
                    
                    if not categorias_por_id:
                        enviar_mensaje_whatsapp(
                            telefono_cliente,
                            "⚠️ No hay categorias disponibles por ahora."
                        )
                        return {"status": "success"}

                    respuesta = "🤖 *SREPI Bot:*\nEstas son las categorias disponibles:\n\n"
                    for categoria_id, nombre in categorias_por_id.items():
                        respuesta += f"🟢 *{categoria_id}* - {nombre}\n"
                    respuesta += "\nResponde con el *numero de la categoria* para ver ofertas."
                    enviar_mensaje_whatsapp(telefono_cliente, respuesta)

                    BOT_ESTADOS[telefono_cliente] = {
                        "estado": ESTADO_ESPERANDO_CATEGORIA
                    }
                
                elif texto_mensaje == "mas":
                    estado_actual = BOT_ESTADOS.get(telefono_cliente, {}).get("estado")
                    if estado_actual != ESTADO_ESPERANDO_MAS:
                        enviar_mensaje_whatsapp(
                            telefono_cliente,
                            "🤖 No tengo mas ofertas pendientes. Escribe *ofertas* para ver categorias."
                        )
                        return {"status": "success"}

                    estado_bot = BOT_ESTADOS.get(telefono_cliente, {})
                    ofertas_filtradas = estado_bot.get("ofertas", [])
                    offset = int(estado_bot.get("offset", 0))

                    if offset >= len(ofertas_filtradas):
                        enviar_mensaje_whatsapp(
                            telefono_cliente,
                            "🤖 Ya no hay mas ofertas en esta categoria."
                        )
                        BOT_ESTADOS[telefono_cliente] = {
                            "estado": ESTADO_ESPERANDO_LOTE,
                            "categoria_id": estado_bot.get("categoria_id")
                        }
                        return {"status": "success"}

                    siguiente_bloque = ofertas_filtradas[offset:offset + MAX_OFERTAS_POR_MENSAJE]
                    respuesta_extra = "🤖 *SREPI Bot:*\nAqui hay mas ofertas:\n\n"
                    respuesta_extra += formatear_ofertas(siguiente_bloque)

                    nuevo_offset = offset + len(siguiente_bloque)
                    restantes = len(ofertas_filtradas) - nuevo_offset
                    if restantes > 0:
                        respuesta_extra += f"\n*(Quedan {restantes} ofertas mas en esta categoria.)*"
                    enviar_mensaje_whatsapp(telefono_cliente, respuesta_extra)

                    BOT_ESTADOS[telefono_cliente] = {
                        "estado": ESTADO_ESPERANDO_MAS if restantes > 0 else ESTADO_ESPERANDO_LOTE,
                        "categoria_id": estado_bot.get("categoria_id"),
                        "ofertas": ofertas_filtradas,
                        "offset": nuevo_offset
                    }

                elif texto_mensaje.isdigit():
                    estado_actual = BOT_ESTADOS.get(telefono_cliente, {}).get("estado")
                    if estado_actual == ESTADO_ESPERANDO_CATEGORIA:
                        categoria_id = int(texto_mensaje)
                        try:
                            categorias_por_id = obtener_categorias_por_id()
                        except HTTPException as he:
                            if he.status_code == 503:
                                enviar_mensaje_whatsapp(
                                    telefono_cliente,
                                    "⚠️ No pudimos consultar las categorias en este momento. Intenta de nuevo en unos minutos."
                                )
                                return {"status": "success"}
                            raise

                        if categoria_id not in categorias_por_id:
                            enviar_mensaje_whatsapp(
                                telefono_cliente,
                                "🤖 Categoria no valida. Escribe el numero de una categoria disponible."
                            )
                            return {"status": "success"}

                        categoria_nombre = categorias_por_id[categoria_id]
                        enviar_mensaje_whatsapp(
                            telefono_cliente,
                            f"🤖 Buscando ofertas para *{categoria_nombre}*..."
                        )

                        try:
                            ofertas = consultar_ofertas_disponibles()["ofertas_activas"]
                        except HTTPException as he:
                            if he.status_code == 503:
                                enviar_mensaje_whatsapp(
                                    telefono_cliente,
                                    "⚠️ No pudimos obtener ofertas disponibles en este momento. Intenta de nuevo en unos minutos."
                                )
                                return {"status": "success"}
                            raise

                        ofertas_filtradas = filtrar_ofertas_por_categoria(ofertas, categoria_nombre)
                        if not ofertas_filtradas:
                            enviar_mensaje_whatsapp(
                                telefono_cliente,
                                f"🤖 No hay ofertas activas en la categoria *{categoria_nombre}* por ahora."
                            )
                            return {"status": "success"}

                        primer_bloque = ofertas_filtradas[:MAX_OFERTAS_POR_MENSAJE]
                        respuesta = "🤖 *SREPI Bot:*\nEstas son las ofertas disponibles:\n\n"
                        respuesta += formatear_ofertas(primer_bloque)
                        enviar_mensaje_whatsapp(telefono_cliente, respuesta)

                        restantes = len(ofertas_filtradas) - len(primer_bloque)
                        if restantes > 0:
                            enviar_mensaje_whatsapp(
                                telefono_cliente,
                                "🤖 Escribe *mas* para ver mas ofertas de esta categoria."
                            )

                        BOT_ESTADOS[telefono_cliente] = {
                            "estado": ESTADO_ESPERANDO_MAS if restantes > 0 else ESTADO_ESPERANDO_LOTE,
                            "categoria_id": categoria_id,
                            "ofertas": ofertas_filtradas,
                            "offset": len(primer_bloque)
                        }
                    elif estado_actual == ESTADO_ESPERANDO_CANTIDAD:
                        estado_bot = BOT_ESTADOS.get(telefono_cliente, {})
                        id_lote = estado_bot.get("id_lote")
                        max_disponible = int(estado_bot.get("max_disponible", 0))
                        cantidad = int(texto_mensaje)

                        if not id_lote:
                            enviar_mensaje_whatsapp(
                                telefono_cliente,
                                "🤖 No tengo un lote seleccionado. Escribe *ofertas* para ver categorias."
                            )
                            return {"status": "success"}

                        if cantidad < 1 or cantidad > max_disponible:
                            enviar_mensaje_whatsapp(
                                telefono_cliente,
                                f"🤖 Cantidad no valida. Elige un numero entre 1 y {max_disponible}."
                            )
                            return {"status": "success"}

                        try:
                            resultado = confirmar_reserva(int(id_lote), telefono_cliente, cantidad)
                        except HTTPException as he:
                            if he.status_code == 503:
                                enviar_mensaje_whatsapp(
                                    telefono_cliente,
                                    "⚠️ No pudimos realizar la reserva en este momento. Intenta de nuevo en unos minutos."
                                )
                                return {"status": "success"}
                            raise

                        if "error" in resultado:
                            enviar_mensaje_whatsapp(telefono_cliente, f"🤖 *Error:* {resultado['error']}")
                        else:
                            if telefono_cliente in BOT_ESTADOS:
                                del BOT_ESTADOS[telefono_cliente]
                    else:
                        # 2. El cliente envía un número (ID de Lote), pedimos cantidad
                        id_lote = int(texto_mensaje)
                        estado_bot = BOT_ESTADOS.get(telefono_cliente, {})
                        ofertas = estado_bot.get("ofertas")

                        if ofertas is None:
                            try:
                                ofertas = consultar_ofertas_disponibles()["ofertas_activas"]
                            except HTTPException as he:
                                if he.status_code == 503:
                                    enviar_mensaje_whatsapp(
                                        telefono_cliente,
                                        "⚠️ No pudimos obtener ofertas disponibles en este momento. Intenta de nuevo en unos minutos."
                                    )
                                    return {"status": "success"}
                                raise

                        oferta_seleccionada = None
                        for oferta in ofertas:
                            if int(oferta.get("id_lote")) == id_lote:
                                oferta_seleccionada = oferta
                                break

                        if not oferta_seleccionada:
                            enviar_mensaje_whatsapp(
                                telefono_cliente,
                                "🤖 No encuentro ese lote en las ofertas activas. Intenta con otro ID."
                            )
                            return {"status": "success"}

                        disponibles = int(oferta_seleccionada.get("unidades_disponibles", 0))
                        max_permitido = min(MAX_UNIDADES_POR_PRODUCTO, disponibles)

                        if max_permitido <= 0:
                            enviar_mensaje_whatsapp(
                                telefono_cliente,
                                "🤖 Ese lote ya no tiene unidades disponibles. Elige otro producto."
                            )
                            return {"status": "success"}

                        enviar_mensaje_whatsapp(
                            telefono_cliente,
                            f"🤖 ¿Cuantas unidades deseas? (1-{max_permitido})"
                        )

                        BOT_ESTADOS[telefono_cliente] = {
                            "estado": ESTADO_ESPERANDO_CANTIDAD,
                            "categoria_id": estado_bot.get("categoria_id"),
                            "ofertas": ofertas,
                            "id_lote": id_lote,
                            "max_disponible": max_permitido
                        }
                
                else:
                    enviar_mensaje_whatsapp(telefono_cliente, "🤖 Escribe *ofertas* para ver categorias o el *numero* del producto que deseas.")
                    
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ Error procesando el Webhook: {e}")
        return {"status": "error"}

# --- MOTOR DDA Y GAMIFICACIÓN ---
def calcular_dda_y_gamificacion(precio_base, dias, multiplicador_xp, params=None):
    """Calcula el descuento según los dias y aplica el multiplicador de la categoría"""
    if params is None:
        params = DEFAULT_DDA_PARAMS
    dias_roja = params.get("dias_roja", 2)
    dias_amarilla = params.get("dias_amarilla", 3)
    desc_roja = params.get("desc_roja", 70.0) / 100
    desc_amarilla = params.get("desc_amarilla", 50.0) / 100
    desc_verde = params.get("desc_verde", 20.0) / 100
    xp_roja = params.get("xp_roja", 100)
    xp_amarilla = params.get("xp_amarilla", 50)
    xp_verde = params.get("xp_verde", 20)

    if dias <= dias_roja:
        descuento, xp_base = desc_roja, xp_roja
    elif dias <= dias_amarilla:
        descuento, xp_base = desc_amarilla, xp_amarilla
    else:
        descuento, xp_base = desc_verde, xp_verde

    precio_final = int(precio_base * (1 - descuento))
    xp_total = int(xp_base * multiplicador_xp)
    return precio_final, xp_total

def clasificar_riesgo_por_dias(dias, params=None):
    if params is None:
        params = DEFAULT_DDA_PARAMS
    if dias <= params.get("dias_roja", 2):
        return "roja"
    if dias <= params.get("dias_amarilla", 3):
        return "amarilla"
    return "verde"

def resumen_dashboard_vacio():
    return {
        "riesgo": {"roja": 0, "amarilla": 0, "verde": 0},
        "ventas": {"roja": 0, "amarilla": 0, "verde": 0, "total": 0},
        "recaudo": {"roja": 0, "amarilla": 0, "verde": 0, "total": 0}
    }

@app.get("/api/dashboard/resumen")
def obtener_dashboard_resumen():
    try:
        params = obtener_params_dda()
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        # Contar lotes realmente en riesgo desde Inventario_Lotes
        cursor.execute("""
            SELECT DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento)
            FROM Inventario_Lotes
            WHERE Cantidad_Disponible > 0
              AND DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento) >= 0
        """)
        riesgo = {"roja": 0, "amarilla": 0, "verde": 0}
        for fila in cursor.fetchall():
            dias = int(fila[0])
            zona = clasificar_riesgo_por_dias(dias, params)
            riesgo[zona] += 1

        cursor.execute("SELECT ID_Transaccion, ID_Lote, Precio_Pagado FROM SREPI_Reservas_Log")
        reservas = cursor.fetchall()

        cursor.execute("SELECT ID_Transaccion FROM Registro_Retiros")
        retiros = [fila[0] for fila in cursor.fetchall()]

        cursor.execute("SELECT ID_Lote, DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento) FROM Inventario_Lotes")
        dias_por_lote = {int(fila[0]): int(fila[1]) for fila in cursor.fetchall()}
        conn.close()

        reservas_por_transaccion = {}
        for fila in reservas:
            id_transaccion = fila[0]
            id_lote = int(fila[1])
            pagado = float(fila[2])
            reservas_por_transaccion[id_transaccion] = {
                "id_lote": id_lote,
                "pagado": pagado
            }

        ventas = {"roja": 0, "amarilla": 0, "verde": 0, "total": 0}
        recaudo = {"roja": 0, "amarilla": 0, "verde": 0, "total": 0}

        for id_transaccion in retiros:
            reserva = reservas_por_transaccion.get(id_transaccion)
            if not reserva:
                continue

            dias = dias_por_lote.get(reserva["id_lote"], 0)
            categoria = clasificar_riesgo_por_dias(dias, params)

            ventas[categoria] += 1
            ventas["total"] += 1

            recaudo[categoria] += reserva["pagado"]
            recaudo["total"] += reserva["pagado"]

        return {
            "riesgo": riesgo,
            "ventas": ventas,
            "recaudo": recaudo
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando dashboard: {str(e)}")

@app.get("/api/dashboard/operacion")
def obtener_dashboard_operacion():
    try:
        params = obtener_params_dda()
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COALESCE(SUM(rl.Precio_Pagado), 0),
                COALESCE(SUM(rl.XP_Otorgada), 0)
            FROM Registro_Retiros rr
            INNER JOIN SREPI_Reservas_Log rl ON rl.ID_Transaccion = rr.ID_Transaccion
        """)
        fila = cursor.fetchone()
        recaudo_total = float(fila[0]) if fila else 0.0
        xp_total = int(fila[1]) if fila else 0

        cursor.execute("""
            SELECT COUNT(*)
            FROM Registro_Retiros rr
            INNER JOIN SREPI_Reservas_Log rl ON rl.ID_Transaccion = rr.ID_Transaccion
            WHERE CAST(rl.Fecha_Reserva AS DATE) = CAST(GETUTCDATE() AS DATE)
        """)
        fila = cursor.fetchone()
        retiros_hoy = int(fila[0]) if fila else 0

        cursor.execute("""
            SELECT COALESCE(SUM(p.Peso_Kg), 0)
            FROM Registro_Retiros rr
            INNER JOIN SREPI_Reservas_Log rl ON rl.ID_Transaccion = rr.ID_Transaccion
            INNER JOIN Inventario_Lotes il ON il.ID_Lote = rl.ID_Lote
            INNER JOIN Productos p ON p.SKU = il.SKU
        """)
        fila = cursor.fetchone()
        desperdicio_kg = float(fila[0]) if fila else 0.0

        cursor.execute("""
            SELECT
                CAST(rl.Fecha_Reserva AS DATE) as fecha,
                COUNT(*) as cantidad
            FROM Registro_Retiros rr
            INNER JOIN SREPI_Reservas_Log rl ON rl.ID_Transaccion = rr.ID_Transaccion
            WHERE rl.Fecha_Reserva >= DATEADD(day, -6, CAST(GETUTCDATE() AS DATE))
            GROUP BY CAST(rl.Fecha_Reserva AS DATE)
            ORDER BY fecha
        """)
        retiros_por_dia = {str(fila[0]): int(fila[1]) for fila in cursor.fetchall()}

        cursor.execute("""
            SELECT DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento)
            FROM Inventario_Lotes
            WHERE Cantidad_Disponible > 0
              AND DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento) >= 0
        """)
        riesgo = {"roja": 0, "amarilla": 0, "verde": 0}
        for fila in cursor.fetchall():
            dias = int(fila[0])
            zona = clasificar_riesgo_por_dias(dias, params)
            riesgo[zona] += 1

        cursor.execute("""
            SELECT TOP 20
                rl.ID_Transaccion,
                rr.Telefono_Usuario,
                p.Nombre,
                p.Precio_Base,
                rl.Precio_Pagado,
                rl.XP_Otorgada,
                rl.Fecha_Reserva,
                rl.Cantidad
            FROM Registro_Retiros rr
            INNER JOIN SREPI_Reservas_Log rl ON rl.ID_Transaccion = rr.ID_Transaccion
            INNER JOIN Inventario_Lotes il ON il.ID_Lote = rl.ID_Lote
            INNER JOIN Productos p ON p.SKU = il.SKU
            ORDER BY rl.Fecha_Reserva DESC
        """)
        transacciones_raw = cursor.fetchall()
        conn.close()

        dias_nombres = ["Dom", "Lun", "Mar", "Mie", "Jue", "Vie", "Sab"]
        hoy = datetime.utcnow().date()
        chart_labels = []
        chart_data = []
        for i in range(6, -1, -1):
            fecha = hoy - timedelta(days=i)
            dia_nombre = dias_nombres[(fecha.weekday() + 1) % 7]
            chart_labels.append(dia_nombre)
            chart_data.append(retiros_por_dia.get(str(fecha), 0))

        transacciones = []
        for t in transacciones_raw:
            precio_base = float(t[3])
            precio_pagado = float(t[4])
            fecha_str = str(t[6])[:10] if t[6] else "-"
            cantidad = int(t[7]) if t[7] is not None else 1
            transacciones.append({
                "id": str(t[0])[:8] + "...",
                "usuario": str(t[1]) if t[1] else "-",
                "producto": str(t[2]),
                "ahorro": round(max(0.0, (precio_base * cantidad) - precio_pagado), 2),
                "recaudo": round(precio_pagado, 2),
                "xp": int(t[5]),
                "fecha": fecha_str,
                "estado": "Retirado"
            })

        return {
            "kpis": {
                "recaudo": recaudo_total,
                "desperdicio_kg": round(desperdicio_kg, 3),
                "retiros_hoy": retiros_hoy,
                "xp_total": xp_total
            },
            "charts": {
                "retiros": {
                    "labels": chart_labels,
                    "data": chart_data
                },
                "riesgo": {
                    "labels": ["Zona Roja", "Zona Amarilla", "Zona Verde"],
                    "data": [riesgo["roja"], riesgo["amarilla"], riesgo["verde"]]
                }
            },
            "transacciones": transacciones
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando dashboard de operacion: {str(e)}")

@app.get("/api/inventario/resumen")
def resumen_inventario():
    try:
        params = obtener_params_dda()
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_lotes,
                COALESCE(SUM(Cantidad_Disponible), 0) as total_unidades,
                COALESCE(SUM(Cantidad_Inicial), 0) as total_inicial
            FROM Inventario_Lotes
            WHERE Cantidad_Disponible > 0
              AND DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento) >= 0
        """)
        fila = cursor.fetchone()
        total_lotes = int(fila[0]) if fila else 0
        total_unidades = int(fila[1]) if fila else 0

        cursor.execute("""
            SELECT DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento)
            FROM Inventario_Lotes
            WHERE Cantidad_Disponible > 0
              AND DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento) >= 0
        """)
        conteo = {"roja": 0, "amarilla": 0, "verde": 0}
        for f in cursor.fetchall():
            zona = clasificar_riesgo_por_dias(int(f[0]), params)
            conteo[zona] += 1

        cursor.execute("""
            SELECT COUNT(*)
            FROM Inventario_Lotes
            WHERE DATEDIFF(day, GETUTCDATE(), Fecha_Vencimiento) < 0
        """)
        fila = cursor.fetchone()
        vencidos = int(fila[0]) if fila else 0

        conn.close()
        return {
            "total_lotes": total_lotes,
            "total_unidades": total_unidades,
            "por_zona": conteo,
            "vencidos": vencidos
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en resumen de inventario: {str(e)}")


@app.get("/api/inventario/lotes")
def listar_inventario_lotes(
    zona: Optional[str] = Query(None),
    categoria_id: Optional[int] = Query(None),
    busqueda: Optional[str] = Query(None),
    incluir_vencidos: Optional[bool] = Query(False)
):
    try:
        params = obtener_params_dda()
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        filtros_sql = []
        if not incluir_vencidos:
            filtros_sql.append("DATEDIFF(day, GETUTCDATE(), L.Fecha_Vencimiento) >= 0")

        where_clause = ""
        if filtros_sql:
            where_clause = "WHERE " + " AND ".join(filtros_sql)

        cursor.execute(f"""
            SELECT
                L.ID_Lote,
                P.SKU,
                P.Nombre,
                C.Nombre AS Categoria,
                C.ID_Categoria,
                P.Precio_Base,
                P.Peso_Kg,
                L.Cantidad_Inicial,
                L.Cantidad_Disponible,
                L.Fecha_Ingreso,
                L.Fecha_Vencimiento,
                DATEDIFF(day, GETUTCDATE(), L.Fecha_Vencimiento) AS Dias_Para_Vencer
            FROM Inventario_Lotes L
            INNER JOIN Productos P ON P.SKU = L.SKU
            INNER JOIN Categorias C ON C.ID_Categoria = P.ID_Categoria
            {where_clause}
            ORDER BY Dias_Para_Vencer ASC
        """)
        filas = cursor.fetchall()
        conn.close()

        lotes = []
        for f in filas:
            dias = int(f[11]) if f[11] is not None else -9999
            zona_lote = clasificar_riesgo_por_dias(dias, params) if dias >= 0 else "vencido"
            nombre_cat = str(f[3])
            nombre_prod = str(f[2])
            sku = str(f[1])

            if zona and zona != "todos" and zona_lote != zona:
                continue
            if categoria_id is not None and int(f[4]) != categoria_id:
                continue
            if busqueda:
                term = busqueda.lower()
                if term not in nombre_prod.lower() and term not in sku.lower() and term not in nombre_cat.lower():
                    continue

            fecha_ingreso = str(f[9])[:10] if f[9] else "-"
            fecha_vencimiento = str(f[10])[:10] if f[10] else "-"

            lotes.append({
                "id_lote": int(f[0]),
                "sku": sku,
                "nombre": nombre_prod,
                "categoria": nombre_cat,
                "categoria_id": int(f[4]),
                "precio_base": float(f[5]),
                "peso_kg": float(f[6]),
                "cantidad_inicial": int(f[7]),
                "cantidad_disponible": int(f[8]),
                "fecha_ingreso": fecha_ingreso,
                "fecha_vencimiento": fecha_vencimiento,
                "dias_para_vencer": dias,
                "zona": zona_lote
            })

        return {"lotes": lotes, "total": len(lotes)}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando inventario: {str(e)}")


@app.get("/api/ofertas")
def consultar_ofertas_disponibles():
    ofertas_procesadas = []
    
    try:
        params = obtener_params_dda()
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
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
            dias = fila[7]
            
            # Pasamos los datos por el motor DDA
            precio_descuento, puntos_xp = calcular_dda_y_gamificacion(precio_base, dias, multiplicador_xp, params)
            
            ofertas_procesadas.append({
                "id_lote": id_lote,
                "sku": sku,
                "producto": f"{nombre} ({categoria})",
                "unidades_disponibles": cantidad,
                "vence_en_dias": dias,
                "precio_original": f"${precio_base:,.0f}",
                "precio_oferta": f"${precio_descuento:,.0f}",
                "recompensa_xp": puntos_xp
            })
            
        conn.close()
        return {"ofertas_activas": ofertas_procesadas}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando al ERP (SQL Server): {str(e)}")

# --- ENDPOINTS: CATEGORIAS Y PRODUCTOS ---
@app.get("/api/categorias")
def listar_categorias():
    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                c.ID_Categoria,
                c.Nombre,
                COALESCE(cfg.Multiplicador_XP, c.Multiplicador_XP, 1.0)
            FROM Categorias c
            LEFT JOIN DDA_Categoria_Config cfg ON cfg.ID_Categoria = c.ID_Categoria
            ORDER BY Nombre
        """)
        filas = cursor.fetchall()
        conn.close()

        categorias = [
            {
                "id": int(fila[0]),
                "nombre": fila[1],
                "multiplicador": float(fila[2])
            }
            for fila in filas
        ]

        return {"categorias": categorias}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando categorias: {str(e)}")


@app.get("/api/productos")
def listar_productos(categoria_id: Optional[int] = Query(None)):
    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        if categoria_id is None:
            cursor.execute("""
                SELECT
                    p.SKU,
                    p.ID_Categoria,
                    p.Nombre,
                    COALESCE(cfg.Descuento_Extra, 0)
                FROM Productos p
                LEFT JOIN DDA_Producto_Config cfg ON cfg.SKU = p.SKU
                ORDER BY Nombre
            """)
        else:
            cursor.execute("""
                SELECT
                    p.SKU,
                    p.ID_Categoria,
                    p.Nombre,
                    COALESCE(cfg.Descuento_Extra, 0)
                FROM Productos p
                LEFT JOIN DDA_Producto_Config cfg ON cfg.SKU = p.SKU
                WHERE p.ID_Categoria = %s
                ORDER BY Nombre
            """, categoria_id)

        filas = cursor.fetchall()
        conn.close()

        productos = [
            {
                "id": fila[0],
                "categoria_id": int(fila[1]),
                "nombre": fila[2],
                "descuento": float(fila[3])
            }
            for fila in filas
        ]

        return {"productos": productos}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando productos: {str(e)}")


class DDAConfigCategoria(BaseModel):
    id: int
    multiplicador: float


class DDAConfigProducto(BaseModel):
    id: str
    descuento: float


class DDAConfigPayload(BaseModel):
    categorias: List[DDAConfigCategoria] = []
    productos: List[DDAConfigProducto] = []


@app.post("/api/dda/config")
def guardar_config_dda(payload: DDAConfigPayload):
    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        for categoria in payload.categorias:
            cursor.execute(
                "SELECT Multiplicador_XP FROM DDA_Categoria_Config WHERE ID_Categoria = %s",
                (categoria.id,)
            )
            fila_actual = cursor.fetchone()
            valor_anterior = float(fila_actual[0]) if fila_actual else None

            cursor.execute("""
                IF EXISTS (SELECT 1 FROM DDA_Categoria_Config WHERE ID_Categoria = %s)
                    UPDATE DDA_Categoria_Config
                    SET Multiplicador_XP = %s, Fecha_Actualizacion = SYSUTCDATETIME()
                    WHERE ID_Categoria = %s
                ELSE
                    INSERT INTO DDA_Categoria_Config (ID_Categoria, Multiplicador_XP)
                    VALUES (%s, %s)
            """, (categoria.id, categoria.multiplicador, categoria.id, categoria.id, categoria.multiplicador))

            if valor_anterior is None or valor_anterior != categoria.multiplicador:
                cursor.execute("""
                    INSERT INTO DDA_Config_Historial (Tipo, Clave, Valor_Anterior, Valor_Nuevo)
                    VALUES (%s, %s, %s, %s)
                """, ("categoria", str(categoria.id), valor_anterior, categoria.multiplicador))

        for producto in payload.productos:
            cursor.execute(
                "SELECT Descuento_Extra FROM DDA_Producto_Config WHERE SKU = %s",
                (producto.id,)
            )
            fila_actual = cursor.fetchone()
            valor_anterior = float(fila_actual[0]) if fila_actual else None

            cursor.execute("""
                IF EXISTS (SELECT 1 FROM DDA_Producto_Config WHERE SKU = %s)
                    UPDATE DDA_Producto_Config
                    SET Descuento_Extra = %s, Fecha_Actualizacion = SYSUTCDATETIME()
                    WHERE SKU = %s
                ELSE
                    INSERT INTO DDA_Producto_Config (SKU, Descuento_Extra)
                    VALUES (%s, %s)
            """, (producto.id, producto.descuento, producto.id, producto.id, producto.descuento))

            if valor_anterior is None or valor_anterior != producto.descuento:
                cursor.execute("""
                    INSERT INTO DDA_Config_Historial (Tipo, Clave, Valor_Anterior, Valor_Nuevo)
                    VALUES (%s, %s, %s, %s)
                """, ("producto", producto.id, valor_anterior, producto.descuento))

        conn.commit()
        conn.close()

        return {"status": "success"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando configuracion DDA: {str(e)}")


@app.get("/api/dda/config")
def leer_config_dda():
    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ID_Categoria, Multiplicador_XP
            FROM DDA_Categoria_Config
            ORDER BY ID_Categoria
        """)
        categorias = [
            {"id": int(fila[0]), "multiplicador": float(fila[1])}
            for fila in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT SKU, Descuento_Extra
            FROM DDA_Producto_Config
            ORDER BY SKU
        """)
        productos = [
            {"id": fila[0], "descuento": float(fila[1])}
            for fila in cursor.fetchall()
        ]

        conn.close()

        return {"categorias": categorias, "productos": productos}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo configuracion DDA: {str(e)}")


@app.get("/api/dda/historial")
def leer_historial_dda(limit: int = Query(100)):
    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP (%s)
                ID_Historial,
                Tipo,
                Clave,
                Valor_Anterior,
                Valor_Nuevo,
                Fecha_Registro
            FROM DDA_Config_Historial
            ORDER BY Fecha_Registro DESC
        """, limit)

        historial = [
            {
                "id": int(fila[0]),
                "tipo": fila[1],
                "clave": fila[2],
                "valor_anterior": float(fila[3]) if fila[3] is not None else None,
                "valor_nuevo": float(fila[4]),
                "fecha": fila[5].isoformat()
            }
            for fila in cursor.fetchall()
        ]

        conn.close()

        return {"historial": historial}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo historial DDA: {str(e)}")

# --- ENDPOINT: GENERACIÓN DE RESERVA Y CÓDIGO QR ---
@app.post("/api/reservar/{id_lote}")
def confirmar_reserva(id_lote: int, telefono_usuario: str, cantidad: int = 1):
    """
    En un entorno de producción, aquí haríamos un UPDATE a SREPI_Reservas en SQL.
    Por ahora, generamos el Token JWT garantizando la validez offline.
    """
    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()
        
# Validamos que el lote exista y tenga stock
        cursor.execute("""
            SELECT P.Nombre, P.Precio_Base, DATEDIFF(day, GETUTCDATE(), L.Fecha_Vencimiento), L.Cantidad_Disponible
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
        dias = producto_db[2]
        disponibles = int(producto_db[3])

        if cantidad < 1 or cantidad > MAX_UNIDADES_POR_PRODUCTO:
            return {"error": f"Cantidad no valida. Maximo {MAX_UNIDADES_POR_PRODUCTO} unidades."}

        if cantidad > disponibles:
            return {"error": "No hay suficientes unidades disponibles para esa cantidad."}
        
        # Calculamos el precio final para meterlo en el QR (Asumimos multiplicador 1.0 por rapidez)
        precio_unitario, xp_unitaria = calcular_dda_y_gamificacion(precio_base, dias, 1.0)
        precio_pagado = int(precio_unitario * cantidad)
        xp_ganados = int(xp_unitaria * cantidad)

# Generamos el payload para el Kiosco Edge
        id_transaccion = str(uuid.uuid4())
        config_reserva = obtener_config_reserva()
        valor_reserva = int(config_reserva.get("valor", DEFAULT_RESERVA_VALOR))
        unidad_reserva = config_reserva.get("unidad", DEFAULT_RESERVA_UNIDAD)
        if unidad_reserva == "dias":
            expiracion = datetime.utcnow() + timedelta(days=valor_reserva)
        else:
            expiracion = datetime.utcnow() + timedelta(hours=valor_reserva)

        payload_qr = {
            "id_transaccion": id_transaccion,  # <--- SELLO DE SEGURIDAD ÚNICO
            "id_lote": id_lote,
            "usuario": telefono_usuario,
            "producto": nombre_prod,
            "cantidad": cantidad,
            "pagado": precio_pagado,
            "xp": xp_ganados,
            "exp": expiracion
        }
# Generamos el Token Criptográfico (JWT)
        token_reserva = jwt.encode(payload_qr, SECRET_KEY, algorithm="HS256")
        
        # Armamos el pie de foto (caption) que acompañará al Código QR
        etiqueta_tiempo = "dias" if unidad_reserva == "dias" else "horas"
        mensaje_pie_foto = (
            f"🎉 *¡Reserva Exitosa!*\n\n"
            f"📦 {nombre_prod}\n"
            f"🔢 Cantidad: {cantidad}\n"
            f"💵 Pagas: ${precio_pagado:,.0f}\n"
            f"⭐ Ganas: {xp_ganados} XP\n\n"
            f"Acércate al Punto Express SREPI y muestra este Código QR a la cámara para retirar tu producto. "
            f"Tienes {valor_reserva} {etiqueta_tiempo} antes de que la reserva expire."
        )
        
        # ¡Magia! Enviamos la imagen directamente al WhatsApp del cliente
        enviar_qr_whatsapp(telefono_usuario, token_reserva, mensaje_pie_foto)

        try:
            conn = obtener_conexion()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM SREPI_Reservas_Log WHERE ID_Transaccion = %s)
                        INSERT INTO SREPI_Reservas_Log (ID_Transaccion, ID_Lote, Precio_Pagado, XP_Otorgada, Cantidad)
                        VALUES (%s, %s, %s, %s, %s)
                """, (id_transaccion, id_transaccion, id_lote, precio_pagado, xp_ganados, cantidad))
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"⚠️ No se pudo registrar la reserva en el log: {e}")

        return {
            "status": "success",
            "cantidad": cantidad,
            "total": precio_pagado,
            "xp": xp_ganados
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la reserva: {str(e)}")
    
    # --- MODELO PARA RECIBIR LOS DATOS DEL KIOSCO ---
# --- MODELO PARA RECIBIR LOS DATOS DEL KIOSCO ---
class DatosRetiro(BaseModel):
    id_transaccion: str   # <--- Requerimos el UUID
    id_lote: int
    usuario: str
    xp_ganada: int
    cantidad: Optional[int] = None
    total_pagado: Optional[float] = None

# --- ENDPOINT: CONFIRMACIÓN DESDE EL KIOSCO EDGE ---
@app.post("/api/kiosco/confirmar-retiro")
def procesar_retiro(datos: DatosRetiro):
    try:
        conn = obtener_conexion()
        if not conn:
            raise HTTPException(status_code=503, detail="No se pudo conectar a la base de datos (timeout de conexion).")
        cursor = conn.cursor()

        # 1. VERIFICACIÓN DE SEGURIDAD: ¿Ya existe esta transacción?
        cursor.execute("SELECT ID_Transaccion FROM Registro_Retiros WHERE ID_Transaccion = %s", datos.id_transaccion)
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Este Código QR ya fue canjeado anteriormente.")

        # 2. Obtener nombre del producto y precio base para el mensaje
        cursor.execute("""
            SELECT P.Nombre, P.Precio_Base
            FROM Inventario_Lotes L
            INNER JOIN Productos P ON P.SKU = L.SKU
            WHERE L.ID_Lote = %s
        """, datos.id_lote)
        prod_fila = cursor.fetchone()
        nombre_producto = str(prod_fila[0]) if prod_fila else "Producto"
        precio_base = float(prod_fila[1]) if prod_fila else 0.0

        # 3. Registrar la transacción para quemar el QR
        cursor.execute(
            "INSERT INTO Registro_Retiros (ID_Transaccion, Telefono_Usuario) VALUES (%s, %s)",
            (datos.id_transaccion, datos.usuario)
        )

        cantidad = max(int(datos.cantidad or 1), 1)
        # 4. Descontar las unidades del lote
        cursor.execute("""
            UPDATE Inventario_Lotes
            SET Cantidad_Disponible = Cantidad_Disponible - %s
            WHERE ID_Lote = %s AND Cantidad_Disponible >= %s
        """, (cantidad, datos.id_lote, cantidad))

        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=400, detail="No hay stock suficiente para completar el retiro.")

        conn.commit()

        # 5. Obtener total pagado (desde el payload o el log de reservas)
        total_pagado = None
        if datos.total_pagado is not None:
            total_pagado = float(datos.total_pagado)
        else:
            try:
                cursor.execute(
                    "SELECT Precio_Pagado FROM SREPI_Reservas_Log WHERE ID_Transaccion = %s",
                    datos.id_transaccion
                )
                fila_total = cursor.fetchone()
                if fila_total:
                    total_pagado = float(fila_total[0])
            except Exception:
                pass

        # 6. Calcular XP total acumulada del usuario (incluyendo esta transacción)
        xp_acumulada = datos.xp_ganada
        try:
            cursor.execute("""
                SELECT COALESCE(SUM(rl.XP_Otorgada), 0)
                FROM Registro_Retiros rr
                INNER JOIN SREPI_Reservas_Log rl ON rl.ID_Transaccion = rr.ID_Transaccion
                WHERE rr.Telefono_Usuario = %s
            """, datos.usuario)
            fila_xp = cursor.fetchone()
            xp_acumulada = int(fila_xp[0]) + datos.xp_ganada if fila_xp else datos.xp_ganada
        except Exception:
            pass

        conn.close()

        # 7. Enviar confirmación por WhatsApp
        try:
            total_linea = f"💵 Total pagado: *${total_pagado:,.0f}*\n" if total_pagado is not None else ""
            mensaje_confirmacion = (
                f"✅ *¡Retiro Exitoso en SREPI!*\n\n"
                f"📦 Producto: *{nombre_producto}*\n"
                f"🔢 Cantidad retirada: *{cantidad}*\n"
                f"{total_linea}"
                f"⭐ XP ganada en este rescate: *{datos.xp_ganada} XP*\n"
                f"🏆 Tu XP total acumulada: *{xp_acumulada} XP*\n\n"
                f"¡Gracias por rescatar este producto y ayudar a reducir el desperdicio! 🌱"
            )
            enviar_mensaje_whatsapp(datos.usuario, mensaje_confirmacion)
        except Exception as e:
            print(f"⚠️ No se pudo enviar la confirmacion WhatsApp: {e}")

        return {"status": "success", "mensaje": "Inventario descontado exitosamente."}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")