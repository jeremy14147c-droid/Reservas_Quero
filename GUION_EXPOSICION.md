# Guion de exposición en vivo — "Diseño de la solución (MVC, TDD, DAO, SOLID)"

> Guion para exponer **mostrando el proyecto al mismo tiempo**: cada capítulo dice
> 🖥️ **QUÉ ABRIR** (carpeta/archivo + función + línea exacta), 🎤 **QUÉ DECIR** (texto listo para
> leer, en lenguaje simple con ejemplos) y 💬 **SI PREGUNTAN** (respuestas probables).
> Tiempo total del bloque: **8–9 minutos** (recortable a ~5 min si solo muestras el resumen del Capítulo E).

---

## ANTES DE EMPEZAR (preparación, 2 minutos)

Tener abiertos, en este orden de pestañas:

1. **VS Code** con el proyecto abierto y estos archivos YA en pestañas (no los abres en vivo, solo alternas):
   - `app/__init__.py` (saltar a la línea 53)
   - `app/db.py` (línea 28)
   - `app/servicios/reservas.py` (líneas 22, 28, 261)
   - `app/api/routes.py` (línea 101)
   - `schema.sql` (líneas 235, 257, 319)
   - `tests/test_fase3_2.py` (abrir al inicio y saltar a la prueba de `fn_duracion_estadia`)
2. **Terminal** lista con el comando ya escrito (no ejecutado aún): `.venv\Scripts\python.exe -X utf8 -m pytest -q` — lo corres en vivo en el Capítulo D.
3. **Navegador**: pizarra `/staff/reservas` abierta con el servidor Flask corriendo y al menos una reserva del día (la uses como demo visual del cierre).
4. ⚡ Truco: dos ventanas lado a lado (VS Code a la izquierda, navegador a la derecha); alternar con `Win + ←` / `Win + →`.

---

## CAPÍTULO A · Arquitectura total (MVC) — 2 min

### 🖥️ QUÉ ABRIR
Vista del árbol de carpetas en VS Code (la lateral izquierda). Señalar con el mouse:

```
Reservas_Quero/
├── schema.sql                ← EL MODELO: 10 tablas + 3 funciones SQL + 2 vistas
├── app/
│   ├── __init__.py           ← punto de entrada (app factory)
│   ├── config.py             ← configuración (clase Config)
│   ├── db.py                 ← DAO: única que "conoce" la base
│   ├── publico/ auth/ reservas/ pedidos/ carta/ admin/ api/   ← CONTROLADOR (blueprints)
│   ├── servicios/            ← la lógica de negocio (python puro)
│   └── templates/ static/    ← VISTA (25 pantallas HTML)
└── tests/                    ← TDD: 8 archivos, 52 pruebas
```

### 🎤 QUÉ DECIR
> "El proyecto sigue el patrón **MVC**, y en un proyecto web en Python se ve así:
> los datos y las reglas del negocio son el **Modelo**, y este es doble: el **Modelo de base de
> datos** (aquí, `schema.sql`: 10 tablas, 3 funciones SQL y 2 vistas) y el **Modelo de negocio en
> Python** (la carpeta `servicios`).
> El **Controlador** son los módulos `routes.py` dentro de cada carpeta: reciben la petición HTTP,
> llaman al servicio y responden. Cada módulo es un 'blueprint' de Flask, que separa las rutas por
> zona: lo público, el staff, la API.
> Y la **Vista** son las 25 plantillas HTML en `templates`, con Jinja2 y Bootstrap.
>
> ¿Por qué así y no todo pegado? Es la misma idea que en JavaScript: en React separan **estado**
> (modelo), **componentes** (vista) y **eventos/manejadores** (controlador). Aquí hacemos lo
> mismo sin frameworks ni build: HTML + Jinja2 para la vista, un `fetch` por tablero, y Python
> detrás para el modelo."

### 💬 SI PREGUNTAN
- **"Muestren el flujo de una petición"** → abrir `app/__init__.py` línea 53–59: los 7
  `register_blueprint`. Decir: "cuando llega una ruta, Flask la reparte según el blueprint
  registrado aquí; como el `router` en un proyecto de JS".
- **"¿Vista y Controlador cómo se comunican?"** → abrir cualquier `routes.py` (ej. `estado` 2):
  "La ruta llama al SERVICIO (no a la base) y devuelve `render_template(...)` con los datos ya
  listos. La vista solo pinta; no sabe nada de SQL".

---

## CAPÍTULO B · DAO — 1.5 min

### 🖥️ QUÉ ABRIR
`app/db.py`, desde la **línea 28**: las 4 funciones.

```python
def consultar_todos(sql, params=None):     # línea 28
def consultar_uno(sql, params=None):       # línea 36
def ejecutar(sql, params=None, ...):       # línea 44
def ejecutar_retornando(sql, ...):         # línea 53
```

### 🎤 QUÉ DECIR
> "Esta es nuestra capa **DAO** (Data Access Object): la ÚNICA del proyecto que conoce cómo
> estamos conectados a la base de datos. Toda otra parte del sistema, si quiere datos, tiene que
> pasar por estas 4 funciones.
>
> Dos detalles que en la práctica nos salvaron el proyecto:
> **1)** todas las consultas usan parámetros con `%s`: el valor **NUNCA se concatena al texto
> SQL**, se pasa por separado. Si en JavaScript preparas la consulta sumando strings con el dato
> del usuario (`"SELECT... WHERE telefono = '" + tel + "'"`), alguien puede inyectar código. Aquí
> un cliente podría escribir `' OR 1=1 --` en su teléfono y solo pasaría que la consulta no
> encuentra nada: psycopg ya se encargó de escapar ese valor.
> **2)** es la abstracción del patrón DAO: el día que cambiemos de driver o de motor de base,
> **solo este archivo se toca**."

### 💬 SI PREGUNTAN
- **"¿Por qué la capa DAO no usa una clase por tabla, como el DAO clásico?"** → "Decisión
  consciente: simple antes que completo. En Python el módulo YA cumple ese rol (todo en Python es
  objeto: también los módulos); `db.py` agrupa el acceso a datos y se importa como una sola
  unidad. Si el proyecto creciera, cada 'clase tabla' sería solo más palabras para lo mismo."
- **"¿Cómo hacen singleton de la conexión?"** → "`db.py` se importa UNA vez: todo el sistema
  comparte el mismo módulo y su conexión. Es el singleton idiomático de Python, sin clases
  complicadas."

---

## CAPÍTULO C · SOLID letra por letra — 3 min  ⭐ ES EL MOMENTO CLAVE

### 🔵 S — Single Responsibility (1 responsabilidad por módulo) — 40 s

🖥️ Mostrar apenas cada archivo (pestaña ya abierta, cambio rápido):
- `app/servicios/reservas.py` (solo reservas),
- `app/servicios/pedidos.py` (solo pedidos),
- `app/servicios/carta.py` (solo carta),
- `app/db.py` (solo acceso a datos).

🎤 DECIR:
> "Cada módulo tiene **una sola razón para cambiar**. Es exactamente el principio de una clase
> en C# o Java ('una clase, un motivo'), pero en Python lo aplicamos al **módulo**: aquí un
> módulo ES una unidad funcional, no hace falta crear 15 clases para separar responsabilidades."

### 🟢 O — Open/Closed (abierto a extender, cerrado a modificar) — 50 s

🖥️ ABRIR: `app/servicios/reservas.py`, **línea 22**:

```python
TRANSICIONES_VALIDAS = {
    "pendiente":  ["confirmada", "rechazada", "cancelada"],
    "confirmada": ["llego", "no_llego", "cancelada"],
    ...
}
```

🎤 DECIR:
> "Este diccionario es la tabla de despacho: la única fuente de verdad de qué estados se pueden
> pasar a qué. Hoy tiene pocas líneas, pero si mañana la dueña quiere un estado nuevo (digamos
> 'sentado'), **agregamos una entrada aquí y no tocamos ninguna función**. Es Open/Closed:
> el código está cerrado a modificación y abierto a extensión por **datos**, no por herencia.
>
> Y pasa igual con la configuración: la duración de mesa por tamaño de grupo (30/60/90 min) la
> cambia la dueña desde una pantalla, NO en el código. Imaginen en JavaScript: es como si la tabla
> de configuración viniera de un API y se aplicara sin redeploy."

### 🟡 L — Liskov (una subclase puede usarse donde se espera la base) — 40 s

🖥️ ABRIR: `app/servicios/reservas.py`, **línea 28**:

```python
class CupoNoDisponible(ValueError):
```

y al lado `app/api/routes.py`, **línea 101** → `_manejar_error_negocio`:

```python
if isinstance(error, CupoNoDisponible):   # primero la específica
    return respuesta_error(CODIGO_CUPO, str(error), 409)
if isinstance(error, ValueError):          # luego la genérica
    return respuesta_error("ERROR_NEGOCIO", str(error), 400)
```

🎤 DECIR:
> "Aquí sí usamos herencia de verdad: `CupoNoDisponible` hereda de `ValueError`. Cuando una ruta
> hace `except ValueError`, la subclase entra por el mismo manejo: puede usarse donde se espera la
> base, sin romper nada. Eso es Liskov, que es 'polimorfismo de substitución'.
> Es también el mismo contrato de un `interface` en Java: 'cualquier error de negocio lo sé
> manejar igual'; lo único que cambia es el código HTTP que sale (409 con un código especial en
> vez de 400), y eso lo decide la línea 101 de `api/routes.py`."

### 🔴 I — Interface Segregation (nadie ve de más) — 30 s

🖥️ ABRIR: `app/api/routes.py` (arriba del error handler, el bloque con `@api_bp.route("/reservas/dia")`).

🎤 DECIR:
> "Tenemos DOS superficies para el mismo negocio: la API JSON (`api/routes.py`) que sirve a los
> tableros que se refrescan solos con `fetch` (mini API REST), y las rutas HTML.
> Un consumidor de la web pública **no depende** de nada del panel del staff, y viceversa: cada
> uno usa solo la porción de interfaz que necesita."

### 🟣 D — Dependency Inversion — 40 s  ⏱️ el cierre que más impresiona

🖥️ MOSTRAR una cosa simple y contundente: en la terminal:

```powershell
Select-String -Path app\servicios\*.py -Pattern "from flask" | Measure-Object | % Count
```
→ **0**

🎤 DECIR:
> "Busquen 'flask' en esta carpeta: **cero** resultados. Los servicios no dependen de Flask ni
> del driver de base de datos: reciben datos y devuelven datos (o lanzan errores de negocio).
> Esa es la inversión de dependencia: la capa de REGLAS depende de abstracciones (funciones
> puras, como un método de dominio en Java que no conoce ni Spring ni JDBC), y sí dependen de
> ella las rutas HTTP y la base de datos. Consecuencia práctica: correr las 52 pruebas no toca
> la base real del local, y la lógica se puede reusar en cualquier contexto."

---

## CAPÍTULO D · TDD (test-driven-development) — 1.5 min

### 🖥️ QUÉ ABRIR
1. Terminal → correr en vivo:
   ```powershell
   .venv\Scripts\python.exe -X utf8 -m pytest -q
   ```
   (resultado en vivo: **52 passed in ~19s**)
2. Con el resultado en pantalla, abrir `tests/test_fase3_2.py`, **función `test_fn_duracion_estadia_por_tamano`**
   (señalar la línea del `esperado = {1: 30, 3: 30, ...}`)

### 🎤 QUÉ DECIR
> "Cada funcionalidad tiene su archivo de pruebas: trabajamos con disciplina **TDD** — primero
> el test define qué debe pasar, después el código que lo cumple. Esta suite son 52 pruebas que
> corren en unos 19 segundos y **no son pruebas de humo**: prueban reglas de negocio contra una
> base PostgreSQL de verdad.
>
> Ejemplo concreto (señalando la pantalla): esta prueba llama a la **función SQL**
> `fn_duracion_estadia` con los valores LIMITES 1, 3, 4, 7, 8, 12 y 13 personas, y comprueba que
> devuelva 30, 60 o 90 minutos. No es al azar: 3 es el borde de los grupos chicos, 4 arranca el
> grupo mediano y 8 el grande. Si mañana alguien cambia la regla y rompe el límite del 7, el test
> explota en rojo ANTES de que el dueño del local lo note.
>
> También hay tests de la MÁQUINA DE ESTADOS y del cobro: pagar más que el total se rechaza, y
> un pedido `cancelado` no puede volver a ningún estado."

### 💬 SI PREGUNTAN
- **"¿Qué es TDD de verdad?"** → "El ciclo ROJO–VERDE–REFACTOR: se escribe primero la prueba
  (rojo), luego el código mínimo que la haga pasar (verde), y después se mejora el código que
  siga en verde. Lo aplicamos en las fases de reglas (2 y 3): incluimos casos de rechazo, no
  solo el camino feliz."
- **"¿Cómo manejan la preparación de pruebas?"** → abrir `tests/conftest.py`:
  "Los fixtures `app`, `cliente` y `usuario_prueba`. La app se montó con una clase test"
  (señalar línea 9) `class TestConfig(Config):` → "es herencia REAL: solo cambia la casilla de
  CSRF desactivada; todo lo demás se hereda de la config de producción. Open/Closed otra vez,
  ahora a nivel de clase."

---

## CAPÍTULO E · Resumen visual (slide de apoyo o pizarra) — 30 s

> "En una frase: **cada letra de SOLID tiene un archivo, cada letra tiene un momento de
> demo, y cada regla tiene un test** por si alguien cambia algo mañana."

| Letra | Archivo | Línea/fn |
|---|---|---|
| S | `app/servicios/` (1 responsabilidad por módulo) | — |
| O | `app/servicios/reservas.py` | `TRANSICIONES_VALIDAS` (L22) |
| L | `app/servicios/reservas.py` + `app/api/routes.py` | `CupoNoDisponible(ValueError)` (L28) + `_manejar_error_negocio` (L101) |
| I | `app/api/routes.py` | rutas JSON separadas de las HTML |
| D | terminal | `Select-String "from flask" app/servicios/*.py` → **0 resultados** |
| DAO | `app/db.py` | 4 helpers (L28) |
| MVC | árbol de carpeta | `schema.sql` (M) · `routes.py` (C) · `templates/` (V) |
| TDD | `tests/` (8 archivos, 52 pruebas) | correr `pytest -q` en vivo |

---

## ANEXO · Comparación pedida en la rúbrica (terminal de emergencia)

Si te preguntan "¿esto cómo se compara con [Java/C#/JS/HTML/CSS]?", responde con esta tabla:

| Concepto de otros lenguajes | Equivalente en este proyecto Python |
|---|---|
| **Clase / interface (Java, C#, TypeScript)** | función de servicio con contrato fijo (recibe datos → devuelve datos o lanza error de negocio) |
| **Herencia polimórfica** | `CupoNoDisponible(ValueError)` — la subclase se usa donde se espera la base (L de Liskov) |
| **Annotation / Decorator de Spring o Express middleware** | `@requiere_rol("admin", "empleado")` en `app/auth/decoradores.py` L7: y envuelve la ruta con control de acceso |
| **Tabla de configuración / switch-case** | diccionarios de despacho (`TRANSICIONES_VALIDAS`, los estados del pedido) |
| **Objeto de JavaScript / Map** | `dict` de Python (los JSON salen de diccionarios de la consulta + helpers de serialización) |
| **Componentes React (vista)** | plantillas Jinja2 + una página por flujo; los tableros se refrescan con `fetch` cada ~10 s (parecido a un hook de recarga en React) |
| **Estado global React/Redux** | una variable de la página (`datosDia` en `pizarra.html`) actualizada por `fetch` — decidimos plantilla server-side porque el dominio es simple: funciona sin build step |
| **`onclick` de JavaScript** | atributo `onclick="marcarLlego(123)"` en la pizarra: técnica idéntica a JS, con la ventaja de que la vista ya llega con los datos del servidor |
| **CSS de Bootstrap en HTML** | clases `card`, `badge`, `progress-bar`: estilos sin build; se ve en la pizarra con las barras de ocupación coloreadas por nivel |
| **script src de HTML** | orden de carga de `main.js` ANTES del `block scripts` en `base.html` (así `esc()` y el banner de sin-conexión están listos en todas las páginas) |

---

## PLAN B si algo falla en vivo (recuperar en 10 s y seguir)

| Falla | Qué hacer |
|---|---|
| pytest tarda o falla por algo raro | Mostrar el archivo de test y decir los números de memoria: "52 pruebas, ~19 s" |
| La pizarra no carga | Abrir directamente la API `/api/v1/reservas/dia` y decir: "esta es la fuente JSON de la pizarra" |
| VS Code se pierde en una pestaña | Ir directo a la tabla del CAPÍTULO E (archivo + línea ya memorizados) |
| Se corta la internet | NADA de este bloque depende de internet: Flask, PostgreSQL y pytest corren 100% local |
