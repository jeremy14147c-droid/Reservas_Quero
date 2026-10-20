# Quero APP – Contexto permanente para el agente

> Colocar este archivo en la RAÍZ del repositorio. El agente debe leerlo y respetarlo en cada tarea.
> La fuente de verdad del modelo de datos es `schema.sql` (en la raíz).

## 1. Qué estamos construyendo
Sistema web para gestionar **reservas** y **pedidos** de una pollería pequeña de Lima, Perú.
Es un proyecto universitario (UTP, Curso Integrador) con un cliente real (la dueña del local).
Debe estar **funcionando en ~1 semana**. El equipo (4 estudiantes) tiene que poder **explicar cada
parte del código en una sustentación**: prioriza código simple, legible y comentado en español.
Nada de abstracciones innecesarias ni patrones complejos.

**Etapas:**
1. **Primer avance (1 semana):** web con Flask que ya incluye los 3 roles: cliente (público, sin cuenta), empleado y admin.
2. **Proyecto final:** la web del cliente se mantiene; el empleado y el admin usarán además una **app** (React Native con Expo)
   que consumirá la API JSON de este mismo servidor. La web del staff NO es provisional: se conserva como respaldo sin instalación
   (por ejemplo, si un celular se queda sin batería, se entra desde cualquier otro dispositivo con el navegador).
Por eso el MVP se construye **preparado para la app** (ver sección 4b).

## 2. Principios no negociables
1. **El staff decide.** Ninguna reserva ni pedido remoto reduce capacidad, entra a cocina ni cambia de
   estado sin una acción explícita del personal. Las alertas son solo visuales; nada se libera ni se cancela solo.
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
│   ├── api/                 # rutas JSON /api/v1/... (las usan los tableros web y, en el proyecto final, la app)
│   ├── notificaciones/      # (proyecto final) correo, enlaces de WhatsApp, plantillas de mensajes
│   ├── templates/  static/
│   └── utils.py             # normalizar teléfono, generar códigos, formateo
├── tests/
└── manage.py                # comandos: init-db, cargar-ejemplo, crear-admin
```

## 4b. Preparación para la app futura (obligatoria desde la Fase 0)
1. **La lógica de negocio vive en `app/servicios/`**: funciones que reciben datos y devuelven resultados o lanzan errores de negocio.
   Las rutas y las plantillas solo llaman a los servicios; nunca contienen reglas.
2. **Los datos de los tableros** (pizarra de reservas, cola de pedidos, cocina) salen de rutas JSON bajo `/api/v1/`
   (ej. `/api/v1/reservas/dia?fecha=2026-10-20`). Las páginas web las consumen con `fetch` para refrescarse solas:
   así la API se prueba todos los días y la app podrá usarla tal cual.
3. **Formato JSON uniforme:** éxito `{"ok": true, "datos": ...}`; error `{"ok": false, "error": {"codigo": "...", "mensaje": "..."}}`
   con el código HTTP correcto. Fechas en ISO 8601.
4. **La identidad del usuario se obtiene SOLO con `obtener_usuario_actual()`.** Hoy lee la sesión; en el proyecto final también leerá un
   token. El decorador de roles usa esa función, nunca la sesión directamente.
5. **Las respuestas de la API nunca incluyen** `password_hash` ni datos de clientes que el usuario no deba ver.
6. (Opcional, Fase 4) `manifest.webmanifest` e iconos para poder instalar la web en el celular.

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
- Capacidad: cuentan solo `confirmada` y `llego`. Cada reserva ocupa mesa durante `duracion_estadia_min`.
  Mesas requeridas = personas / `personas_por_mesa`, redondeado hacia arriba (un grupo de 2 usa una mesa entera).
  Usar las funciones `fn_carga_dia` y `fn_hay_cupo` de `schema.sql`; no reimplementar esa lógica en Python.
- `porcentaje_reservable` limita cuánto del local pueden ocupar las reservas (el resto queda para walk-in). NULL = 100 %.
- Al confirmar o crear una reserva sin cupo: mostrar advertencia clara; el staff puede **forzar** con una confirmación explícita.
- **Cambiar hora:** botón de dos toques. Misma reserva y mismo código; guardar la hora previa en `hora_anterior`;
  validar con `fn_hay_cupo(..., p_excluir_reserva => id)`; advertir pero permitir forzar.
- **Tolerancia:** si una reserva sigue `confirmada` pasada `hora + tolerancia_min`, resaltarla en rojo. No cambiar su estado sola.
- Validaciones públicas: fecha entre hoy y hoy + `dias_max_anticipacion`; hora dentro del horario; personas ≥ 1 y ≤ aforo;
  teléfono de 9 dígitos que empiece en 9; consentimiento de datos obligatorio.
- Al cliente nunca se le muestran números de capacidad. Solo un semáforo por hora: *disponible / pocas mesas / lleno*
  (usar la constante `PORC_POCAS = 25` de `config.py` como valor de ejemplo ajustable).
- Un cliente no puede tener dos reservas activas a la misma fecha y hora (ya lo garantiza un índice único; mostrar el error en claro).

## 8. Reglas de negocio – Pedidos y pagos
- Dos tipos: `local` (cliente presente, lo registra el staff; `cliente_id` puede ir vacío) y `recojo` (lo pide el cliente por la web; exige cliente).
- Estados: `pendiente` → `aceptado` | `rechazado` | `cancelado`; `aceptado` → `en_preparacion` | `cancelado`;
  `en_preparacion` → `listo` | `cancelado`; `listo` → `entregado`. Centralizar las transiciones en UNA función
  (`transicion_pedido`) que rechace las inválidas y llene `aceptado_en`, `listo_en`, `entregado_en`.
- **Pedido `recojo`:** el staff revisa disponibilidad ANTES de cobrar. Puede quitar o ajustar líneas mientras está `pendiente`.
  Al aceptar, el monto queda fijo (el detalle ya no se edita). Rechazar exige `motivo_rechazo`.
- **Pago:** se registra en la tabla `pago` (monto, medio, referencia). Lo confirma SIEMPRE el staff, mirando el Yape/Plin real.
  Nunca confiar en capturas subidas por el cliente. No permitir pagar más que el total. `cobrado` sale de `v_pedido_resumen`.
- Un pedido `recojo` aceptado pasa a `en_preparacion` (cocina) solo cuando queda cobrado.
  Un pedido `local` creado por el staff nace `en_preparacion` y puede cobrarse en cualquier momento.
- `precio_venta` se copia del `precio` del plato al crear la línea. No se puede pedir un plato con `disponible = FALSE` o `activo = FALSE`.
- El cliente sigue su pedido en `/pedido/<token>` (UUID, no el id). Esa página muestra estado, total, y las instrucciones de pago
  (datos Yape de `config_local`) cuando está `aceptado` y por cobrar.

## 9. Contacto (MVP) y notificaciones (proyecto final)
> **En el MVP solo se implementa el menú ⋮ de contacto** (enlaces `wa.me`, `tel:` y `mailto:`, que no necesitan ninguna API).
> El correo automático, el modal de WhatsApp y el uso de la tabla `notificacion` son del **proyecto final**: NO implementarlos todavía.
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
- CSS `@media print` con ancho configurable (80 mm por defecto; variable CSS para cambiar a 58 mm). Impresión con `window.print()`; botón "Reimprimir".

## 11. Interfaz
- Español de Perú, moneda **S/**, fechas `dd/mm/aaaa`, horas en formato 12 h con am/pm, zona `America/Lima`.
- Mobile-first: las pantallas del staff se usan en celular o tablet. Botones grandes, pocas acciones por pantalla.
- Pizarra digital del día (reservas): columnas por franja horaria con las reservas que ocupan esa franja (las que continúan desde
  antes se marcan "continúa"), y una fila final con personas, mesas, libres y cuál limita (`fn_carga_dia`). Las solicitudes
  `pendiente` van en un panel aparte, no en las columnas.
- Los tableros se refrescan solos cada ~10 s con `fetch` (sin WebSockets).

## 12. Seguridad (obligatorio)
Consultas SIEMPRE parametrizadas · CSRF en todos los formularios · contraseñas con hash · autoescape de Jinja activo ·
validar todo en el servidor · tokens UUID en URLs públicas · formularios públicos con campo trampa (honeypot) · sin secretos en el repo.

## 13. Fuera de alcance del MVP (no implementar)
Ingresos y egresos, trabajadores y sueldos, delivery, reportes, lista de espera walk-in por QR, tabla de mesas físicas,
bitácora, pagos automáticos con Yape/Plin, notificaciones automáticas (correo, WhatsApp por API, push), cuentas de cliente,
app móvil (es del proyecto final; en el MVP solo se deja lista la API, secc. 4b).

## 14. Forma de trabajar
1. Antes de programar cada fase: presenta un plan de implementación y espera aprobación.
2. Haz commits pequeños y descriptivos, uno por funcionalidad.
3. Al terminar cada fase: levanta la app, **prueba los flujos en el navegador** y reporta qué funciona, qué falta y qué dudas quedan.
4. No modifiques `schema.sql` sin avisar; si hace falta un cambio, propónlo como un script aparte.
5. Comentarios en español, nombres de variables y funciones en español claro, sin abreviaturas raras.
6. Si algo no está definido aquí, **pregunta o propón una opción**; no inventes reglas del negocio.
