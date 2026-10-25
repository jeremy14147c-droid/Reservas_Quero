# Prompts por fase para Antigravity – Quero APP (v3, solo web)

## Antes de empezar (una sola vez)
1. Haz primero los **pasos previos** de `PASOS_PREVIOS.md` (instalaciones, base de datos, `.env`).
2. Copia a la raíz del repo: `AGENTS.md`, `schema.sql` (la versión nueva), `seed.sql` (revisa que no inserte la columna `documento`, que ya no existe) (y deja `GUIA_IMPRESION.md` a mano para la Fase 4).
3. Abre la carpeta en Antigravity. Usa el modo **Planning** en cada fase y **revisa el plan antes de aprobarlo**.
4. Pega UN prompt por vez. No pases a la siguiente fase hasta probar la anterior y hacer commit.
5. Si el agente propone cambiar el esquema o agregar paquetes, no lo aceptes sin discutirlo en el equipo.

## Alcance
- **Sistema solo web** (adaptable a celular y computador, instalable como PWA). No hay app móvil.
- **Primer avance (1 semana):** Fases 0 a 4.
- **Proyecto final:** Fases 5A, 5B y 5C (notificaciones, impresión automática y reservas por WhatsApp). Son borradores: se revisan cuando llegue el momento.

Calendario sugerido del avance: Fase 0 día 1 · Fase 1 día 2 · Fase 2 días 3–4 · Fase 3 días 5–6 · Fase 4 día 7.

---

## Prompt de arranque (solo lectura, no escribe código)
```
Lee AGENTS.md y schema.sql completos. Este proyecto es un sistema SOLO WEB (sin app móvil), con cliente público sin cuenta
y empleado y admin con login. No escribas código todavía.
Respóndeme: (1) un resumen de 10 líneas de lo que entendiste del sistema, (2) las reglas de negocio que consideras
más fáciles de implementar mal, (3) cualquier contradicción o ambigüedad que veas entre AGENTS.md y schema.sql,
(4) las dudas que necesitas resolver antes de la Fase 0. Espera mi respuesta.
```

---

## Fase 0 – Base del proyecto, login y esqueleto de API interna
```
Contexto: sigue AGENTS.md (incluida la sección 4b) y usa schema.sql como fuente de verdad. Esta es la Fase 0.

Objetivo: una app Flask que arranque, conecte a PostgreSQL y permita iniciar sesión por rol.
Solo el personal tiene login (roles admin y empleado). El cliente NO tiene cuenta: usa páginas públicas.

Haz:
1. Estructura de carpetas de AGENTS.md (sección 4, con servicios/ y api/), requirements.txt con versiones fijadas, .env.example y .gitignore para Python.
2. App factory, config desde .env (python-dotenv), módulo db.py con helpers para consultar y ejecutar con parámetros (psycopg 3).
3. manage.py con tres comandos: init-db (ejecuta schema.sql), cargar-ejemplo (ejecuta seed.sql) y crear-admin
   (pide nombre, correo y contraseña; guarda el hash; debe_cambiar_clave en FALSE para este primer admin).
4. Autenticación con Flask-Login: login por correo + contraseña, logout, /cambiar-clave obligatorio si debe_cambiar_clave, CSRF en todos los formularios.
5. obtener_usuario_actual() como única forma de saber quién es el usuario, y un decorador de roles (admin / empleado) que use SOLO esa función.
6. Blueprint api/ con GET /api/v1/salud (devuelve {"ok": true, "datos": {"estado": "vivo"}}), un helper para respuestas JSON de éxito y error
   con el formato de AGENTS.md 4b, y manejo de errores 401/403/404/500 en JSON bajo /api/ y en HTML fuera de /api/.
7. Layout base con Bootstrap 5, mobile-first, barra de navegación que cambia según el rol, mensajes flash.
8. Script base en el layout para "sin conexión" (AGENTS.md sección 11): escucha los eventos online/offline y los fallos de fetch, muestra el banner
   "Sin conexión: no se puede operar" y deshabilita todo elemento con data-requiere-conexion. Sin modo offline ni borradores locales.
9. Página de inicio pública mínima con botones "Reservar" y "Hacer pedido" (aún sin funcionar) y el nombre del local desde config_local.
10. README con los pasos para levantar el proyecto desde cero.

Criterio de terminado: creo la BD, corro init-db, cargar-ejemplo y crear-admin, inicio sesión, veo el menú según mi rol, /staff devuelve 403 o
redirige si no hay sesión, GET /api/v1/salud responde el JSON esperado y al cortar el internet aparece el banner. Prueba esto en el navegador y reporta.
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
   (aforo, mesas, personas por mesa, duración de estadía, franja, tolerancia, umbral de preparación de cocina, umbral de alerta de ocupación (%), máximo de reservas web por teléfono en 24 h, horario, días de anticipación,
   porcentaje reservable, datos de Yape). Mostrar ayuda breve en cada campo.
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
   Nunca mostrar números de capacidad al cliente. En la web el cupo SÍ bloquea: una hora llena no se puede enviar. No pedir documento de identidad.
   Teléfono obligatorio y correo opcional; sin códigos de verificación. Reutilizar al cliente si el teléfono ya existe, sin sobrescribir su nombre ni su correo.
   Si ese teléfono ya tiene max_reservas_web_por_telefono reservas web activas en las últimas 24 h (v_cliente_actividad_24h.reservas_web_24h), rechazar con un mensaje claro.
   Si no, crear la reserva en estado 'pendiente', con código único generado por la app, y mostrar /reserva/<token> con su estado (se refresca sola).
2. Pizarra digital /staff/reservas con selector de día (hoy por defecto):
   - Los datos salen de GET /api/v1/reservas/dia?fecha=... (JSON con formato de AGENTS.md 4b). La página los pide con fetch cada ~10 s y se repinta.
   - Columnas por franja horaria con las reservas que ocupan esa franja; las que continúan desde antes se marcan "continúa".
   - Fila final por franja con personas, mesas, libres y cuál limita (usa fn_carga_dia; no reimplementes ese cálculo). Coloréala con la columna `nivel`:
     alerta (amarillo) y excedido (rojo); los libres negativos se muestran en rojo. Las reservas con excede_cupo = TRUE llevan una marca visible.
   - Panel aparte de "Solicitudes pendientes" (no cuentan para la capacidad). Si el cliente ya tiene actividad en las últimas 24 h (v_cliente_actividad_24h),
     la solicitud muestra una insignia de aviso.
   - Cada tarjeta: botones "Llegó" y "No vino", y menú ⋮ (WhatsApp, Llamar, Correo si hay, Ver detalle, Cambiar hora, Imprimir ticket).
   - Resaltar en rojo las reservas confirmadas que pasaron hora + tolerancia. No cambiar su estado solas ni bloquear nada: desde esa tarjeta el staff puede
     liberarla ("No vino") o cambiar su hora.
3. Alertas en el panel (AGENTS.md sección 11): insignia con el número de solicitudes pendientes nuevas y un sonido OPCIONAL con un botón
   "Activar sonido". Sonar solo cuando aparece una solicitud nueva respecto a la consulta anterior.
4. Acciones del staff: confirmar, rechazar (con motivo) y cancelar solicitudes; crear una reserva desde el staff (nace confirmada);
   si no hay cupo, advertir y permitir forzar con confirmación explícita, guardando excede_cupo = TRUE (también al confirmar una solicitud web que ya no cabe).
   El staff nunca queda bloqueado por el cupo. Toda la lógica va en app/servicios/ y las rutas solo la llaman.
5. Cambiar hora en dos toques: misma reserva y código, guarda hora_anterior, valida con fn_hay_cupo excluyendo la propia reserva, advierte pero permite forzar
   (marcando excede_cupo). Debe funcionar también cuando ya pasó la tolerancia, mientras la reserva siga confirmada.
6. Ticket de reserva imprimible (AGENTS.md sección 10, nivel 1) con QR y la línea "ANTES → AHORA" cuando hubo cambio, y botón Reimprimir.
7. Helper en utils.py para normalizar teléfonos y construir el enlace de WhatsApp (51 + 9 dígitos) con mensaje codificado (solo el enlace del menú ⋮).
8. Pruebas con pytest: transiciones de estado de reserva, normalización de teléfono, enlace de WhatsApp, que la ruta JSON del día devuelva el formato esperado
   (incluida la columna nivel), que el staff pueda forzar una reserva sin cupo y quede con excede_cupo = TRUE, que la web NO pueda reservar una hora llena
   que se pueda cambiar la hora de una reserva pasada de tolerancia, que la web rechace una reserva por encima del tope por teléfono y que el staff no tenga ese tope.

Criterio de terminado: pido una reserva como cliente, aparece como pendiente con alerta; la confirmo como staff y se refleja en la fila de totales;
la muevo de hora y el ticket muestra el cambio; una reserva que no cabe me avisa, puedo forzarla y queda marcada; una franja casi llena sale en amarillo y una excedida en rojo;
una reserva pasada de tolerancia la puedo liberar o moverle la hora; desde la web no puedo reservar una hora llena; con el mismo teléfono la web me rechaza al pasar el tope de reservas en 24 h; el staff puede seguir registrando; una segunda solicitud del mismo cliente en menos de 24 h sale con aviso. Prueba todo en el navegador y reporta.
Presenta el plan antes de programar.
```

---

## Fase 3 – Pedidos, cobro y cocina
```
Contexto: AGENTS.md (sobre todo secciones 4b, 8, 9, 10 y 11) y schema.sql. Fases 0 a 2 terminadas. Esta es la Fase 3.

Objetivo: pedidos de recojo desde la web y pedidos en local desde el staff, con aceptación, cobro manual, cocina y ticket.

Haz:
1. Formulario público /pedir: lista de platos disponibles por categoría con cantidades, nombre, teléfono, correo opcional, nota y consentimiento (sin códigos de verificación).
   Crear un pedido tipo 'recojo' en estado 'pendiente' con precio_venta copiado de cada plato. Mostrar /pedido/<token>: estado, total y,
   cuando esté aceptado y por cobrar, las instrucciones de pago (datos de Yape de config_local). Se refresca solo.
2. Cola del staff /staff/pedidos con columnas: Pendientes · Por cobrar · En cocina · Listos. Los datos salen de GET /api/v1/pedidos/cola
   (JSON con formato de AGENTS.md 4b) y la página los pide con fetch cada ~10 s. Cada fila con menú ⋮ (WhatsApp, Llamar, Correo, Ver detalle, Imprimir ticket).
   Alertas en el panel: insignia y sonido opcional cuando aparece un pedido pendiente nuevo, y la insignia "ya pidió hace menos de 24 h" (v_cliente_actividad_24h; solo aviso).
3. Detalle /staff/pedido/<id> (a donde apunta el QR del ticket): botones según el estado.
   - Pendiente: ajustar o quitar líneas, ACEPTAR o RECHAZAR (motivo obligatorio). Al aceptar, el detalle queda fijo.
   - Aceptado y por cobrar: registrar pago (monto por defecto = total, medio, referencia). No permitir pagar de más.
     Al quedar cobrado, un pedido 'recojo' pasa solo a 'en_preparacion' (se llena preparacion_en).
   - En preparación → Listo → Entregado. Cancelar mientras no esté entregado.
4. Crear un pedido en local desde el staff (cliente opcional, mesa como texto, platos y notas): nace 'en_preparacion', se puede cobrar en cualquier momento.
5. Tablero de cocina /staff/cocina estilo Kanban (datos de GET /api/v1/pedidos/cocina): tarjetas por pedido en orden de llegada con temporizador desde preparacion_en,
   resaltado en rojo al superar umbral_preparacion_min (solo visual), botón "Listo", y la pantalla se mantiene encendida con Screen Wake Lock cuando el navegador lo permita.
5b. Casilla opcional "Imprimir al pasar a cocina" (apagada por defecto) que abre el ticket del pedido y llama a window.print() (AGENTS.md sección 10, nivel 2).
6. Todas las transiciones pasan por una sola función transicion_pedido en app/servicios/ que rechaza las inválidas y llena aceptado_en, preparacion_en, listo_en y entregado_en.
7. Ticket de pedido imprimible con QR (AGENTS.md sección 10). Botón de impresión y Reimprimir.
8. Pruebas con pytest: todas las transiciones válidas e inválidas, que no se pague de más, que el total y cobrado de v_pedido_resumen sean correctos
   y que las rutas JSON de cola y cocina devuelvan el formato esperado.

Criterio de terminado: pido como cliente, el staff acepta, veo las instrucciones de pago, el staff registra el pago, el pedido pasa a cocina,
la cocina ve el temporizador y lo marca listo y se entrega; un pedido con un plato agotado se puede ajustar antes de aceptar. Prueba todo en el navegador y reporta.
Presenta el plan antes de programar.
```

---

## Fase 4 – Cierre del primer avance (instalable, impresión y demostración)
```
Contexto: AGENTS.md y schema.sql. Fases 0 a 3 terminadas. Esta es la Fase 4. NO se implementan notificaciones automáticas ni impresión automática desde el servidor (son del proyecto final).

Objetivo: dejar el avance sólido, instalable en el celular, con impresión configurada y listo para la demostración.

Haz:
1. Instalable (AGENTS.md 4b punto 6): manifest.webmanifest, iconos y un service worker mínimo que NO guarde datos en caché (solo cumple la instalación).
   Verifica que Chrome ofrezca instalar la web y que las pantallas operativas sigan pidiendo datos frescos.
2. Impresión: página /staff/imprimir/prueba con un ticket de prueba para calibrar ancho (80 mm / 58 mm) y márgenes, sin encabezados del navegador. Añade al README una sección
   "Configurar la tiquetera" que resuma GUIA_IMPRESION.md.
3. Comando manage.py cargar-demo con datos de demostración creíbles: reservas en varios horarios (incluida una forzada por el staff con excede_cupo, una franja en alerta y otra excedida, y una pasada de tolerancia)
   y pedidos en todos los estados (incluido uno que supere el umbral de cocina).
4. Revisa que cada ruta de /staff, /admin y /api exija el rol correcto, que ninguna respuesta de la API incluya password_hash, mensajes de error en claro,
   estados vacíos y que todo se vea bien en celular.
5. Verifica que ninguna regla de negocio esté escrita dentro de las plantillas o de las rutas (deben estar en app/servicios/ o en las funciones SQL).
6. README completo: instalar, configurar .env, crear la BD, correr, y una lista de comprobación para el día de la demostración
   (incluye "abrir la página unos minutos antes" si el hosting se duerme).
7. Informe final: qué quedó hecho, qué queda para el proyecto final, riesgos conocidos y deuda técnica.

Criterio de terminado: un recorrido completo de la demostración (reserva → confirmación → pizarra → pedido → cobro → cocina → entrega → ticket impreso) sin errores. Prueba y reporta.
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
5. (Opcional) Notificaciones push web para el personal en Android y computador (VAPID + service worker). Aclara en pantalla que en iPhone solo llegan
   si la web está instalada en la pantalla de inicio y que no son 100 % confiables.

Criterio de terminado: confirmo una reserva con correo y llega el correo; el modal de WhatsApp abre el mensaje correcto; si apago el SMTP la acción
del staff sigue funcionando y la notificación queda como fallida. Prueba y reporta. Presenta el plan antes de programar.
```

## Fase 5B – Impresión automática con agente local
```
Contexto: AGENTS.md (sección 10, nivel 3) y GUIA_IMPRESION.md. Esta es la Fase 5B.

Objetivo: que los tickets salgan solos en la tiquetera al pasar un pedido a cocina o confirmar una reserva, sin que nadie toque la pantalla.
El servidor está en internet y NO puede alcanzar la impresora; por eso la impresión la hace un programa pequeño en el equipo del local.

Haz:
1. Un script SQL APARTE (migracion_impresion.sql, sin tocar schema.sql) con la tabla trabajo_impresion: tipo (reserva o pedido), la referencia, estado
   (pendiente, impresa, fallida), creado_en, impreso_en, error.
2. Al confirmar una reserva o pasar un pedido a 'en_preparacion', el servicio crea un trabajo de impresión (si la impresión automática está activada).
3. Rutas JSON protegidas con una clave de API en el .env (cabecera X-API-Key, comparación segura): GET /api/v1/impresiones/pendientes y
   POST /api/v1/impresiones/<id>/resultado.
4. Carpeta agente_impresion/ con un script Python para el equipo del local: cada pocos segundos pide los pendientes, imprime en la tiquetera con ESC/POS
   (por ejemplo con python-escpos; la conexión depende del modelo: USB, red o Bluetooth) y reporta el resultado. Manejo claro de errores y reintentos.
5. Respaldo: si el agente no responde, la impresión manual (nivel 1 y 2) sigue funcionando y el panel muestra una alerta de "agente desconectado".
6. Pruebas de la ruta con y sin clave, y README del agente (instalación como servicio en Windows).

Criterio de terminado: acepto un pedido y el ticket sale solo; si apago el agente, aparece la alerta y puedo imprimir a mano. Prueba y reporta. Presenta el plan antes de programar.
```

## Fase 5C – Reservas por WhatsApp (opcional; depende de la API oficial)
```
Contexto: AGENTS.md y la documentación del proveedor de la API de WhatsApp elegido. Esta es la Fase 5C. Solo si el equipo ya tiene la cuenta de la API oficial aprobada.

Objetivo: que un cliente pueda enviar una reserva por WhatsApp con un formato fijo y que llegue al panel como solicitud PENDIENTE. El staff siempre confirma.

Haz:
1. Un script SQL APARTE para permitir el canal 'whatsapp' en reserva (el esquema actual solo acepta 'web' y 'staff').
2. Ruta /webhook/whatsapp que verifique la firma del proveedor, ignore mensajes duplicados y limite la frecuencia por número.
3. Parser del mensaje con formato fijo (ejemplo: "Reserva / Nombre / 4 personas / 25 de octubre / 8:00 pm") con validaciones iguales a las del formulario web.
   Si el formato es incorrecto, responder automáticamente con el formato esperado. Si es correcto, crear la reserva en estado 'pendiente' y responder que
   la solicitud fue recibida y será confirmada por el local. NUNCA confirmar automáticamente.
4. La solicitud aparece en el panel con su insignia y sonido, igual que las de la web.
5. Pruebas del parser con mensajes bien y mal escritos.

Criterio de terminado: envío un mensaje con el formato, aparece como pendiente en la pizarra y recibo la respuesta automática. Prueba y reporta. Presenta el plan antes de programar.
```
