# Prompts por fase para Antigravity – Quero APP (v2)

## Antes de empezar (una sola vez)
1. Haz primero los **pasos previos** de `PASOS_PREVIOS.md` (instalaciones, base de datos, `.env`).
2. Copia a la raíz del repo: `AGENTS.md`, `schema.sql`, `seed.sql`.
3. Abre la carpeta en Antigravity. Usa el modo **Planning** en cada fase y **revisa el plan antes de aprobarlo**.
4. Pega UN prompt por vez. No pases a la siguiente fase hasta probar la anterior y hacer commit.
5. Si el agente propone cambiar el esquema o agregar paquetes, no lo aceptes sin discutirlo en el equipo.

## Alcance
- **Primer avance (1 semana):** Fases 0 a 4. Web con los 3 roles (cliente, empleado, admin), preparada para la app.
- **Proyecto final:** Fases 5A, 5B y 5C (notificaciones, API con tokens y app). Son borradores: se revisan cuando llegue el momento.

Calendario sugerido del avance: Fase 0 día 1 · Fase 1 día 2 · Fase 2 días 3–4 · Fase 3 días 5–6 · Fase 4 día 7.

---

## Prompt de arranque (solo lectura, no escribe código)
```
Lee AGENTS.md y schema.sql completos, con especial atención a la sección 4b (preparación para la app).
No escribas código todavía.
Respóndeme: (1) un resumen de 10 líneas de lo que entendiste del sistema, (2) las reglas de negocio que consideras
más fáciles de implementar mal, (3) cualquier contradicción o ambigüedad que veas entre AGENTS.md y schema.sql,
(4) las dudas que necesitas resolver antes de la Fase 0. Espera mi respuesta.
```

---

## Fase 0 – Base del proyecto, login y esqueleto de API
```
Contexto: sigue AGENTS.md (incluida la sección 4b) y usa schema.sql como fuente de verdad. Esta es la Fase 0.

Objetivo: una app Flask que arranque, conecte a PostgreSQL, permita iniciar sesión por rol y deje listo el esqueleto para la app futura.

Haz:
1. Estructura de carpetas de AGENTS.md (sección 4, con servicios/ y api/), requirements.txt con versiones fijadas, .env.example y .gitignore para Python.
2. App factory, config desde .env (python-dotenv), módulo db.py con helpers para consultar y ejecutar con parámetros (psycopg 3).
3. manage.py con tres comandos: init-db (ejecuta schema.sql), cargar-ejemplo (ejecuta seed.sql) y crear-admin
   (pide nombre, correo y contraseña; guarda el hash; debe_cambiar_clave en FALSE para este primer admin).
4. Autenticación con Flask-Login: login por correo + contraseña, logout, /cambiar-clave obligatorio si debe_cambiar_clave,
   CSRF en todos los formularios.
5. **obtener_usuario_actual()** como única forma de saber quién es el usuario, y un decorador de roles (admin / empleado) que use SOLO esa función.
6. Blueprint api/ con: GET /api/v1/salud (devuelve {"ok": true, "datos": {"estado": "vivo"}}), un helper para respuestas JSON de éxito y de error
   con el formato de AGENTS.md 4b, y manejo de errores 401/403/404/500 en JSON bajo /api/ y en HTML fuera de /api/.
7. Layout base con Bootstrap 5, mobile-first, barra de navegación que cambia según el rol, mensajes flash.
8. Página de inicio pública mínima con botones "Reservar" y "Hacer pedido" (aún sin funcionar) y el nombre del local desde config_local.
9. README con los pasos para levantar el proyecto desde cero.

Criterio de terminado: creo la BD, corro init-db, cargar-ejemplo y crear-admin, inicio sesión, veo el menú según mi rol, /staff devuelve 403 o
redirige si no hay sesión y GET /api/v1/salud responde el JSON esperado. Prueba esto en el navegador y reporta.
Presenta el plan antes de programar.
```

---

## Fase 1 – Carta, configuración y personal
```
Contexto: AGENTS.md (incluida la sección 4b), schema.sql. Fases anteriores terminadas. Esta es la Fase 1.

Objetivo: que la carta, la configuración del local y el personal se puedan administrar desde la web.

Haz:
1. Carta pública /carta: platos por categoría, con los agotados (disponible = FALSE) marcados como "Agotado". No mostrar platos inactivos.
2. Carta del staff /staff/carta (admin y empleado): lista de platos con un INTERRUPTOR rápido de "disponible" y edición del precio.
   El interruptor llama a una ruta JSON (POST /api/v1/platos/<id>/disponible) y actualiza la fila sin recargar la página.
   La regla vive en app/servicios/. Solo el admin crea, edita y desactiva platos y categorías. Nunca borrar un plato: desactivarlo.
3. /admin/config (solo admin): formulario para editar config_local con todas las validaciones del esquema
   (aforo, mesas, personas por mesa, duración de estadía, franja, tolerancia, horario, días de anticipación, porcentaje reservable, datos de Yape).
   Mostrar ayuda breve en cada campo.
4. /admin/personal (solo admin): listar, crear (con contraseña inicial y debe_cambiar_clave en TRUE), desactivar y reactivar cuentas,
   y restablecer contraseña. Un admin no puede desactivarse a sí mismo.

Criterio de terminado: cambio el aforo en /admin/config y se guarda; apago un plato en /staff/carta y aparece "Agotado" en /carta;
creo un empleado, entra y es obligado a cambiar su clave. Prueba en el navegador y reporta.
Presenta el plan antes de programar.
```

---

## Fase 2 – Reservas (núcleo)
```
Contexto: AGENTS.md (sobre todo secciones 4b, 7, 9, 10 y 11) y schema.sql. Fases 0 y 1 terminadas. Esta es la Fase 2.

Objetivo: reservas completas, desde la solicitud del cliente hasta la pizarra digital del día.

Haz:
1. Formulario público /reservar: nombre, teléfono (9 dígitos), correo opcional, fecha, hora, personas, nota, consentimiento de datos.
   La hora se elige entre las franjas del horario del local, con semáforo (disponible / pocas mesas / lleno) calculado con fn_hay_cupo.
   Nunca mostrar números de capacidad al cliente. Reutilizar al cliente si el teléfono ya existe. Al enviar, crear la reserva en estado
   'pendiente', con código único generado por la app, y mostrar /reserva/<token> con su estado (se refresca sola).
2. Pizarra digital /staff/reservas con selector de día (hoy por defecto):
   - Los datos salen de GET /api/v1/reservas/dia?fecha=... (JSON con formato de AGENTS.md 4b). La página los pide con fetch cada ~10 s y se repinta.
   - Columnas por franja horaria con las reservas que ocupan esa franja; las que continúan desde antes se marcan "continúa".
   - Fila final por franja con personas, mesas, libres y cuál limita (usa fn_carga_dia; no reimplementes ese cálculo).
   - Panel aparte de "Solicitudes pendientes" (no cuentan para la capacidad).
   - Cada tarjeta: botones "Llegó" y "No vino", y menú ⋮ (WhatsApp, Llamar, Correo si hay, Ver detalle, Cambiar hora, Imprimir ticket).
   - Resaltar en rojo las reservas confirmadas que pasaron hora + tolerancia. No cambiar su estado solas.
3. Acciones del staff: confirmar, rechazar (con motivo) y cancelar solicitudes; crear una reserva desde el staff (nace confirmada);
   si no hay cupo, advertir y permitir forzar con confirmación explícita. Toda la lógica va en app/servicios/ y las rutas solo la llaman.
4. Cambiar hora en dos toques: misma reserva y código, guarda hora_anterior, valida con fn_hay_cupo excluyendo la propia reserva, advierte pero permite forzar.
5. Ticket de reserva imprimible (AGENTS.md sección 10) con QR y la línea "ANTES → AHORA" cuando hubo cambio, y botón Reimprimir.
6. Helper en utils.py para normalizar teléfonos y construir el enlace de WhatsApp (51 + 9 dígitos) con mensaje codificado (solo el enlace del menú ⋮).
7. Pruebas con pytest: transiciones de estado de reserva, normalización de teléfono, enlace de WhatsApp y que la ruta JSON del día devuelva el formato esperado.

Criterio de terminado: pido una reserva como cliente, aparece como pendiente; la confirmo como staff y se refleja en la fila de totales;
la muevo de hora y el ticket muestra el cambio; una reserva que no cabe me avisa y puedo forzarla. Prueba todo en el navegador y reporta.
Presenta el plan antes de programar.
```

---

## Fase 3 – Pedidos, cobro y cocina
```
Contexto: AGENTS.md (sobre todo secciones 4b, 8, 9 y 10) y schema.sql. Fases 0 a 2 terminadas. Esta es la Fase 3.

Objetivo: pedidos de recojo desde la web y pedidos en local desde el staff, con aceptación, cobro manual, cocina y ticket.

Haz:
1. Formulario público /pedir: lista de platos disponibles por categoría con cantidades, nombre, teléfono, correo opcional, nota y consentimiento.
   Crear un pedido tipo 'recojo' en estado 'pendiente' con precio_venta copiado de cada plato. Mostrar /pedido/<token>: estado, total y,
   cuando esté aceptado y por cobrar, las instrucciones de pago (datos de Yape de config_local). Se refresca solo.
2. Cola del staff /staff/pedidos con columnas: Pendientes · Por cobrar · En cocina · Listos. Los datos salen de GET /api/v1/pedidos/cola
   (JSON con formato de AGENTS.md 4b) y la página los pide con fetch cada ~10 s. Cada fila con menú ⋮ (WhatsApp, Llamar, Correo, Ver detalle, Imprimir ticket).
3. Detalle /staff/pedido/<id> (a donde apunta el QR del ticket): botones según el estado.
   - Pendiente: ajustar o quitar líneas, ACEPTAR o RECHAZAR (motivo obligatorio). Al aceptar, el detalle queda fijo.
   - Aceptado y por cobrar: registrar pago (monto por defecto = total, medio, referencia). No permitir pagar de más.
     Al quedar cobrado, un pedido 'recojo' pasa solo a 'en_preparacion'.
   - En preparación → Listo → Entregado. Cancelar mientras no esté entregado.
4. Crear un pedido en local desde el staff (cliente opcional, mesa como texto, platos y notas): nace 'en_preparacion', se puede cobrar en cualquier momento.
5. Pantalla /staff/cocina (datos de GET /api/v1/pedidos/cocina): pedidos en preparación en orden de llegada, con tiempo transcurrido y botón "Listo".
6. Todas las transiciones pasan por una sola función transicion_pedido en app/servicios/ que rechaza las inválidas y llena los tiempos.
7. Ticket de pedido imprimible con QR (AGENTS.md sección 10). Botón de impresión y Reimprimir.
8. Pruebas con pytest: todas las transiciones válidas e inválidas, que no se pague de más, que el total y cobrado de v_pedido_resumen sean correctos
   y que las rutas JSON de cola y cocina devuelvan el formato esperado.

Criterio de terminado: pido como cliente, el staff acepta, veo las instrucciones de pago, el staff registra el pago, el pedido pasa a cocina,
cocina lo marca listo y se entrega; un pedido con un plato agotado se puede ajustar antes de aceptar. Prueba todo en el navegador y reporta.
Presenta el plan antes de programar.
```

---

## Fase 4 – Cierre del primer avance
```
Contexto: AGENTS.md y schema.sql. Fases 0 a 3 terminadas. Esta es la Fase 4. NO se implementan notificaciones automáticas (son del proyecto final).

Objetivo: dejar el avance sólido, probado y listo para la demostración.

Haz:
1. Comando manage.py cargar-demo con datos de demostración creíbles: reservas en varios horarios (incluida una que no cabe y una pasada de tolerancia)
   y pedidos en todos los estados.
2. Revisa que cada ruta de /staff, /admin y /api exija el rol correcto, que ninguna respuesta de la API incluya password_hash, mensajes de error en claro,
   estados vacíos y que todo se vea bien en celular.
3. Verifica que ninguna regla de negocio esté escrita dentro de las plantillas o de las rutas (deben estar en app/servicios/ o en las funciones SQL).
4. (Opcional) manifest.webmanifest, iconos y las etiquetas necesarias para poder instalar la web en el celular.
5. README completo: instalar, configurar .env, crear la BD, correr, y una lista de comprobación para el día de la demostración
   (incluye "abrir la página unos minutos antes" si el hosting se duerme).
6. Informe final: qué quedó hecho, qué queda para el proyecto final, riesgos conocidos y deuda técnica.

Criterio de terminado: un recorrido completo de la demostración (reserva → confirmación → pizarra → pedido → cobro → cocina → entrega) sin errores. Prueba y reporta.
Presenta el plan antes de programar.
```

---

# PROYECTO FINAL (borradores: revisar cuando llegue el momento)

## Fase 5A – Notificaciones (correo y WhatsApp en un toque)
```
Contexto: AGENTS.md (sección 9 completa) y schema.sql. Avance terminado. Esta es la Fase 5A.

Haz:
1. Módulo notificaciones con una interfaz simple enviar(canal, destino, mensaje) y plantillas de mensaje en un solo archivo, en español, para:
   reserva confirmada, reserva rechazada, pedido aceptado (con total e instrucciones de pago), pedido rechazado (con motivo) y pedido listo.
2. Correo automático (SMTP del .env) al confirmar/rechazar una reserva y al aceptar/rechazar/dejar listo un pedido, solo si el cliente tiene correo.
   Envío en segundo plano; si falla, registrar 'fallida' con el error en la tabla notificacion y NO romper la acción del staff.
3. Después de cada una de esas acciones, un modal "Enviar confirmación por WhatsApp" con el mensaje listo y un botón que abre el enlace wa.me
   y registra la notificación como 'manual'.
4. Vista /staff/notificaciones (admin) con las últimas notificaciones y su estado, y un botón para reintentar las fallidas.

Criterio de terminado: confirmo una reserva con correo y llega el correo; el modal de WhatsApp abre el mensaje correcto; si apago el SMTP la acción
del staff sigue funcionando y la notificación queda como fallida. Prueba y reporta. Presenta el plan antes de programar.
```

## Fase 5B – API con tokens y documentación (para la app)
```
Contexto: AGENTS.md (secciones 4b y 6). Esta es la Fase 5B.

Objetivo: que la app pueda autenticarse y operar todo lo del staff por la API, sin cambiar las reglas.

Haz:
1. Login por token (por ejemplo JWT de acceso con vencimiento corto y renovación) en POST /api/v1/auth/login, y que obtener_usuario_actual()
   acepte sesión O token. El decorador de roles NO cambia.
2. Completar /api/v1/ con todo lo que hace el staff en la web: reservas (confirmar, rechazar, cancelar, llegó, no vino, cambiar hora, crear),
   pedidos (aceptar, rechazar, cobrar, cambiar estado, crear en local), carta (disponibilidad). Cada endpoint llama a app/servicios/.
3. Registro de dispositivos para notificaciones push (tabla nueva propuesta como script aparte, sin tocar schema.sql) y envío de un aviso al staff
   cuando llega una reserva o un pedido nuevo.
4. Documentación de la API (lista de endpoints con ejemplos) y pruebas de cada endpoint, incluidas las de permisos por rol.

Criterio de terminado: con un cliente HTTP, inicio sesión por token y hago un recorrido completo de reserva y de pedido. Prueba y reporta. Presenta el plan antes de programar.
```

## Fase 5C – App del staff (React Native con Expo)
```
Contexto: AGENTS.md y la documentación de la API de la Fase 5B. Esta es la Fase 5C. Es un proyecto aparte (carpeta quero-staff).

Objetivo: app Android para empleado y admin que consuma la API existente. NO reimplementes reglas de negocio en la app.

Haz:
1. Proyecto Expo con TypeScript. Login, almacenamiento seguro del token y cierre de sesión.
2. Pantallas de operación diaria: pizarra de reservas del día con totales por franja, cola de pedidos, cocina, detalle de reserva y de pedido con sus acciones,
   cobro y menú de contacto (WhatsApp, llamar). El admin además ve configuración y personal en una segunda etapa.
3. Notificaciones push al llegar una reserva o pedido nuevo (requiere una build de desarrollo; no funciona en Expo Go).
4. Manejo claro de errores de red y estados vacíos. Pantallas grandes y simples.
5. Instrucciones para generar el APK e instalarlo en los celulares del staff.

Criterio de terminado: en un celular real, recibo un aviso de pedido nuevo, lo acepto, lo cobro y lo paso a cocina. Prueba y reporta. Presenta el plan antes de programar.
```
