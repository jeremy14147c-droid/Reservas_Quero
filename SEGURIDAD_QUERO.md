# Seguridad de Quero APP: diagnóstico, respuestas y plan

Material de la Semana 14 (Pruebas de Seguridad + laboratorio de auditoría cruzada) aplicado a tu proyecto.

## 0. Cómo se hizo esto (léelo, cambia cómo usas los resultados)

- **Qué ejecuté:** levanté una **copia local** de tu proyecto (el zip `Reservas_Quero (5)`) con PostgreSQL 16 y los datos de `seed.sql`, y corrí los casos con el cliente de pruebas de Flask. Eso da resultados reales del **código**.
- **Qué NO ejecuté:** tu sistema desplegado en Render y Neon, el botón "Atrás" del navegador, las subidas de archivos (aún no existen) ni pruebas de XSS en JavaScript.
- **Qué debes hacer tú:** el laboratorio exige **capturas de pantalla sobre el sistema real**. Repite cada caso en tu sistema con **usuarios de prueba** (sección 7). Mis resultados te dicen qué esperar y dónde mirar, pero no reemplazan tu evidencia.
- **Regla del laboratorio:** solo se prueba el sistema asignado, con usuarios de prueba y sin datos reales.

---

## 1. Resumen

**Lo que ya está bien (verificado):**

| Control | Evidencia |
|---|---|
| Autorización en el servidor | 44 rutas del personal protegidas con `@requiere_rol` y 8 públicas a propósito (6 del cliente, el login y `/salud`). Un empleado recibe **403** en todo lo de admin; un anónimo es redirigido al login (páginas) o recibe **401** (API). |
| Inyección SQL | Ninguna consulta se arma pegando datos del usuario (búsqueda en el código: 0 coincidencias). `' OR '1'='1' -- ` en login, buscador del staff y formulario de reservas **no hizo nada** y la tabla `reserva` quedó intacta. |
| Contraseñas | Se guardan con hash `scrypt` (`scrypt:32768:8:1$...`), nunca en texto plano. |
| CSRF | Un POST sin token es rechazado con **400**. |
| XSS en la página pública | Un nombre con `<script>alert(1)</script>` aparece escapado (`&lt;script&gt;`) en la página de seguimiento. |
| Mensaje de login | Usuario inexistente y contraseña incorrecta devuelven el **mismo** texto. |
| Token de cierre | Al cerrar sesión en el navegador, volver a una página protegida redirige al login. |

**Lo que se diagnosticó y su estado actual (Fases S1 y S2 aplicadas):**

| # | Hallazgo | Severidad | Estado actual |
|---|---|---|---|
| H-1 | La sesión **no se puede revocar**: una cookie copiada antes de cerrar sesión sigue funcionando. | **Alto** | **RESUELTO** (sesión revocable con `sesion_version`). |
| H-2 | **No hay bloqueo** por intentos fallidos de login. | Medio | **RESUELTO** (bloqueo por 5 fallos en 10 min por correo y 20 por IP). |
| H-3 | **Redirección abierta** en el login (`?next=https://sitio-externo`). | Medio | **RESUELTO** (función `destino_seguro` restringe a rutas internas). |
| H-4 | El **tiempo de respuesta** delata si un correo existe (~9 ms vs ~88 ms). | Medio | **RESUELTO** (cálculo de hash falso `HASH_FALSO_DUMMY` iguala los tiempos). |
| H-5 | La cookie de sesión no lleva `Secure` ni `SameSite`. | Medio | **RESUELTO** (`SameSite=Lax`, `Secure` en producción y vida de 12 h). |
| H-6 | No hay **cabeceras de seguridad** (`X-Frame-Options`, `nosniff`, etc.). | Bajo | **RESUELTO** (cabeceras nosniff, DENY, CSP, Permissions-Policy en `after_request`). |
| H-7 | `/reserva/<texto>` y `/pedido/<texto>` responden **500** en vez de 404. | Bajo | **RESUELTO** (convertidor `<uuid:token>` responde 404 antes de BD). |
| H-8 | El logout se hace por **GET** (un enlace puede cerrar tu sesión). | Bajo | **RESUELTO** (logout exclusivamente por POST con CSRF, GET da 405). |
| H-9 | Contraseña mínima de **6** caracteres. | Bajo | **RESUELTO** (política mínima de 10 caracteres y bloqueo de claves comunes). |
| H-10 | `SECRET_KEY` tiene un valor **por defecto** público si falta la variable. | Condicional | **RESUELTO** (validación bloquea arranque en producción si falta o es corta). |
| H-11 | Un empleado puede cambiar precios y no queda **registro** de quién lo hizo. | Decisión de negocio | Pendiente para Fase S3 (bitácora Semana 16). |

No encontré hallazgos **Críticos**. Eso es bueno, pero solo cubre lo que probé.

---

## 2. Tus dos preguntas

### 2.1 ¿Limitar el login de mozo y admin a ciertos dispositivos o IP?

**No lo recomiendo como primera defensa. Es frágil y puede dejar al local sin sistema.**

| Problema | Por qué importa en tu caso |
|---|---|
| IP cambiante | Si el local no tiene IP fija (lo habitual en conexiones residenciales y en datos móviles; confírmalo con su proveedor), la lista se rompe sola y el personal queda **bloqueado en plena atención**. |
| Celulares del personal | Con datos móviles la IP cambia constantemente: no hay forma de listarlas. |
| Detrás de Render | Flask ve la IP del proxy, no la del cliente. Hay que leer `X-Forwarded-For` con `ProxyFix` bien configurado; mal hecho, o bloquea a todos o permite falsificar la IP. |
| Alcance limitado | No protege si el atacante está en la misma red (Wi‑Fi del local) y **no sustituye** la contraseña. |
| Falla "hacia el cierre" | Es un control de **confidencialidad** que daña la **disponibilidad**. Para un restaurante, perder disponibilidad cuesta más. |

**Qué sí hacer (mejor protección con menos riesgo):**

1. **Bloqueo por intentos fallidos** y límite de velocidad (H-2). Frena adivinar contraseñas desde cualquier IP.
2. **Sesiones revocables y con vida corta** (H-1, H-5).
3. **Contraseñas más largas** (H-9) y, para el admin, **verificación en dos pasos** (TOTP, como Google Authenticator).
4. **Registrar** IP y dispositivo de cada inicio de sesión y mostrar al admin el "último acceso": **alerta sin bloquear**.
5. Si aun así quieres una lista de IP, hazla **solo para el rol admin** (se usa poco) y con una salida de emergencia (por ejemplo, la verificación en dos pasos).
6. Más adelante, si hay presupuesto: proteger el panel con un servicio de acceso por identidad (Cloudflare Access) o una VPN. Es la forma correcta de "solo desde dispositivos autorizados", pero añade complejidad.

### 2.2 ¿Separar una página para el cliente y otra para mozo y admin?

**Ya están separadas donde importa: en el servidor.** Esa es la separación que protege. Ocultar un botón no es seguridad; lo que protege es que el servidor exija el rol en cada ruta, y eso ya pasa (44 de 44 rutas del personal).

Hay tres niveles de "separar":

| Nivel | Qué es | ¿Ya lo tienes? | Opinión |
|---|---|---|---|
| 1. Separación lógica | Rutas del personal bajo `/staff` y `/admin`, con rol exigido en el servidor | **Sí** | Es lo esencial. |
| 2. Separación visual | Plantilla del cliente distinta a la del staff (Fase 3.4) y **sin menú de staff en páginas públicas** | En camino | Mejora la experiencia y evita confusión. |
| 3. Separación física | Panel del staff en otro servicio o subdominio (`panel.tudominio.pe`) | No | Da más aislamiento (cookies separadas, reglas de red solo para el panel), pero cuesta un servicio más y duplica configuración. **No lo hagas ahora**; considéralo cuando el local opere a diario y haya presupuesto. |

### 2.3 Y los clientes invitados

Sin cuentas, el riesgo del cliente es menor, pero hay cosas que cuidar:

| Riesgo | Qué ya tienes | Qué falta |
|---|---|---|
| Que alguien vea reservas o pedidos ajenos | Enlaces con UUID imposible de adivinar | Que un texto inválido dé **404** y no 500 (H-7). |
| Reservas basura (spam) | Campo trampa y tope de reservas web por teléfono | Límite por IP en los formularios públicos; un CAPTCHA gratuito (Cloudflare Turnstile) si aparece spam. |
| Datos personales (nombre, teléfono, correo) | Solo el staff los ve | Mostrar lo mínimo en las páginas públicas y definir cuánto tiempo se guardan. |
| Código inyectado en nombre o nota | Jinja escapa el HTML | Mantener el `esc()` en todo `innerHTML` de JavaScript. |
| Comprobantes de pago (Fase 3.7) | Aún no existen | Aplicar las reglas de la sección 12 de `AGENTS.md` (tipo real, tamaño, solo staff). |

---

## 3. Activos críticos de Quero (para tu ficha)

| Categoría | Activo | Por qué es crítico |
|---|---|---|
| Datos sensibles | Credenciales del personal (`personal.password_hash`) | Dan acceso a todo el panel. |
| Datos sensibles | Datos de clientes (nombre, teléfono, correo) | Información personal. |
| Datos sensibles | Comprobantes de pago (Fase 3.7) | Contienen datos de terceros. |
| Alto impacto | **Registrar un pago** (`/pedidos/<id>/pagar`) | Mueve dinero y manda el pedido a cocina. |
| Alto impacto | Cambiar precios y la carta | Afecta lo que se cobra. |
| Alto impacto | Confirmar o cancelar reservas y pedidos | Afecta el servicio y los clientes. |
| Puntos de acceso | Login del personal (`/auth/login`) | Puerta de entrada. |
| Puntos de acceso | Panel de administración (`/admin/*`) | Crea personal y cambia configuración. |
| Puntos de acceso | Sesión activa (cookie `session`) | Quien la tenga, es el usuario. |

**Los 3 más críticos para tu ficha:** (1) Credenciales del personal, (2) Función de registrar pagos, (3) Panel de administración.

---

## 4. Ficha de ejecución (resultados en copia local)

> Completa la columna "Captura N°" **repitiendo cada caso en tu sistema**. La columna "Resultado obtenido" es lo que vi en mi copia local; en el tuyo puede variar (por ejemplo, las cookies seguras en producción).

| # | Tipo | Activo | Acción realizada | Resultado esperado | Resultado obtenido (copia local) | ¿Es seguro? | Captura N° |
|---|---|---|---|---|---|---|---|
| PS-02 | Autorización | Panel de administración | Anónimo abre `/admin/personal`, `/admin/config`, `/staff/reservas`; llama `/api/v1/reservas/dia`. Con el empleado de prueba abre `/admin/personal` y envía POST a crear plato y crear personal. | Redirige al login o muestra acceso denegado | Anónimo: **302** al login (API: **401**). Empleado: **403** en las páginas y en los POST de admin. POST sin token CSRF: **400**. | **Sí** | |
| PS-03 | Inyección | Credenciales y buscador | `' OR '1'='1' -- ` (con espacio al final) en correo y en contraseña; en el buscador de platos del staff; en el nombre del formulario `/reservar`. | No inicia sesión; sin error técnico | Login: vuelve a mostrar el formulario (**200**), sin sesión. Buscador y formulario: sin error técnico. La tabla `reserva` sigue existiendo. | **Sí** | |
| PS-04 | Cifrado | Credenciales | Ver la columna `password_hash` de `personal` en pgAdmin o `psql`. | Un hash largo e ilegible | `scrypt:32768:8:1$6JuKj...` (hash `scrypt` con sal aleatoria) | **Sí** (ver nota) | |
| PS-05 | Sesión | Sesión activa | a) Iniciar sesión, cerrar sesión y abrir `/staff/reservas`. b) Copiar el valor de la cookie `session`, cerrar sesión, volver a poner esa cookie y recargar. | Pide iniciar sesión en ambos casos | a) **302** al login. b) **302**: la sesión previa queda invalidada en el servidor mediante `sesion_version`. | **Sí** | |
| PS-06 | Autorización (propio) | Funciones de alto impacto del admin | Con el empleado de prueba: crear personal y crear plato. | Acceso denegado | **403** | **Sí** | |
| PS-07 | Validación de entrada (propio) | Páginas públicas de seguimiento | Abrir `/reserva/1` y `/pedido/1`. | Página 404 | **404** (convertidor `<uuid:token>` rechaza antes de tocar la BD). | **Sí** | |
| PS-08 | Autenticación (propio) | Login | Iniciar sesión con `/auth/login?next=https://evil.example/robo`. | Ignora el destino externo | Ignora el enlace malicioso y redirige a la ruta interna por defecto. | **Sí** | |
| PS-01 | Autenticación | Credenciales | a) Usuario inexistente. b) Usuario de prueba con contraseña incorrecta 6 veces. c) Comparar los mensajes. Luego iniciar sesión con la contraseña correcta. | Mismo mensaje y bloqueo temporal | Mismo mensaje en a) y b) con tiempo parejo (hash falso H-4). **Con bloqueo**: al 5to fallo bloquea temporalmente por 10 min. | **Sí** | |

**Ejecuta PS-01 al final** (así lo pide la guía), por si algún día hay bloqueo.

**Nota sobre PS-04:** la guía espera ver `$2b$` (bcrypt) o `$argon2`. `scrypt` es otra función de hash lenta y con sal, diseñada para contraseñas; la guía de almacenamiento de contraseñas de OWASP la acepta. Si el evaluador pregunta, explícalo así y muestra que no es MD5 ni texto plano. Cambiar a Argon2 es posible pero no urgente.

---

## 5. Reporte de hallazgos

Severidad según el criterio de la guía (Crítico, Alto, Medio, Bajo).

| N° | Caso | Severidad | Hallazgo (qué pasó) | Recomendación |
|---|---|---|---|---|
| H-1 | PS-05 | **Alto** | Copié la cookie `session`, cerré sesión y volví a ponerla: el panel se abrió (**200**). Flask guarda la sesión **firmada en la cookie**, así que el servidor no tiene forma de anularla; dura hasta 31 días. | Agregar a `personal` una **versión de sesión** que se guarde en la cookie y se incremente al cerrar sesión, cambiar o restablecer clave y desactivar al usuario; el cargador de usuario rechaza cookies con versión vieja. Reducir la vida de la sesión (por ejemplo 12 h). |
| H-2 | PS-01 | Medio | Seis contraseñas incorrectas seguidas y después el login correcto entró: no hay bloqueo ni límite de intentos. | Bloquear temporalmente tras 5 fallos en 10 minutos por correo (aunque el correo no exista) y por IP. Mismo mensaje en todos los casos. |
| H-3 | PS-08 | Medio | `?next=https://evil.example/robo` redirige a un sitio externo tras iniciar sesión (sirve para phishing). | Aceptar solo destinos internos (empiezan con `/`, no con `//` ni contienen esquema o dominio). |
| H-4 | PS-01 | Medio | Con un correo inexistente la respuesta tarda ~9 ms; con uno existente y clave mala, ~88 ms (mediana de 12 intentos, dos corridas). La diferencia delata qué correos existen. | Si el usuario no existe, comparar igual contra un hash falso para que el tiempo sea parecido. |
| H-5 | PS-05 | Medio | La cookie de sesión solo lleva `HttpOnly`: sin `Secure` ni `SameSite`. | `SESSION_COOKIE_SECURE=True` en producción y `SameSite=Lax` (Fase D). |
| H-6 | Extra | Bajo | Ninguna cabecera de seguridad (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, HSTS, CSP). | Agregarlas en una función `after_request`. |
| H-7 | PS-07 | Bajo | `/reserva/1` y `/pedido/1` provocan un error de base de datos (UUID inválido) y responden 500. | Declarar el parámetro como `<uuid:token>` para que dé 404 antes de tocar la base. |
| H-8 | PS-05 | Bajo | `/auth/logout` funciona por GET: una imagen o enlace en otra página puede cerrarte la sesión. | Pasarlo a POST con token CSRF. |
| H-9 | Código | Bajo | `cambiar_clave` acepta contraseñas de 6 caracteres. | Mínimo 10 y rechazar claves comunes. |
| H-10 | Código | Condicional | `SECRET_KEY` tiene un valor por defecto público (`dev-secret-key-...`) si falta la variable. Con ese valor cualquiera puede falsificar cookies de sesión. | Verifica que la variable existe en Render y haz que la app **no arranque** en producción sin una clave larga (Fase D). |
| H-11 | Decisión | Info | `AGENTS.md` permite que el empleado cambie precios; el servicio responde **200**. No queda registro de quién ni cuándo. | No quitar el permiso: añadir una **bitácora** (OWASP A09, Semana 16). |

**Relación con OWASP Top 10 (lista de la sesión):** A01 control de acceso → bien resuelto en rutas, con H-3 pendiente. A02 criptografía → hash correcto, cookie sin `Secure`. A03 inyección → resiste. A04 diseño inseguro → H-7. A07 autenticación → H-1, H-2, H-4. A09 registro → H-11.

---

## 6. Hoja de entrega del anfitrión (plantilla)

| Campo | Completar |
|---|---|
| Equipo anfitrión / sistema | (tu equipo) / Quero APP (reservas y pedidos de restaurante) |
| Tipo de sistema | Web |
| Tecnologías | HTML, CSS, Bootstrap y JavaScript · Flask (Python) · PostgreSQL |
| URL o forma de acceso | tu enlace de Render (o `http://localhost:5000` si lo corres en local) |
| Usuario de prueba rol básico | `auditor.empleado@prueba.pe` / contraseña temporal que solo uses para esto |
| Usuario de prueba rol administrador | `auditor.admin@prueba.pe` / contraseña temporal |
| Ruta solo para administrador | `/admin/personal` |
| Registro de otro usuario | Una reserva con su enlace `/reserva/<token>` creada por el admin |
| 3 activos críticos | Credenciales del personal; función de registrar pagos; panel de administración |

**Reglas para las cuentas de prueba:**
- Créalas desde el panel de Personal y **bórralas o desactívalas al terminar**.
- **Nunca** pongas contraseñas reales en este documento ni se las des a otro equipo.
- No uses la cuenta del dueño ni de personal real para estas pruebas.
- Si implementas el bloqueo por intentos (H-2), no hagas PS-01 con la cuenta real del administrador: la bloquearías.

---

## 7. Cómo repetir cada caso en tu sistema (con capturas)

**Toma una captura antes y otra después de cada caso.** Abre las herramientas del navegador con **F12**.

| Caso | Pasos |
|---|---|
| **PS-02** | Cerrado, escribe `/admin/personal` en la barra: debe llevarte al login. Inicia sesión con el **empleado** de prueba y escribe `/admin/personal` y `/admin/config`: debe decir acceso denegado (403). Captura. |
| **PS-03** | En el login escribe `' OR '1'='1' -- ` (con un espacio al final) en correo y en contraseña. Debe volver al formulario. Con el empleado, en el buscador de platos de "Nuevo pedido en local", escribe lo mismo. Captura. |
| **PS-04** | Con el admin crea un usuario de prueba con la contraseña `Prueba123`. Abre la base (pgAdmin, o en Neon el editor SQL) y ejecuta `SELECT correo, password_hash FROM personal;`. Captura el campo largo que empieza con `scrypt:`. |
| **PS-05 a)** | Inicia sesión, copia la URL de `/staff/reservas`, cierra sesión y pégala en otra pestaña. Captura. |
| **PS-05 b)** | Inicia sesión. F12 → pestaña **Application** (Aplicación) → **Cookies** → tu sitio → copia el **Value** de `session`. Cierra sesión. Vuelve a esa fila, pega el valor anterior en **Value** y recarga `/staff/reservas`. Si se abre el panel, es vulnerable. Captura ambos momentos. |
| **PS-07** | Escribe `/reserva/1` en la barra. Si ves una página de error 500, es el hallazgo; debería ser 404. Captura. |
| **PS-08** | Cierra sesión y abre `/auth/login?next=https://example.com`. Inicia sesión con el empleado: si terminas en `example.com`, es vulnerable. Captura. |
| **PS-01** (al final) | a) usuario inexistente + cualquier clave: anota el mensaje. b) empleado de prueba con clave incorrecta 6 veces: anota el mensaje. c) compara. Luego inicia con la clave correcta: si entra, no hay bloqueo. Captura. |

---

## 8. Auditoría de código (si el sistema no corre)

| Tipo | Pregunta | Dónde mirar | Respuesta |
|---|---|---|---|
| Inyección | ¿Las consultas usan parámetros? | `app/db.py`, `app/servicios/*.py` | **Sí**: `%s` con los datos aparte; 0 consultas armadas con `+`, `f"..."` o `.format`. |
| Cifrado | ¿La contraseña se guarda con un hash seguro? | `manage.py` (`crear-admin`), `app/auth/routes.py` (`cambiar_clave`) | **Sí**: `generate_password_hash` (scrypt). |
| Autorización | ¿Cada ruta de administración valida el rol? | `app/admin/routes.py`, `app/auth/decoradores.py` | **Sí**: `@requiere_rol("admin")` en las 5 rutas de admin y en las de carta que modifican. |
| Autenticación | ¿Mismo mensaje para usuario inexistente y clave incorrecta? | `app/auth/routes.py`, función `login` | **Sí** el mensaje; **no** el tiempo (H-4) y no hay bloqueo (H-2). |
| Sesión | ¿El logout invalida la sesión en el servidor? | `app/auth/routes.py`, función `logout` | **No**: `logout_user()` borra la cookie del navegador, pero la sesión firmada que alguien copió sigue válida (H-1). |

---

## 9. Plan de correcciones

Orden por impacto y esfuerzo. Todas siguen TDD (`AGENTS.md` sección 14.7): primero la prueba en rojo.

| Fase | Contenido | Hallazgos |
|---|---|---|
| **S1** | Endurecer login y sesión | H-1, H-2, H-3, H-4, H-5, H-8, H-9 |
| **S2** | Cabeceras, UUID y clave secreta | H-6, H-7, H-10 |
| **S3** (opcional) | Bitácora de acciones y verificación en dos pasos del admin | H-11, A09 |

**Orden recomendado respecto de tus otras fases:** haz S1 y S2 **antes de dar el enlace a clientes reales** y junto a la Fase D (despliegue). S3 puede esperar al proyecto final (la Semana 16 trata el registro de eventos).

### Prompt S1: endurecer login y sesión

```
Contexto: AGENTS.md (secciones 4b, 12 y 14) y SEGURIDAD_QUERO.md (hallazgos H-1 a H-9). Esta es la Fase S1. Trabaja con TDD (AGENTS.md 14.7): para cada punto escribe primero la prueba, muéstrala en rojo, commit "test:", luego el código, commit "fix:". Las reglas puras se prueban SIN base de datos. No cambies funcionalidades fuera de lo pedido.

Haz, un punto por commit:
1. Redirección segura (H-3): función pura destino_seguro(next) que acepta solo rutas internas (empieza con "/", no con "//" ni "\\", sin esquema ni dominio); si no, redirige al inicio. Úsala en el login. Pruebas con https://evil.example, //evil.example, /\evil.example y rutas válidas.
2. Tiempo parecido (H-4): si el correo no existe, ejecuta igualmente check_password_hash contra un hash falso generado al arrancar. Mismo mensaje en todos los casos.
3. Bloqueo por intentos (H-2): migración migraciones/NNN_intento_login.sql (repetible) y schema.sql con la tabla intento_login (intento_id, correo_lower, ip, exitoso, creado_en). Regla pura debe_bloquear(intentos_recientes, ahora): 5 fallos en 10 minutos por correo (exista o no) y 20 por IP bloquean por 10 minutos. Los valores van como constantes en Config. Mensaje genérico idéntico ("Demasiados intentos. Espera unos minutos."). Un login correcto limpia el contador de ese correo. Lee la IP real con ProxyFix solo si PRODUCCION=1.
4. Cookies y vida de la sesión (H-5): con PRODUCCION=1 SESSION_COOKIE_SECURE y REMEMBER_COOKIE_SECURE en True; SESSION_COOKIE_SAMESITE="Lax"; PERMANENT_SESSION_LIFETIME de 12 horas.
5. Sesión revocable (H-1): migración que agrega personal.sesion_version INT NOT NULL DEFAULT 1. Se guarda en la sesión al iniciar; el cargador de usuario rechaza la sesión si no coincide; se incrementa al cerrar sesión, al cambiar la clave, al restablecerla y al desactivar a la persona. Prueba obligatoria: la cookie copiada ANTES de cerrar sesión ya no abre el panel (redirige al login).
6. Logout por POST (H-8): botón en un formulario con token CSRF; GET a /auth/logout responde 405.
7. Contraseñas (H-9): mínimo 10 caracteres y lista corta de claves comunes bloqueadas, en cambiar clave, crear personal y restablecer clave.

No toques: reservas, pedidos, pagos ni la interfaz del cliente.
Criterio de terminado: pytest en verde; los casos PS-01 (bloqueo), PS-05 b) y PS-08 de SEGURIDAD_QUERO.md pasan a "seguro" en una copia local; el flujo normal de login del personal sigue funcionando. Actualiza SEGURIDAD_QUERO.md con los resultados. Presenta el plan antes de programar.
```

### Prompt S2: cabeceras, UUID y clave secreta

```
Contexto: AGENTS.md (secciones 4b, 12 y 14) y SEGURIDAD_QUERO.md (H-6, H-7, H-10). Esta es la Fase S2. TDD obligatorio.

Haz:
1. Rutas públicas de seguimiento (H-7): cambia el parámetro token a <uuid:token> en /reserva/<token> y /pedido/<token> (y donde aplique) para que un texto inválido responda 404 sin tocar la base. Prueba primero: /reserva/1 y /pedido/abc devuelven 404.
2. Cabeceras (H-6) en una función after_request: X-Content-Type-Options: nosniff; X-Frame-Options: DENY; Referrer-Policy: strict-origin-when-cross-origin; Permissions-Policy: camera=(), microphone=(), geolocation=(); Strict-Transport-Security solo con PRODUCCION=1.
   Content-Security-Policy: revisa de qué dominios cargan los scripts y estilos (CDN de Bootstrap, fuentes) y propón una política que no rompa las páginas (hay JavaScript dentro de las plantillas, así que script-src necesitará 'unsafe-inline'). Pruébala navegando todas las pantallas y avísame si algo se rompe.
3. Clave secreta (H-10): con PRODUCCION=1 la app NO arranca si SECRET_KEY es la de desarrollo o tiene menos de 32 caracteres (error claro). Función pura probada primero. (Si la Fase D ya lo hizo, solo verifica y cierra el punto.)
4. Verifica que ninguna página de error muestre rastros técnicos (500 y 404 genéricos).

Criterio de terminado: pytest en verde; los casos PS-07 pasa a "seguro"; las cabeceras aparecen en la pestaña Network; todas las pantallas se ven y funcionan igual. Presenta el plan antes de programar.
```

### Parche para `AGENTS.md` (sección 12)

Agrega al final de la sección 12:

```
Autenticación y sesión (Fase S1): bloqueo temporal por intentos fallidos (por correo, exista o no, y por IP), mismo mensaje y tiempo de respuesta parecido para usuario inexistente y clave incorrecta,
destinos de `next` solo internos, cookies Secure y SameSite=Lax en producción, vida de sesión de 12 h, sesión revocable con `sesion_version`, logout por POST con CSRF, contraseña mínima de 10 caracteres.
Rutas públicas con token: siempre `<uuid:token>`. Cabeceras de seguridad en toda respuesta. No hay restricción por IP para el personal (frágil y puede dejar al local sin acceso): se registra IP y dispositivo en una bitácora y se alerta.
```

---

## 10. Respuestas modelo a las preguntas de la sesión

1. **¿Diferencia entre probar que funciona y probar que es seguro?** Lo funcional pregunta si el sistema hace lo que debe con datos correctos; lo de seguridad pregunta si resiste lo que **no** debe, con datos manipulados. Quero tiene decenas de pruebas funcionales y aun así dejaba reutilizar una sesión cerrada.
2. **¿Qué tipo de prueba es más urgente?** Sesión (PS-05): es el único hallazgo **Alto** y permite mantener un acceso que debería estar cerrado. Después, autenticación (bloqueo de intentos).
3. **¿Qué encontraron al ejecutar PS-01?** Los mensajes son iguales (bien), pero no hay bloqueo y el tiempo de respuesta delata qué correos existen. Se corrigen en la Fase S1.
4. **¿Qué cambió en cómo ven su sistema?** Que el hecho de que no haya errores funcionales no significa que esté protegido: probar "lo que no debería pasar" encontró varias puertas mal cerradas que nunca habíamos mirado.

---

## 11. Qué falta probar (no lo cubrí)

- Tu sistema desplegado en Render y Neon (las cookies y cabeceras pueden diferir en producción).
- El botón "Atrás" del navegador tras cerrar sesión (el laboratorio lo pide).
- Pruebas de XSS en las pantallas armadas con JavaScript (pizarra, cola, cocina).
- Subidas de archivos (Fase 3.7) y límites de velocidad en formularios públicos.
- Una revisión de dependencias con vulnerabilidades conocidas (`pip-audit`).
- Una herramienta automática como OWASP ZAP, que la sesión menciona como paso posterior al análisis manual.
