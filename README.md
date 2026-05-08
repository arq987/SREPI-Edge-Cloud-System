# SREPI — Sistema de Reduccion de Excedentes y Perdidas en Inventario

SREPI es una plataforma de gestion inteligente de inventarios perecederos para cadenas de supermercados. Combina un motor de descuentos dinamicos basado en vencimiento, gamificacion de usuarios por XP, un bot conversacional de WhatsApp y kioscos de autoretiro con soporte offline (Edge Computing).

---

## Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Stack Tecnologico](#stack-tecnologico)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Modulos y Funcionalidades](#modulos-y-funcionalidades)
   - [Motor DDA](#1-motor-dda--descuento-dinamico-adaptativo)
   - [Gamificacion XP](#2-gamificacion-xp)
   - [Bot de WhatsApp](#3-bot-de-whatsapp-conversacional)
   - [Kiosco Edge](#4-kiosco-edge--punto-de-retiro)
   - [Inventario y Lotes](#5-inventario-y-lotes)
   - [Dashboard de Operaciones](#6-dashboard-de-metricas-de-operacion)
   - [Red de Supermercado](#7-monitoreo-de-red-de-supermercado)
5. [API REST — Referencia de Endpoints](#api-rest--referencia-de-endpoints)
6. [Base de Datos](#base-de-datos)
7. [Configuracion del Entorno](#configuracion-del-entorno)
8. [Puesta en Marcha](#puesta-en-marcha)

---

## Arquitectura General

```
Usuario (WhatsApp)
        |
        v
Meta Cloud API  <-->  [Backend FastAPI]  <-->  Azure SQL (pymssql)
                             |
                        JWT firmado
                             |
                        Codigo QR
                             |
                    [Kiosco Edge HTML/JS]
                      (camara + scan)
                             |
                  /api/kiosco/confirmar-retiro
                             |
                   Descuenta stock en BD
                             +
                   WhatsApp de confirmacion
```

El administrador gestiona el sistema desde el panel web (`/frontend/views/`). Los usuarios finales interactuan exclusivamente via WhatsApp — reciben ofertas, hacen reservas, obtienen un QR y lo presentan en el kiosco fisico para retirar su producto.

---

## Stack Tecnologico

| Capa | Tecnologia |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Base de datos | Azure SQL (Microsoft SQL Server), pymssql |
| Autenticacion QR | PyJWT (HS256) |
| Mensajeria | Meta Cloud API v17.0 (WhatsApp Business) |
| Frontend | HTML5, CSS3, JavaScript (Vanilla) |
| Fuentes | Space Grotesk, DM Serif Display (Google Fonts) |
| QR generation | api.qrserver.com (imagen dinamica via URL) |

---

## Estructura del Proyecto

```
SREPI/
├── backend/
│   ├── backend_srepi.py      # API principal FastAPI (todos los endpoints)
│   ├── bot_whatsapp.py       # Logica auxiliar del bot (legacy)
│   ├── validador_edge.py     # Validacion de tokens JWT en el kiosco
│   └── requirements.txt
├── database/
│   └── migrations/
│       ├── V001__creacion_schema.sql      # Tablas base: Categorias, Productos, Inventario_Lotes, Registro_Retiros
│       ├── V002__dda_config.sql           # DDA_Categoria_Config, DDA_Producto_Config, DDA_Config_Historial
│       ├── V003__dashboard_reservas.sql   # sp_ObtenerLotesEnRiesgo, vistas de operacion
│       ├── V004__reserva_config.sql       # SREPI_Reserva_Config (tiempo de reserva global)
│       ├── V005__reservas_log_xp.sql      # SREPI_Reservas_Log (log de XP por transaccion)
│       └── V006__dda_params_config.sql    # DDA_Params_Config (umbrales globales del motor)
├── frontend/
│   ├── index.html                         # Landing page — 5 modulos
│   ├── css/
│   │   ├── style.css                      # Estilos globales (admin-shell, cards, badges)
│   │   └── dashboard.css
│   ├── js/
│   │   ├── admin.js                       # Logica del Motor DDA
│   │   ├── dashboard.js                   # Logica del Dashboard de Operaciones
│   │   ├── inventario.js                  # Logica del modulo de Inventario
│   │   └── kiosco.js                      # Logica del Kiosco Edge (camara, JWT, offline)
│   └── views/
│       ├── admin.html                     # Panel Motor DDA
│       ├── dashboard.html                 # Metricas de Operacion
│       ├── inventario.html                # Inventario y Lotes
│       ├── kiosco.html                    # Kiosco Edge (punto de retiro)
│       └── red.html                       # Monitoreo de Red de Supermercado
└── .env                                   # Variables de entorno (no subir a git)
```

---

## Modulos y Funcionalidades

### 1. Motor DDA — Descuento Dinamico Adaptativo

**Panel:** `frontend/views/admin.html` | **JS:** `frontend/js/admin.js`

El Motor DDA calcula automaticamente el precio de oferta y los puntos XP de cada lote de producto segun los dias restantes hasta su vencimiento. Los lotes se clasifican en tres zonas de riesgo:

| Zona | Color | Condicion (defecto) | Descuento (defecto) | XP (defecto) |
|---|---|---|---|---|
| Roja | Rojo | <= 2 dias | 70% | 100 XP |
| Amarilla | Amarbar | <= 3 dias | 50% | 50 XP |
| Verde | Verde | > 3 dias | 20% | 20 XP |

**Funcionalidades del panel:**

- **Parametros globales del motor** — Configuracion de umbrales de dias, porcentajes de descuento y XP base para cada zona. Guardado en `DDA_Params_Config` via `POST /api/dda/params`.
- **Multiplicador XP por categoria** — Cada categoria de producto puede tener un multiplicador independiente (ej: Lacteos x1.5, Panaderia x2.0). Guardado en `DDA_Categoria_Config`.
- **Descuento extra por producto (SKU)** — Cada SKU puede recibir un porcentaje adicional de descuento sobre el precio calculado. Guardado en `DDA_Producto_Config`.
- **Simulador de Vista Rapida** — Selector de producto + dias de anticipacion que calcula y muestra en tiempo real el precio final, el descuento aplicado y los XP que obtendria el usuario.
- **Chips de segmento activo** — Selector visual por zona (Roja / Amarilla / Verde) que filtra la lista de categorias y productos a configurar.
- **Historial de cambios** — Registro auditado de cada modificacion a los parametros DDA, con valor anterior y nuevo. Consultable via `GET /api/dda/historial`.
- **Tiempo de reserva global** — Configuracion del tiempo de validez del QR generado (en horas o dias). Guardado en `SREPI_Reserva_Config`.

---

### 2. Gamificacion XP

El sistema recompensa a los usuarios con puntos de experiencia (XP) por cada producto que rescatan antes de su vencimiento.

**Formula de calculo:**

```
XP_base     = zona_riesgo (100 / 50 / 20)
XP_ganada   = XP_base * multiplicador_categoria
```

El multiplicador global (`Multiplicador_XP` en `DDA_Params_Config`) puede escalar toda la recompensa del sistema.

**Acumulacion de XP:**

- Cada transaccion exitosa registra la XP en `SREPI_Reservas_Log.XP_Otorgada`.
- Al confirmar el retiro en el kiosco, el backend calcula la XP total acumulada del usuario (`SUM` de todas sus transacciones previas + la actual).
- El usuario recibe la XP acumulada en el mensaje de confirmacion de WhatsApp.

---

### 3. Bot de WhatsApp Conversacional

**Endpoint:** `POST /webhook` (Webhook de Meta Cloud API)

El bot atiende a los usuarios finales de forma completamente automatica via WhatsApp. El flujo conversacional es:

```
Usuario envia cualquier mensaje
    -> Bot responde con categorias disponibles (numeradas)

Usuario selecciona numero de categoria
    -> Bot lista ofertas activas de esa categoria con precio, descuento y XP

Usuario envia el ID de lote del producto que desea
    -> Bot confirma la reserva y envia el Codigo QR como imagen adjunta
    -> El QR es un JWT firmado con los datos de la transaccion

Usuario presenta el QR en el kiosco fisico
    -> Kiosco valida el JWT y confirma el retiro
```

**Funcionalidades del bot:**

- Listado dinamico de categorias desde la base de datos.
- Filtrado de ofertas por categoria seleccionada.
- Paginacion de ofertas (maximo 10 por mensaje) con opcion "Ver mas".
- Generacion de reserva y envio de QR como imagen directamente al chat.
- Mensaje de confirmacion de retiro exitoso con XP ganada y XP acumulada total.
- Manejo de estado por conversacion (diccionario `BOT_ESTADOS` en memoria).
- Fallback con mensaje de ayuda si el usuario envia algo inesperado.

**Envio de mensajes:**

- `enviar_mensaje_whatsapp(telefono, texto)` — Envia texto plano via Meta Graph API v17.0.
- `enviar_qr_whatsapp(telefono, token_jwt, caption)` — Genera una imagen QR dinamica (qrserver.com) y la envia como mensaje tipo `image` con pie de foto.
- Si `META_ACCESS_TOKEN` no esta configurado, las funciones simulan el envio imprimiendo en consola (modo desarrollo).

---

### 4. Kiosco Edge — Punto de Retiro

**Vista:** `frontend/views/kiosco.html` | **JS:** `frontend/js/kiosco.js`

El kiosco es una interfaz web que corre en el punto fisico de venta (computador o tablet en la caja). Activa la camara del dispositivo para leer el QR del cliente.

**Funcionalidades:**

- **Activacion de camara** — Usa `getUserMedia` + `jsQR` para escaneo continuo de QR desde el navegador, sin instalar aplicaciones.
- **Validacion del JWT** — Decodifica el token localmente usando la clave secreta (`SECRET_KEY`). Verifica firma y expiracion antes de proceder.
- **Extraccion de datos del QR** — Muestra al operador: nombre del producto, precio pagado, XP a otorgar y telefono del usuario.
- **Confirmacion de retiro** — Llama a `POST /api/kiosco/confirmar-retiro` para:
  - Verificar que el QR no haya sido canjeado antes (proteccion anti-doble uso por `ID_Transaccion` unico).
  - Descontar 1 unidad de `Inventario_Lotes.Cantidad_Disponible`.
  - Registrar la transaccion en `Registro_Retiros`.
  - Enviar mensaje de confirmacion de WhatsApp al usuario.
- **Modo Edge (offline)** — Si no hay conexion a internet, el kiosco guarda el retiro en `localStorage` y lo sincroniza automaticamente al recuperar conexion (`sincronizarPendientes()`).
- **Indicador de estado** — Badge visual que indica si el kiosco esta Online u Offline con detector de conectividad en tiempo real.
- **Proteccion de QR expirado** — Si el JWT esta vencido, muestra error inmediato sin intentar la transaccion.
- **Proteccion de QR ya canjeado** — El backend rechaza con HTTP 400 cualquier intento de reusar el mismo `ID_Transaccion`.

---

### 5. Inventario y Lotes

**Vista:** `frontend/views/inventario.html` | **JS:** `frontend/js/inventario.js`

Panel de consulta del inventario completo, con filtros y clasificacion por zona de riesgo DDA.

**Funcionalidades:**

- **KPIs de inventario** — Tarjetas con totales: lotes criticos (zona roja), lotes en alerta (zona amarilla), lotes saludables (zona verde) y cantidad total de lotes activos.
- **Tabla de lotes** — Columnas: SKU, Nombre, Categoria, Precio Base, Cantidad (inicial/disponible), Fecha Ingreso, Fecha Vencimiento, Dias para Vencer y Zona de Riesgo (badge coloreado).
- **Filtro por zona de riesgo** — Botones toggle: Todos / Critico / Alerta / Saludable.
- **Filtro por categoria** — Selector que carga dinamicamente las categorias desde la API.
- **Busqueda de texto libre** — Filtra por nombre de producto, SKU o categoria en tiempo real.
- **Ordenamiento** — Clic en encabezados de columna para ordenar ascendente/descendente.
- **Datos en tiempo real** — Consulta `GET /api/inventario/lotes` con los parametros de zona, categoria y busqueda activos.

---

### 6. Dashboard de Metricas de Operacion

**Vista:** `frontend/views/dashboard.html` | **JS:** `frontend/js/dashboard.js`

Panel de analisis de operacion con KPIs y grafico de tendencias.

**Funcionalidades:**

- **Resumen de operacion** — KPIs: total de retiros realizados, XP total distribuida, ahorro generado para los usuarios (precio base vs precio pagado), productos rescatados del desperdicio.
- **Grafico de tendencia** — Linea temporal de retiros por periodo usando Chart.js.
- **Tabla de ultimas transacciones** — Registro de los retiros mas recientes con: ID de transaccion, telefono del usuario, lote, producto, precio pagado, XP otorgada y fecha.
- **Boton de actualizar** — Recarga los datos desde el backend sin recargar la pagina.

---

### 7. Monitoreo de Red de Supermercado

**Vista:** `frontend/views/red.html`

Panel de estado de conectividad de todos los kioscos SREPI en los puntos fisicos de venta.

**Funcionalidades:**

- **Tarjetas por kiosco** — Una card por cada punto de venta configurado. Borde superior verde (online) o rojo (offline).
- **Informacion por kiosco** — Estado de conexion, ultima sincronizacion y cantidad de registros pendientes en modo Edge.
- **Indicador de estado del sistema** — Badge global que muestra si el sistema de sincronizacion central esta operativo.
- **Boton Ver Logs** — Para kioscos online, acceso al log de actividad.
- **Boton Forzar Ping** — Para kioscos offline, intenta forzar la reconexion y sincronizacion de registros pendientes.

---

## API REST — Referencia de Endpoints

### Ofertas y Reservas

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/api/ofertas` | Lista todos los lotes en riesgo con precio DDA y XP calculados |
| `POST` | `/api/reservar/{id_lote}?telefono_usuario={tel}` | Crea reserva, genera JWT y envia QR por WhatsApp |

### Kiosco Edge

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `POST` | `/api/kiosco/confirmar-retiro` | Valida QR, descuenta stock, registra retiro, envia WhatsApp de confirmacion |

### Inventario

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/api/inventario/resumen` | KPIs de inventario (conteo por zona) |
| `GET` | `/api/inventario/lotes` | Lista de lotes con filtros opcionales: `zona`, `categoria_id`, `busqueda` |

### Categorias y Productos

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/api/categorias` | Lista categorias con multiplicador XP vigente |
| `GET` | `/api/productos` | Lista productos con descuento extra (filtrable por `categoria_id`) |

### Motor DDA — Configuracion

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/api/dda/params` | Lee parametros globales del motor (umbrales, descuentos, XP) |
| `POST` | `/api/dda/params` | Guarda parametros globales del motor |
| `GET` | `/api/dda/config` | Lee multiplicadores de categorias y descuentos de productos |
| `POST` | `/api/dda/config` | Guarda configuracion de categorias y productos |
| `GET` | `/api/dda/historial` | Lee historial auditado de cambios en la configuracion |
| `GET` | `/api/dda/reserva-config` | Lee el tiempo de validez global de reservas |
| `POST` | `/api/dda/reserva-config` | Guarda el tiempo de validez global de reservas |

### Dashboard

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/api/dashboard/resumen` | KPIs globales de operacion |
| `GET` | `/api/dashboard/operacion` | Datos de transacciones para la tabla y grafico |

### WhatsApp Webhook

| Metodo | Endpoint | Descripcion |
|---|---|---|
| `GET` | `/webhook` | Verificacion del webhook por Meta (handshake inicial) |
| `POST` | `/webhook` | Recepcion de mensajes entrantes del bot de WhatsApp |

---

## Base de Datos

### Tablas principales

| Tabla | Descripcion |
|---|---|
| `Categorias` | Categorias de productos con multiplicador XP base |
| `Productos` | Catalogo de productos con SKU, nombre, precio base y categoria |
| `Inventario_Lotes` | Lotes de producto con fechas de ingreso/vencimiento y cantidad disponible |
| `Registro_Retiros` | Log de cada retiro confirmado (ID_Transaccion, Telefono_Usuario) |
| `SREPI_Reservas_Log` | Log de reservas generadas con precio pagado y XP otorgada por transaccion |
| `DDA_Categoria_Config` | Multiplicadores XP por categoria |
| `DDA_Producto_Config` | Descuentos extra por SKU |
| `DDA_Config_Historial` | Auditoria de cambios en la configuracion DDA |
| `DDA_Params_Config` | Parametros globales del motor: umbrales de dias, descuentos y XP por zona |
| `SREPI_Reserva_Config` | Configuracion global del tiempo de validez de reservas |

### Stored Procedure

| Nombre | Descripcion |
|---|---|
| `sp_ObtenerLotesEnRiesgo` | Devuelve lotes activos con stock > 0 y dias para vencer calculados |

---

## Configuracion del Entorno

Crear el archivo `.env` en la raiz del proyecto con las siguientes variables:

```env
# Base de datos Azure SQL
DB_SERVER=tu_servidor.database.windows.net
DB_USER=tu_usuario
DB_PASSWORD=tu_contrasena
DB_NAME=nombre_de_la_base

# JWT — clave secreta para firmar los QR
SECRET_KEY_JWT=una_clave_secreta_larga_y_aleatoria

# Meta (WhatsApp Business API)
VERIFY_TOKEN_META=token_de_verificacion_del_webhook
META_ACCESS_TOKEN=tu_token_de_acceso_permanente_de_meta
META_PHONE_ID=id_del_numero_de_telefono_de_meta
```

> Si `META_ACCESS_TOKEN` no esta configurado o tiene el valor por defecto, el sistema opera en **modo simulacion**: imprime los mensajes de WhatsApp en la consola del backend sin hacer llamadas reales a Meta.

---

## Puesta en Marcha

### 1. Instalar dependencias del backend

```bash
cd backend
pip install -r requirements.txt
```

### 2. Ejecutar las migraciones de base de datos

Aplicar los scripts SQL en orden en Azure SQL (Azure Portal o Azure Data Studio):

```
V001 → V002 → V003 → V004 → V005 → V006
```

### 3. Iniciar el servidor

```bash
uvicorn backend.backend_srepi:app --reload --host 0.0.0.0 --port 8000
```

La documentacion interactiva de la API queda disponible en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 4. Abrir el frontend

Abrir `frontend/index.html` directamente en el navegador o servirlo con cualquier servidor estatico. Las llamadas a la API apuntan por defecto a `http://localhost:8000`.

### 5. Configurar el Webhook de WhatsApp (produccion)

El endpoint `/webhook` debe ser accesible desde internet. En desarrollo usar un tunel como [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
```

Registrar la URL publica en el panel de Meta for Developers como Webhook URL, con el `VERIFY_TOKEN_META` definido en el `.env`.
