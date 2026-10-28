# Fase 3.x: cambios pedidos, diagnóstico y prompts

Basado en el zip `Reservas_Quero (2).zip` (Fase 3). Todo lo que dice "verificado" lo comprobé leyendo tu código; **no ejecuté la app ni las pruebas**.

## 1. Qué encontré en cada punto

| # | Lo que reportaste | Diagnóstico | Qué hacer |
|---|---|---|---|
| 1 | Tiempo en mesa según personas | Hoy hay **una sola** duración para todos (`duracion_estadia_min`, usada en `fn_carga_dia`, `fn_hay_cupo` y `reservas.py` línea 470). | Sub-fase 3.2. **Ojo con el aviso de la sección 2.** |
| 2 | Pizarra "triplicada" | No es un error: una reserva de 90 min aparece en cada franja de 30 min que ocupa (con el marcador "continúa"). Es correcto para el conteo, pero confunde a la vista. | Sub-fase 3.2: tarjeta completa solo en su franja de inicio. |
| 3 | Al pedir como cliente se pone rol "mozo" | **Verificado: ningún código asigna roles al pedir.** Los roles son solo `admin` y `empleado`; "mozo" aparece únicamente como texto en la pantalla de personal. Lo más probable: tu navegador **tiene la sesión del staff abierta**, y `base.html` muestra el menú y la insignia de staff en todas las páginas, también en las públicas. | Prueba `/pedir` en una **ventana de incógnito**. Si ahí sale limpio, no hay bug. Mejora opcional en 3.1. |
| 4 | El pago pide escribir el medio | Es el modal "Registrar pago" de `detalle.html` (medio, monto, referencia). | Sub-fase 3.3: comprobante del cliente y un solo botón. |
| 5 | Listo → Entregado obligatorio en local | Hoy el local nace `en_preparacion` y solo puede ir a `listo` y luego `entregado`. Dijiste que por ahora es una aclaración. | Descartado por ahora (decisión tuya). |
| 6 | Recojo primero en la vista | `obtener_cola` y `obtener_cocina` ordenan solo por hora de llegada. | Sub-fase 3.4. |
| 7 | Número de mesa obligatorio | **Verificado: ya es opcional.** El servicio hace `or None` y el input de `nuevo.html` no lleva `required`. Lo que sí molesta es que la tarjeta muestra "Mesa: Mesa 2" (texto repetido). | Corregir el texto en 3.1. |
| 8 | El buscador de platos no funciona | **Causa encontrada:** `nuevo.html` llama a `esc(...)` (líneas 98, 101 y 126) pero **esa función no está definida en esa página**. Solo existe dentro de `pizarra.html`, `cocina.html` y `js_pedidos.js`. Cuando la búsqueda devuelve platos, el script lanza `ReferenceError` y no pinta nada (si no hay resultados sí muestra el mensaje, por eso parece "medio vivo"). | Sub-fase 3.1: definir `esc` una sola vez en `main.js`. |
| 9 | Carrito tipo Rappi, imagen por plato, mejor navegación | Opinión en la sección 2. | Sub-fases 3.5 y 3.6. |

## 2. Opinión crítica (lo que no te conviene ignorar)

**a) Con franja de 30 min, "40" y "60" son lo mismo: tu opción real es 30 o 60.** El cupo se calcula por franjas de 30 min. Un grupo de 40 min que llega a las 8:00 ocupa las franjas de 8:00 y 8:30, igual que uno de 60. Con 30, 60 y 90 min cada grupo ocupa exactamente 1, 2 y 3 franjas, y encaja limpio con las horas que elige el cliente. **Decisión tomada:** `franja_min` se queda en 30 y 1 a 3 personas pasa a 30 min. Es técnicamente correcto. El riesgo es de negocio y es silencioso: si un grupo chico se queda 40 o 50 min, el sistema liberará su mesa a los 30 y podrá aceptar otra reserva mientras sigue ocupada. Los tiempos se cambian en Administración > Configuración, sin tocar código. Valida con la dueña (o cronometra unos días) cuánto tardan de verdad.

**b) Una captura de Yape se puede falsificar.** Existen editores que fabrican capturas falsas. Por eso tu `AGENTS.md` decía "nunca confiar en capturas". Mi propuesta **mantiene el espíritu**: la captura es un apoyo, y el staff **siempre abre su Yape real** para ver si llegó el monto exacto. La captura nunca aprueba nada sola. Cambio la regla en `AGENTS.md` (parche abajo) en vez de ignorarla. Además, la captura trae nombre y teléfono del cliente: son datos personales. Quita los metadatos de la imagen, no la expongas por una URL pública y define cuánto tiempo se guarda.

**c) Las imágenes se guardan en la base de datos, no en el disco.** En los planes gratuitos el disco se borra al reiniciar (sección 7), pero la base de datos es lo que persiste. Por eso las imágenes viven en PostgreSQL (columna BYTEA), reducidas a unos 100–250 KB por comprobante (estimación mía, no medida). Así funciona igual en cualquier hosting y sin servicios extra. Los comprobantes se borran solos pasados 30 días (comando de limpieza) para no llenar la base ni guardar datos personales de más.

**d) Carrito tipo Rappi: sí, pero solo para el cliente.** En celular es el patrón correcto: categorías pegadas arriba, platos con botones +/−, barra inferior "Ver pedido (3) S/ 45". Se puede construir **sin tocar el backend**: el formulario sigue enviando la misma lista de platos. En cambio, la pantalla del mozo para pedidos en local debe seguir siendo rápida (buscar por número o nombre). No la rediseñes igual: tu staff trabaja con la tiquetera.

**e) Imágenes por plato: déjalas para el final.** Necesitan subida de archivos, columnas nuevas y, sobre todo, **fotos reales de los platos**. Sin fotos, todo queda con un cuadro gris. Si la dueña no las tiene, es esfuerzo perdido. Reutilizan la misma lógica de subida de la 3.3, así que conviene hacerlas después.

**f) Alcance y tiempo.** La profesora pidió algo funcionando en pocas semanas. 3.1 a 3.4 corrigen y simplifican lo que ya existe. 3.5 y 3.6 son mejoras de presentación. Si el tiempo aprieta, recorta 3.6 primero y 3.5 después.

## 3. Cómo hacerlo sin romper nada

1. **Una rama por sub-fase:** `git checkout -b fase-3-1` (y así con cada una). Si sale mal, vuelves a `main`.
2. **Antes y después de cada sub-fase:** `pytest` en verde. Si algo ya fallaba antes, anótalo.
3. **Cambios de base de datos solo con scripts en `migraciones/`**, escritos para poder repetirse (`ADD COLUMN IF NOT EXISTS`, etc.). Tu base ya tiene datos y `init-db` volvería a crear tablas que ya existen. Se aplican así:
   ```
   psql -h localhost -p 5433 -U quero_app -d quero -f migraciones\NNN_nombre.sql
   ```
   El agente también actualiza `schema.sql` para instalaciones nuevas (el prompt se lo autoriza de forma explícita).
4. **Cambios en la API JSON solo aditivos** (campos nuevos, nunca quitar ni renombrar), para que las pantallas existentes sigan funcionando.
5. **Orden:** 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → (3.6). Cada una se prueba en el navegador antes de empezar la siguiente.

## 4. Parche para `AGENTS.md`

Pega estos cambios **antes** de lanzar los prompts, para que el agente tenga las reglas nuevas. Cada bloque dice qué línea reemplaza o agrega.

**Sección 4 (estructura), agregar una línea dentro del árbol:**
```
├── migraciones/             # scripts SQL repetibles para bases ya creadas (NNN_nombre.sql)
```

**Sección 7 (Reservas), reemplazar el punto "Capacidad":**
```
- Capacidad: cuentan solo `confirmada` y `llego`. **Cada reserva ocupa mesa un tiempo que depende de su tamaño**:
  de 1 a 3 personas `duracion_1_3_min` (30), de 4 a 7 `duracion_4_7_min` (60), de 8 en adelante `duracion_8_mas_min` (90),
  todos en `config_local`. La duración sale de la función SQL `fn_duracion_estadia(personas)`; no recalcular en Python.
  Mesas requeridas = personas / `personas_por_mesa`, redondeado hacia arriba (un grupo de 2 usa una mesa entera).
  Usar las funciones `fn_carga_dia` y `fn_hay_cupo` de `schema.sql`; no reimplementar esa lógica en Python.
```

**Sección 8 (Pedidos), reemplazar el punto "Pago":**
```
- **Pago:** se registra en la tabla `pago` (monto, medio, referencia). Lo confirma SIEMPRE el staff, mirando el Yape/Plin real.
  El cliente puede adjuntar una captura de su pago como APOYO (tabla `comprobante_pago`), pero la captura nunca aprueba el pago ni
  mueve el pedido sola: puede estar editada. El staff abre su Yape, comprueba que llegó el monto exacto y recién ahí confirma.
  Confirmar = un solo botón, sin escribir el medio (se deduce: Yape si hay comprobante, efectivo si cobra en caja).
  No permitir pagar más que el total. `cobrado` sale de `v_pedido_resumen`.
```

**Sección 8, agregar al final:**
```
- **Orden en cocina:** en las columnas "En cocina" y "Listos" y en el tablero de cocina, los pedidos `recojo` van PRIMERO (el cliente espera afuera
  o avisa su llegada) y luego los `local`, cada grupo por hora de llegada. En "Pendientes" y "Por cobrar" el orden sigue siendo por llegada.
- **Mesa:** `mesa_referencia` es siempre opcional. Mostrarla solo si existe, sin repetir el texto ("Mesa 2", no "Mesa: Mesa 2").
```

**Sección 11 (Interfaz), reemplazar el punto de la pizarra:**
```
- Pizarra digital del día (reservas): una columna por franja horaria. **Cada reserva se dibuja completa SOLO en su franja de inicio**
  (nombre, código, personas, hora, hasta qué hora ocupa mesa, botones). En las franjas siguientes se muestra una línea compacta y apagada
  ("↳ Matías · 8 pax · continúa") sin botones; al tocarla se resalta la tarjeta original. La fila final de cada franja usa barras de progreso
  ("Personas 16/55", "Mesas 4/15") coloreadas según `nivel` (alerta / excedido) y muestra cuál recurso limita, con texto que no se corte en celular.
  Las reservas con `excede_cupo` llevan una marca visible. Las solicitudes `pendiente` van en un panel aparte.
```

**Sección 12 (Seguridad), agregar:**
```
Subidas de archivos: máximo 5 MB; aceptar solo imágenes JPEG, PNG o WebP verificadas por su contenido real (no por la extensión);
reconvertirlas y quitarles los metadatos; guardarlas en la base de datos (columna BYTEA), nunca en el disco ni en `static/`; los comprobantes solo los puede ver el staff y se borran pasados 30 días del cierre del pedido.
```

**Sección 14, punto 4, reemplazar por:**
```
4. Los cambios de base de datos se hacen en scripts repetibles dentro de `migraciones/` y, en las fases que lo indiquen explícitamente, también en `schema.sql`.
```

## 5. Prompts (pégalos de a uno, en orden)

> Antes de cada uno: rama nueva y `pytest` en verde. Después de cada uno: probar en el navegador lo que dice el "Criterio de terminado".

### 3.1 Arreglos urgentes (buscador y textos)

```
Contexto: AGENTS.md y el código actual. Fase 3 hecha, con errores. Esta es la Fase 3.1. No cambies reglas de negocio ni la base de datos.

Objetivo: que "Nuevo pedido en local" funcione y quitar fallos de interfaz.

Diagnóstico ya hecho (confírmalo leyendo el código antes de cambiar): app/templates/pedidos/nuevo.html usa la función esc() en las líneas ~98, ~101 y ~126,
pero esa función NO está definida en esa página; solo existe dentro de pizarra.html, cocina.html y static/js/js_pedidos.js. Al llegar resultados, el script falla con ReferenceError.

Haz:
1. Define esc(texto) UNA sola vez en app/static/js/main.js (escapa HTML; null/undefined devuelven cadena vacía) y que quede disponible globalmente.
   Quita las copias duplicadas de pizarra.html, cocina.html y js_pedidos.js SOLO si son equivalentes; si alguna difiere, déjala y avísame.
2. En nuevo.html: envuelve buscar() en try/catch y muestra en #resultados un mensaje claro si la petición falla (en vez de fallar en silencio).
   Si falta la etiqueta meta csrf-token, muestra un aviso visible.
3. Mesa: es opcional (ya lo es en el servicio). Comprueba que ni el HTML ni la API la exijan, y corrige la visualización para no repetir el texto:
   mostrar "Mesa 2" (no "Mesa: Mesa 2") y no mostrar nada si está vacía. Aplica en cola, cocina, detalle y ticket.
4. [Opcional, avísame si lo haces] En las páginas públicas (/, /carta, /reservar, /pedir), si hay una sesión de staff abierta, no mostrar el menú de staff
   ni la insignia de rol: mostrar solo una franja discreta "Sesión de staff abierta · Volver al panel". Las páginas del staff no cambian.
5. Pruebas con pytest: que /static/js/main.js defina esc; que crear un pedido local SIN mesa funcione; que /api/v1/platos/buscar devuelva resultados por nombre y por código.

No toques: schema.sql, servicios de reservas, estados de pedido.
Criterio de terminado: en /staff/pedidos/nuevo escribo "ceviche" y un número de plato y aparecen resultados con botón Agregar; creo un pedido sin mesa y llega a cocina.
Prueba en el navegador y reporta. Presenta el plan antes de programar.
```

### 3.2 Tiempo en mesa por tamaño del grupo + pizarra más clara

> Decisión tomada: `franja_min` se queda en 30 y 1 a 3 personas pasa a 30 min (sección 2a). El prompt no toca `franja_min`.

```
Contexto: AGENTS.md (secciones 7 y 11, ya actualizadas), schema.sql y el código actual. Esta es la Fase 3.2.

Objetivo: (A) el tiempo que una reserva ocupa mesa depende de su cantidad de personas; (B) la pizarra del día deja de verse "triplicada".

Parte A: duración por tamaño de grupo
1. Crea migraciones/001_duracion_por_grupo.sql, repetible (IF NOT EXISTS / CREATE OR REPLACE), que:
   a) agregue a config_local tres columnas INT NOT NULL con CHECK > 0: duracion_1_3_min (DEFAULT 30), duracion_4_7_min (DEFAULT 60), duracion_8_mas_min (DEFAULT 90);
      los valores por defecto (30, 60 y 90) son los que valen; no copies el valor de duracion_estadia_min;
   b) cree la función SQL fn_duracion_estadia(p_personas INT) RETURNS INT STABLE: de 1 a 3 → duracion_1_3_min; de 4 a 7 → duracion_4_7_min; de 8 en adelante → duracion_8_mas_min;
   c) reemplace fn_carga_dia y fn_hay_cupo para usar fn_duracion_estadia(cantidad_personas) en lugar de c.duracion_estadia_min;
   d) recién DESPUÉS de reemplazar las funciones, elimine la columna duracion_estadia_min (así no quedan dos fuentes de verdad).
   Actualiza schema.sql con exactamente el mismo resultado final (esta fase SÍ te autoriza a modificarlo) y seed.sql.
2. app/servicios/reservas.py (obtener_pizarra, ~línea 470): no calcules la duración en Python; agrega al SELECT de reservas el valor fn_duracion_estadia(r.cantidad_personas) AS duracion_min
   y a la respuesta de la API un campo nuevo "hasta" (hora de fin de ocupación, formato HH:MM). Solo AGREGA campos; no quites ni renombres ninguno.
3. Admin > Configuración: reemplaza el campo "Duración de estadía" por los tres campos (con etiquetas "1 a 3 personas", "4 a 7 personas", "8 o más personas"),
   con validación en servicios/configuracion.py (enteros > 0, paso de 5 min). Actualiza README y PASOS_PREVIOS donde mencionen duracion_estadia_min.
4. Ninguna columna nueva en reserva: la duración se deduce de cantidad_personas.

Parte B: pizarra
5. En pizarra.html cada reserva se dibuja COMPLETA solo en su franja de inicio: nombre, código, personas, hora, "hasta HH:MM", marcas (excede_cupo, atrasada) y botones.
6. En las franjas siguientes que la misma reserva ocupa, dibuja una línea compacta y apagada "↳ Nombre · N pax · continúa" SIN botones.
   Al tocarla, desplaza y resalta la tarjeta original. No uses el texto "continúa" en la tarjeta completa.
7. Fila final de cada franja: dos barras de progreso, "Personas 16/55" y "Mesas 4/15", coloreadas según el campo nivel que ya devuelve la API (ok, alerta, excedido),
   más el texto "Libres: 39 personas · 11 mesas" y cuál recurso limita. El texto no debe cortarse en celular (hoy se ve "pers./me sas" y "person as").
   Los libres negativos siguen en rojo. No recalcules nada en JavaScript: usa los valores de la API.
8. Mantén el refresco cada ~10 s y no cambies el orden de las franjas.

Pruebas con pytest: fn_duracion_estadia en los límites 1, 3, 4, 7, 8, 12 y 13; fn_hay_cupo con grupos de distinto tamaño en la misma hora;
fn_carga_dia muestra que un grupo de 8 ocupa 3 franjas de 30 min uno de 5 ocupa 2 y uno de 2 ocupa 1 (con franja de 30 min y los valores por defecto); la API del día incluye "hasta" y conserva todos los campos anteriores.
Actualiza las pruebas existentes que usaban duracion_estadia_min.

No toques: estados de reserva, tope por teléfono, tolerancia, pedidos.
Criterio de terminado: creo reservas de 2, 5 y 9 personas a la misma hora; en la pizarra cada una aparece como tarjeta completa una sola vez y como línea apagada en las franjas siguientes,
con "hasta" distinto; las barras de la fila final cambian de color al acercarse al límite. Prueba en el navegador y reporta. Presenta el plan antes de programar.
```

### 3.3 Pago con comprobante del cliente y un solo botón

```
Contexto: AGENTS.md (sección 8 y 12, ya actualizadas) y el código actual. Esta es la Fase 3.3.

Objetivo: el cliente adjunta una captura de su pago; el staff la ve, verifica en su Yape real que llegó el monto exacto y con UN botón el pedido pasa a cocina.
La captura es solo apoyo: nunca aprueba el pago ni mueve el pedido por sí sola.

Haz:
1. Crea migraciones/002_comprobante_pago.sql (repetible) y actualiza schema.sql (esta fase lo autoriza). Tabla comprobante_pago:
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

### 3.4 Orden de cocina, mesa y atajo para pedidos en local

```
Contexto: AGENTS.md (sección 8, ya actualizada) y el código actual. Esta es la Fase 3.4.

Objetivo: los pedidos para llevar se ven primero en cocina y quedan claramente etiquetados.

Haz:
1. En app/servicios/pedidos.py, obtener_cola y obtener_cocina: en "En cocina", "Listos" y en el tablero de cocina, ordena primero los pedidos de tipo recojo y luego los de tipo local,
   cada grupo por preparacion_en y luego por pedido_id. En "Pendientes" y "Por cobrar" el orden NO cambia (por llegada). Todo el orden se hace en la consulta SQL, no en JavaScript.
2. Etiqueta visible "PARA LLEVAR" en las tarjetas de recojo (y "LOCAL" en las demás) en cola y cocina.
3. No cambies la regla de cobro del recojo ni agregues estados. Los pedidos local siguen pasando por listo y entregado como hoy.

Pruebas con pytest: el orden de obtener_cola y obtener_cocina con pedidos mezclados (recojo primero, luego local); las transiciones válidas e inválidas siguen igual.
Criterio de terminado: con un recojo y dos locales en cocina, el recojo aparece primero y con la etiqueta; las columnas de pendientes y por cobrar conservan su orden. Prueba en el navegador y reporta.
Presenta el plan antes de programar.
```

### 3.5 Pedido del cliente tipo carrito

```
Contexto: AGENTS.md (secciones 3, 8, 11 y 12) y app/templates/publico/pedir.html. Esta es la Fase 3.5.

Objetivo: rediseñar SOLO la pantalla /pedir como un carrito de compras fácil en celular, sin cambiar el backend ni la API: el formulario debe seguir enviando los mismos campos
(items como JSON, nombre, telefono, correo, nota, acepta_datos, honeypot y CSRF). Stack: Bootstrap 5 y JavaScript vanilla, sin frameworks nuevos.

Haz:
1. Barra de categorías pegada arriba (chips con scroll horizontal); al tocar una, desplaza a su sección; la categoría visible se resalta mientras se hace scroll (IntersectionObserver).
   Buscador por nombre o número de plato (reusa la normalización sin tildes de la carta).
2. Cada plato en una tarjeta: nombre, número si lo tiene, descripción corta, precio y control +/−. Los agotados se ven apagados y no se pueden sumar.
   Deja un espacio reservado para una imagen que hoy muestra un cuadro neutro con un ícono (la Fase 3.6 la rellenará); sin imagen la tarjeta debe verse bien.
3. Barra flotante inferior "Ver pedido · N platos · S/ total", visible apenas haya algo en el carrito. Al tocarla abre un panel (offcanvas de Bootstrap) con las líneas, cambiar cantidad, quitar,
   campo de nota del pedido y el total estimado (el precio real lo vuelve a calcular el servidor).
4. Segundo paso dentro del panel: datos (nombre, teléfono 9 dígitos obligatorio, correo opcional, consentimiento) y botón "Enviar pedido". Mantén las validaciones del servidor.
5. El carrito se conserva en sessionStorage para que recargar no lo pierda; se limpia al enviar con éxito. No guardes datos personales en el navegador.
6. Respeta el banner "Sin conexión" y data-requiere-conexion. Accesible: botones con aria-label y foco visible.

Pruebas con pytest: POST a /pedir con items válidos crea el pedido igual que antes; plato agotado rechazado; la página renderiza las categorías y los platos activos.
Criterio de terminado: desde un celular (o el modo móvil del navegador) armo un pedido de 3 platos de 2 categorías, ajusto cantidades, lleno mis datos y lo envío; aparece en la cola del staff como Pendiente.
Prueba en el navegador y reporta. Presenta el plan antes de programar.
```

### 3.6 Imagen por plato (opcional; solo si hay fotos)

```
Contexto: AGENTS.md y app/servicios/archivos.py (Fase 3.3). Esta es la Fase 3.6.

Objetivo: cada plato puede tener una foto opcional que se ve en la carta pública y en /pedir.

Haz:
1. migraciones/003_plato_imagen.sql (repetible) y schema.sql: tabla plato_imagen (plato_id INT PK FK a plato, contenido BYTEA NOT NULL, tipo_mime VARCHAR(20) NOT NULL, actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()).
   Es una tabla aparte para que las consultas de plato no arrastren los bytes. Sin fila = plato sin imagen.
2. Reutiliza servicios/archivos.py (mismas validaciones y quitar metadatos) con lado máximo 800 px y calidad ajustada para que cada imagen pese menos de 200 KB. Se guarda en la base, no en el disco.
3. Carta Staff: al crear o editar un plato, campo opcional "Foto" y botón para quitarla. Al reemplazarla se sobrescribe la fila; al quitarla se borra.
4. Ruta pública GET /img/plato/<plato_id> que entrega la foto con cabeceras de caché; si no hay foto, devuelve un ícono neutro. Estas imágenes SÍ son públicas (a diferencia de los comprobantes).
5. Mostrar la imagen en /carta y en las tarjetas de /pedir (con carga diferida, loading="lazy"). Sin imagen, la tarjeta sigue viéndose bien.

Pruebas: subida válida; archivo no imagen rechazado; reemplazar sobrescribe y quitar elimina la imagen; /img/plato/<id> devuelve imagen o ícono; la carta pública carga sin fotos.
Criterio de terminado: subo la foto de dos platos desde Carta Staff y aparecen en la carta pública y en /pedir; los demás platos siguen bien sin foto. Prueba en el navegador y reporta. Presenta el plan antes de programar.
```

## 6. Decisiones tomadas

1. `franja_min` se queda en 30. Tiempos por defecto: 1 a 3 personas 30 min, 4 a 7 personas 60 min, 8 o más 90 min (editables en Configuración). Pendiente: validar con la dueña cuánto se quedan de verdad los grupos chicos.
2. Atajo "local directo a entregado": descartado por ahora.
3. Fotos de platos: aún no hay; se piden a la dueña cuando llegue la 3.6.
4. Imágenes en la base de datos (no en el disco); comprobantes con borrado a los 30 días.
5. Pendiente: si se paga hosting para el local real (sección 7).

## 7. Hosting y costos (consultado el 27/10/2026; confirma en la página de cada proveedor antes de pagar)

| Opción | Costo aproximado | Para qué sirve |
|---|---|---|
| Render gratis (web + Postgres) | $0 | Solo demo. La web se duerme tras 15 min sin tráfico (despierta en ~1 min) y el Postgres gratuito caduca a los 30 días. |
| Supabase gratis (solo base de datos y archivos) | $0 | Solo demo. 500 MB de base, 1 GB de archivos; el proyecto se pausa tras 1 semana sin actividad. No aloja Flask. |
| Render de pago (web Starter + Postgres básico) | ≈ $13/mes juntos (cifra de Render, julio 2026) | Local real sin administrar servidores. Disco persistente opcional: $0.25 por GB al mes. |
| Railway Hobby | $5/mes que incluyen $5 de uso | Cobra por consumo; con web y Postgres siempre encendidos suele pasar de $5, es menos predecible. |
| VPS (Hetzner, DigitalOcean) | desde unos €4 a €8 o $4 a $6 al mes, según plan y fuente (Hetzner subió precios en abril 2026) | El más barato, pero tú instalas y mantienes Postgres, servidor web, HTTPS y respaldos. |
| PythonAnywhere | plan pago base entre $5 y $10 (las fuentes difieren) | Mal encaje: Postgres solo en planes superiores. |

**Mi recomendación:** no elimines las imágenes. Guárdalas en la base de datos y el problema del disco desaparece en cualquier hosting. Para la entrega a la profesora, el plan gratuito sirve. Para el local operando, el gratuito no sirve (la base caduca o se pausa) y lo más simple es Render de pago, unos $13 al mes; el VPS es más barato pero exige administrarlo.
