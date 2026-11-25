# Herramientas y Stack Tecnológico — Quero APP

Este documento detalla todas las tecnologías, librerías y herramientas utilizadas en el sistema web de **Quero Gastrobar**, explicando de forma sencilla y directa **para qué sirve cada una en el proyecto**, ideal para consulta del equipo y sustentación académica.

---

## 1. Arquitectura General del Proyecto

El sistema está construido siguiendo el patrón arquitectónico **MVC (Modelo - Vista - Controlador)** desacoplado con una **Capa de Servicios de Negocio** y una **Capa DAO (Data Access Object)**:
* **Vista:** Plantillas Jinja2 + HTML5 semántico + Bootstrap 5 CDN + JavaScript Vanilla (sin frameworks pesados).
* **Controlador:** Blueprints modulares de Flask (`publico`, `auth`, `reservas`, `pedidos`, `carta`, `admin`, `api`).
* **Modelo de Negocio (Servicios):** Módulos en `app/servicios/` con lógica pura de negocio, reglas de transición y cálculos, sin acoplamiento a Flask ni a SQL.
* **Modelo de Acceso a Datos (DAO):** Clases en `app/dao/` (`ReservaDAO`, `PedidoDAO`, `ClienteDAO`, etc.) que encapsulan el 100% de las consultas SQL nativas.
* **Base de Datos:** PostgreSQL 16 relacional con funciones nativas (`fn_duracion_estadia`, `fn_carga_dia`, `fn_hay_cupo`).

---

## 2. Tecnologías del Backend

| Herramienta / Librería | Versión | ¿Para qué sirve en este proyecto? |
|---|---|---|
| **Python** | 3.11+ / 3.12 | Lenguaje de programación principal del servidor. Permite un código conciso, legible y fácil de explicar. |
| **Flask** | 3.x | Microframework web que gestiona el enrutamiento HTTP, manejo de peticiones, respuestas y la fábrica de la aplicación (`create_app()`). |
| **psycopg 3 (`psycopg[binary]`)** | 3.x | Driver oficial de conexión a PostgreSQL. Ejecuta sentencias SQL nativas con parámetros seguros (`%s`), previniendo al 100% ataques de inyección SQL. |
| **Flask-Login** | 0.6+ | Gestión de sesiones de autenticación para el personal del staff (recepción, mozo, admin). Controla el estado de sesión y validación de usuarios autenticados. |
| **Flask-WTF** | 1.2+ | Generación y validación de tokens **CSRF** en todos los formularios HTML para evitar ataques de falsificación de peticiones en sitios cruzados. |
| **werkzeug.security** | Integrado | Funciones criptográficas para generar y verificar hashes seguros de contraseñas (`generate_password_hash`, `check_password_hash`). |
| **python-dotenv** | 1.0+ | Carga variables de entorno sensibles (cadena de conexión `DATABASE_URL`, `SECRET_KEY`, etc.) desde el archivo local `.env` sin exponer credenciales en el código fuente. |
| **tzdata / zoneinfo** | Estándar | Manejo preciso de la zona horaria oficial del restaurante (`America/Lima`), garantizando que la apertura, cierre y reservas se calculen con la hora exacta de Perú, incluso en servidores en la nube ubicados en EE.UU. |
| **qrcode + Pillow** | 7.x / 10.x | Generación dinámica de códigos QR en formato base64 para los tickets de reserva y pedidos, permitiendo al staff escanearlos con la cámara y abrir el detalle en el panel. |
| **gunicorn** | 22.x | Servidor WSGI HTTP de nivel de producción utilizado para servir la aplicación Flask en el entorno de despliegue en Linux (Render). |

---

## 3. Tecnologías del Frontend

| Herramienta | Tipo | ¿Para qué sirve en este proyecto? |
|---|---|---|
| **HTML5 Semántico** | Marcado | Estructura de las páginas web públicas (cliente) y paneles administrativos (staff), optimizado para accesibilidad y dispositivos móviles. |
| **Bootstrap 5 (CDN)** | Framework CSS | Provee el diseño adaptable (*mobile-first*), sistema de rejillas (*grid*), tarjetas (*cards*), ventanas modales, insignias (*badges*) y paneles laterales (*offcanvas*). |
| **Bootstrap Icons (CDN)** | Iconografía | Iconos visuales ligeros en formato fuente SVG para botones, estados y acciones operativas. |
| **CSS3 Custom Properties** | Estilos propios | Variables CSS en `cliente.css` y `style.css` que centralizan la paleta de colores de la marca (rojo, naranja, amarillo, crema, tinta) y tipografías. |
| **Google Fonts** | Tipografía CDN | Fuentes de alto rendimiento web cargadas con `font-display: swap`: **Playfair Display** (títulos elegantes de carta) y **Source Sans 3** (texto legible en celular). |
| **JavaScript Vanilla** | Lenguaje cliente | Interactividad ligera (selección de franjas horarias, recarga periódica de la pizarra cada 10s con `fetch()`, carrito en `sessionStorage` y banner sin conexión) sin requerir compiladores pesados ni dependencias de npm. |

---

## 4. Base de Datos y Persistencia

| Componente | Tipo | ¿Para qué sirve en este proyecto? |
|---|---|---|
| **PostgreSQL 16** | RDBMS Relacional | Motor de base de datos relacional robusto. Es la fuente de verdad de toda la información (reservas, clientes, carta, pedidos, configuración). |
| **Neon Serverless Postgres** | Base en la Nube | Instancia de PostgreSQL 16 alojada en la nube con escalado automático, utilizada como entorno de pruebas y producción para el despliegue en línea. |
| **Funciones SQL Nativas** | Procedimientos en BD | `fn_duracion_estadia(personas)` (calcula estadía de 30/60/90 min según grupo), `fn_carga_dia(fecha)` (ocupación por franja) y `fn_hay_cupo(fecha, hora, personas)`. El cálculo vive en la BD para evitar transferir miles de filas a Python. |

---

## 5. Pruebas y Calidad de Código (TDD)

| Herramienta | ¿Para qué sirve en este proyecto? |
|---|---|
| **pytest** | Framework de pruebas automatizadas. Ejecuta en segundos la suite completa de más de 100 pruebas. |
| **Tests Unitarios sin BD** (`tests/unidad/`) | Prueban reglas de negocio puras (franja reservable, tope de reservas, validaciones de marca, transiciones) inyectando DAOs falsos en memoria, sin necesitar conexión a PostgreSQL. |
| **Tests de Integración** (`tests/test_*.py`) | Prueban flujos completos extremo a extremo contra PostgreSQL: inyecciones de datos, endpoints JSON de la API, restricciones únicas e integridad referencial. |

---

## 6. Despliegue e Infraestructura Cloud

| Servicio | Proveedor | ¿Para qué sirve? |
|---|---|---|
| **Web Service** | Render | Aloja y ejecuta la aplicación Flask con Python y Gunicorn, conectada al repositorio Git para despliegue continuo automático. |
| **Base de Datos Cloud** | Neon Tech | Aloja la base de datos PostgreSQL 16 con conexión segura SSL / TLS. |
| **Control de Versiones** | Git + GitHub | Gestión del código fuente, ramas por fase (`fase-3-x`) y registro de auditoría de cambios. |
