# Quero Gastrobar – Sistema Web de Reservas y Pedidos

Sistema web responsive y PWA para la gestión operativa de **reservas** y **pedidos** del restaurante y gastrobar **Quero** en Lima, Perú.  
Desarrollado como proyecto universitario (UTP, Curso Integrador) para un cliente real.

---

## 1. Tecnologías
- **Backend:** Python 3.12+ con **Flask** (patrón Application Factory + Blueprints).
- **Base de Datos:** **PostgreSQL 16** con **psycopg 3** y SQL explícito parametrizado (sin ORM).
- **Frontend:** **Jinja2** + **Bootstrap 5** (CDN) + JavaScript vanilla (sin frameworks ni build steps).
- **Seguridad y Sesión:** Flask-Login, Flask-WTF (CSRF), `werkzeug.security` (hash de contraseñas), `python-dotenv`.
- **Pruebas:** `pytest`.

---

## 2. Requisitos Previos
- **Git** instalado (`git --version`).
- **Python 3.11 o superior** instalado con la opción *"Add Python to PATH"* marcada.
- **PostgreSQL 16** instalado en Windows (por defecto el servicio puede estar en el puerto `5432` o `5433`).

---

## 3. Instalación y Puesta en Marcha (Windows)

### Paso 1: Clonar el repositorio y entrar a la carpeta
```bash
git clone <URL-del-repositorio>
cd Reservas_Quero
```

### Paso 2: Crear y activar el entorno virtual
En PowerShell o CMD:
```bash
python -m venv .venv
.venv\Scripts\activate
```

### Paso 3: Instalar dependencias
```bash
pip install -r requirements.txt
```

### Paso 4: Base de Datos en PostgreSQL
Abre pgAdmin o tu terminal conectada al usuario principal `postgres` y crea el usuario y la base de datos:
```sql
CREATE ROLE quero_app LOGIN PASSWORD 'TU_CLAVE_AQUI';
CREATE DATABASE quero OWNER quero_app;
```

### Paso 5: Configurar variables de entorno (`.env`)
Copia el archivo `.env.example` y renómbralo a `.env`:
```bash
copy .env.example .env
```
Edita `.env` con tus credenciales reales:
```ini
DATABASE_URL=postgresql://quero_app:TU_CLAVE_AQUI@localhost:5433/quero
SECRET_KEY=clave-secreta-larga-y-segura
BASE_URL=http://localhost:5000
```
*(Nota: Ajusta el puerto a `5433` o `5432` según donde esté instalado tu PostgreSQL 16).*

### Paso 6: Inicializar la base de datos y cargar datos
Con el entorno virtual activo, ejecuta:
```bash
# 1. Crear las tablas, vistas y funciones del esquema
python manage.py init-db

# 2. Cargar los datos de ejemplo iniciales (configuración y platos base)
python manage.py cargar-ejemplo

# 3. Crear el primer usuario Administrador interactivo
python manage.py crear-admin
```

### Paso 7: Ejecutar las pruebas automatizadas
Para comprobar que la base de datos, las funciones de ocupación y los endpoints responden correctamente:
```bash
pytest
```

### Paso 8: Iniciar el servidor web de desarrollo
```bash
flask --app manage run --debug
```
Abre en tu navegador: [http://localhost:5000](http://localhost:5000)

---

## 4. Roles y Cuentas del Sistema
| Rol | Acceso | Modo de acceso |
|---|---|---|
| **Público (Cliente)** | Inicio, reservar mesa, realizar pedido de recojo y seguimiento con token. | Sin cuenta ni contraseña (invitado). |
| **Empleado** (Staff) | Pizarra de reservas del día, cola de pedidos, cocina (Kanban) y disponibilidad de platos. | Login con correo y contraseña. |
| **Admin** (Dueña) | Todo lo del empleado + Configuración del local y gestión del personal. | Login con correo y contraseña. |

---

## 5. Comportamiento Sin Conexión
El sistema **no opera offline**. Si se corta la conexión a internet o falla la comunicación con el servidor, la aplicación:
1. Muestra un banner superior permanente: *"Sin conexión: no se puede operar"*.
2. Bloquea de inmediato todos los botones y acciones operativas (`data-requiere-conexion`) para proteger la integridad de los datos.
3. Al volver la red, quita el banner y reanuda las consultas en tiempo real.
