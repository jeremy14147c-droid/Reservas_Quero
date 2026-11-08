# Prompts por fase para Antigravity – Quero APP (v3, solo web)

## Antes de empezar (una sola vez)
1. Haz primero los **pasos previos** de `PASOS_PREVIOS.md` (instalaciones, base de datos, `.env`).
2. Copia a la raíz del repo: `AGENTS.md`, `schema.sql` (la versión nueva), `seed.sql` (revisa que no inserte la columna `documento`, que ya no existe) (y deja `GUIA_IMPRESION.md` a mano para la Fase 4).
3. Abre la carpeta en Antigravity. Usa el modo **Planning** en cada fase y **revisa el plan antes de aprobarlo**.
4. Pega UN prompt por vez. No pases a la siguiente fase hasta probar la anterior y hacer commit.
5. Si el agente propone cambiar el esquema o agregar paquetes, no lo aceptes sin discutirlo en el equipo.

## Alcance
- **Plan vigente de las fases 3.x (desde el 03/11/2026): sección "Fases 3.x" más abajo, después de la Fase 3.** El estado y el orden están en `ESTADO_ACTUAL.md`.
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
## Fase 1.1 – Código de plato, búsqueda y platos con dos precios

Contexto: AGENTS.md (versión nueva, sección del código de plato y de los platos con dos precios) y schema.sql. Fases 0 y 1 ya están hechas. Esta es la Fase 1.1.

Objetivo: agregar el código de plato y la búsqueda por nombre o número, sin tocar nada más.

Antes de programar (solo lectura): compara la base de datos y el código con schema.sql y AGENTS.md y dime las diferencias que encuentres. Revisa en especial:
plato.codigo, config_local.umbral_alerta_pct, config_local.max_reservas_web_por_telefono, reserva.excede_cupo, la vista v_cliente_actividad_24h,
que fn_carga_dia devuelva la columna nivel y que cliente NO tenga la columna documento. Si falta algo del esquema, dame el comando SQL exacto y espera mi aprobación:
no modifiques la base de datos ni schema.sql por tu cuenta.

Haz:
1. Servicio de carta (app/servicios/): soportar plato.codigo, que es un número entero mayor que cero, único y opcional, y NO es el plato_id.
   Si el código ya existe, devuelve un mensaje claro (nunca un error 500). Varios platos pueden tener el código vacío. Un plato desactivado conserva su código (no se reutiliza).
2. Búsqueda de platos: una función reutilizable buscar_platos(texto) en app/servicios/. Si el texto son solo dígitos, devuelve el plato activo cuyo código coincide EXACTAMENTE
   (1 no debe traer el 10 ni el 11); si no, busca por nombre sin distinguir mayúsculas ni tildes. Expónla como GET /api/v1/platos/buscar?q=... (JSON: id, codigo, nombre, precio,
   disponible y categoría; solo platos activos). La usará la Fase 3 en "Nuevo pedido en local"; NO construyas esa pantalla ahora.
3. Carta pública /carta: muestra el código junto al nombre cuando exista, y mantiene los agotados marcados y los inactivos ocultos.
4. Carta del staff /staff/carta: agrega un buscador por nombre o número (usa buscar_platos) y muestra el código. Empleado y admin pueden buscar y cambiar disponible y precio;
   solo el admin crea o edita platos, y por lo tanto solo el admin asigna o cambia el código.
5. Formulario de plato (solo admin): campo "Código (opcional)" con ayuda breve ("Número corto para buscar el plato; no se repite") y un aviso:
   "Si el plato tiene dos precios (por ejemplo personal y fuente), créalo dos veces, una por tamaño, cada una con su precio y su código. Los sabores con el mismo precio no son platos distintos."
   No agregues una segunda columna de precio ni tablas nuevas.
6. Si /admin/config no tiene los campos de umbral de alerta de ocupación (%) y de máximo de reservas web por teléfono en 24 h, agrégalos con sus validaciones. Si ya existen, no cambies nada.
7. Si seed.sql inserta platos, asígnales códigos de ejemplo y deja un par de variantes de ejemplo (un mismo plato en dos tamaños). Avísame qué cambiaste.
8. Pruebas con pytest: el código exacto no trae coincidencias parciales; un código repetido se rechaza con mensaje claro; dos platos sin código son válidos;
   un plato desactivado conserva su código; un empleado no puede crear platos ni cambiar códigos; la búsqueda por nombre ignora mayúsculas y tildes.

Criterio de terminado: en /staff/carta escribo 1 y aparece solo el plato con código 1; escribo "cevi" y aparecen los ceviches; intento repetir un código y veo un mensaje claro;
creo el mismo plato en dos tamaños con precio y código distintos y aparecen como dos platos en /carta. Prueba en el navegador y reporta.
Presenta el plan antes de programar. No cambies el esquema ni agregues paquetes sin avisarme.

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

## Fases 3.x – Plan vigente (actualizado el 03/11/2026)

**Estado:** 3.1 y 3.2 están HECHAS (52 pruebas en verde). Sigue la 3.0. Las fases se hacen en este orden, una rama por fase (AGENTS.md 14.8):

| Fase | Qué | Estado |
|---|---|---|
| 3.1 | Buscador de platos, mesa sin texto repetido | Hecha |
| 3.2 | Tiempo en mesa por tamaño de grupo (30/60/90) y pizarra clara | Hecha |
| **3.0** | Higiene de Git (`.venv` versionado, integrar a `main`) | **Siguiente** |
| 3.R | Capa DAO real + arranque del TDD | Pendiente |
| 3.3 | Horas pasadas no reservables y vencimiento automático | Pendiente |
| 3.4 | Identidad visual del cliente (logo, fuentes, WhatsApp, Maps) | Pendiente |
| 3.5 | Carta y pedido en celular (categorías, desplegables, carrito) | Pendiente |
| 3.6 | Cocina: imprimir, recojo primero | Pendiente |
| 3.7 | Pago con comprobante del cliente y un solo botón | Pendiente |
| 3.8 | WhatsApp sin costo: mensajes listos y botones | Pendiente |
| 3.9 | Imágenes de platos (opcional, solo si hay fotos) | Opcional |

> Esta numeración **reemplaza** la de `FASE_3_1_CAMBIOS.md` (que queda como documento histórico).
> Todas las fases siguen AGENTS.md sección 14: plan primero, TDD (prueba en rojo → verde → refactor), commits con prefijo, probar en el navegador y reportar.

### Fase 3.0 – Higiene de Git (sin tocar el código de la app)
```
Contexto: AGENTS.md (sección 14) y ESTADO_ACTUAL.md. El repositorio está en GitHub; la rama fase-3-1 contiene las Fases 3.1 y 3.2 (52 pruebas). Esta es la Fase 3.0. No cambies código de la aplicación.

Haz:
1. Revisa `git status`. Si hay cambios de código sin guardar, muéstramelos y pregúntame antes de seguir.
2. El directorio .venv/ está versionado por error (más de 3000 archivos) aunque aparece en .gitignore. Quítalo del índice SIN borrarlo del disco:
   `git rm -r --cached .venv` y commit "chore: dejar de versionar .venv". Haz lo mismo con __pycache__/ y .vscode/ si están versionados.
3. Comprueba que .env NO está ni estuvo nunca en el historial (`git log --all --oneline -- .env`). Si alguna vez estuvo, avísame ANTES de hacer nada más (habría que cambiar las claves).
4. Prueba que requirements.txt instala todo desde cero (venv nuevo, `pip install -r requirements.txt`) y agrega `tzdata` (zona horaria America/Lima en Windows). Commit "chore: tzdata en requirements".
5. Integra fase-3-1 a main con un merge que conserve los commits (sin squash, sin reescribir historia, sin force push) con las 52 pruebas en verde. Crea la etiqueta v0.3.2 y sube main y la etiqueta.
6. Crea la rama fase-3-r desde main.

Criterio de terminado: `git ls-files | wc -l` baja de miles a cientos; mi .venv local sigue funcionando; main contiene los commits de 3.1 y 3.2; pytest en verde; .gitignore sigue ignorando .venv y .env. Presenta el plan antes de ejecutar.
```

### Fase 3.R – Capa DAO real y arranque del TDD
```
Contexto: AGENTS.md (secciones 4, 4b y 14, ya actualizadas) y el código actual. Fase 3.0 terminada, rama fase-3-r, 52 pruebas en verde. Esta es la Fase 3.R. Es un REFACTOR: el comportamiento visible NO cambia.

Objetivo: separar de verdad el acceso a datos (patrón DAO) para que se cumpla MVC + servicios + DAO y se pueda demostrar en la exposición.

Estado a corregir (verificado en el código): el SQL está repartido dentro de los servicios (carta.py, pedidos.py, reservas.py, personal.py, clientes.py, configuracion.py) y además hay consultas directas en rutas:
app/auth/routes.py (3) y app/publico/routes.py (3). app/db.py es solo un conjunto de helpers genéricos, no un DAO.

Haz, UNA entidad por commit y con las pruebas en verde después de CADA commit:
1. Crea el paquete app/dao/ con una clase por entidad: ConfigDAO, ClienteDAO, PersonalDAO, CartaDAO (categoría y plato), ReservaDAO, PedidoDAO (incluye detalle y pago).
   Cada método recibe parámetros y devuelve diccionarios o listas (nunca cursores), usa SOLO consultas parametrizadas y los helpers de app/db.py. Nombres en español
   (ej. ReservaDAO.insertar, .buscar_por_id, .listar_del_dia, .actualizar_estado). Las llamadas a funciones SQL (fn_hay_cupo, fn_carga_dia, fn_duracion_estadia) también van en el DAO.
2. Los servicios dejan de escribir SQL: piden los datos al DAO y conservan las reglas (validaciones, TRANSICIONES_VALIDAS, mensajes de error). Cada servicio recibe su DAO como dependencia
   con un valor por defecto (parámetro o atributo de módulo reemplazable) para poder cambiarlo por uno falso en las pruebas.
3. Las rutas dejan de importar app.db: auth/routes.py y publico/routes.py llaman a servicios (servicio_configuracion.obtener_config_local(), servicios/personal.py, etc.).
   Al terminar, estas dos búsquedas deben salir vacías (las excepciones, si las hay, se explican una por una):
   `grep -rn "app.db" app/*/routes.py app/api` y `grep -rniE "SELECT |INSERT |UPDATE |DELETE " app/servicios app/*/routes.py app/api`.
4. Pruebas unitarias SIN base de datos en tests/unidad/ con un DAO falso en memoria. Mínimo tres: transicion_reserva rechaza pasar de rechazada a confirmada; un pedido recojo no pasa a cocina sin estar cobrado;
   el tope de reservas web por teléfono. Deben pasar con PostgreSQL apagado. Esa es la evidencia de DAO + inversión de dependencias.
5. TDD empezando aquí: para estas pruebas nuevas escribe la prueba primero, muéstrala en rojo, commit "test: ..." y luego implementa, commit "refactor: ...". El resto del refactor lo protegen las pruebas que ya existen.
6. Documentos de defensa: corrige DEFENSA_RUBRICA.md, GUION_EXPOSICION.md y GUIA_ENTENDER_EL_PROYECTO.md para que digan SOLO lo que ahora es cierto: capa DAO en app/dao/, pruebas unitarias sin base,
   y que hasta la Fase 3.2 las pruebas se escribieron al final de cada fase y que el TDD estricto empieza en la 3.R (con la evidencia en `git log --oneline`: commits test: antes de feat:).
   Actualiza el conteo de pruebas, el mapa de carpetas y las líneas citadas, y quita el banner de advertencia cuando todo sea verdad.
7. Actualiza AGENTS.md sección 4 si algo cambió.

No toques: schema.sql, el comportamiento visible, las URL ni el formato JSON de la API.
Criterio de terminado: pytest en verde (las 52 + las nuevas); las dos búsquedas con grep salen vacías; tests/unidad pasa con PostgreSQL apagado; la app funciona igual.
Si el tiempo aprieta: haz Reserva, Cliente y Config primero (un commit por entidad) y dime cuáles quedan pendientes. Presenta el plan antes de programar.
```

### Fase 3.3 – Horas pasadas no reservables y vencimiento automático
```
Contexto: AGENTS.md (secciones 2, 4b, 7 y 14, ya actualizadas) y el código actual. Fase 3.R terminada. Esta es la Fase 3.3. Trabaja con TDD (AGENTS.md 14.7): primero las pruebas en rojo (commit "test:"), luego el código ("feat:").

Objetivo: (A) las horas que ya pasaron no se pueden reservar y el staff no ve lo que ya terminó; (B) las reservas vencidas se cierran solas.

Diagnóstico verificado: validar_fecha solo compara fechas y validar_hora_en_franjas solo comprueba que la hora sea una franja del horario: hoy se puede reservar a las 12:00 pm cuando son las 4:00 pm.
Además hoy() y ahora_local() usan datetime.now(): la hora del equipo, no la de Lima (en un servidor en la nube serían 5 horas de diferencia).

Haz:
1. Hora única: ajusta ahora_local() y hoy() para usar ZoneInfo("America/Lima") y reemplaza TODO uso suelto de datetime.now() / date.today() en app/ (grep).
2. Migración migraciones/002_anticipacion_minima.sql (repetible) y schema.sql / seed.sql (esta fase lo autoriza): config_local.anticipacion_min_min SMALLINT NOT NULL DEFAULT 30 CHECK (anticipacion_min_min >= 0).
   Campo en Administración > Configuración con su validación.
3. Regla PURA (sin base de datos) franja_reservable(fecha, hora_inicio, minutos_franja, ahora, canal, anticipacion_min) → (bool, motivo). Web: reservable si el inicio de la franja >= ahora + anticipacion_min.
   Staff: reservable si el FIN de la franja > ahora (puede usar la franja en curso). Días futuros: siempre; días pasados: nunca.
4. horarios_con_semaforo(fecha) añade a cada hora el campo pasada. En /reservar las horas pasadas salen deshabilitadas con el texto "Ya pasó" (no se esconden sin explicar). Si hoy no queda ninguna:
   "Hoy ya no hay horarios disponibles; elige otro día". Se valida SIEMPRE también en el servidor: crear_reserva_web, crear_reserva_staff y cambiar_hora rechazan una hora pasada con un mensaje claro
   ("Esa hora ya pasó. Elige una hora posterior; se necesitan al menos 30 min de anticipación.").
5. Pizarra del staff y API /api/v1/reservas/dia: para HOY, por defecto solo las franjas cuyo fin es posterior a la hora actual y las reservas que aún ocupan mesa; parámetro ver_pasadas=1 y un interruptor
   "Ver horas anteriores" en la pantalla para ver el día completo. Otros días: completos. Solo AGREGAR campos a la API (ej. franjas_ocultas); no quitar ni renombrar ninguno.
6. Vencimiento automático (única excepción al principio 2.1): servicio liberar_reservas_vencidas(ahora=None) con las reglas de AGENTS.md sección 7 (pendiente cuya hora pasó → rechazada "Vencida: nadie la atendió a tiempo";
   confirmada cuya ocupación terminó (hora + fn_duracion_estadia) → no_llego "Automático: no se registró la llegada"; llego no cambia). Se llama de forma perezosa al consultar la pizarra, el semáforo público y la API del día,
   y con `python manage.py liberar-vencidas`. Sin hilos ni tareas de fondo. Devuelve cuántas cerró. Todo el SQL va en ReservaDAO.
7. Pruebas (TDD; las reglas puras SIN base de datos): franja_reservable en los bordes (justo en el límite de anticipación, franja en curso para staff, día futuro, día pasado); el servidor rechaza hora pasada por web, por staff y en cambiar_hora;
   el semáforo marca las pasadas; la API oculta franjas pasadas y con ver_pasadas=1 las muestra; liberar_reservas_vencidas cierra solo lo que corresponde y NO toca llego, futuras ni otros días; es idempotente (la segunda llamada no cierra nada).
8. Actualiza DICCIONARIO_BASE_DE_DATOS.md (columna nueva) y el README si cambia algún comando.

No toques: capacidad (fn_carga_dia / fn_hay_cupo), tope por teléfono, pedidos.
Criterio de terminado: son las 4 pm y en /reservar de hoy las horas anteriores aparecen deshabilitadas con "Ya pasó"; forzar una hora pasada por la URL devuelve un error claro; la pizarra de hoy empieza en la franja actual y el interruptor muestra el resto;
una reserva confirmada de la mañana sin "Llegó" aparece como no llegó (automático) al recargar; pytest en verde. Prueba en el navegador y reporta. Presenta el plan antes de programar.
```

### Fase 3.4 – Identidad visual del cliente
```
Contexto: AGENTS.md (secciones 4, 11 y 12) y las plantillas actuales. Fase 3.3 terminada. Esta es la Fase 3.4. Es una fase visual: el comportamiento no cambia. Lo que tiene regla (validar datos de contacto y enlaces) se hace con TDD (AGENTS.md 14.7).

Objetivo: que lo que ve el CLIENTE se sienta como un restaurante (llamativo, con accesos directos y datos del local) y que lo que usa el STAFF siga siendo sobrio y legible.

Datos del local: NO inventes ninguno (nombre comercial, logo, colores, eslogan, WhatsApp, dirección, enlace de Google Maps, redes). Si falta alguno usa un marcador visible ("Pendiente: número de WhatsApp") y dímelo al reportar; yo te los doy.

Haz:
1. Migración migraciones/003_contacto_marca.sql (repetible) y schema.sql / seed.sql (autorizado): config_local.whatsapp_numero VARCHAR(15) NULL, direccion VARCHAR(150) NULL, maps_url VARCHAR(300) NULL, instagram_url VARCHAR(200) NULL, facebook_url VARCHAR(200) NULL.
   En Administración > Configuración una sección "Contacto y marca" con validación en el servidor: whatsapp = 9 dígitos que empiezan en 9 (reusa la normalización de teléfono); maps_url, instagram_url y facebook_url deben empezar por https:// (rechaza javascript: y cualquier otro esquema).
   Un context processor `marca` entrega estos datos a las plantillas públicas.
2. Plantilla templates/base_cliente.html para TODAS las páginas públicas (/, /carta, /reservar, /pedir, /reserva/<token>, /pedido/<token>):
   - Encabezado con logo (static/img/logo.png; si no existe, el nombre del local con la tipografía de títulos) y accesos directos grandes: Reservar mesa · Hacer pedido · Carta · Cómo llegar (maps_url) · WhatsApp (https://wa.me/51<número>).
   - Pie con dirección, horario (de config_local), enlace al mapa, redes y WhatsApp.
   - Botón flotante de WhatsApp abajo a la derecha (solo si hay número).
   - Estilos en static/css/cliente.css con variables CSS (colores, tipografías, radios) para cambiar la marca en un solo lugar.
   - Tipografía: una fuente de títulos con personalidad y una de texto muy legible. Propón 2 combinaciones con vista previa antes de aplicarlas; carga con font-display: swap y pila de respaldo (o alójalas en static/fonts/).
3. Inicio (/): sección principal con nombre, eslogan y 3 botones (Reservar, Pedir, Ver carta); tarjetas "Cómo llegar", "Horario" y "Escríbenos"; sin números de capacidad ni datos internos.
4. Las páginas del staff siguen con base.html (sobrio). En las páginas públicas NUNCA se muestra el menú de staff ni la insignia de rol: si hay sesión de staff abierta, solo una franja discreta "Sesión de staff abierta · Volver al panel".
5. Móvil primero, buen contraste, imágenes con loading="lazy", sin librerías nuevas aparte de las fuentes. Favicon y theme-color con la marca.
6. Pruebas (TDD en lo que tiene regla): validación de whatsapp_numero y de las URL (https obligatorio, esquemas peligrosos rechazados); las páginas públicas responden 200 SIN menú de staff aunque haya un staff logueado; el enlace wa.me se arma bien; sin número configurado no aparece el botón flotante.

No toques: reglas de reservas ni pedidos, ni la API.
Criterio de terminado: en el celular (modo móvil del navegador) el inicio se ve como un restaurante; los botones Reservar, Pedir, Cómo llegar y WhatsApp funcionan; el staff sigue viendo su panel sobrio y las páginas públicas no muestran el menú de staff aunque esté logueado.
Prueba y reporta con capturas. Presenta el plan antes de programar.
```

### Fase 3.5 – Carta y pedido en celular (categorías, desplegables, carrito)
```
Contexto: AGENTS.md (secciones 3, 8, 11 y 12), app/templates/publico/pedir.html y carta.html. Fase 3.4 terminada. Esta es la Fase 3.5. TDD en lo que tiene regla (AGENTS.md 14.7).

Objetivo: elegir platos desde el celular debe ser corto y fácil (la lista actual es muy larga), y debe escalar a más o menos platos y a imágenes después. El formulario sigue enviando los MISMOS campos al servidor
(items como JSON, nombre, telefono, correo, nota, acepta_datos, honeypot y CSRF): el backend de pedidos no cambia. Stack: Bootstrap 5 y JavaScript vanilla, sin frameworks nuevos.

Haz:
1. Barra de categorías horizontal pegada arriba (chips con scroll lateral) y debajo secciones DESPLEGABLES por categoría (acordeón; abierta la categoría elegida, las demás cerradas para que la página no sea larga).
   Al tocar un chip se abre y desplaza a esa categoría. Buscador por nombre o por número de plato (reusa la normalización sin tildes).
2. Cada plato en una tarjeta compacta: nombre, número si tiene, descripción corta, precio y control +/−. Los agotados se ven apagados y no se pueden sumar. La tarjeta reserva un espacio para imagen (hoy un cuadro neutro con ícono;
   la Fase 3.9 lo rellena) y debe verse bien sin ella.
3. Barra flotante inferior "Ver pedido · N platos · S/ total" apenas haya algo. Al tocarla abre un panel (offcanvas de Bootstrap) con las líneas (cambiar cantidad, quitar), la nota del pedido y el total estimado
   (el precio real lo vuelve a calcular el servidor).
4. Segundo paso en el panel: datos (nombre, teléfono de 9 dígitos obligatorio, correo opcional, consentimiento) y botón "Enviar pedido". Se mantienen las validaciones del servidor.
5. "Complementa tu pedido": migración migraciones/004_categoria_complemento.sql (repetible) y schema.sql / seed.sql (autorizado): categoria.es_complemento BOOLEAN NOT NULL DEFAULT FALSE, con casilla en Carta Staff.
   En el panel del carrito, antes de enviar, un bloque con hasta 3 platos disponibles de categorías marcadas como complemento (bebidas, postres...) y botón +. Si no hay categorías marcadas, el bloque no aparece.
6. La carta pública (/carta) usa el mismo estilo de categorías desplegables, solo lectura.
7. El carrito se conserva en sessionStorage para que recargar no lo pierda y se limpia al enviar con éxito. No guardes datos personales en el navegador.
8. Respeta el banner "Sin conexión" y data-requiere-conexion. Accesible: botones con aria-label y foco visible. Estilos con las variables de cliente.css (Fase 3.4).
9. Pruebas: POST a /pedir con items válidos crea el pedido igual que antes; plato agotado rechazado; la página renderiza las categorías y solo los platos activos; el bloque de complementos solo muestra platos disponibles de categorías marcadas
   (regla pura probada sin base de datos).

Criterio de terminado: desde el celular (modo móvil) armo un pedido de 3 platos de 2 categorías sin hacer scroll interminable, ajusto cantidades, agrego un complemento, lleno mis datos y lo envío; aparece en la cola del staff como Pendiente.
Prueba en el navegador y reporta con capturas. Presenta el plan antes de programar.
```

### Fase 3.6 – Cocina: imprimir y recojo primero
```
Contexto: AGENTS.md (secciones 8 y 10, ya actualizadas) y el código actual. Fase 3.5 terminada. Esta es la Fase 3.6. Trabaja con TDD (AGENTS.md 14.7).

Objetivo: la pantalla de cocina imprime pedidos igual que la cola, y los pedidos para llevar se ven primero cuando están en cocina.

Haz:
1. Orden (TDD, en el DAO/servicio, no en JavaScript): en "En cocina", "Listos" y en el tablero de cocina, primero los pedidos de tipo recojo y luego los local, cada grupo por preparacion_en y luego por pedido_id.
   En "Pendientes" y "Por cobrar" el orden NO cambia (por llegada). Prueba primero con pedidos mezclados.
2. Etiqueta visible "PARA LLEVAR" en las tarjetas de recojo y "LOCAL" en las demás, en cola y cocina.
3. Imprimir desde cocina: en cada tarjeta de cocina.html el mismo botón "Imprimir ticket" que ya existe en la cola (misma ruta y plantilla: /staff/pedido/<id>/ticket). Además, en la pantalla de cocina la casilla
   "Imprimir automáticamente los pedidos nuevos de esta pantalla" (apagada por defecto, recuerda su elección): imprime cada pedido nuevo UNA sola vez (recuerda los ya impresos en sessionStorage) y funciona con la tiquetera configurada con --kiosk-printing
   (ver GUIA_IMPRESION.md). Junto a la casilla muestra la advertencia: "Activa la impresión automática en un solo equipo (cocina o caja) para no imprimir duplicados."
   Comparte el JS común con js_pedidos.js sin duplicar código (muévelo a un archivo estático compartido).
4. No cambies estados, cobros ni la regla de cocina solo cuando está cobrado.
5. Pruebas: orden de la cola y de cocina con pedidos mezclados (recojo primero); las transiciones y el cobro siguen igual; la ruta del ticket responde para un pedido en cocina.

Criterio de terminado: con un recojo y dos locales en cocina, el recojo aparece primero y con la etiqueta; cada tarjeta de cocina tiene "Imprimir ticket"; con la casilla activa, un pedido nuevo en cocina se imprime una vez.
Prueba en el navegador y reporta. Presenta el plan antes de programar.
```

### Fase 3.7 – Pago con comprobante del cliente y un solo botón
```
Contexto: AGENTS.md (secciones 4b, 8, 12 y 14, ya actualizadas) y el código actual. Esta es la Fase 3.7. Trabaja con TDD (AGENTS.md 14.7) y con la capa DAO (ComprobanteDAO en app/dao/; los servicios y las rutas no escriben SQL).

Objetivo: el cliente adjunta una captura de su pago; el staff la ve, verifica en su Yape real que llegó el monto exacto y con UN botón el pedido pasa a cocina.
La captura es solo apoyo: nunca aprueba el pago ni mueve el pedido por sí sola.

Haz:
1. Crea migraciones/005_comprobante_pago.sql (repetible) y actualiza schema.sql (esta fase lo autoriza). Tabla comprobante_pago:
   comprobante_id INT identity PK; pedido_id INT NOT NULL FK; contenido BYTEA NOT NULL (la imagen ya reducida, nunca el archivo original); tipo_mime VARCHAR(20) NOT NULL;
   bytes INT NOT NULL; estado VARCHAR(10) NOT NULL DEFAULT 'pendiente' CHECK IN ('pendiente','aprobado','rechazado'); motivo_rechazo VARCHAR(200) NULL;
   subido_en TIMESTAMPTZ NOT NULL DEFAULT now(); revisado_por INT NULL FK personal; revisado_en TIMESTAMPTZ NULL. Índice por pedido_id.
2. app/servicios/archivos.py (nuevo, reutilizable): recibe el archivo subido, valida tamaño (máx 5 MB), verifica con Pillow que es una imagen real JPEG, PNG o WebP
   (no confiar en extensión ni en el tipo declarado), la reconvierte a JPEG con lado máximo 1200 px, calidad cercana a 70 y SIN metadatos (EXIF/GPS), y devuelve los bytes y los datos para guardarlos en la base (NO en el disco). Configura MAX_CONTENT_LENGTH en config.py y maneja el error 413 con mensaje claro.
2b. Retención: agrega el comando de manage.py `limpiar-comprobantes [--dias 30]`, que borra los comprobantes de pedidos ya entregados, rechazados o cancelados con más de N días.
   Todas las consultas de listas y colas deben EXCLUIR la columna contenido (nunca SELECT *).
3. Cliente, en /pedido/<token>, cuando el pedido está aceptado y por cobrar: junto a las instrucciones de Yape, un formulario "Adjuntar comprobante" (input de imagen, permite cámara en celular, con CSRF y honeypot).
   Ruta POST /pedido/<token>/comprobante. Máximo 3 comprobantes pendientes por pedido. Muestra el estado del último: "Recibido, el local lo está verificando" o "Rechazado: <motivo>" (permite subir otro).
   Un token solo puede subir a su propio pedido. La página sigue refrescándose sola.
4. Staff:
   - Ruta GET /staff/comprobante/<id> con @requiere_rol("admin","empleado") que lee la imagen de la base y la entrega (nunca desde static/ ni del disco). Cabeceras para que no se cachee en proxys públicos.
   - Cola, columna "Por cobrar": insignia "Comprobante recibido" en las tarjetas que lo tengan, y esas tarjetas primero dentro de la columna. El botón de la tarjeta dice "Revisar pago".
   - Detalle del pedido: muestra la imagen grande, el total, el número/titular de Yape y el texto "Abre tu Yape y confirma que llegó S/ <saldo>". Botones:
       a) "Confirmar pago y enviar a cocina": UN clic, sin ventana emergente y sin escribir nada. Registra el pago por el saldo completo con medio 'yape', marca el comprobante como aprobado
          (revisado_por y revisado_en) y el pedido pasa a en_preparacion (reusa registrar_pago; no dupliques la lógica).
       b) "Cobrar en efectivo": con una confirmación simple, registra el saldo completo con medio 'efectivo' y pasa a cocina.
       c) "Rechazar comprobante": pide motivo, marca el comprobante rechazado; el pedido sigue aceptado y el cliente puede subir otro.
       d) Enlace pequeño "Otro medio o pago parcial" que abre el modal actual (no lo elimines: conserva esa función). El campo "referencia" sale del flujo normal.
5. API /api/v1/pedidos/cola: agrega (solo agregar) el campo tiene_comprobante por pedido.
6. Un pedido nunca pasa a cocina sin pago registrado por el staff (regla actual intacta). No pagar de más.
7. Pruebas con pytest: subida válida; archivo que no es imagen (aunque se llame .jpg) rechazado; archivo mayor a 5 MB rechazado; un token no puede subir al pedido de otro;
   /staff/comprobante/<id> exige sesión de staff; "Confirmar pago y enviar a cocina" registra el saldo y deja el pedido en en_preparacion; rechazar permite subir otro; no se puede pagar de más;
   los metadatos EXIF no sobreviven al guardado; limpiar-comprobantes borra solo comprobantes antiguos de pedidos cerrados.

No toques: reservas, estados de pedido, la regla "solo a cocina cuando queda cobrado".
Criterio de terminado: como cliente pido, el staff acepta, subo una captura desde el celular; en la cola aparece "Comprobante recibido"; el staff abre el detalle, ve la imagen, pulsa un botón y el pedido está en cocina.
Rechazo un comprobante y puedo subir otro. Prueba en el navegador y reporta. Presenta el plan antes de programar.
```

### Fase 3.8 – WhatsApp sin costo: mensajes listos y botones
```
Contexto: AGENTS.md (secciones 4b, 9 y 14, ya actualizadas), WHATSAPP_COSTOS.md y el código actual (enlace_whatsapp en utils.py, menú ⋮ de pizarra.html y js_pedidos.js). Fase 3.7 terminada. Esta es la Fase 3.8. TDD obligatorio (AGENTS.md 14.7).

Objetivo: comunicar al cliente por WhatsApp cada paso de su reserva o pedido con mensajes fáciles de leer, amables y con emojis, SIN usar la API de pago: todo con enlaces wa.me que abren WhatsApp con el texto ya escrito.

Haz:
1. servicios/mensajes.py: funciones PURAS (sin base de datos ni Flask) que devuelven el texto: reserva_recibida, reserva_confirmada, reserva_rechazada(motivo), reserva_cambio_hora(antes, ahora), pedido_recibido, pedido_aceptado(total, datos de Yape, enlace para subir el comprobante),
   pedido_listo, pedido_entregado (agradecimiento), pedido_rechazado(motivo). Estilo: saludo con el nombre, 1 a 3 emojis bien puestos, líneas cortas, datos clave en negrita de WhatsApp (*así*), código de la reserva o número del pedido,
   enlace de seguimiento (/reserva/<token> o /pedido/<token>), nombre del local, máximo ~600 caracteres, sin la palabra "None" ni campos vacíos. Una sola invitación suave a pedir más, en pedido_entregado ("¿Se te antojó algo más? Mira la carta: <enlace>"); no en los demás mensajes.
   Escribe PRIMERO las pruebas (contienen código/nombre/enlace, no contienen "None", no pasan del largo máximo, se codifican bien en la URL) y haz commit "test:" antes del código.
2. Botón "Avisar por WhatsApp" (verde, grande) que aparece justo después de cada acción del staff (confirmar, rechazar, cambiar hora; aceptar, rechazar, listo, entregado) y abre WhatsApp con el mensaje del estado correspondiente.
   El menú ⋮ conserva "WhatsApp", ahora con el mensaje correcto según el estado actual. No uses la tabla notificacion ni ninguna API.
3. Botones para el cliente, con el número de config_local.whatsapp_numero: en /reserva/<token> y /pedido/<token> "Enviar por WhatsApp al local" (texto prellenado con código y datos) y, en pedidos por cobrar,
   "Ya pagué: enviar captura por WhatsApp" como alternativa a subir el comprobante en la página. Sin número configurado, estos botones no aparecen.
4. Reemplaza los textos de WhatsApp que hoy están escritos dentro de pizarra.html y js_pedidos.js por llamadas a mensajes.py (vía una ruta o dato de la API), para que haya UN solo lugar con los textos.
5. Pruebas de integración: tras confirmar una reserva el botón aparece con el enlace wa.me correcto y el mensaje de "confirmada"; un teléfono sin 9 dígitos no genera enlace; sin whatsapp_numero no aparecen los botones del cliente.

No toques: la tabla notificacion, el correo automático ni la API oficial (quedan para la 5A).
Criterio de terminado: confirmo una reserva y con un toque se abre WhatsApp con un mensaje amable y claro; marco un pedido listo y abre el mensaje de "listo"; el cliente puede escribirle al local desde su página de seguimiento.
Prueba en el navegador y reporta con ejemplos de los mensajes. Presenta el plan antes de programar.
```

### Fase 3.9 – Imagen por plato (opcional; solo si hay fotos reales)
```
Contexto: AGENTS.md y app/servicios/archivos.py (Fase 3.7). Esta es la Fase 3.9. Trabaja con TDD (AGENTS.md 14.7) y con la capa DAO (PlatoImagenDAO en app/dao/).

Objetivo: cada plato puede tener una foto opcional que se ve en la carta pública y en /pedir.

Haz:
1. migraciones/006_plato_imagen.sql (repetible) y schema.sql: tabla plato_imagen (plato_id INT PK FK a plato, contenido BYTEA NOT NULL, tipo_mime VARCHAR(20) NOT NULL, actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()).
   Es una tabla aparte para que las consultas de plato no arrastren los bytes. Sin fila = plato sin imagen.
2. Reutiliza servicios/archivos.py (mismas validaciones y quitar metadatos) con lado máximo 800 px y calidad ajustada para que cada imagen pese menos de 200 KB. Se guarda en la base, no en el disco.
3. Carta Staff: al crear o editar un plato, campo opcional "Foto" y botón para quitarla. Al reemplazarla se sobrescribe la fila; al quitarla se borra.
4. Ruta pública GET /img/plato/<plato_id> que entrega la foto con cabeceras de caché; si no hay foto, devuelve un ícono neutro. Estas imágenes SÍ son públicas (a diferencia de los comprobantes).
5. Mostrar la imagen en /carta y en las tarjetas de /pedir (con carga diferida, loading="lazy"). Sin imagen, la tarjeta sigue viéndose bien.

Pruebas: subida válida; archivo no imagen rechazado; reemplazar sobrescribe y quitar elimina la imagen; /img/plato/<id> devuelve imagen o ícono; la carta pública carga sin fotos.
Criterio de terminado: subo la foto de dos platos desde Carta Staff y aparecen en la carta pública y en /pedir; los demás platos siguen bien sin foto. Prueba en el navegador y reporta. Presenta el plan antes de programar.
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
> Nota (03/11/2026): los botones de WhatsApp con mensaje ya redactado (`wa.me`) se adelantaron a la Fase 3.8 y los textos viven en `servicios/mensajes.py`.
> La 5A solo agrega el correo automático, el registro en la tabla `notificacion` y, si se decide pagar, la API oficial de WhatsApp (ver `WHATSAPP_COSTOS.md`).
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
