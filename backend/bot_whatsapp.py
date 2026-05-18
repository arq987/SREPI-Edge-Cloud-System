import requests
import time

URL_BASE = "http://127.0.0.1:8000/api"
MAX_OFERTAS_POR_MENSAJE = 10
MAX_UNIDADES_POR_PRODUCTO = 5

def filtrar_ofertas_por_categoria(ofertas, categoria_nombre):
    marcador = f"({categoria_nombre})"
    return [item for item in ofertas if marcador in item.get("producto", "")]

def imprimir_ofertas(ofertas):
    for oferta in ofertas:
        print(f"   🟢 ID: {oferta['id_lote']} | {oferta['producto']}")
        print(f"      📦 Disponibles: {oferta.get('unidades_disponibles', 0)} unidades")
        print(f"      Antes: {oferta['precio_original']} -> AHORA: {oferta['precio_oferta']}")
        print(f"      ⏳ ¡Vence en {oferta['vence_en_dias']} dias! Ganas {oferta['recompensa_xp']} XP.")
        print("   ---")

def simular_chat_whatsapp():
    print("📱 [WhatsApp] - Chat con 'SREPI Bot'")
    print("-" * 40)
    print("🤖 SREPI Bot: ¡Hola! Soy tu asistente de rescate de alimentos.")
    print("🤖 SREPI Bot: Primero elige una categoria para ver ofertas...")
    time.sleep(1.5)

    # 1. El bot consulta las categorias
    try:
        respuesta_categorias = requests.get(f"{URL_BASE}/categorias")
        categorias = respuesta_categorias.json()["categorias"]
        if not categorias:
            print("🤖 SREPI Bot: No hay categorias disponibles.")
            return

        print("\n🤖 SREPI Bot: Categorias disponibles:")
        for categoria in categorias:
            print(f"   🟢 {categoria['id']} - {categoria['nombre']}")
    except Exception as e:
        print("🤖 SREPI Bot: Ups, parece que el servidor (ERP) está desconectado.")
        return

    # 2. Interacción con el usuario (El cliente responde en el chat)
    print("\n✍️  Tú: (Escribe el ID de la categoria, o 'salir')")
    seleccion_categoria = input(">> ")
    
    if seleccion_categoria.lower() == 'salir':
        print("🤖 SREPI Bot: ¡Entendido! Avísame si quieres rescatar alimentos luego.")
        return

    if not seleccion_categoria.isdigit():
        print("🤖 SREPI Bot: Categoria no valida.")
        return

    categoria_id = int(seleccion_categoria)
    categoria_nombre = None
    for categoria in categorias:
        if categoria["id"] == categoria_id:
            categoria_nombre = categoria["nombre"]
            break

    if not categoria_nombre:
        print("🤖 SREPI Bot: Categoria no valida.")
        return

    # 3. Consultamos ofertas y filtramos por categoria
    try:
        respuesta_ofertas = requests.get(f"{URL_BASE}/ofertas")
        ofertas = respuesta_ofertas.json()["ofertas_activas"]
        ofertas_filtradas = filtrar_ofertas_por_categoria(ofertas, categoria_nombre)

        if not ofertas_filtradas:
            print(f"\n🤖 SREPI Bot: No hay ofertas activas en {categoria_nombre}.")
            return

        print("\n🤖 SREPI Bot: ¡Encontré estas Cajas Sorpresa para ti hoy!")
        imprimir_ofertas(ofertas_filtradas[:MAX_OFERTAS_POR_MENSAJE])

        if len(ofertas_filtradas) > MAX_OFERTAS_POR_MENSAJE:
            print("\n🤖 SREPI Bot: Escribe 'mas' para ver mas ofertas.")
            respuesta_mas = input(">> ").strip().lower()
            if respuesta_mas == "mas":
                print("\n🤖 SREPI Bot: Hay mas ofertas disponibles:")
                imprimir_ofertas(ofertas_filtradas[MAX_OFERTAS_POR_MENSAJE:MAX_OFERTAS_POR_MENSAJE * 2])
    except Exception as e:
        print("🤖 SREPI Bot: Ups, parece que el servidor (ERP) está desconectado.")
        return

    print("\n✍️  Tú: (Escribe el ID del producto que quieres rescatar, o 'salir')")
    seleccion = input(">> ")
    if seleccion.lower() == 'salir':
        print("🤖 SREPI Bot: ¡Entendido! Avísame si quieres rescatar alimentos luego.")
        return

    oferta_seleccionada = None
    for oferta in ofertas_filtradas:
        if str(oferta.get("id_lote")) == seleccion:
            oferta_seleccionada = oferta
            break

    if not oferta_seleccionada:
        print("🤖 SREPI Bot: Ese ID no está en las ofertas disponibles.")
        return

    disponibles = int(oferta_seleccionada.get("unidades_disponibles", 0))
    max_permitido = min(MAX_UNIDADES_POR_PRODUCTO, disponibles)
    if max_permitido <= 0:
        print("🤖 SREPI Bot: Ese lote ya no tiene unidades disponibles.")
        return

    print(f"✍️  Tú: (Escribe la cantidad a reservar, 1-{max_permitido})")
    cantidad = input(">> ")
    if not cantidad.isdigit():
        print("🤖 SREPI Bot: Cantidad no valida.")
        return
    cantidad = int(cantidad)
    if cantidad < 1 or cantidad > max_permitido:
        print("🤖 SREPI Bot: Cantidad fuera de rango.")
        return

    print("✍️  Tú: (Escribe tu número de teléfono para la reserva)")
    telefono = input(">> ")

    print("\n🤖 SREPI Bot: Procesando tu reserva...")
    time.sleep(1)

    # 3. El bot envía la confirmación al backend
    respuesta_reserva = requests.post(
        f"{URL_BASE}/reservar/{seleccion}?telefono_usuario={telefono}&cantidad={cantidad}"
    )
    
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