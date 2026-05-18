import jwt

# La misma llave secreta configurada en la nube para verificar la firma
# (En un modelo de producción avanzado, el Edge usaría una clave pública asimétrica)
SECRET_KEY = "srepi_llave_secreta_edge"

def validador_kiosco_offline(token_escaneado):
    print("--- KIOSCO SREPI: Iniciando Validación Edge (MODO OFFLINE) ---")
    try:
        # El sistema decodifica el token y valida matemáticamente la firma
        # ¡Todo esto ocurre sin consultar a internet ni a la base de datos!
        payload = jwt.decode(token_escaneado, SECRET_KEY, algorithms=["HS256"])
        
        print("\n[ ✅ ÉXITO ] Firma JWT verificada. Código original e inalterado.")
        print("==================================================")
        print("              ENTREGA AUTORIZADA                  ")
        print("==================================================")
        print(f"👤 Cliente (Tel) : {payload['usuario']}")
        print(f"📦 Producto      : {payload['producto']}")
        if "cantidad" in payload:
            print(f"🔢 Cantidad      : {payload['cantidad']}")
        print(f"💵 Total a Pagar : ${payload['pagado']}")
        print(f"⭐ XP Otorgado   : {payload['xp']}")
        print("==================================================")
        print(">> Instrucción en pantalla: Entregar producto al cliente.\n")
        
    except jwt.ExpiredSignatureError:
        print("\n[ ❌ ERROR ] El código QR ha expirado. El tiempo de reserva (2 horas) terminó.")
    except jwt.InvalidTokenError:
        print("\n[ 🚨 ALERTA CRÍTICA ] Firma inválida. El código QR fue alterado o falsificado.")

if __name__ == "__main__":
    # --- SIMULACIÓN DEL ESCÁNER ÓPTICO ---
    # Reemplaza el texto entre comillas con el Token larguísimo que generaste en Swagger UI
    # Esto simula el momento exacto en que la cámara del kiosco lee la pantalla del celular
    token_qr_simulado = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c3VhcmlvIjoiMzAwMDI0IiwicHJvZHVjdG8iOiJNYW56YW5hcyB4NCIsInBhZ2FkbyI6MjQwMCwieHAiOjEwMCwiZXhwIjoxNzc3NjY0ODQ2fQ.Osd6P53QRgzIY4opFr0i9Wx8PGSGAZdZXXJMUr-s0_A"
    
    if token_qr_simulado == "PEGA_AQUÍ_EL_TOKEN_JWT_QUE_GENERASTE_EN_EL_PASO_ANTERIOR":
        print("⚠️ Atención: Debes pegar el token JWT en la variable 'token_qr_simulado' antes de ejecutar.")
    else:
        validador_kiosco_offline(token_qr_simulado)