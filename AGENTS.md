# Quero APP – Contexto permanente para el agente

> Colocar este archivo en la RAÍZ del repositorio. El agente debe leerlo y respetarlo en cada tarea.
> La fuente de verdad del modelo de datos es `schema.sql` (en la raíz).

## 1. Qué estamos construyendo
Sistema web para gestionar **reservas** y **pedidos** de una pollería pequeña de Lima, Perú.
Es un proyecto universitario (UTP, Curso Integrador) con un cliente real (la dueña del local).
Debe estar **funcionando en ~1 semana**. El equipo (4 estudiantes) tiene que poder **explicar cada
parte del código en una sustentación**: prioriza código simple, legible y comentado en español.
Nada de abstracciones innecesarias ni patrones complejos.

**Alcance de la plataforma:** sistema **solo web** (adaptable a celular, tablet y computador, e instalable como PWA).
**No habrá app móvil nativa**: los requerimientos del APF se reescribieron como sistema web y la profesora lo aprobó.
Los tres roles usan la misma web desde cualquier dispositivo con navegador:
- **cliente:** páginas públicas (QR, reservar, pedir, seguimiento), sin cuenta;
- **empleado** y **admin:** panel con login. La web del staff funciona en cualquier equipo (si un celular se queda sin batería, se entra desde otro).

**Etapas:**
1. **Primer avance (1 semana):** Fases 0 a 4 de `PROMPTS_POR_FASE.md`.
2. **Proyecto final:** el mismo sistema + notificaciones (correo y WhatsApp en un toque), impresión automática en la tiquetera y,
   opcional, recepción de reservas por WhatsApp.

## 2. Principios no negociables
1. **El staff decide.** Ninguna reserva ni pedido remoto reduce capacidad, entra a cocina ni cambia de
   estado sin una acción explícita del personal. Las alertas son solo visuales; nada se libera ni se cancela solo.
   **El staff nunca queda bloqueado por el cupo ni por la tolerancia:** la app avisa, el staff decide.
2. **Cambiar lo mínimo los procesos del local.** La dueña hoy usa una pizarra, WhatsApp y tickets de una
   tiquetera. El sistema se adapta a eso.
3. **Lo calculado no se guarda** (totales, cupos, saldo): sale de vistas/funciones SQL o de consultas.
4. **Simple antes que completo.** Respeta la lista de "Fuera de alcance".
5. Todo valor propio del local (aforo, mesas, duración de estadía, horario, tolerancia) sale de la tabla
   `config_local`, nunca de constantes en el código.

## 3. Stack (no cambiar sin avisar)
- Python 3.11+, **Flask** (patrón app factory + blueprints).
- **PostgreSQL 16**, acceso con **psycopg 3** y **SQL explícito con parámetros** (sin ORM: `schema.sql` manda).
- Plantillas **Jinja2** + **Bootstrap 5** (CDN) + JavaScript vanilla mínimo. Sin frameworks de frontend ni build steps.
- Flask-Login (sesiones), Flask-WTF (solo para CSRF), `werkzeug.security` (hash de contraseñas), `python-dotenv` (lee el `.env`).
- `gunicorn` solo para el hosting (Linux); en Windows se desarrolla con el servidor de Flask.
- `qrcode` + `Pillow` (QR), `smtplib` o Flask-Mail (correo), `pytest` (pruebas).
- Dependencias fijadas en `requirements.txt`. No agregar paquetes sin avisar.

## 4. Estructura de carpetas
```
quero/
├── AGENTS.md  schema.sql  seed.sql  requirements.txt  .env.example  README.md  .gitignore
├── app/
│   ├── __init__.py          # create_app()
│   ├── config.py            # lee .env
│   ├── db.py                # conexión y helpers (consultar, ejecutar)
│   ├── auth/                # login, logout, cambiar clave, decorador por rol
│   ├── publico/             # inicio, carta, reservar, pedir, seguimiento (sin login)
│   ├── reservas/            # pizarra del día, detalle, cambiar hora, ticket
│   ├── pedidos/             # cola, cocina, cobro, ticket
│   ├── carta/               # gestión de platos (staff)
│   ├── admin/               # config del local y personal
│   ├── servicios/           # lógica de negocio (reglas, transiciones, cálculos), SIN depender de Flask
│   ├── api/                 # rutas JSON /api/v1/... (las usan los tableros de la propia web y, en el final, el agente de impresión)
│   ├── notificaciones/      # (proyecto final) correo, enlaces de WhatsApp, plantillas de mensajes
│   ├── templates/  static/
│   └── utils.py             # normalizar teléfono, generar códigos, formateo
├── migraciones/             # scripts SQL repetibles para bases ya creadas (NNN_nombre.sql)
├── tests/
└── manage.py                # comandos: init-db, cargar-ejemplo, crear-admin
```

## 4b. Servicios y API interna (obligatorio desde la Fase 0)
1. **La lógica de negocio vive en `app/servicios/`**: funciones que reciben datos y devuelven resultados o lanzan errores de negocio.
   Las rutas y las plantillas solo llaman a los servicios; nunca contienen reglas.
2. **Los datos de los tableros** (pizarra de reservas, cola de pedidos, cocina) salen de rutas JSON bajo `/api/v1/`
   (ej. `/api/v1/reservas/dia?fecha=2026-10-20`). Las páginas web las consumen con `fetch` para refrescarse solas:
   así esa API interna se prueba todos los días.
3. **Formato JSON uniforme:** éxito `{"ok": true, "datos": ...}`; error `{"ok": false, "error": {"codigo": "...", "mensaje": "..."}}`
   con el código HTTP correcto. Fechas en ISO 8601.
4. **La identidad del usuario se obtiene SOLO con `obtener_usuario_actual()`** (lee la sesión de Flask-Login). El decorador de roles usa esa función,
   nunca la sesión directamente.
5. **Las respuestas de la API nunca incluyen** `password_hash` ni datos de clientes que el usuario no deba ver.
6. **Instalable (Fase 4):** `manifest.webmanifest`, iconos y un service worker mínimo que NO guarda datos en caché (solo cumple con la instalación).
   Toda pantalla operativa pide siempre datos frescos al servidor.

## 5. Variables de entorno (`.env`, nunca se sube; subir solo `.env.example` con valores falsos)
`DATABASE_URL`, `SECRET_KEY`, `BASE_URL` (para los QR), `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_FROM`. Zona horaria de la app: `America/Lima`.

## 6. Roles y permisos
| Rol | Acceso |
|---|---|
| **admin** (dueña) | Todo lo del empleado + configuración del local + gestión de personal |
| **empleado** (recepción/mozo/cocina) | Reservas, pedidos, cocina, carta (cambiar disponibilidad y precio) |
| **cliente** | Sin cuenta. Solo rutas públicas. |
- Login único por correo + contraseña. Si `debe_cambiar_clave` es TRUE, obligar a `/cambiar-clave` antes de todo lo demás.
- Las cuentas del staff las crea el admin. Verificar el rol en el servidor en TODA ruta de `/staff` y `/admin`.

## 7. Reglas de negocio – Reservas
- Estados: `pendiente` → `confirmada` | `rechazada` | `cancelada`; `confirmada` → `llego` | `no_llego` | `cancelada`.
  Los estados finales no cambian.
- Reserva pedida por la web nace `pendiente` (NO cuenta para la capacidad). Reserva creada por el staff nace `confirmada`.
- Capacidad: cuentan solo `confirmada` y `llego`. **Cada reserva ocupa mesa un tiempo que depende de su tamaño**:
  de 1 a 3 personas `duracion_1_3_min` (30), de 4 a 7 `duracion_4_7_min` (60), de 8 en adelante `duracion_8_mas_min` (90),
  todos en `config_local`. La duración sale de la función SQL `fn_duracion_estadia(personas)`; no recalcular en Python.
  Mesas requeridas = personas / `personas_por_mesa`, redondeado hacia arriba (un grupo de 2 usa una mesa entera).
  Usar las funciones `fn_carga_dia` y `fn_hay_cupo` de `schema.sql`; no reimplementar esa lógica en Python.
- `porcentaje_reservable` limita cuánto del local pueden ocupar las reservas (el resto queda para walk-in). NULL = 100 %.
- **Cupo: la web bloquea, el staff solo recibe alertas.** En la web pública, `fn_hay_cupo` es un filtro duro (el cliente no ve el salón). Para el staff nunca bloquea:
  al confirmar o crear una reserva, o al cambiar su hora, si no hay cupo se muestra una advertencia clara y el staff puede **forzar** con una confirmación explícita;
  al forzar se guarda `reserva.excede_cupo = TRUE` (así se sabe después qué se forzó). Lo mismo si confirma una solicitud que vino de la web y ya no cabe.
- **Alertas de ocupación:** `fn_carga_dia` devuelve la columna `nivel` por franja: `ok`, `alerta` (ocupación ≥ `umbral_alerta_pct` de `config_local`, "a punto de superar")
  o `excedido` (se superó el límite de personas o de mesas). Usar ese valor para colorear (alerta en amarillo, excedido en rojo); no recalcularlo en Python.
  Los libres pueden salir negativos: mostrarlos en rojo, sin ocultarlos. Los **pedidos no se limitan** por aforo ni mesas.
- **Cambiar hora:** botón de dos toques. Misma reserva y mismo código; guardar la hora previa en `hora_anterior` (solo guarda el último cambio);
  validar con `fn_hay_cupo(..., p_excluir_reserva => id)`; advertir pero permitir forzar (y marcar `excede_cupo` si se fuerza).
  **Se permite aunque ya haya pasado la tolerancia**, mientras la reserva siga `confirmada`.
- **Tolerancia:** si una reserva sigue `confirmada` pasada `hora + tolerancia_min`, resaltarla en rojo. Es solo una alerta: no cambia su estado sola ni impide ninguna acción.
  El staff decide, desde esa misma tarjeta: **liberar** (marcar `no_llego`, que libera el cupo) o **cambiar la hora** si el cliente avisa que quiere otra.
  `no_llego` es final: si el cliente aparece después, el staff crea una reserva nueva (el índice único ignora las `no_llego`).
- Validaciones públicas: fecha entre hoy y hoy + `dias_max_anticipacion`; hora dentro del horario; personas ≥ 1 y ≤ aforo;
  teléfono de 9 dígitos que empiece en 9 (obligatorio); correo opcional; consentimiento de datos obligatorio.
  **No se pide documento de identidad (DNI, CE ni pasaporte):** es un dato personal sin uso en el MVP.
- **Identidad del cliente:** el teléfono es la llave (única). El correo NO es único; nunca fusionar fichas de clientes automáticamente. Sin cuenta, sin contraseña, sin login de cliente.
- **No se verifica el contacto con códigos (ni SMS ni correo).** Decisión del equipo: el teléfono es obligatorio y el correo es opcional.
  Un número ajeno no le sirve a quien lo escribe: los pedidos de recojo no entran a cocina ni se imprimen hasta que el staff los acepta y confirma el pago real,
  y las reservas web nacen `pendiente` (no reducen capacidad) hasta que el staff las confirma. Antes de confirmar una reserva web, el staff puede escribir al cliente
  por WhatsApp (menú ⋮) para comprobar que el número es suyo.
- **Si el teléfono ya existe**, reutilizar la ficha del cliente y NO sobrescribir su nombre ni su correo con lo que llegó en el formulario.
- **Tope de reservas web por teléfono:** una reserva pedida por la web se rechaza con un mensaje claro si ese cliente ya tiene `max_reservas_web_por_telefono`
  (de `config_local`, por defecto 2) reservas web activas creadas en las últimas 24 h (`v_cliente_actividad_24h.reservas_web_24h`). El staff no tiene tope.
  Es el único bloqueo por actividad; para los pedidos solo hay aviso.
- **Actividad repetida:** `v_cliente_actividad_24h` (pedidos y reservas de las últimas 24 h, sin contar rechazados ni cancelados). Si el cliente de una solicitud web ya tiene
  actividad reciente, mostrar al staff una insignia "ya pidió hace menos de 24 h" en esa solicitud. Es solo un aviso: no bloquea ni rechaza nada (el staff decide).
- Al cliente nunca se le muestran números de capacidad. Solo un semáforo por hora: *disponible / pocas mesas / lleno*
  (usar la constante `PORC_POCAS = 25` de `config.py` como valor de ejemplo ajustable).
- Un cliente no puede tener dos reservas activas a la misma fecha y hora (ya lo garantiza un índice único; mostrar el error en claro).

## 8. Reglas de negocio – Pedidos y pagos
- Dos tipos: `local` (cliente presente, lo registra el staff; `cliente_id` puede ir vacío) y `recojo` (lo pide el cliente por la web; exige cliente).
- Estados: `pendiente` → `aceptado` | `rechazado` | `cancelado`; `aceptado` → `en_preparacion` | `cancelado`;
  `en_preparacion` → `listo` | `cancelado`; `listo` → `entregado`. Centralizar las transiciones en UNA función
  (`transicion_pedido`) que rechace las inválidas y llene `aceptado_en`, `preparacion_en`, `listo_en`, `entregado_en`.
- **Pedido `recojo`:** el staff revisa disponibilidad ANTES de cobrar. Puede quitar o ajustar líneas mientras está `pendiente`.
  Al aceptar, el monto queda fijo (el detalle ya no se edita). Rechazar exige `motivo_rechazo`.
- **Pago:** se registra en la tabla `pago` (monto, medio, referencia). Lo confirma SIEMPRE el staff, mirando el Yape/Plin real.
  El cliente puede adjuntar una captura de su pago como APOYO (tabla `comprobante_pago`), pero la captura nunca aprueba el pago ni
  mueve el pedido sola: puede estar editada. El staff abre su Yape, comprueba que llegó el monto exacto y recién ahí confirma.
  Confirmar = un solo botón, sin escribir el medio (se deduce: Yape si hay comprobante, efectivo si cobra en caja).
  No permitir pagar más que el total. `cobrado` sale de `v_pedido_resumen`.
- Un pedido `recojo` aceptado pasa a `en_preparacion` (cocina) solo cuando queda cobrado.
  Un pedido `local` creado por el staff nace `en_preparacion` y puede cobrarse en cualquier momento.
- `precio_venta` se copia del `precio` del plato al crear la línea. No se puede pedir un plato con `disponible = FALSE` o `activo = FALSE`.
- **Código del plato:** `plato.codigo` es un número corto, único y opcional que define la dueña (no es el `plato_id`). En "Nuevo pedido en local" se puede buscar por nombre,
  por categoría o escribiendo el número: el número muestra solo el plato cuyo código coincide exactamente (`1` no trae el 10 ni el 11). La carta pública puede mostrarlo junto al nombre.
  Los platos desactivados conservan su código reservado.
- **Platos con dos precios:** cada tamaño o presentación se registra como un plato aparte (por ejemplo "Ceviche de pescado — Personal" y "— Fuente"), con su precio y su código.
  Solo se crea una variante cuando cambia el precio; los sabores con el mismo precio van en la nota del pedido y los ingredientes en la descripción. No agregar una segunda columna de precio.
- El cliente sigue su pedido en `/pedido/<token>` (UUID, no el id). Esa página muestra estado, total, y las instrucciones de pago
  (datos Yape de `config_local`) cuando está `aceptado` y por cobrar.
- **Cocina:** cada pedido en preparación muestra el tiempo transcurrido desde `preparacion_en`. Si supera `umbral_preparacion_min` de `config_local`,
  se resalta en rojo (solo visual; no cambia su estado).
- **Orden en cocina:** en las columnas "En cocina" y "Listos" y en el tablero de cocina, los pedidos `recojo` van PRIMERO (el cliente espera afuera
  o avisa su llegada) y luego los `local`, cada grupo por hora de llegada. En "Pendientes" y "Por cobrar" el orden sigue siendo por llegada.
- **Mesa:** `mesa_referencia` es siempre opcional. Mostrarla solo si existe, sin repetir el texto ("Mesa 2", no "Mesa: Mesa 2").

## 9. Contacto (MVP) y notificaciones (proyecto final)
> **En el MVP se implementa:** el menú ⋮ de contacto (enlaces `wa.me`, `tel:` y `mailto:`, sin ninguna API) y las **alertas dentro del panel**
> (insignia con el número de solicitudes nuevas y aviso sonoro opcional; ver sección 11).
> El correo automático, el modal de WhatsApp, el uso de la tabla `notificacion` y las notificaciones push son del **proyecto final**: NO implementarlos todavía.
> El resto de esta sección queda como especificación para esa etapa.
- **Menú ⋮ en cada fila** de reservas y pedidos: WhatsApp (enlace `https://wa.me/51<9 dígitos>?text=<mensaje codificado>`),
  Llamar (`tel:+51...`), Correo (`mailto:`, solo si hay correo), Ver detalle, Imprimir ticket, y Cambiar hora (reservas).
- **Al confirmar/rechazar una reserva y al aceptar/rechazar/dejar listo un pedido:**
  1. Correo automático si el cliente tiene correo (envío en segundo plano; nunca bloquear ni romper la acción si falla).
  2. Un modal "Enviar confirmación por WhatsApp" con el mensaje ya redactado; al tocarlo se abre WhatsApp y se registra la notificación como `manual`.
- Todo envío se registra en la tabla `notificacion` (`enviada`, `fallida` con el error, o `manual`).
- El envío automático por WhatsApp (API oficial) queda FUERA del MVP. Dejar el envío detrás de una interfaz simple
  (`enviar(canal, destino, mensaje)`) para poder conectarlo después.

## 10. Tickets (impresión en tiquetera)
- Una sola plantilla para reservas y pedidos, con la etiqueta **RESERVA** o **PEDIDO** muy grande.
- Reserva: código, nombre, fecha, hora, personas, nota. Si hubo cambio, una línea "ANTES 1:00 pm → AHORA 2:00 pm".
- Pedido: número, nombre (si hay), tipo, platos × cantidad con notas, total y estado de cobro.
- Un **QR** con la dirección interna (`BASE_URL/staff/reserva/<id>` o `/staff/pedido/<id>`): lo escanea el staff con la cámara del celular
  y abre el detalle (pide login si hace falta) con los botones de acción.
- CSS `@media print` con ancho configurable (80 mm por defecto; variable CSS para cambiar a 58 mm), sin márgenes ni encabezados del navegador.

**Estrategia de impresión por niveles:**
1. **Nivel 1 (MVP): impresión manual** con `window.print()`: botones "Imprimir" y "Reimprimir".
2. **Nivel 2 (MVP; es configuración del equipo de la tiquetera, no código):** ese equipo abre Chrome o Edge con el parámetro `--kiosk-printing`
   y la tiquetera como impresora predeterminada; así `window.print()` imprime sin cuadro de confirmación (ver `GUIA_IMPRESION.md`).
   En la app: una casilla activable "Imprimir al pasar a cocina" que abre el ticket y llama a `window.print()`. Debe estar apagada por defecto.
3. **Nivel 3 (proyecto final): impresión automática desde el servidor** mediante un agente local en el equipo de la tiquetera. NO implementar ahora.
- El servidor NO puede imprimir directo en la tiquetera si está alojado en internet: no alcanza la red del local.
- Página `/staff/imprimir/prueba` con un ticket de prueba para calibrar ancho y márgenes.

## 11. Interfaz
- Español de Perú, moneda **S/**, fechas `dd/mm/aaaa`, horas en formato 12 h con am/pm, zona `America/Lima`.
- Mobile-first: las pantallas del staff se usan en celular o tablet. Botones grandes, pocas acciones por pantalla.
- Pizarra digital del día (reservas): una columna por franja horaria. **Cada reserva se dibuja completa SOLO en su franja de inicio**
  (nombre, código, personas, hora, hasta qué hora ocupa mesa, botones). En las franjas siguientes se muestra una línea compacta y apagada
  ("↳ Matías · 8 pax · continúa") sin botones; al tocarla se resalta la tarjeta original. La fila final de cada franja usa barras de progreso
  ("Personas 16/55", "Mesas 4/15") coloreadas según `nivel` (alerta / excedido) y muestra cuál recurso limita, con texto que no se corte en celular.
  Las reservas con `excede_cupo` llevan una marca visible. Las solicitudes `pendiente` van en un panel aparte.
- Los tableros se refrescan solos cada ~10 s con `fetch` (sin WebSockets).
- **Cocina (estilo Kanban):** tarjetas por pedido con temporizador; resaltado en rojo al superar `umbral_preparacion_min`; botón "Listo".
- **Alertas en el panel:** insignia con las solicitudes o pedidos nuevos y un sonido OPCIONAL. Los navegadores exigen un toque del usuario antes de
  reproducir audio, así que debe haber un botón "Activar sonido". Sonar solo cuando aparece algo nuevo respecto a la consulta anterior.
- **Pantalla de cocina:** pedir que la pantalla no se apague (Screen Wake Lock API) cuando el navegador lo permita.
- **Sin conexión no se opera. No hay modo offline.** Si falla la conexión (evento `offline` o error de `fetch`), mostrar el banner "Sin conexión: no se puede operar"
  y deshabilitar los botones de acción (atributo `data-requiere-conexion`). Al volver la red, quitar el banner y refrescar. No guardar borradores locales.

## 12. Seguridad (obligatorio)
Consultas SIEMPRE parametrizadas · CSRF en todos los formularios · contraseñas con hash · autoescape de Jinja activo ·
validar todo en el servidor · tokens UUID en URLs públicas · formularios públicos con campo trampa (honeypot) · sin secretos en el repo.
Subidas de archivos: máximo 5 MB; aceptar solo imágenes JPEG, PNG o WebP verificadas por su contenido real (no por la extensión);
reconvertirlas y quitarles los metadatos; guardarlas en la base de datos (columna BYTEA), nunca en el disco ni en `static/`; los comprobantes solo los puede ver el staff y se borran pasados 30 días del cierre del pedido.

## 13. Fuera de alcance del MVP (no implementar)
Ingresos y egresos, trabajadores y sueldos, delivery, reportes, lista de espera walk-in por QR, tabla de mesas físicas,
bitácora, pagos automáticos con Yape/Plin, notificaciones automáticas (correo, WhatsApp por API, push), verificación del contacto por código (SMS o correo), impresión automática desde el servidor,
recepción de reservas por WhatsApp, modo sin conexión, cuentas de cliente y app móvil (descartada).

## 14. Forma de trabajar
1. Antes de programar cada fase: presenta un plan de implementación y espera aprobación.
2. Haz commits pequeños y descriptivos, uno por funcionalidad.
3. Al terminar cada fase: levanta la app, **prueba los flujos en el navegador** y reporta qué funciona, qué falta y qué dudas quedan.
4. Los cambios de base de datos se hacen en scripts repetibles dentro de `migraciones/` y, en las fases que lo indiquen explícitamente, también en `schema.sql`.
5. Comentarios en español, nombres de variables y funciones en español claro, sin abreviaturas raras.
6. Si algo no está definido aquí, **pregunta o propón una opción**; no inventes reglas del negocio.
