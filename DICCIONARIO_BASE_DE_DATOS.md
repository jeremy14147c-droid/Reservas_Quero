# Diccionario de la base de datos – Quero APP (actualizado a `schema.sql` v3)

Explica **columna por columna**: qué guarda, por qué tiene ese tipo, por qué es `NOT NULL` o `NULL`, y qué pasa si falta el dato.

**Cambios respecto a la versión anterior de este documento** (decisiones tomadas desde entonces):

| Cambio | Detalle |
|---|---|
| `cliente.documento` **eliminado** | Ningún formulario lo pedía y es un dato personal sin uso. |
| `cliente.correo` sigue **opcional** y no único | Se descartó el correo obligatorio y la verificación por código. |
| `config_local.umbral_alerta_pct` **nuevo** | % de ocupación desde el cual una franja pasa a "alerta". |
| `config_local.max_reservas_web_por_telefono` **nuevo** | Tope de reservas web por teléfono en 24 h (por defecto 2). |
| `reserva.excede_cupo` **nuevo** | Marca las reservas que el staff aceptó aun superando el cupo. |
| `plato.codigo` **nuevo** | Número corto y opcional para buscar un plato (no es el ID). |
| Vista `v_cliente_actividad_24h` **nueva** | Pedidos y reservas recientes del cliente. |
| `fn_carga_dia` devuelve `nivel` | `ok`, `alerta` o `excedido`. |

Siguen **sin decidir** los puntos D1, D2, D4, D5, D6, D7, D9 a D21 de la sección 8. Mientras no se decidan, esas columnas y tablas permanecen en el esquema.

## 0. Cómo leer este documento

- **NOT NULL (obligatoria):** la base rechaza guardar la fila si ese dato no viene. Ejemplo: `nombre` en `cliente` es NOT NULL, así que no se puede registrar un cliente sin nombre.
- **NULL (opcional):** la columna puede quedar vacía. "Vacío" significa *sin valor* (NULL), no un texto en blanco ni un cero.
- **PK (llave primaria):** identifica de forma única cada fila de la tabla.
- **FK (llave foránea):** apunta a una fila de otra tabla; la base impide apuntar a algo que no existe.
- **Estado:** "OK" si se queda como está; "D#" si está pendiente de debate (sección 8); "Nuevo" si se añadió en esta versión.
- **Quién hace cumplir la regla:** donde diga "la app", la base de datos **no** lo impide; lo valida el código de Flask. Donde diga "la base", es imposible saltárselo.

## 1. Glosario de términos poco conocidos

| Término | Qué significa |
|---|---|
| **INT / SMALLINT** | Número entero. INT llega a unos 2 mil millones; SMALLINT a unos 32 mil y ocupa la mitad de espacio. Se usa SMALLINT en porcentajes y contadores chicos. |
| **VARCHAR(n)** | Texto de hasta *n* caracteres. El límite evita textos absurdamente largos. |
| **BOOLEAN** | Verdadero o falso (TRUE / FALSE). Sirve para interruptores como `activo` o `disponible`. |
| **NUMERIC(10,2)** | Decimal exacto: hasta 10 dígitos en total, 2 decimales. Se usa para dinero porque no comete errores de redondeo como los decimales "flotantes" (con ellos, 0.1 + 0.2 puede dar 0.30000000000000004). |
| **DATE** | Solo una fecha (día, mes, año). |
| **TIME** | Solo una hora del día, sin fecha ni zona horaria. |
| **TIMESTAMPTZ** | "Timestamp with time zone". Guarda un **instante exacto** (fecha + hora + segundos). Por dentro lo guarda en UTC y, al mostrarlo, lo convierte a la zona de la conexión (Lima, UTC−5). **No guarda la zona**, guarda el momento. Sirve para eventos que ocurrieron ("se creó", "se aceptó"): restar dos instantes da el tiempo real transcurrido (el temporizador de cocina) y no se desfasa si el servidor del hosting trabaja en otra zona, algo común (los servidores suelen estar en UTC). |
| **DATE + TIME separados (en `reserva`)** | La reserva es una cita "a las 8:00 pm del 25 de octubre en el local": una **hora de reloj del local**, no un instante. Por eso se guarda sin zona, y la pizarra filtra por día y pinta horas. Unirlos en un solo campo también sería válido (ver D12). |
| **UUID** | Código largo, aleatorio e imposible de adivinar (ej. `3f2b...`). Va en los enlaces del cliente para que nadie vea pedidos ajenos cambiando un número en la dirección. |
| **gen_random_uuid()** | Función de la base que genera un UUID nuevo automáticamente. |
| **now()** | Función que devuelve el instante actual. Se usa como valor por defecto de las fechas de creación. |
| **GENERATED ALWAYS AS IDENTITY** | La base asigna sola un número creciente (1, 2, 3...). `ALWAYS` significa que ni siquiera la app puede escribirlo a mano. Es el "autoincremental". |
| **DEFAULT** | Valor que se usa si no se indica ninguno al guardar. |
| **UNIQUE** | No puede haber dos filas con el mismo valor en esa columna. En PostgreSQL, varias filas con NULL **sí** pueden convivir en una columna UNIQUE (un NULL no se considera igual a otro NULL). |
| **CHECK** | Regla que el dato debe cumplir (ej. `cantidad > 0`). Si no la cumple, se rechaza. |
| **CHECK ... IN (...)** | El dato solo puede ser uno de una lista cerrada (ej. `rol` solo `admin` o `empleado`). Se usa en lugar de ENUM porque agregar valores después es más fácil. |
| **Índice** | "Índice de libro": hace rápida la búsqueda por esa columna. Las columnas UNIQUE ya tienen uno. |
| **Índice único parcial (`WHERE`)** | Un UNIQUE que solo aplica a algunas filas. En `reserva` impide dos reservas **activas** del mismo cliente a la misma fecha y hora, pero permite repetir si una está cancelada. |
| **Índice sobre `lower(correo)`** | Compara el correo en minúsculas, así `Ana@x.com` y `ana@x.com` cuentan como el mismo. |
| **Hash de contraseña** | La contraseña transformada con una fórmula que no se puede revertir. Se guarda el hash, nunca la contraseña real. |
| **Expresión regular (`~ '^9[0-9]{8}$'`)** | Patrón de texto: empieza con 9 y lleva 8 dígitos más (9 en total), como un celular peruano. |
| **ON DELETE CASCADE** | Si se borra la fila "padre", se borran sus filas "hijas". En `detalle_pedido`, borrar un pedido borra sus líneas. |
| **Vista (VIEW)** | Consulta guardada con nombre que se usa como una tabla. No guarda datos propios. |
| **Función (FUNCTION)** | Cálculo guardado en la base que recibe datos y devuelve un resultado. |
| **num_nonnulls(a, b)** | Cuenta cuántos valores no están vacíos. Se usa para exigir que una notificación tenga exactamente un origen. |

## 2. Tablas

Orden de creación (respeta las FK): `personal`, `config_local`, `cliente`, `categoria`, `plato`, `reserva`, `pedido`, `detalle_pedido`, `pago`, `notificacion`.

### 2.1 `personal` – Usuarios con login (admin y empleado)
El cliente **no** está aquí: no tiene cuenta ni contraseña.

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `personal_id` | INT identity, PK. Un entero basta: el personal son pocas personas. | NOT NULL. La base lo asigna sola. | Identifica a la persona. Otras tablas lo usan para saber **quién** hizo algo (`creado_por`, `confirmado_por`). | OK |
| `nombre` | VARCHAR(100). Texto corto. | NOT NULL. No se puede crear una cuenta sin nombre. | Nombre que se ve en el panel y en "quién cobró o creó". | OK |
| `correo` | VARCHAR(120). Texto con límite razonable. Índice único sobre `lower(correo)`. | NOT NULL. Sin correo no hay login; dos cuentas no pueden compartirlo (sin importar mayúsculas). | Es el **usuario para iniciar sesión**. | OK |
| `password_hash` | VARCHAR(255). Largo suficiente para el hash que genera Flask/Werkzeug. | NOT NULL. Toda cuenta tiene clave. | Guarda la contraseña como hash. Ni el admin puede ver la original. | OK |
| `rol` | VARCHAR(10) con CHECK (`admin` o `empleado`). | NOT NULL. Cualquier otro valor se rechaza. | `admin` (dueña: configuración y personal) o `empleado` (operación diaria). Define qué pantallas ve. | OK |
| `activo` | BOOLEAN, DEFAULT TRUE. Solo hay dos estados. | NOT NULL. Si no se indica, la cuenta queda activa. | Desactiva una cuenta sin borrarla, para conservar quién hizo qué. Una cuenta inactiva no puede entrar. | OK |
| `debe_cambiar_clave` | BOOLEAN, DEFAULT TRUE. | NOT NULL. Por defecto TRUE; el primer admin (comando `crear-admin`) se crea con FALSE. | Obliga a cambiar la contraseña en el primer ingreso de cuentas creadas por el admin. | OK |
| `creado_en` | TIMESTAMPTZ, DEFAULT `now()`. Es un evento ocurrido, necesita instante exacto. | NOT NULL. La base la llena sola. | Cuándo se creó la cuenta. | OK |

### 2.2 `config_local` – Configuración del local (una sola fila)
Todo lo que la dueña ajusta vive aquí, no en el código. `config_id = 1` (con CHECK) impide tener dos filas.

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `config_id` | SMALLINT, PK, DEFAULT 1, CHECK = 1. | NOT NULL. Nunca se toca. | Truco para que exista **una sola** configuración. | OK |
| `nombre_local` | VARCHAR(100). | NOT NULL. La web pública lo necesita siempre. | Nombre del local en la web y en los tickets. | OK |
| `aforo_personas` | INT, CHECK > 0. Cantidad de personas, entero positivo. | NOT NULL. Sin él no se calcula el cupo de reservas. | Máximo de personas dentro del local. | OK |
| `total_mesas` | INT, CHECK > 0. | NOT NULL, por el mismo motivo. | Cantidad de mesas. Es un límite **distinto** al aforo: con muchas reservas de 2 o 3 personas las mesas se acaban aunque el aforo no esté lleno. | OK |
| `personas_por_mesa` | INT, CHECK > 0. | NOT NULL. Sin él no se pueden calcular las mesas que ocupa un grupo. | Personas que se sientan por mesa en promedio. Convierte personas en mesas (redondeo hacia arriba). | OK |
| `duracion_1_3_min` | INT en minutos, CHECK > 0. DEFAULT 30. | NOT NULL. Sin él no se sabe cuándo termina la mesa de un grupo chico. | Cuánto tiempo ocupa mesa un grupo de 1 a 3 personas. El sistema libera el cupo solo, sin que nadie registre la salida. | OK |
| `duracion_4_7_min` | INT en minutos, CHECK > 0. DEFAULT 60. | NOT NULL. Idem para grupos medianos. | Cuánto tiempo ocupa mesa un grupo de 4 a 7 personas. | OK |
| `duracion_8_mas_min` | INT en minutos, CHECK > 0. DEFAULT 90. | NOT NULL. Idem para grupos grandes. | Cuánto tiempo ocupa mesa un grupo de 8 personas o más. La función SQL `fn_duracion_estadia(personas)` elige la columna que corresponde según el tamaño del grupo; nada recibe la duración desde Python. | OK |
| `franja_min` | INT, solo 15, 30 o 60; DEFAULT 30. | NOT NULL. Si no se indica, 30. | Ancho de cada columna de la pizarra y de los horarios que se pueden elegir. | OK |
| `tolerancia_min` | INT en minutos, CHECK ≥ 0. | NOT NULL. 0 significa sin tolerancia. | **Solo referencia:** pasados estos minutos desde la hora de la reserva, la app la **alerta** en rojo. No libera ni cancela nada. El staff decide si libera (`no_llego`) o reprograma. | OK |
| `umbral_preparacion_min` | INT en minutos, CHECK > 0. | NOT NULL. | Minutos en cocina desde los cuales un pedido se resalta en rojo. También es solo visual. | OK |
| `max_reservas_web_por_telefono` | SMALLINT, DEFAULT 2, CHECK ≥ 1. Contador chico. | NOT NULL. Si no se indica, 2. | Tope de reservas que un mismo teléfono puede pedir **por la web** en 24 h. El staff no tiene tope. **La base solo guarda el número; quien bloquea es la app**, comparándolo con `v_cliente_actividad_24h.reservas_web_24h`. | Nuevo |
| `umbral_alerta_pct` | SMALLINT, DEFAULT 80, CHECK entre 1 y 100. Es un porcentaje. | NOT NULL. Si no se indica, 80. | Desde este % de ocupación (personas o mesas, lo que esté más lleno), `fn_carga_dia` marca la franja como `alerta` (amarillo, "a punto de llenarse"). | Nuevo |
| `hora_apertura` | TIME. Es hora del día, sin fecha. | NOT NULL. Sin ella no se generan franjas. | Inicio del horario reservable y de la pizarra. | OK |
| `hora_cierre` | TIME. | NOT NULL. Debe ser mayor que la apertura (`ck_config_horario`). | Fin del horario. **No permite cerrar pasada la medianoche.** | D9 |
| `dias_max_anticipacion` | INT, CHECK ≥ 0. | NOT NULL. 0 = solo se reserva para hoy. | Con cuántos días de anticipación se puede reservar. La web lo usa para limitar el calendario. | OK |
| `porcentaje_reservable` | SMALLINT, CHECK entre 1 y 100. | **NULL permitido, a propósito.** Vacío = 100 %, sin límite adicional. | Qué porcentaje de personas y mesas pueden ocupar las **reservas**; el resto queda libre para quien llega sin reserva. | OK |
| `abierto` | BOOLEAN, DEFAULT TRUE. | NOT NULL. Por defecto abierto. | Indicaría si el local está abierto. **Hoy ninguna pantalla lo usa.** | D1 |
| `yape_numero` | VARCHAR(15). Texto porque es un número de contacto, no se hacen cuentas con él. | **NULL permitido.** Si queda vacío, la pantalla de pago no tiene qué mostrar. Hay que llenarlo antes de aceptar pedidos de recojo. | Número al que el cliente paga por Yape. | OK |
| `yape_titular` | VARCHAR(100). | **NULL permitido.** Si queda vacío, se muestra solo el número. | Nombre del titular, para que el cliente verifique que paga a la cuenta correcta. | OK |
| `mensaje_pago` | VARCHAR(300). | **NULL permitido.** Si queda vacío, no se muestra nada. | Texto extra junto a las instrucciones de pago. Probablemente innecesario. | D2 |

### 2.3 `cliente` – Quien reserva o pide (sin cuenta)
Se identifica por teléfono y se reutiliza si vuelve. No hay cuenta, contraseña ni verificación por código: el staff comprueba el teléfono al escribirle por WhatsApp antes de confirmar. Según `AGENTS.md`, si el teléfono ya existe se reutiliza la ficha **sin** sobrescribir nombre ni correo.

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `cliente_id` | INT identity, PK. | NOT NULL. La base lo asigna. | Identifica al cliente. | OK |
| `nombre` | VARCHAR(100). | NOT NULL. Sin nombre no se registra reserva ni pedido de recojo. | Cómo llamar al cliente; sale en el ticket. | OK |
| `telefono` | VARCHAR(9), UNIQUE, CHECK con patrón (9 dígitos que empiezan en 9). Es **texto** porque no se hacen cuentas con él y así no se pierden ceros. | NOT NULL. Sin teléfono no se puede contactar. Dos clientes no pueden compartir teléfono. | Medio de contacto (menú ⋮, WhatsApp) y llave para reconocerlo si vuelve. **Solo acepta celulares peruanos.** | D8 |
| `correo` | VARCHAR(120). Índice parcial sobre `lower(correo)` solo donde hay correo. | **NULL permitido.** Vacío = no hay confirmación por correo; el contacto sigue por teléfono. **No es único:** una familia puede compartirlo, y fusionar fichas por un dato no verificado es peor que tener un duplicado. | Correo opcional del cliente. | OK |
| `acepta_datos` | BOOLEAN con CHECK que exige TRUE. | NOT NULL. No se guarda un cliente que no aceptó. Como siempre es TRUE, **no aporta información**. | Constancia de que aceptó el uso de sus datos. | D4 |
| `acepta_datos_en` | TIMESTAMPTZ, DEFAULT `now()`. | NOT NULL. La base la llena sola. | Cuándo aceptó. Es la evidencia útil del consentimiento. | OK |
| `creado_en` | TIMESTAMPTZ, DEFAULT `now()`. | NOT NULL. | Cuándo se registró por primera vez. | OK |

### 2.4 `categoria` – Grupos de la carta

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `categoria_id` | INT identity, PK. | NOT NULL. | Identifica la categoría. | OK |
| `nombre` | VARCHAR(50), UNIQUE. | NOT NULL. No puede haber dos categorías con el mismo nombre. | Título de la categoría en la carta. | OK |
| `orden` | SMALLINT, DEFAULT 0. Pocas categorías, número chico. | NOT NULL. Por defecto 0 (empatan y se ordenan por nombre). | Posición en la carta (menor número primero). | OK |
| `activa` | BOOLEAN, DEFAULT TRUE. | NOT NULL. Por defecto visible. | Oculta una categoría sin borrarla. | OK |

### 2.5 `plato` – Carta
Un plato con dos precios (personal/fuente, 1 L/1½ L) se registra como **dos platos**, uno por tamaño, cada uno con su precio y su código. Los sabores sin cambio de precio van en la nota del pedido, no como platos distintos. Los ingredientes van en `descripcion`.

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `plato_id` | INT identity, PK. | NOT NULL. | Identificador interno. **No** es el número que ve el usuario en la carta. | OK |
| `categoria_id` | INT, FK → `categoria`. | NOT NULL. No existe un plato sin categoría; pertenece a una sola. | A qué grupo de la carta pertenece. | OK |
| `codigo` | INT, UNIQUE, CHECK > 0. Entero para que `1` coincida exactamente con el plato 1 y no con el 10 o el 11. | **NULL permitido.** Vacío = el plato aún no tiene número. Varios platos pueden estar sin código a la vez (PostgreSQL permite varios NULL en UNIQUE). Si se repite un número, la base rechaza. No acepta 0 ni negativos. | Número corto para buscar el plato en "Nuevo pedido en local" (como alternativa a nombre o categoría). Lo define la dueña. Un plato desactivado conserva su número reservado. **Hoy la carta física no tiene números:** hay que numerarla o pegarlos. | Nuevo |
| `nombre` | VARCHAR(100). | NOT NULL. | Nombre en la carta, el pedido y el ticket. Para variantes, incluye el tamaño ("— Personal"). | OK |
| `descripcion` | VARCHAR(300). | **NULL permitido.** Vacío = la carta muestra solo nombre y precio. | Texto opcional (ingredientes, tamaño). | D7 |
| `precio` | NUMERIC(10,2), CHECK ≥ 0. Dinero exacto. | NOT NULL. Sin precio no se puede vender. Acepta 0 (cortesías). | Precio vigente de la carta. | OK |
| `disponible` | BOOLEAN, DEFAULT TRUE. | NOT NULL. Por defecto disponible. | Interruptor "plato agotado": un plato no disponible no se puede pedir. Cambia varias veces al día. | OK |
| `activo` | BOOLEAN, DEFAULT TRUE. | NOT NULL. Por defecto activo. | Retira un plato de la carta **sin borrarlo**, porque puede estar en pedidos pasados. | OK |

Diferencia: `disponible` = "se acabó hoy, vuelve mañana"; `activo` = "ya no se vende".

### 2.6 `reserva` – Reservas de mesa

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `reserva_id` | INT identity, PK. | NOT NULL. | Identificador interno. | OK |
| `codigo` | VARCHAR(12), UNIQUE. Texto corto que genera la app. | NOT NULL. Toda reserva tiene código y no se repite. | Código que cliente y staff usan para nombrar la reserva; sale en el ticket y en el QR. | OK |
| `token` | UUID, UNIQUE, DEFAULT `gen_random_uuid()`. UUID para que no se pueda adivinar. | NOT NULL. La base lo genera sola. | Va en el enlace de seguimiento del cliente. | OK |
| `cliente_id` | INT, FK → `cliente`. | NOT NULL. No hay reserva sin cliente. | Quién reservó. | OK |
| `fecha` | DATE. | NOT NULL. La pizarra filtra por día. | Día de la reserva. | D12 |
| `hora` | TIME. Hora de reloj del local, no un instante. | NOT NULL. | Hora de llegada. | D12 |
| `hora_anterior` | TIME. | **NULL permitido.** Vacío = nunca se cambió. | Hora previa tras un cambio; permite el ticket "ANTES → AHORA". **Solo guarda el último cambio:** si se reprograma dos veces, se pierde la primera hora. | D13 |
| `cantidad_personas` | INT, CHECK > 0. | NOT NULL. | Tamaño del grupo. Con él se calculan mesas y aforo. | OK |
| `estado` | VARCHAR(12), CHECK, DEFAULT `pendiente`. | NOT NULL. Valores: `pendiente`, `confirmada`, `rechazada`, `cancelada`, `llego`, `no_llego`. | Solo `confirmada` y `llego` ocupan cupo. Las `pendiente` **no**. `no_llego`, `cancelada` y `rechazada` liberan el cupo. `no_llego` es estado final: si el cliente aparece después, se crea una reserva nueva. | OK |
| `canal` | VARCHAR(5), CHECK (`web` o `staff`), DEFAULT `staff`. | NOT NULL. | Cómo entró la reserva. Agregar WhatsApp como canal requiere cambiar este CHECK. | OK |
| `excede_cupo` | BOOLEAN, DEFAULT FALSE. | NOT NULL. Por defecto FALSE. | TRUE cuando el staff confirmó o creó la reserva **aun superando** el cupo. Sirve para saber después qué reservas se forzaron. Es una marca del momento: si luego se cancelan otras reservas, la marca no se recalcula. | Nuevo |
| `nota` | VARCHAR(300). | **NULL permitido.** | Comentario del cliente o del staff (cumpleaños, silla de bebé). | OK |
| `motivo` | VARCHAR(200). | **NULL permitido.** Vacío en reservas normales. La app debe exigirlo al rechazar o cancelar (la base no lo exige). | Por qué se rechazó o canceló. | OK |
| `creado_por` | INT, FK → `personal`. | **NULL permitido.** Vacío = la pidió el cliente por la web. | Qué empleado la creó. | D14 |
| `creado_en` | TIMESTAMPTZ, DEFAULT `now()`. | NOT NULL. | Cuándo se solicitó. Con él se cuentan las reservas web de las últimas 24 h. | OK |
| `actualizado_en` | TIMESTAMPTZ, DEFAULT `now()`. | NOT NULL. **No se actualiza solo:** la app debe llenarlo en cada cambio. | Última modificación. | D11 |

**Reglas de la tabla (las hace cumplir la base):**
- `ux_reserva_cliente_fecha_hora`: un cliente no puede tener dos reservas `pendiente`, `confirmada` o `llego` a la misma fecha y hora. Una `no_llego`, `cancelada` o `rechazada` no cuenta.
- `ck_reserva_forzar_solo_staff`: una reserva en estado `pendiente`, de canal `web` y sin `creado_por` **no puede** venir con `excede_cupo = TRUE`. La web nunca fuerza el cupo. Ojo: la regla solo cubre ese caso; si el staff confirma después una reserva web sobre el cupo, `excede_cupo` sí puede quedar en TRUE.
- No hay columna de mesa: el sistema **cuenta** mesas, no las asigna.

### 2.7 `pedido` – Pedidos de recojo y de local
Los pedidos **no** se limitan por aforo ni por mesas.

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `pedido_id` | INT identity, PK. | NOT NULL. | Número de pedido que sale en el ticket. | OK |
| `token` | UUID, UNIQUE, DEFAULT aleatorio. | NOT NULL. | Enlace de seguimiento del cliente. | OK |
| `cliente_id` | INT, FK → `cliente`. | **NULL permitido.** En `recojo` es **obligatorio** (hay que avisarle); en `local` puede quedar vacío (cliente anónimo en mesa). Lo garantiza `ck_pedido_cliente`. | Quién pidió. | OK |
| `reserva_id` | INT, FK → `reserva`. | **NULL permitido.** Vacío = cliente sin reserva (walk-in). **Ninguna pantalla lo llena hoy.** | Reserva de la que viene el pedido. | D6 |
| `tipo` | VARCHAR(6), CHECK (`local` o `recojo`). | NOT NULL. | `local`: cliente presente, lo crea el staff. `recojo`: lo pide el cliente por la web. Define el flujo. Delivery no existe todavía. | OK |
| `canal` | VARCHAR(5), CHECK (`web` o `staff`), DEFAULT `staff`. | NOT NULL. | Quién lo registró. | OK |
| `estado` | VARCHAR(14), CHECK, DEFAULT `pendiente`. | NOT NULL. Valores: `pendiente`, `aceptado`, `en_preparacion`, `listo`, `entregado`, `rechazado`, `cancelado`. | Las transiciones válidas las controla la app. En recojo, el staff no acepta ni imprime hasta confirmar el pago real. | OK |
| `mesa_referencia` | VARCHAR(20). Texto libre porque no existe tabla de mesas. | **NULL permitido.** Vacío en recojo. | Mesa del pedido en local (ej. "Mesa 4"). | OK |
| `nota` | VARCHAR(300). | **NULL permitido.** | Comentario general. Aquí van los sabores sin cambio de precio. | OK |
| `motivo_rechazo` | VARCHAR(200). | **NULL permitido.** Vacío salvo en rechazados; la app lo exige al rechazar. | Por qué se rechazó. | OK |
| `creado_por` | INT, FK → `personal`. | **NULL permitido.** Vacío = lo pidió el cliente por la web. | Qué empleado lo registró. | D14 |
| `creado_en` | TIMESTAMPTZ, DEFAULT `now()`. | NOT NULL. | Cuándo entró. | OK |
| `aceptado_en` | TIMESTAMPTZ. | **NULL permitido.** Vacío mientras esté pendiente. | Cuándo lo aceptó el staff. | D13 |
| `preparacion_en` | TIMESTAMPTZ. | **NULL permitido.** Vacío hasta pasar a `en_preparacion`. En recojo pasa un rato entre aceptado y cobrado, por eso es columna aparte. | Cuándo entró a cocina. **Base del temporizador** de cocina. | OK |
| `listo_en` | TIMESTAMPTZ. | **NULL permitido.** | Cuándo cocina lo marcó listo. Con `preparacion_en` da el tiempo de preparación. | OK |
| `entregado_en` | TIMESTAMPTZ. | **NULL permitido.** | Cuándo se entregó. | OK |

**Regla de la tabla:** `recojo` exige cliente; `local` puede ser anónimo. El **total no se guarda**: lo calcula la vista `v_pedido_resumen`.

### 2.8 `detalle_pedido` – Líneas de cada pedido

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `detalle_id` | INT identity, PK. | NOT NULL. | Identifica la línea. Así un mismo plato puede repetirse en dos líneas con notas distintas. | OK |
| `pedido_id` | INT, FK → `pedido`, ON DELETE CASCADE. | NOT NULL. No existe una línea sin pedido. Si se borra el pedido, se borran sus líneas (la app no debería borrar pedidos: los cancela). | A qué pedido pertenece. | OK |
| `plato_id` | INT, FK → `plato`. | NOT NULL. | Qué plato se pidió. | OK |
| `cantidad` | INT, CHECK > 0. | NOT NULL. No acepta 0 ni negativos. | Cuántas unidades. | OK |
| `precio_venta` | NUMERIC(10,2), CHECK ≥ 0. | NOT NULL. La app lo copia del precio del plato al crear la línea. | Precio **al momento del pedido**: si la carta sube mañana, los pedidos viejos no cambian. | OK |
| `nota` | VARCHAR(200). | **NULL permitido.** | Indicación de esa línea (sin ají, bien cocido). | OK |

### 2.9 `pago` – Cobros registrados por el staff

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `pago_id` | INT identity, PK. | NOT NULL. | Identifica el pago. | OK |
| `pedido_id` | INT, FK → `pedido`. | NOT NULL. Un pedido puede tener varios pagos. | Qué pedido se paga. | OK |
| `monto` | NUMERIC(10,2), CHECK > 0. | NOT NULL. No acepta cero ni negativos. La app impide pagar más que el total. | Cuánto se cobró. | OK |
| `medio` | VARCHAR(13), CHECK (`efectivo`, `yape`, `plin`, `transferencia`, `otro`). | NOT NULL. | Cómo pagó el cliente. | OK |
| `referencia` | VARCHAR(60). | **NULL permitido.** Vacío en efectivo. | Número de operación (Yape, transferencia). | OK |
| `confirmado_por` | INT, FK → `personal`. | NOT NULL. Todo pago lo confirma una persona identificada. | Qué empleado verificó el pago. Es la responsabilidad del cobro. | OK |
| `confirmado_en` | TIMESTAMPTZ, DEFAULT `now()`. | NOT NULL. | Cuándo se confirmó. | OK |

Limitación: **un pago no se puede anular** (D10). Esta tabla es el punto de enlace futuro con ingresos y egresos.

### 2.10 `notificacion` – Registro de avisos (proyecto final)

| Columna | Tipo y por qué | NOT NULL / NULL y qué pasa | Qué hace | Estado |
|---|---|---|---|---|
| `notificacion_id` | INT identity, PK. | NOT NULL. | Identifica el aviso. | D5 |
| `tipo` | VARCHAR(30). Texto libre (sin CHECK) para añadir tipos sin tocar la base. | NOT NULL. | Qué se avisó (`reserva_confirmada`, `pedido_aceptado`, `pedido_listo`...). | D5 |
| `canal` | VARCHAR(10), CHECK (`correo` o `whatsapp`). | NOT NULL. | Por dónde se avisó. | D5 |
| `destino` | VARCHAR(120). | NOT NULL. | Correo o teléfono al que se envió. | D5 |
| `reserva_id` | INT, FK → `reserva`. | **NULL permitido.** Se llena solo si el aviso es de una reserva. | Reserva relacionada. | D5 |
| `pedido_id` | INT, FK → `pedido`. | **NULL permitido.** Se llena solo si es de un pedido. | Pedido relacionado. | D5 |
| `estado` | VARCHAR(10), CHECK, DEFAULT `pendiente`. | NOT NULL. Valores: `pendiente`, `enviada`, `fallida`, `manual` (el staff abrió el enlace de WhatsApp). | Permite reintentar las fallidas. | D5 |
| `error` | VARCHAR(300). | **NULL permitido.** Vacío si no hubo error. | Mensaje del fallo. | D5 |
| `creado_en` | TIMESTAMPTZ, DEFAULT `now()`. | NOT NULL. | Cuándo se generó. | D5 |
| `enviada_en` | TIMESTAMPTZ. | **NULL permitido.** Vacío mientras no se envió. | Cuándo se envió. | D5 |

**Regla de la tabla:** exactamente **uno** de `reserva_id` o `pedido_id` debe tener valor (`num_nonnulls = 1`). **No se usa hasta el proyecto final** (D5).

## 3. Relaciones (llaves foráneas)

| Desde | Hacia | Significado | Obligatoria |
|---|---|---|---|
| `plato.categoria_id` | `categoria` | Un plato tiene una categoría | Sí |
| `reserva.cliente_id` | `cliente` | Quién reservó | Sí |
| `reserva.creado_por` | `personal` | Quién la creó | No (vacío si vino de la web) |
| `pedido.cliente_id` | `cliente` | Quién pidió | Solo en `recojo` |
| `pedido.reserva_id` | `reserva` | Pedido de una reserva | No |
| `pedido.creado_por` | `personal` | Quién lo registró | No |
| `detalle_pedido.pedido_id` | `pedido` | Líneas del pedido (se borran con él) | Sí |
| `detalle_pedido.plato_id` | `plato` | Qué plato es la línea | Sí |
| `pago.pedido_id` | `pedido` | Qué pedido se paga | Sí |
| `pago.confirmado_por` | `personal` | Quién confirmó el cobro | Sí |
| `notificacion.reserva_id` / `pedido_id` | `reserva` / `pedido` | Origen del aviso | Exactamente uno |

## 4. Vistas y funciones que se toman en cuenta
Son cálculos que **no se guardan**: se calculan al consultar para no tener datos duplicados que se desactualicen.

### 4.1 Vista `v_pedido_resumen`
- **Qué calcula:** por pedido, `total` (suma de cantidad × `precio_venta`), `pagado` (suma de pagos) y `cobrado` (TRUE si hay total y lo pagado lo cubre).
- **Dónde se usa:** cola de pedidos, detalle, validar que no se pague de más y decidir cuándo un pedido de recojo pasa a cocina.
- **Detalles:** un pedido sin líneas tiene total 0 y **no** se considera cobrado. Un pago equivocado se suma igual (D10).

### 4.2 Vista `v_cliente_actividad_24h` (nueva)
- **Qué calcula:** por cliente, en las últimas 24 h: `pedidos_24h`, `reservas_24h` (cualquier canal) y `reservas_web_24h` (solo canal web).
- **Qué no cuenta:** pedidos `rechazado` o `cancelado` y reservas `rechazada` o `cancelada`, para no marcar como abuso un reintento legítimo.
- **Dónde se usa:** (1) aviso al staff "ya pidió hace menos de 24 h", que es solo una alerta, no un bloqueo; (2) `reservas_web_24h` se compara con `config_local.max_reservas_web_por_telefono` para limitar a la web.

### 4.3 Función `fn_carga_dia(fecha, [reserva_a_excluir])`
- **Qué calcula:** para cada franja del día (de apertura a cierre, cada `franja_min`): reservas, personas, mesas, límites, lo libre, cuál recurso limita (`limita`: `mesas` o `personas`) y el `nivel`.
- **Reglas de conteo:** solo cuentan `confirmada` y `llego`. Cada reserva ocupa mesa durante la duración que manda `fn_duracion_estadia(personas)` (30 min para 1–3 pax, 60 para 4–7, 90 para 8 o más), así que aparece en **todas** las franjas que cubre. Mesas por reserva = personas ÷ `personas_por_mesa`, redondeado hacia arriba. Límites = aforo y mesas × `porcentaje_reservable` (vacío = 100 %), redondeados hacia abajo.
- **`nivel`:** `excedido` si se superó el límite de personas o de mesas (se pinta en rojo); `alerta` si el más lleno de los dos llega a `umbral_alerta_pct`; `ok` en los demás casos. `personas_libres` y `mesas_libres` **pueden ser negativas** cuando hay exceso.
- **Dónde se usa:** la pizarra digital del día. El parámetro opcional ignora una reserva al moverla de hora.

### 4.4 Función `fn_hay_cupo(fecha, hora, personas, [reserva_a_excluir])`
- **Qué calcula:** responde SÍ o NO a "¿cabe este grupo en todas las franjas que ocuparía?". Fuera del horario del local responde NO.
- **Uso por canal:** la **web** la usa como filtro duro (el cliente no ve el salón). El **staff** la usa solo para mostrar la advertencia; si fuerza, la reserva se guarda con `excede_cupo = TRUE`. El staff nunca queda bloqueado.

### 4.5 Cálculos que hace la aplicación y no la base
- **Reserva pasada de tolerancia:** `fecha + hora + tolerancia_min` ya pasó y la reserva sigue `confirmada` → alerta en rojo. El staff puede liberarla (`no_llego`) o cambiar la hora, aunque la tolerancia ya haya pasado.
- **Pedido demorado en cocina:** el tiempo desde `preparacion_en` supera `umbral_preparacion_min` → rojo.
- **Tope de reservas web por teléfono:** la app lee `reservas_web_24h` y lo compara con el tope.
- **Búsqueda de plato por número:** coincidencia exacta con `plato.codigo`.

### 4.6 Vistas que NO existen y podrían añadirse (D21)
Pedidos del día con total y medio de pago; ventas por día; reservas "no llegó" por semana; tiempo promedio de preparación.

## 5. Lo que la base no tiene (a propósito, por ahora)
Tabla de mesas (se cuentan, no se asignan), bitácora de acciones, ingresos y egresos, trabajadores con sueldo, días de alta demanda, historial completo de cambios de hora, cuentas de cliente, verificación del teléfono o correo, recepción de reservas por WhatsApp, delivery, y tabla de presentaciones (tamaños) por plato.

## 6. Decisiones ya tomadas que afectan la base

| Tema | Decisión |
|---|---|
| Identificar al cliente | Invitado sin cuenta; teléfono obligatorio y único; correo opcional. |
| Verificación de contacto | Sin códigos. El staff comprueba por WhatsApp antes de confirmar reservas, y confirma el pago real antes de aceptar pedidos de recojo. |
| Documento de identidad | Eliminado. |
| Límite de mesas o personas | La **web** bloquea; el **staff** solo recibe alerta y puede forzar (`excede_cupo`). |
| Tolerancia | Solo alerta visual; el staff libera o reprograma cuando quiera. |
| Abuso por teléfono | Tope configurable de reservas web en 24 h (por defecto 2) y aviso de actividad en 24 h. |
| Platos con dos precios | Un plato por tamaño, cada uno con su código. |
| Código del plato | Columna aparte, opcional y única. No usar `plato_id`. |

## 7. Riesgos que conviene tener presentes
- **El teléfono ajeno no se puede evitar** en reservas. El costo es una reserva pendiente que el staff descarta tras escribir al número.
- **Teléfono único + ficha reutilizada:** si un cliente escribe mal su nombre una vez, esa ficha conserva ese nombre.
- **Teléfono solo peruano:** un cliente extranjero no puede registrarse (D8).
- **Tope por teléfono:** lo hace cumplir la app, no la base. Un error en el código lo anula sin que la base lo detecte.
- **`excede_cupo` es una foto del momento** y no se recalcula.
- **`hora_anterior` pierde el historial** si se reprograma más de una vez.
- **Pagos sin anulación** (D10).
- **`actualizado_en` no se actualiza solo** (D11).
- **Códigos de plato sin asignar:** mientras la dueña no numere la carta, `codigo` queda vacío y la búsqueda por número no sirve.

## 8. Puntos pendientes por debatir

**Eliminar o posponer**
- **D1. `config_local.abierto`:** hoy no tiene uso. *Recomiendo* usarlo (si está en FALSE, la web muestra "cerrado" y no recibe reservas ni pedidos) o eliminarlo.
- **D2. `config_local.mensaje_pago`:** probablemente innecesario. *Recomiendo* eliminarlo.
- **D4. `cliente.acepta_datos`:** siempre es TRUE, así que no aporta; basta `acepta_datos_en`. *Recomiendo* quitar el booleano.
- **D5. Tabla `notificacion`:** vacía hasta el proyecto final. *Recomiendo* sacarla de `schema.sql` y dejarla en un script aparte.
- **D6. `pedido.reserva_id`:** ninguna pantalla lo llena. Definir su uso (elegir la reserva del día por su código al crear un pedido en local) o eliminarlo.
- **D7. `plato.descripcion`:** conservarla solo si la carta pública la va a mostrar. Ahora cobra más sentido: los ingredientes y los tamaños de variantes van ahí.

**Cambiar**
- **D8. Teléfono solo peruano:** el UNIQUE se mantiene por decisión. Queda pendiente si se acepta formato internacional.
- **D9. Cierre después de medianoche:** `hora_cierre` debe ser mayor que la apertura. ¿A qué hora cierra la pollería? Si pasa de las 12 am hay que cambiar el diseño.
- **D10. Pagos que no se pueden anular:** *recomiendo* una columna opcional `anulado_en` y que la vista ignore los anulados.
- **D11. `reserva.actualizado_en`:** que la app lo llene siempre (sencillo) o un disparador en la base (más seguro).
- **D12. Fecha y hora de la reserva:** ¿separadas (como está) o en un solo campo?
- **D13. Pedidos `local` y sus marcas de tiempo:** definir qué valen `aceptado_en` y `preparacion_en` cuando el pedido nace directo en cocina. *Recomiendo* que valgan lo mismo que `creado_en`.
- **D22. Historial de horas de reserva:** ¿importa conservar todos los cambios, no solo el último? Hoy `hora_anterior` guarda uno.

**Añadir**
- **D14. ¿Quién confirmó o aceptó?** Hoy se sabe quién creó y quién cobró, pero no quién confirmó una reserva ni aceptó un pedido. Opción: `confirmada_por` y `aceptado_por`.
- **D15. Foto del plato:** `plato.imagen_url`. Implica dónde alojar las imágenes.
- **D16. Congelar el nombre del plato en la línea:** si renombran un plato, los pedidos antiguos cambiarían de nombre.
- **D17. Tabla de mesas:** solo si la dueña quiere asignar mesas concretas.
- **D18. Días de alta demanda:** no tienen dónde guardarse.
- **D19. Teléfono del personal:** para recuperar contraseña por WhatsApp (proyecto final).
- **D20. Bitácora de acciones críticas:** fuera del alcance actual.
- **D21. Vistas de reportes** de la sección 4.6.
- **D23. Tabla de presentaciones por plato:** modelo más limpio para platos con varios tamaños. Hoy se resuelve con un plato por tamaño; se puede migrar después sin perder datos.

**Cómo responder:** por ejemplo, "D2, D4 eliminar; D1 usar; D9 cierra a la 1 am".
