import requests
import time

URL_BASE = "http://127.0.0.1:8000/api"

def simular_chat_whatsapp():
    print("📱 [WhatsApp] - Chat con 'SREPI Bot'")
    print("-" * 40)
    print("🤖 SREPI Bot: ¡Hola! Soy tu asistente de rescate de alimentos.")
    print("🤖 SREPI Bot: Buscando productos próximos a vencer en tu sede más cercana...")
    time.sleep(1.5)

    # 1. El bot consulta el backend automáticamente
    try:
        respuesta_ofertas = requests.get(f"{URL_BASE}/ofertas")
        ofertas = respuesta_ofertas.json()["ofertas_activas"]
        
        print("\n🤖 SREPI Bot: ¡Encontré estas Cajas Sorpresa para ti hoy!")
        for oferta in ofertas:
            print(f"   🟢 ID: {oferta['id']} | {oferta['producto']}")
            print(f"      Antes: {oferta['precio_original']} -> AHORA: {oferta['precio_oferta']}")
            print(f"      ⏳ ¡Vence en {oferta['vence_en_horas']} horas! Ganas {oferta['recompensa_xp']} XP.")
            print("   ---")
            
    except Exception as e:
        print("🤖 SREPI Bot: Ups, parece que el servidor (ERP) está desconectado.")
        return

    # 2. Interacción con el usuario (El cliente responde en el chat)
    print("\n✍️  Tú: (Escribe el ID del producto que quieres rescatar, o 'salir')")
    seleccion = input(">> ")
    
    if seleccion.lower() == 'salir':
        print("🤖 SREPI Bot: ¡Entendido! Avísame si quieres rescatar alimentos luego.")
        return

    print("✍️  Tú: (Escribe tu número de teléfono para la reserva)")
    telefono = input(">> ")

    print("\n🤖 SREPI Bot: Procesando tu reserva...")
    time.sleep(1)

    # 3. El bot envía la confirmación al backend
    respuesta_reserva = requests.post(f"{URL_BASE}/reservar/{seleccion}?telefono_usuario={telefono}")
    
    if respuesta_reserva.status_code == 200:
        datos_reserva = respuesta_reserva.json()
        if "error" in datos_reserva:
            print(f"🤖 SREPI Bot: {datos_reserva['error']}")
        else:
            print("\n✅ 🤖 SREPI Bot:", datos_reserva["mensaje"])
            print("🤖 SREPI Bot:", datos_reserva["instrucciones"])
            print("\n[ CÓDIGO QR GENERADO - Listo para escanear en tienda ]")
            print("==================================================")
            print(datos_reserva["codigo_qr_jwt"])
            print("==================================================")
            print("📍 Dirígete al carril express del supermercado.")
    else:
        print("🤖 SREPI Bot: Hubo un problema comunicándonos con el sistema central.")

if __name__ == "__main__":
    simular_chat_whatsapp()