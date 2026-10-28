# Guía para entender Quero APP (Flask + Python) desde lo que ya sabes

Pensada para alguien que sabe **HTML, CSS, JavaScript, POO y patrones de diseño**, y que hoy ve "Flask", "blueprint" y "servicio" como otro idioma. Todos los ejemplos salen de **tu propio código** (`Reservas_Quero.zip`, Fase 2). No hay teoría suelta.

Cómo usarla: lee las secciones 1 a 3 (15 minutos). Eso ya te permite explicar el proyecto. Las demás las consultas cuando haga falta.

---

## 1. La idea central: tu proyecto es un restaurante

Una web con backend se organiza como un restaurante. Es la mejor forma de no perderte:

| En el restaurante | En el proyecto | Carpeta | Lo que ya conoces |
|---|---|---|---|
| **La carta** (lo que ve el cliente) | Plantillas HTML | `app/templates/` | HTML + CSS |
| **El mozo** (recibe el pedido y lo lleva) | Rutas | `app/*/routes.py` | Un `addEventListener`, pero para URLs |
| **La cocina** (donde están las reglas) | Servicios | `app/servicios/` | Las clases con la lógica de negocio en POO |
| **El almacén** (donde se guarda todo) | Base de datos PostgreSQL | `schema.sql` | Donde vive la información |
| **El jefe de sala** (quién entra y adónde) | Login y roles | `app/auth/` | Control de acceso |

**Regla de oro del proyecto** (está en `AGENTS.md`): el mozo no cocina. Las rutas solo reciben y entregan; las reglas ("¿hay cupo?", "¿puede pasar de pendiente a confirmada?") viven en `servicios/`. Esto es lo que más importa para SOLID (sección 9).

**El camino de cualquier acción:**

```
Navegador  →  Ruta (mozo)  →  Servicio (cocina)  →  Base de datos (almacén)
   ↑                                                        │
   └──────────── HTML o JSON de vuelta ←────────────────────┘
```

---

## 2. Python para alguien que sabe JavaScript

| JavaScript | Python | Ejemplo de tu código |
|---|---|---|
| `{ }` para bloques | **Sangría (4 espacios)** | Si la sangría está mal, el código falla |
| `;` al final | No se usa | |
| `const x = 5` | `x = 5` | Sin `const`/`let` |
| `null` | `None` | `if not reserva:` |
| `true / false` | `True / False` | Con mayúscula |
| `function f(a) {}` | `def f(a):` | `def hoy():` |
| `` `Hola ${nombre}` `` | `f"Hola {nombre}"` | `f"Código: {reserva['codigo']}"` |
| Objeto `{a: 1}` | Diccionario `{"a": 1}` | `fila["nombre"]`: se accede por llave |
| Array `[]` | Lista `[]` | `fechas_permitidas = []` |
| `this` | `self` | `class UsuarioStaff` |
| `constructor` | `__init__` | `def __init__(self, datos):` |
| `import x from './x'` | `from app.db import consultar_uno` | |
| `index.js` de una carpeta | `__init__.py` | Marca la carpeta como paquete |
| `try / catch` | `try / except` | `except ValueError as error:` |
| `throw new Error()` | `raise ValueError("...")` | |
| `...args` (rest) | `*args` | `requiere_rol(*roles_permitidos)` |
| `npm` / `package.json` | `pip` / `requirements.txt` | |
| `node_modules` | `.venv` (entorno virtual) | Cada proyecto con sus propias librerías |
| `try/finally` para cerrar | `with ... as ...:` | `with db.cursor() as cur:` cierra solo |
| `@` no existe | **Decorador** `@algo` | Ver 4.1 |

**`__pycache__`** son archivos que Python genera solo (código ya traducido). Se ignoran: están en `.gitignore`.

---

## 3. Mapa del proyecto: qué es cada archivo

```
Reservas_Quero/
├── manage.py            ← Botones de consola: init-db, cargar-ejemplo, crear-admin. Y arranca la app.
├── schema.sql           ← Todas las tablas, vistas y funciones SQL.
├── seed.sql             ← Datos de ejemplo.
├── requirements.txt     ← Lista de librerías (como package.json).
├── .env                 ← Secretos (clave de BD). NUNCA se sube a Git.
├── AGENTS.md            ← Reglas del proyecto para Antigravity.
├── PROMPTS_POR_FASE.md  ← Las órdenes por fase.
├── tests/               ← Pruebas automáticas (pytest).
└── app/
    ├── __init__.py      ← create_app(): arma toda la aplicación.
    ├── config.py        ← Lee el .env y guarda la configuración.
    ├── db.py            ← 5 funciones para hablar con PostgreSQL.
    ├── utils.py         ← Herramientas sueltas (normalizar teléfono, QR, formato de hora).
    ├── publico/         ← Rutas del cliente: /, /carta, /reservar, /reserva/<token>
    ├── auth/            ← Login, logout, roles.
    ├── reservas/        ← Páginas del staff: pizarra, detalle, ticket.
    ├── carta/           ← Carta del staff.
    ├── admin/           ← Configuración y personal (solo admin).
    ├── api/             ← Rutas que devuelven JSON (los datos de la pizarra, botones).
    ├── servicios/       ← LAS REGLAS: reservas, clientes, carta, personal, configuracion.
    ├── templates/       ← HTML con huecos para datos (Jinja2).
    └── static/          ← CSS y JS que no cambian (style.css, main.js).
```

**Por qué hay una carpeta por tema** (`publico/`, `auth/`, `reservas/`...): cada una es un **Blueprint** (sección 4.4). Es separar el código por módulos, como separarías componentes en JS.

---

## 4. Los conceptos de Flask, uno por uno

### 4.1 Ruta y decorador: "cuando alguien visite esta URL, ejecuta esta función"

Tu código (`publico/routes.py`):

```python
@publico_bp.route("/carta")
def carta():
    carta_datos = servicio_carta.obtener_carta_publica()
    return render_template("publico/carta.html", carta=carta_datos, ...)
```

- Es como `boton.addEventListener('click', fn)`, pero el "evento" es **alguien visitando una URL**.
- Lo que empieza con `@` es un **decorador**: una función que recibe otra función y la "envuelve" con algo extra. En JS es una *función de orden superior*.
- `render_template` toma un HTML y le rellena los datos. Devuelve la página al navegador.

**Tu decorador más importante: `requiere_rol`** (`auth/decoradores.py`). Se pone sobre las rutas del staff:

```python
@reservas_bp.route("/reservas")
@requiere_rol("admin", "empleado")
def pizarra(): ...
```

Antes de ejecutar `pizarra()`, el decorador revisa: ¿hay sesión? ¿debe cambiar clave? ¿su rol está permitido? Si no, redirige o devuelve 401/403. **Una sola vez escrito, protege todas las rutas.** Tiene tres funciones anidadas (`requiere_rol` → `decorador` → `envoltura`); es un *closure* de JS, nada nuevo.

### 4.2 GET, POST y redirect

- **GET** = "dame esta página". **POST** = "te envío datos de un formulario".
- En `/reservar`, la misma ruta atiende los dos: GET muestra el formulario; POST lo procesa.
- Al terminar un POST con éxito, el código hace `redirect(...)` en vez de mostrar la página directamente. Se llama *Post/Redirect/Get*: evita que, si el cliente recarga la página, se envíe la reserva dos veces.
- `flash("mensaje", "success")` guarda un aviso que se muestra **en la siguiente página**. Es el recuadro verde o rojo de Bootstrap.
- `url_for("publico.reserva_estado", token=...)` construye la URL por el **nombre de la función**, no escribiendo el texto. Si cambias la URL, nada se rompe.

### 4.3 Plantillas Jinja2: HTML con huecos

En `templates/base.html`:

```html
<title>{% block titulo %}Quero Gastrobar{% endblock %} - Reservas y Pedidos</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```

- `{{ algo }}` imprime un valor (como `${algo}` en un template literal).
- `{% ... %}` son instrucciones (`if`, `for`, `block`).
- `base.html` es el **molde** (menú, banner "sin conexión"). Las demás páginas hacen `{% extends "base.html" %}` y solo rellenan sus `block`. Es **herencia de plantillas**: escribes el menú una vez.

### 4.4 Blueprint: un módulo de rutas

```python
publico_bp = Blueprint("publico", __name__)
reservas_bp = Blueprint("reservas", __name__, url_prefix="/staff")
```

Es un paquete de rutas con nombre. `url_prefix="/staff"` pone `/staff` delante de todas sus URLs. Después, en `app/__init__.py`, se "enchufan": `app.register_blueprint(...)`. Piénsalo como **un componente por sección** de la web.

### 4.5 App Factory: una función que fabrica la aplicación

`app/__init__.py` tiene `create_app()`. En vez de crear la app suelta, la construye dentro de una función: configura la base de datos, el login, el CSRF, enchufa los blueprints y los manejadores de error. **Es el patrón de diseño *Factory Method***: una función que fabrica el objeto ya armado. Sirve para que las pruebas creen una app distinta (con `TestConfig`) sin tocar la real.

### 4.6 `.env` y `config.py`: los secretos fuera del código

`.env` contiene `DATABASE_URL`, `SECRET_KEY` y `BASE_URL`. `config.py` los lee con `os.getenv(...)`. Así la contraseña de tu base **no está escrita en el código** ni se sube a GitHub (por eso `.env` está en `.gitignore`).

### 4.7 Hablar con la base de datos: `db.py`

Cinco funciones, todas con la misma idea:

```python
consultar_uno("SELECT ... FROM cliente WHERE telefono = %s", (tel,))
```

- **`%s` y la tupla aparte**: se llama *consulta parametrizada*. **Nunca** se pega el dato dentro del texto SQL. Es la defensa contra la *inyección SQL* (que alguien escriba código SQL en un formulario para atacar la base).
- Devuelve **diccionarios** (`fila["nombre"]`) por la opción `dict_row`.
- **Sin ORM:** escribes el SQL tú mismo. Un ORM (como Hibernate/JPA, que ya viste en tu otro curso) traduce clases a tablas automáticamente. Aquí se eligió lo contrario: más control y más fácil de entender qué pasa. Tiene un costo: el SQL queda repartido en los servicios.
- `g` es un cajón que Flask crea **por cada petición** y vacía al terminar. Ahí se guarda la conexión (`g.db`). `app.teardown_appcontext(cerrar_db)` garantiza que se cierre al final, pase lo que pase. Es el `finally` de la petición.

### 4.8 Login y seguridad

| Pieza | Qué hace |
|---|---|
| **Flask-Login** | Recuerda quién inició sesión (con una cookie). `UsuarioStaff` es la clase que representa al usuario. |
| **`generate_password_hash`** | Convierte la contraseña en un código irreversible. Se guarda el hash, nunca la clave. |
| **CSRF (Flask-WTF)** | Un código secreto escondido en cada formulario, para que otra página maliciosa no pueda enviar formularios en nombre del usuario. |
| **Honeypot** | En `/reservar` hay un campo `pagina_web` que un humano no ve. Los bots lo llenan; si viene lleno, se rechaza. |
| **`obtener_usuario_actual()`** | La **única** forma permitida de saber quién es el usuario. Si mañana el login cambia a tokens, solo se cambia esta función. |

### 4.9 Manejo de errores

En `create_app` hay un `@app.errorhandler(404)` (y 400, 401, 403, 500). Si la ruta empieza con `/api/`, responde JSON; si no, muestra una página HTML de error. **Un solo lugar, respuestas consistentes.**

### 4.10 API JSON y `fetch`: la pizarra que se actualiza sola

- Rutas bajo `/api/v1/...` no devuelven HTML, devuelven **datos** en formato fijo: `{"ok": true, "datos": ...}` o `{"ok": false, "error": {...}}` (`api/helpers.py`).
- `pizarra.html` hace `fetch(...)` a `/api/v1/reservas/dia` y vuelve a pintar. Con `setInterval(refrescar, 10000)` lo repite **cada 10 segundos** (al final de `pizarra.html`, línea 587).
- Es tu JavaScript de siempre. La novedad: **el servidor ya no manda HTML, manda JSON**, y tu JS dibuja.
- Los botones del staff (confirmar, rechazar, "llegó", cambiar hora) llaman rutas `POST` de esa API.

### 4.11 `manage.py`: botones de consola

```
python manage.py init-db        # crea las tablas
python manage.py cargar-ejemplo # carga datos de prueba
python manage.py crear-admin    # crea tu cuenta de administrador
```

Son como los `scripts` de `package.json`. `manage.py` también crea la `app`, por eso el servidor se levanta con `flask --app manage run --debug` (así lo dice tu README).

### 4.12 `pytest`: pruebas automáticas

- Cada función `test_...` comprueba una regla. Hay **35 pruebas** en 5 archivos (`tests/`).
- `conftest.py` prepara el escenario común (como un `beforeEach` de Jest): crea una app de prueba y usuarios de prueba, y los borra al terminar.
- Ejecutas `pytest` y debe salir todo en verde. El caché de tu zip muestra **cero fallos** en la última corrida, pero no la ejecuté yo.
- Ojo: **las pruebas usan tu base de datos real** (la del `.env`). Por eso borran lo que crean.

---

## 5. Seguimos una petición completa: "un cliente reserva"

Lo que pasa cuando alguien llena `/reservar` y pulsa Enviar:

1. **Navegador** envía un POST a `/reservar`.
2. **`publico/routes.py → reservar()`** recibe los datos y revisa el campo trampa.
3. Llama a **`servicio_reservas.crear_reserva_web(datos)`** (la cocina).
4. El servicio, en orden:
   - valida nombre, teléfono (9 dígitos que empiezan en 9), fecha y número de personas;
   - comprueba que la hora sea una franja válida;
   - pregunta a la base si hay cupo (`fn_hay_cupo`, una función SQL). **En la web, sin cupo no se reserva** (`CupoNoDisponible`);
   - busca al cliente por teléfono o lo crea, sin sobrescribir sus datos (`obtener_o_crear_cliente`);
   - revisa el tope de reservas web por teléfono en 24 h;
   - revisa que no tenga ya una reserva igual;
   - hace el `INSERT` con estado `pendiente` y un código `Q-XXXXXX`.
5. Si algo falla, el servicio lanza `ValueError("mensaje claro")`. La ruta lo atrapa y lo muestra con `flash(...)`.
6. Si todo sale bien, **redirige** a `/reserva/<token>`, que muestra el estado.

Luego el **staff** ve la solicitud en la pizarra, la **confirma** (`confirmar_reserva`) y recién ahí ocupa cupo. Si ya no cabe, le advierte y puede **forzar**; queda marcada con `excede_cupo = TRUE`.

**Lo importante:** la ruta tiene unas 20 líneas útiles y **ninguna regla**. Todas están en el servicio. Eso es lo que le da orden al proyecto.

---

## 6. Dos ideas del servicio de reservas que conviene entender

### 6.1 Máquina de estados

```python
TRANSICIONES_VALIDAS = {
    "pendiente":  {"confirmada", "rechazada", "cancelada"},
    "confirmada": {"llego", "no_llego", "cancelada"},
}
```

Es un diccionario que dice **a dónde se puede ir desde cada estado**. Y `transicion_reserva()` es la **única función** que cambia un estado: revisa este diccionario y rechaza lo imposible (por ejemplo, de `rechazada` a `confirmada`). Los estados finales (`llego`, `no_llego`...) no aparecen como llave, así que no se pueden mover. Para agregar un estado nuevo, **añades datos**, no código.

### 6.2 Qué hace la base de datos y no Python

El cálculo de "cuántas personas y mesas hay por franja" (`fn_carga_dia`) y "¿cabe este grupo?" (`fn_hay_cupo`) están **en SQL**, no en Python. Python solo las llama. Ventaja: hay **una sola fuente de la verdad** y no se calcula distinto en dos sitios. Desventaja: para entender esa regla tienes que leer SQL.

---

## 7. ¿Qué es una "fase" y cómo trabajar sin saber Flask?

Una fase es un paquete de trabajo para el agente (Antigravity). Cada prompt termina con "Presenta el plan antes de programar" y un **criterio de terminado**. Tu trabajo no es escribir Flask: es **dirigir y verificar**.

**Checklist al terminar cada fase:**
1. Lee el plan **antes** de aprobar. Pregunta: "¿qué archivos vas a crear?" y "¿esto cumple las reglas de `AGENTS.md`?".
2. Corre `pytest`. Todo debe salir en verde.
3. Prueba el **criterio de terminado** del prompt en el navegador, punto por punto.
4. `git status` y luego un commit. Confirma que `.env` **no** aparece.

**Qué construyó la Fase 2:** formulario público `/reservar`, seguimiento `/reserva/<token>`, la pizarra del staff con alertas por color, las acciones (confirmar, rechazar, cancelar, llegó, no vino, cambiar hora, forzar cupo), el ticket imprimible con QR y las pruebas.

---

## 8. POO y patrones de diseño: qué hay realmente

Primero lo importante y poco cómodo: **este proyecto es sobre todo programación modular con funciones, no POO clásica.** Hay clases, pero pocas: `UsuarioStaff`, `Config`, `CupoNoDisponible`. Los servicios son módulos de funciones, no clases. Eso no es un error (Python lo permite y Flask lo promueve), pero si la profesora pregunta por POO, hay que decirlo con claridad.

| Patrón | Dónde está | Comentario |
|---|---|---|
| **Factory Method** | `create_app()` | Fabrica la app ya configurada. |
| **Decorator** | `@requiere_rol(...)` | Es el patrón y además una función del lenguaje. |
| **Service Layer** | `app/servicios/` | La lógica de negocio fuera de las rutas. |
| **Máquina de estados** | `TRANSICIONES_VALIDAS` | Sustituye a un montón de `if`. |
| **Herencia de plantillas** | `base.html` + `extends` | Parecido a *Template Method*: el molde fija la estructura y cada página rellena huecos. |
| **Inyección de configuración** | `create_app(config_class=Config)` | Se verá en D de SOLID. |
| **Módulo/Facade ligero** | `db.py` | Esconde psycopg tras 5 funciones simples. |

---

## 9. SOLID aplicado a tu proyecto (evaluación honesta)

Una advertencia antes de presumir: **si dices "cumple todo SOLID", la profesora puede desmontarlo en un minuto.** Si dices "cumple S, O y D en parte, y estos son los puntos débiles", demuestras que entendiste. Eso vale más.

### S: Responsabilidad única: *cumple a medias*
**A favor:** cada capa hace una sola cosa. Rutas = HTTP; servicios = reglas; `db.py` = acceso a datos; `templates/` = presentación; `config.py` = configuración. Cada servicio es de un tema (`clientes`, `carta`, `personal`).

**En contra, con evidencia:**
- `publico/routes.py` hace `consultar_uno("SELECT ...")` **tres veces** (líneas 14, 24 y 34) y `auth/routes.py` accede a la base en tres puntos. Eso **rompe la regla del propio proyecto** ("las rutas no tocan la base").
- `servicios/reservas.py` tiene **542 líneas** con validaciones, cupo, estados, semáforo público y armado de la pizarra. Son varias responsabilidades en un solo archivo.

### O: Abierto/Cerrado: *cumple bien*
**A favor:** agregar un estado de reserva es agregar una entrada a `TRANSICIONES_VALIDAS`, sin tocar la función que valida. `requiere_rol(*roles)` acepta cualquier combinación de roles sin modificarse. Agregar un módulo nuevo es crear un blueprint y sumar **una línea** en `create_app`.
**Límite:** un canal nuevo (por ejemplo WhatsApp) también exige cambiar un `CHECK` en `schema.sql`.

### L: Sustitución de Liskov: *casi no aplica*
Hay dos casos reales: `CupoNoDisponible(ValueError)` se puede usar donde se espere un `ValueError` (las rutas atrapan `ValueError` y funciona igual), y `UsuarioStaff(UserMixin)` es aceptado por Flask-Login como cualquier usuario. Con tan poca herencia, **no hay evidencia fuerte**. Dilo así.

### I: Segregación de interfaces: *aceptable, débil como evidencia*
Python no tiene interfaces. Se cumple de forma indirecta: módulos chicos y funciones pequeñas, y cada ruta importa **solo el servicio que usa** (`from app.servicios import carta as servicio_carta`). No obliga a nadie a depender de lo que no usa. Es un argumento razonable, pero no es una demostración.

### D: Inversión de dependencias: *cumple en parte*
**A favor:**
- `create_app(config_class=Config)` **recibe** la configuración en vez de fijarla dentro. Las pruebas pasan `TestConfig` y no cambian una sola línea de la app. Es inyección de dependencias real.
- `obtener_usuario_actual()` es una abstracción: las rutas dependen de **esa función**, no de cómo se guarda la sesión.

**En contra:** los servicios importan `app.db` directo (`from app.db import consultar_uno...`). Dependen de la implementación concreta, no de una abstracción. Por eso las pruebas necesitan la base real.

### Resumen

| Principio | Valoración | Argumento más fuerte |
|---|---|---|
| S | Parcial | Capas separadas; pero 3 rutas tocan la BD y `reservas.py` es muy grande |
| O | Bueno | `TRANSICIONES_VALIDAS`, `requiere_rol(*roles)`, blueprints |
| L | Poco aplicable | Solo 2 herencias |
| I | Aceptable | Módulos pequeños y dependencias mínimas |
| D | Parcial | `create_app(config_class)` y `obtener_usuario_actual()` |

### Cómo decirlo en la exposición
> "Usamos arquitectura en capas con *service layer*: rutas, servicios y acceso a datos separados. Cumple claramente **Abierto/Cerrado** (estados como datos y decoradores parametrizados) y en parte **Responsabilidad única** e **Inversión de dependencias** (configuración inyectada en la fábrica de la app). **Liskov** e **Interfaces** aplican poco porque el diseño es modular y no jerárquico. Identificamos dos puntos a mejorar: algunas rutas consultan la base directamente y el servicio de reservas debería dividirse."

### Mejoras baratas que subirían la nota (no están hechas)
1. En `publico/routes.py`, cambiar los `consultar_uno(...)` por `servicios/configuracion.obtener_config_local()`, que **ya existe**. Mueve las lecturas a su capa.
2. Mover las consultas de `auth/routes.py` a `servicios/personal.py`.
3. Dividir `servicios/reservas.py` en `validaciones`, `cupo`, `ciclo_vida` y `pizarra`.

Si quieres, le pido a Antigravity las tres como "Fase 2.1", con la condición de que las pruebas sigan en verde.

---

## 10. Preguntas de repaso (para comprobar que lo entendiste)

1. ¿Por qué `reservar()` no tiene la regla "¿hay cupo?" escrita dentro?
2. ¿Qué diferencia hay entre una ruta de `publico/` y una de `api/`?
3. ¿Qué pasa si alguien quita el decorador `@requiere_rol` de `pizarra()`?
4. ¿Por qué se escribe `%s` y no se pega el teléfono en el SQL?
5. ¿Cómo agregarías el estado `"en_mesa"` a las reservas? ¿Qué archivos tocarías?
6. ¿Por qué `create_app` recibe `config_class`?

**Respuestas cortas:** (1) para que la regla viva en un solo sitio y sirva a web, staff y API. (2) `publico/` devuelve HTML; `api/` devuelve JSON. (3) cualquiera, sin sesión, vería la pizarra. (4) para evitar inyección SQL. (5) `TRANSICIONES_VALIDAS` en el servicio **y** el `CHECK` de `estado` en `schema.sql`. (6) para poder crear una app de pruebas con otra configuración.

---

## 11. Glosario rápido

| Palabra | Equivalente que ya conoces |
|---|---|
| Flask | El servidor que escucha URLs y responde |
| Ruta | `addEventListener`, pero para URLs |
| Decorador | Función de orden superior |
| Blueprint | Un módulo/componente de rutas |
| Jinja2 | Template literals, con herencia entre páginas |
| venv / `.venv` | `node_modules` por proyecto |
| pip / `requirements.txt` | npm / `package.json` |
| `.env` | Variables de entorno (secretos) |
| Servicio | La clase/módulo con la lógica de negocio |
| ORM | Hibernate/JPA (aquí **no** se usa) |
| `fetch` + JSON | Tu JS de siempre contra una API |
| CSRF | Código oculto en cada formulario contra envíos falsos |
| Hash | Contraseña transformada que no se revierte |
| pytest | Jest/JUnit |
| Fase | Un paquete de trabajo para el agente, con criterio de terminado |
