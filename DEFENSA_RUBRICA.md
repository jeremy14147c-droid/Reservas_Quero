# Defensa de sustentación — Quero Gastrobar (mapeo a la rúbrica)

> Documento para prepararte en minutos. Cada criterio tiene: **qué hicimos**, **dónde está la
> evidencia** (archivos concretos que puedes abrir en vivo), **cómo defenderlo** y
> **preguntas probables con respuesta modelo**.

## Datos duros que conviene memorizar

| Dato | Valor | Dónde verificarlo |
|---|---|---|
| Commits | 34, pequeños y descriptivos, en ramas por fase | `git log --oneline` |
| Ramas | `main` (estable) + `fase-3-1` (desarrollo) | `git branch` |
| Pruebas automatizadas | **52 funciones de test** en 8 archivos (`tests/test_fase*.py`) | `pytest -q` |
| Lógica de negocio | 61 funciones divididas en `app/servicios/` | `app/servicios/*.py` |
| Capa de datos | SQL explícito: `schema.sql` con 10 tablas, **3 funciones SQL** (cupo, carga, duración) y **2 vistas** | `schema.sql` |
| Plantillas | 25 archivos HTML con ~3200 líneas (incluye tickets) | `app/templates/` |
| Reglas centralizadas | 123 `raise ValueError` = toda validación rechaza con mensaje claro | `app/servicios/` |

---

## Criterio 1 · Diseño de la solución (MVC, TDD, DAO, SOLID) — 3 pts

### El discurso de 30 segundos
"Usamos Flask con **app factory + blueprints**, que implementa MVC en Python:
el **Modelo** es PostgreSQL con funciones SQL (`schema.sql`), el **Controlador** son los
blueprints de rutas, y las **Vistas** son plantillas Jinja2. La lógica de negocio vive en una
capa de servicios separada, y el acceso a datos es una capa DAO propia sobre psycopg 3 con SQL
parametrizado — sin ORM, para que el diseño de la base de datos mande. Desarrollamos con la
disciplina de TDD: cada fase trae su archivo de pruebas y hoy hay 52 pruebas automatizadas que
corren en 19 segundos."

### Tabla de mapeo (muéstrala)

| Concepto de la rúbrica | Cómo se materializa en el proyecto | Archivo de evidencia |
|---|---|---|
| **Modelo (M)** | 10 tablas, 3 funciones SQL (`fn_carga_dia`, `fn_hay_cupo`, `fn_duracion_estadia`) y 2 vistas (`v_pedido_resumen`, `v_cliente_actividad_24h`). La lógica de capacidad vive EN la base, no en el código; la máquina de estados vive en el servicio (`transicion_reserva` / `transicion_pedido`) | `schema.sql`, `app/servicios/` |
| **Vista (V)** | 25 plantillas Jinja2 con Bootstrap 5 (públicas + staff + tickets de impresión) | `app/templates/` |
| **Controlador (C)** | Blueprints por módulo: `publico`, `reservas`, `pedidos`, `carta`, `admin`, `auth`, `api` | `app/*/routes.py`, `app/__init__.py` |
| **DAO / capa de acceso a datos** | `app/db.py`: helpers `consultar_todos`, `consultar_uno`, `ejecutar`, `ejecutar_retornando`. Punto ÚNICO de conexión, consultas SIEMPRE parametrizadas (%s) — anti SQL-Injection | `app/db.py` |
| **Capa de servicios** | Toda la lógica de negocio; las rutas solo llaman a servicios y nunca contienen reglas | `app/servicios/reservas.py`, `app/servicios/pedidos.py` |
| **TDD** | Cada fase añade su suite: 52 pruebas, 8 archivos, fixtures en `conftest.py`. Se corren antes de cada entrega | `tests/` |

### Cómo "defender SOLID en Python" (el punto clave)

Si preguntan *"¿y dónde está SOLID/algo orientado a objetos si su código son funciones?"*,
esta es tu argumentación — Python es multiparadigma y SOLID se aplica a MÓDULOS, no solo a clases:

> "En Python los principios SOLID se cumplen a nivel de **módulos y funciones**, no exige clases.
> Nuestro diseño lo cumple así:"

| Principio | Dónde se cumple (evidencia concreta) |
|---|---|
| **S — Single Responsibility** | No hay un archivo gigante: `servicios/reservas.py` solo reserva, `servicios/pedidos.py` solo pedidos, `servicios/carta.py` solo carta, `db.py` solo accede datos, `auth/` solo identidad. Cada módulo tiene UN motivo para cambiar |
| **O — Open/Closed** | Las transiciones de estado válidas están en *diccionarios* (`TRANSICIONES_VALIDAS` en `reservas.py`, las del pedido en `pedidos.py`). Agregar un estado nuevo = agregar una entrada al diccionario, **sin tocar** la función que valida. Igual: los valores del negocio salen de `config_local` — cambiar la duración de mesa NO toca código |
| **L — Liskov (equivalente en Python: duck typing + jerarquía de excepciones)** | `CupoNoDisponible` **hereda de `ValueError`**: cualquier ruta que trata errores de negocio con `except ValueError` funciona polimórficamente sin conocer la subclase. Es el mismo contrato que una clase derivada que responde al mismo mensaje |
| **I — Interface Segregation (equivalente: contratos de módulo pequeños)** | Ningún módulo "ve" de más: la vista pública solo llama a las funciones públicas que necesita; la API JSON (`api/routes.py`) y las rutas HTML son superficies **separadas** — un cliente de la API no carga el panel del staff. La escritura de errores es uniforme: `{"ok": true/false, "datos"/"error"}` |
| **D — Dependency Inversion (el más defendible)** | Las funciones de `servicios/` **NO importan Flask** — son Python puro que recibe datos y devuelve resultados (el doc de reglas lo exige). Las rutas dependen de la abstracción "servicio", no de la BD directa; y `db.py` es la única que conoce el driver (psycopg). Cambiar de driver o de presentador no obliga a reescribir reglas |

Frase de remate si insisten con clases:
> "Sí usamos clases donde Python las pide de verdad: `Config` con herencia para pruebas
> (`TestConfig(Config)` sobrescribe solo lo que cambia — Open/Closed exacto a nivel de clase),
> clases de error (`CupoNoDisponible(ValueError)`), y el sistema de roles se inyecta con
> decoradores `@requiere_rol('admin')`, que es el mecanismo de composición idiomático de Python
> en lugar de herencia."

### TDD — cómo presentarlo con honestidad y fuerza

- "Practicamos un ciclo de **prueba por funcionalidad**: cada fase (0, 1, 2, 3 y subfases 3.1–3.2)
  tiene su archivo `tests/test_faseN.py` con reglas de negocio, no con pruebas de humo:
  - `test_fase3_2.py` prueba la FUNCIÓN SQL `fn_duracion_estadia` en los casos límite (1, 3, 4, 7, 8, 12, 13)
  - `test_fase3.py` prueba la **máquina de estados** de pedidos (transiciones válidas y las rechazadas)
  - `test_fase2.py` prueba el TOPE de reservas por teléfono y el campo honeypot
- Un ejemplo perfecto de "el test primero atrapó un bug real": en la fase 3.1 las pruebas del
  buscador fallaron en el navegador y la causa fue un `SyntaxError` de JS duplicado; se corrigió
  y quedó con prueba permanente.
- "Las pruebas usan fixtures con **limpieza automática** (`yield` + `finally`): dejan la base como
  estaban. Eso nos deja probar contra PostgreSQL real, no contra un mock que miente."

### Preguntas probables (Criterio 1) y respuesta modelo

1. **"¿Por qué no usaron un ORM como SQLAlchemy?"**
   → "La fuente de verdad del negocio es la base de datos (cálculo de cupos, carga por franja,
   duración por tamaño de grupo). Si lo hubiéramos puesto en Python, cualquier conteo se podría
   duplicar y desincronizar. Con SQL explícito y funciones en la BD hay UNA sola versión de cada
   regla. La rúbrica pide DAO: nuestra capa `db.py` es exactamente eso, el desacoplamiento entre
   dominio y driver."
2. **"MVC clásico no separa modelo de controlador ¿cómo lo ven ustedes?"**
   → "En web moderna el modelo se reparte: entidades y reglas en la BD + capa de servicios;
   el controlador es delgado (recibe HTTP, llama servicio, responde). Es una evolución del MVC."
3. **"¿Cómo garantizan que no caigan en la trampa de solo probar felices?"**
   → "Las pruebas cubren caso límite y de rechazo: exceder el tope por teléfono, pagar más que
   el total, estados finales que no cambian, fecha fuera del horario, honeypot lleno, etc."
4. **"¿Qué es exactamente `CupoNoDisponible` y por qué no lanzan excepciones propias para todo?"**
   → "Es una excepción de dominio que indica 'no hay cupo pero el staff PUEDE forzar'. Hereda de
   `ValueError` para que las rutas la manejen ya con un solo `except`; el controlador la traduce a
   HTTP 409 con el código `CUPO_NO_DISPONIBLE`, y la pizarra muestra el diálogo de forzado."

---

## Criterio 2 · Uso de recursos del lenguaje elegido — 2 pts

Recursos del lenguaje INTELIGENTEMENTE elegidos (no alardes gratuitos). Cada uno con el "por qué":

1. **Decoradores** (`@requiere_rol("admin", "empleado")`, `@app.errorhandler(404/500)`,
   `@app.context_processor`): control de acceso declarativo en ~1 línea por ruta; el mecanismo
   de composición propio de Python. *Evidencia: `app/auth/decoradores.py` + cualquier `routes.py`.*
2. **App factory + Blueprints** (`create_app()`): una función que arma la app con distintas
   configuraciones (producción vs `TestConfig` para las 52 pruebas). Es la forma idiomática de
   Flask y la razón por la que correr 52 pruebas no toca los datos reales del local.
3. **Manejo de excepciones como contrato de negocio**: 123 `raise ValueError("mensaje al usuario")`
   espejo de las rutas; `try/except/finally` para limpieza de recursos (los archivos de prueba
   restauran la base con `finally` incluso si algo falla).
4. **f-strings y formato localizado Perú**: moneda `S/`, fechas `dd/mm/aaaa`, hora 12 h am/pm;
   todo formateado en `utils.py`.
5. **Diccionarios y listas por comprensión** para mapear datos: serialización JSON uniforme
   (`{"ok": true, "datos": ...}`), tablas de transición de estados, listas de franjas horarias.
6. **`datetime`, `timedelta` y SQL de fechas**: cálculo de tolerancia, franjas de 30 min, ciclos
   `generate_series` para el horario. Lo calculado (cupos, totales, saldo) sale de SQL — nunca
   duplicado en Python (ej. `schema.sql` genera 22 franjas del día con un solo `SELECT`).
7. **psycopg 3 con parámetros %s** + context manager (`with db.cursor()`); transacciones con
   `commit`/`rollback` explícitos.
8. **`werkzeug.security`** (`generate_password_hash`, `check_password_hash`): nunca guardamos
   contraseñas en claro.
9. **python-dotenv**: secretos en `.env` (nunca en el repo); solo se publica `.env.example` falsa.
10. **Jinja2 + autoescape activo** y el helper `esc()` global en JavaScript para el lado del navegador.

Pregunta probable: **"¿Dónde usan realmente programación funcional?"** → "Donde tiene sentido:
hecha por módulos puros que reciben datos y retornan datos (la capa de servicios), comprehensions
para transformaciones, funciones de orden superior con decoradores, y diccionarios como
tablas de despacho para las transiciones."

---

## Criterio 3 · Control de versiones (GitHub) — 3 pts

Tienes 34 commits bien nombrados y ramas por fase. Para defenderlo:

1. **Historia contable**: `git log --oneline` muestra commits temáticos pequeños:
   *"Fase 3.2: pizarra - tarjeta completa solo en su franja..."*, no "cambios" ni "arreglos varios".
2. **Estrategia de ramas**: `main` estable + rama `fase-3-1` por bloque de cambio (el propio
   doc `AGENTS.md` sección 14 lo exige: "commits pequeños y descriptivos, uno por funcionalidad").
3. **`.gitignore` serio**: la base de datos viva, `.env` (secretos), `__pycache__`, `.venv` nunca
   subieron. El `.env.example` sí, con valores falsos (seguridad demostrable en vivo).
4. **Trabajo en equipo**: la propia historia refleja entregas por fase y agrupación — cada fase
   es un punto de restauración. Si mañana se rompe algo, se puede mirar el estado exacto de Fase 3.
5. **Documentación viviendo en el repo**: `AGENTS.md` (reglas del proyecto), `README.md` (cómo
   instalar: python, venv, pip install, init-db, seed), `DICCIONARIO_BASE_DE_DATOS.md` (tabla por
   tabla), `PASOS_PREVIOS.md` (entrevistas) — un compañero nuevo onboarding se hace leyendo el repo.

Demo en vivo sugerida: `git log --oneline | head` + `git diff <hash_fase2>..<hash_fase3> --stat`
para mostrar el volumen por fase. Pregunta probable: **"¿Qué pasa si dos editan el mismo
archivo?"** → "Los módulos están separados por blueprint; en la práctica los conflictos fueron
raros, y cuando ocurrieron se resolvieron a mano revisando con `git pull`."

---

## Criterio 4 · Implementación de interfaces gráficas — 6 pts (¡el más pesado!)

25 pantallas evaluables (6 puntos: el criterio más pesado). El orden sugerido del recorrido (5–7 min):

| # | Pantalla | Qué dice el evaluador |
|---|---|---|
| 1 | `/` pública + carta | El cliente ve la carta completa escaneando el **QR** de su mesa (sin cuenta, sin descargar apps) |
| 2 | `/reservar` | Formulario: validación teléfono 9 dígitos que empieza en 9, honeypot, consentimiento; el semáforo por hora **sin exponer números del aforo** |
| 3 | `/pedido/<token>` | Seguimiento del pedido con UUID (no el id) + instrucciones Yape |
| 4 | Login staff + `/staff/reservas` | **La joya**: pizarra con una tarjeta completa solo en su franja, líneas compactas "↳ continúa", barras de progreso coloreadas por nivel (`fn_carga_dia`), menú ⋮ de WhatsApp/teléfono/correo, cambiar hora en dos toques |
| 5 | `/staff/pedidos` (cola) + `/staff/pedidos/cocina` | Kanban con temporizador en rojo al superar el umbral, los pedidos **recojo primero** (el cliente espera afuera), **pantalla que no se duerme** (Screen Wake Lock), botón de sonido opcional para pedidos nuevos |
| 6 | `/staff/pedido/<id>/ticket` | Ticket para tiquetera 80 mm con **QR que abre el detalle desde el celular** del staff |
| 7 | `/admin/config` | Dueña edita aforo, mesas, **3 duraciones de mesa**, umbral de cocina: cero código cuando la regla cambia |

Argumentos técnicos que suben nota:
- **Mobile-first real**: se demuestra abriendo las mismas pantallas desde el celular (el staff opera
  con tablet/celular desde la pizarra), no exportando a escritorio.
- **Accesibilidad de la operación**: botones grandes, estados finales sin botones de regreso —
  el sistema guía al staff solo hacia transiciones válidas.
- **Refresco automático cada 10 s con `fetch`** (sin WebSockets) y **banner "Sin conexión: no se
  puede operar"** con los botones deshabilitados (`data-requiere-conexion` en `main.js`) —
  coherente con la regla: sin conexión no se opera, no hay modo offline que mienta.
- **Instalable desde el navegador (PWA)**: solo mencionarlo si la Fase 4 ya está implementada;
  si no, no tocar el tema.

Pregunta probable: **"¿Por qué Bootstrap y no componentes propios?"** → "Estamos en pocos días
reales con un cliente esperando: Bootstrap nos dio formularios accesibles y responsive listos, y
el esfuerzo lo invertimos en los tableros de operación (pizarra, cocina), que es lo que sostiene
el negocio."

---

## Criterio 5 · Construcción del producto final — 4 pts

**Está corriendo de verdad para un cliente real** (la pollería Quero de Lima, con su carta
oficial, su número de Yape real y su horario real — todo cargado en `seed.sql`). Puntos fuertes:

1. **Flujo de extremo a extremo demostrable**: QR → carta → reserva o pedir → el staff recibe
   (solicitudes pendientes + insignia "ya pidió hace menos de 24 h") → cocina → listo → cobrado
   (el pago se confirma SIEMPRE mirando el Yape/Plin real, nunca la captura del cliente) → entregado → ticket.
2. **52 pruebas en verde** en la sesión completa (`pytest -q` corre en ~19 s).
3. **Datos = los del local**: aforo, mesas, duraciones, umbrales editables por la dueña en
   Configuración (principio "cambiar lo mínimo los procesos del local": la dueña sigue usando
   su Yape, su WhatsApp y una tiquetera; el sistema se ajustó a eso).
4. **Estados con máquina segura**: una sola función `transicion_pedido` / `transicion_reserva`
   rechaza estados inválidos (un pedido `cancelado` no puede volver a nada; `no_llego` es final).
5. **Instalación documentada y reproducible**: el `README.md` permite montar el sistema en otra
   máquina en minutos: crear venv → `pip install -r requirements.txt` →
   `python manage.py init-db` → `python manage.py cargar-ejemplo` + `crear-admin` → correr Flask.

Pregunta probable: **"¿Qué pasa si la dueña quiere cobrar un pedido que aún no se preparó?"**
→ "Puede cobrar en cualquier momento — un pedido local nace directamente en preparación y otro
queda por cobrar sin bloquear la caja. La regla es 'el staff decide': el sistema nunca mueve
estados ni pagos por su cuenta, el cliente no bloquea ni cambia nada."

---

## Criterio 6 · Sustentación oral — 2 pts

Estructura de exposición (8 min si te dejan, 5 min con cronólogo estricto):

1. **(1 min) Problema** — "La pollería Quero (San Juan de Lurigancho, cliente real) gestiona hoy
  reservas con pizarra de papel, pedidos por WhatsApp y tickets de tiquetera. Se pierden reservas,
  se saturan mesas y no hay control de Yape."
2. **(1 min) Solución + alcance** — "Web adaptable a celular/tablet/computador, instalable como
  PWA (sin app nativa), tres roles: cliente sin cuenta, empleado y admin. Alcance acotado con el negocio."
3. **(2 min) Arquitectura** — apoyado en AGENTS.md sección 4 y la tabla de Mapeo del Criterio 1.
  Mostrar `schema.sql` un minuto: "las reglas de capacidad viven en la base de datos".
4. **(2 min) Demo guiada** — el recorrido del Criterio 4 con datos pre-cargados.
5. **(1 min) Calidad** — `pytest` en vivo (52 verde en 19 s) + `git log --oneline`.
6. **(1 min) Cierre** — lo aprendido + qué haría con 1 semana más (notificaciones por correo,
  recepción de reservas por WhatsApp, impresión automática en la tiquetera — ya especificado en el doc).

### Frases que te evitan puntos perdidos

- Si no sabes algo: *"esa decisión la tomamos por X en su momento y quedó documentada en `AGENTS.md`"*.
  Nunca inventes en vivo.
- Si preguntan algo de otra parte del código: *"el módulo se llama X, su único trabajo es Y"*
  (usando la tabla de mapeo del Criterio 1).
- Si preguntan por "clases": devuelve a las 2 clases REALES que existen (`Config`, `CupoNoDisponible`)
  y al decorador de roles. Eso demuestra conocer Python, no recitar UML.
- Termina SIEMPRE con: *"el sistema está en producción local con datos reales del cliente y 52
  pruebas en verde"* — es la oración que resume Criterio 4 y 5 a la vez.

### Preguntas trampa ya previstas (estudia estas cinco)

1. **"¿Cómo evita el cliente un doble pago con Yape?"** → El staff compara el monto exacto encima
   de Yape real; el sistema no permite registrar más que el total, y `cobrado` sale de la vista
   `v_pedido_resumen` en BD.
2. **"¿Qué impide que alguien reserve o pida para otro desde el celular?"** → El teléfono es obligatorio
   (9 dígitos que empiezan en 9) pero la reserva web nace PENDIENTE: no ocupa cupo hasta que el staff
   la revisa y confirma; el tope es de 2 reservas web por teléfono en 24 h y el staff puede verificar
   el número por WhatsApp antes de confirmar.
3. **"¿Por qué permiten que el cliente ponga un teléfono ajeno?"** → Lo miramos de frente: una
   reserva web nace PENDIENTE (no reduce cupo) y un pedido `recojo` no entra a cocina hasta que el
   staff lo acepta y confirma el pago real; con el menú ⋮ de WhatsApp el staff verifica el número
   antes de confirmar. Un número falso igual acaba en nada que entregar, y los datos del cliente
   nunca se fusionan automáticamente.
4. **"¿Qué pasa si la app se cae en medio del servicio?"** → El staff no queda bloqueado: cada
   acción es un paso independiente y los pedidos ya vivos quedan en PostgreSQL (base de datos de
   verdad, no memoria). Al reiniciar el servidor todo está ahí; el ticket impreso es el plan B
   físico que el local ya usaba.
5. **"¿Cuál fue la parte más difícil?"** → Respuesta honesta y técnica: "que la pizarra no
   bloquee al staff. El cupo es un filtro duro para la web pública, pero para el staff es solo una
   alerta: si no hay cupo, el sistema advierte y le da la opción de FORZAR dejando la reserva
   marcada (`excede_cupo = TRUE`). Nos obligó a diseñar la misma regla con dos comportamientos
   distintos según quién la ejecute."

---

## Bonus: tabla-resumen para tu slide 3 (arquitectura)

```
Cliente (QR) ──► Flask publico/ ──► servicios/ ──► db.py ──► PostgreSQL (schema.sql)
Staff (login) ──► reservas/ pedidos/ carta/ admin/ (blueprints) ▲
                                  api/ (JSON /api/v1)  ────────┘  ← la usan la pizarra, la cocina
                                                              y (futuro) el agente de impresión
Reglas de negocio: config_local + funciones SQL (fn_carga_dia, fn_hay_cupo, fn_duracion_estadia)
```
