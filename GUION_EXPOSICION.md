> ✅ **ESTADO DEL PROYECTO (Fase 3.R completada):**
> Este proyecto cuenta con arquitectura en capas estricta: Controlador (blueprints) → Servicio (reglas de negocio) → DAO (acceso a datos en `app/dao/`) → Base de datos (`schema.sql` y `app/db.py`).
> El 100 % de las sentencias SQL vive en la capa DAO. Los servicios aceptan inyección de dependencias (`dao=...`), lo que permite pruebas unitarias aisladas sin base de datos en `tests/unidad/`, complementadas por pruebas de integración contra PostgreSQL (75 pruebas en total).

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
├── schema.sql                ← EL MODELO DE DATOS: 10 tablas + 3 funciones SQL + 2 vistas
├── app/
│   ├── __init__.py           ← punto de entrada (app factory)
│   ├── config.py             ← configuración (clase Config)
│   ├── db.py                 ← conexión y helpers de bajo nivel (psycopg 3 con parámetros %s)
│   ├── dao/                  ← CAPA DAO: una clase por entidad con TODO el SQL (ReservaDAO, PedidoDAO...)
│   ├── publico/ auth/ reservas/ pedidos/ carta/ admin/ api/   ← CONTROLADOR (blueprints)
│   ├── servicios/            ← MODELO DE NEGOCIO: reglas puras (sin Flask, sin SQL directo)
│   └── templates/ static/    ← VISTA (pantallas HTML con Jinja2 y Bootstrap 5)
└── tests/                    ← SUITE DE PRUEBAS: 13 archivos, 75 pruebas (unitarias en tests/unidad/ e integración)
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
`app/dao/reserva_dao.py` (o la carpeta `app/dao/` con `ConfigDAO`, `ClienteDAO`, `PersonalDAO`, `CartaDAO`, `ReservaDAO`, `PedidoDAO`), y `app/db.py` (helpers con `%s`).

```python
class ReservaDAO:
    def hay_cupo(self, fecha, hora, personas, personas_por_mesa, duracion_min, excluir_reserva_id=None):
        ...
    def insertar(self, datos):
        ...
    def actualizar_estado(self, reserva_id, nuevo_estado, motivo=None):
        ...
```

### 🎤 QUÉ DECIR
> "Nuestra capa **DAO** (Data Access Object) vive en `app/dao/`: tenemos **una clase DAO por entidad** (`ReservaDAO`, `PedidoDAO`, `ClienteDAO`, `CartaDAO`, `PersonalDAO`, `ConfigDAO`).
> Es la ÚNICA capa del proyecto que escribe SQL. Ninguna ruta y ningún servicio contiene una sola sentencia `SELECT`, `INSERT` o `UPDATE`.
>
> Dos detalles técnicos clave:
> **1)** Todo el acceso de bajo nivel pasa por `app/db.py`, donde todas las consultas usan parámetros con `%s`: el valor **NUNCA se concatena al texto SQL**, se pasa por separado. Si un cliente escribiera `' OR 1=1 --` en su teléfono, psycopg lo escapa de forma segura evitando inyección SQL.
> **2)** **Inyección de dependencias:** Los servicios reciben su DAO como parámetro opcional (`dao=None`, con instancia por defecto). Esto nos permite inyectar un **DAO falso** en pruebas unitarias (`tests/unidad/`) y probar las reglas de negocio en milisegundos sin levantar una base de datos."

### 💬 SI PREGUNTAN
- **"¿Por qué una clase por entidad y no un ORM como SQLAlchemy?"** → "Decisión deliberada: la fuente de verdad de nuestro modelo es `schema.sql`. Con psycopg 3 y DAOs explícitos mantenemos control total del SQL, usamos funciones nativas de PostgreSQL (`fn_carga_dia`, `fn_hay_cupo`) sin capas opacas, y cumplimos el patrón DAO clásico que cualquier docente de Java/C# reconoce de inmediato."
- **"¿Cómo se comunican el Servicio y el DAO?"** → "El servicio contiene las reglas ('¿este estado puede pasar a aquel?'). Cuando la regla se aprueba, el servicio le pide al DAO que persista el cambio (`dao.actualizar_estado(...)`). El DAO solo sabe de SQL, el servicio solo sabe de negocio."

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

🖥️ MOSTRAR dos cosas simples y contundentes en la terminal:

1. Sin acoplamiento a la web:
```powershell
Select-String -Path app\servicios\*.py -Pattern "from flask" | Measure-Object | % Count
```
→ **0**

2. Sin acoplamiento a base de datos (todo el SQL está en los DAOs):
```powershell
Select-String -Path app\servicios\*.py -Pattern "SELECT |INSERT |UPDATE |DELETE " | Measure-Object | % Count
```
→ **0**

🎤 DECIR:
> "Busquen 'flask' en la carpeta de servicios: **cero** resultados. Y busquen sentencias SQL en los servicios: **cero** resultados.
> Los servicios no dependen ni de Flask ni de la base de datos directa: dependen de abstracciones (la capa DAO inyectable, `dao=None`).
> Esa es la Inversión de Dependencias: la capa de REGLAS es de alto nivel y no depende de los detalles de acceso a datos.
> Consecuencia práctica: gracias a esto tenemos pruebas unitarias puras en `tests/unidad/` que corren en milisegundos sin levantar PostgreSQL, usando DAOs falsos en memoria."

---

## CAPÍTULO D · TDD (test-driven-development) — 1.5 min

### 🖥️ QUÉ ABRIR
1. Terminal → correr en vivo:
   ```powershell
   .venv\Scripts\python.exe -X utf8 -m pytest -q
   ```
   (resultado en vivo: **75 passed in ~20s**)
2. Con el resultado en pantalla, mostrar `tests/unidad/test_horas_pasadas_unitarias.py` (pruebas unitarias sin BD) y luego `tests/test_fase3_2.py`, **función `test_fn_duracion_estadia_por_tamano`**
   (señalar la línea del `esperado = {1: 30, 3: 30, ...}`)

### 🎤 QUÉ DECIR
> "Cada funcionalidad tiene su archivo de pruebas: trabajamos con disciplina **TDD**. Esta suite cuenta con 75 pruebas que corren en unos 20 segundos.
> Tenemos dos tipos de pruebas claramente separadas:
> **1)** **Pruebas unitarias puras** en `tests/unidad/`: prueban la lógica de negocio usando DAOs simulados (fakes en memoria), sin tocar la base de datos ni requerir red.
> **2)** **Pruebas de integración**: prueban reglas de negocio y restricciones complejas contra una base PostgreSQL de verdad.
>
> Ejemplo concreto (señalando la pantalla): esta prueba llama a la **función SQL**
> `fn_duracion_estadia` con los valores LÍMITES 1, 3, 4, 7, 8, 12 y 13 personas, y comprueba que
> devuelva 30, 60 o 90 minutos. No es al azar: 3 es el borde de los grupos chicos, 4 arranca el
> grupo mediano y 8 el grande. Si mañana alguien cambia la regla y rompe el límite del 7, el test
> explota en rojo ANTES de que el dueño del local lo note.
>
> También hay tests de la MÁQUINA DE ESTADOS, de seguridad (bloqueo por fuerza bruta H-2, rotación de sesiones H-1) y del cobro."

### 💬 SI PREGUNTAN
- **"¿Qué es TDD de verdad?"** → "El ciclo ROJO–VERDE–REFACTOR: se escribe primero la prueba
  (rojo), luego el código mínimo que la haga pasar (verde), y después se mejora el código que
  siga en verde. Lo aplicamos en las fases de reglas (2, 3 y seguridad S1/S2): incluimos casos de rechazo, no
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
| S | `app/servicios/` (1 responsabilidad por módulo, sin SQL) | — |
| O | `app/servicios/reservas.py` | `TRANSICIONES_VALIDAS` (L22) |
| L | `app/servicios/reservas.py` + `app/api/routes.py` | `CupoNoDisponible(ValueError)` (L28) + `_manejar_error_negocio` (L101) |
| I | `app/api/routes.py` | rutas JSON separadas de las HTML |
| D | `app/servicios/` + `app/dao/` | Inyección de DAO (`dao=None`) + 0 SQL en servicios + 0 Flask |
| DAO | `app/dao/` | Una clase por entidad (`ReservaDAO`, `PedidoDAO`, etc.) + `db.py` |
| MVC | árbol de carpetas | `schema.sql` y `app/dao/` (M) · `routes.py` (C) · `templates/` (V) |
| TDD | `tests/` (13 archivos, 75 pruebas) | `tests/unidad/` (sin BD) + integración en vivo con `pytest -q` |

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
| pytest tarda o falla por algo raro | Mostrar el archivo de test y decir los números de memoria: "75 pruebas, ~20 s" |
| La pizarra no carga | Abrir directamente la API `/api/v1/reservas/dia` y decir: "esta es la fuente JSON de la pizarra" |
| VS Code se pierde en una pestaña | Ir directo a la tabla del CAPÍTULO E (archivo + línea ya memorizados) |
| Se corta la internet | NADA de este bloque depende de internet: Flask, PostgreSQL y pytest corren 100% local |
