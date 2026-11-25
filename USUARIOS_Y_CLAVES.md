# Usuarios y Contraseñas del Sistema — Quero Gastrobar

Este documento consolida las credenciales de acceso para el personal del restaurante (administrador y empleados), tanto para desarrollo local, pruebas y sustentación del proyecto ante el jurado.

---

## 1. Cuentas de Acceso Preconfiguradas

| Rol | Nombre | Correo de acceso | Contraseña | ¿Debe cambiar clave? | Propósito |
|---|---|---|---|:---:|---|
| **admin** (Dueña / Gerencia) | Admin Quero | `admin@quero.pe` | `Admin123456*` | No | Configuración total del local, personal, carta, pizarra y pedidos. |
| **empleado** (Mozo / Recepción / Cocina) | Mozo 1 | `mozo1@quero.pe` | `Mozo123456*` | No | Pizarra del día, toma de pedidos en salón, tablero de cocina y caja. |

> [!NOTE]
> Cumpliendo con la directiva de seguridad **H-9 (OWASP)** implementada en el sistema, todas las contraseñas tienen un mínimo obligatorio de **10 caracteres** y son procesadas con hash seguro mediante `werkzeug.security` (Scrypt / PBKDF2).

---

## 2. Dónde y Cómo Ingresar al Panel de Staff

El acceso al personal se realiza desde la ruta:
* URL directa: `http://localhost:5000/auth/login` (o en la web desplegada en `/auth/login`).
* Enlace en la web pública: Ubicado de forma discreta en el pie de página de la web (*Acceso Personal / Staff*).
* Si ya hay una sesión activa, el sistema muestra una franja superior discreta: *"Sesión de staff activa · Volver al panel"*.

---

## 3. Comandos de Gestión de Usuarios en Consola

Para crear un nuevo administrador o gestionar cuentas desde la terminal:

```bash
# Crear un nuevo administrador interactivamente
python manage.py crear-admin
```
*(Solicitará nombre, correo y contraseña con confirmación; la cuenta se creará activa y lista para usar sin obligar a cambio de clave).*

---

## 4. Usuarios de Pruebas Automatizadas (Pytest)

Durante la ejecución de las pruebas unitarias e integrales (`pytest`), el sistema genera temporalmente en su fixture:
* `admin_test@quero.pe` (clave: `clave123`)
* `empleado_test@quero.pe` (clave: `clave123`)
*(Estos usuarios son de uso interno para pruebas y se limpian automáticamente tras cada ejecución).*
