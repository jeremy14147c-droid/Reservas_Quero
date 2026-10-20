# Pasos previos – Quero APP (hacer ANTES de la Fase 0)

## 1. Cuentas
- **GitHub** (repositorio privado, ya lo vas a crear).
- Para el proyecto final: cuenta gratuita de **Expo** y un proyecto de **Firebase** (no los necesitas ahora).

## 2. Instalaciones (Windows)
| Qué | Verificación |
|---|---|
| **Git** | `git --version` |
| **Python 3.11 o superior** (marca "Add Python to PATH") | `python --version` |
| **PostgreSQL 16** (el instalador trae pgAdmin) | `psql --version` (si no la reconoce, usa la ruta completa, ej. `"C:\Program Files\PostgreSQL\16\bin\psql.exe"`) |
| **Antigravity** | Abre una carpeta sin errores |
| **Node.js LTS** (solo para el proyecto final) | `node --version` |

Anota la contraseña del usuario `postgres` que elijas al instalar PostgreSQL.

## 3. Flask no tiene un "generador" como Spring Initializr
Se crea a mano: un entorno virtual y las librerías. (En la Fase 0 el agente crea toda la estructura de carpetas.)
```
git clone <URL-de-tu-repo>
cd <carpeta>
python -m venv .venv
.venv\Scripts\activate
pip install flask "psycopg[binary]" flask-login flask-wtf python-dotenv "qrcode[pil]" pytest
pip freeze > requirements.txt
```
- Si PowerShell bloquea `activate`, usa CMD (Símbolo del sistema).
- `gunicorn` solo se necesita en el hosting (Linux); no lo ejecutes en Windows.
- Verifica: `python -c "import flask, psycopg; print('ok')"`

## 4. PostgreSQL: usuario propio y base de datos
No uses el usuario `postgres` para la aplicación. Crea uno propio que sea dueño de la base de datos.

**Paso A (en pgAdmin, Query Tool conectado como `postgres`; ejecuta cada sentencia por separado):**
```sql
CREATE ROLE quero_app LOGIN PASSWORD 'ELIGE_UNA_CLAVE';
CREATE DATABASE quero OWNER quero_app;
```

**Paso B (en una terminal, en la carpeta del repo, para que las tablas queden a nombre de `quero_app`):**
```
psql -h localhost -U quero_app -d quero -f schema.sql
psql -h localhost -U quero_app -d quero -f seed.sql
```
Te pedirá la contraseña de `quero_app`.

**Paso C (comprobar):**
```
psql -h localhost -U quero_app -d quero -c "SELECT nombre_local, aforo_personas FROM config_local"
psql -h localhost -U quero_app -d quero -c "SELECT count(*) FROM fn_carga_dia(CURRENT_DATE)"
```
La primera debe devolver una fila y la segunda un número de franjas (con los datos de ejemplo, 20).
Probé estos pasos en PostgreSQL 16.

## 5. Archivo `.env` (en la raíz; NO se sube a Git)
```
DATABASE_URL=postgresql://quero_app:TU_CLAVE@localhost:5432/quero
SECRET_KEY=pon-aqui-una-cadena-larga-y-aleatoria
BASE_URL=http://localhost:5000
```
Si la clave tiene caracteres especiales (`@`, `:`, `/`), hay que codificarlos en la URL. Más fácil: usa una clave solo con letras y números.

## 6. Datos que debes pedirle a la dueña (antes de la Fase 2)
Aforo, número de mesas, personas por mesa, duración de una estadía, horario, tolerancia, días de anticipación para reservar,
la carta con precios, y el número y titular de su Yape. El `seed.sql` trae valores de ejemplo.

## 7. Para el proyecto final (no ahora)
```
npx create-expo-app@latest quero-staff
cd quero-staff
npx expo start
```
- Escaneas el QR con la app **Expo Go** para ver la interfaz.
- **Las notificaciones push NO funcionan en Expo Go desde el SDK 53:** necesitas una *development build* (EAS Build, con cuenta de Expo) y un **celular real** (no emulador). En Android 13 o superior, además, la app debe pedir permiso de notificaciones.
- Verifica las versiones cuando llegue el momento: Expo cambia seguido.

## 8. Base de datos gratuita en la nube (si la necesitas) y migración
Tu código solo usa `DATABASE_URL`: cambiar de proveedor es cambiar esa línea y mover los datos.

| Opción | Gratis | Lo que debes saber |
|---|---|---|
| **Local** (tu laptop) | Sí | Cero riesgo para la demo. Solo tú accedes |
| **Neon** (recomendada si necesitas nube) | 100 horas de cómputo al mes y 0,5 GB por proyecto | PostgreSQL estándar, sin lock-in. Se suspende tras 5 min sin actividad y reanuda al primer acceso |
| **Supabase** | 500 MB | El proyecto gratuito se pausa tras una semana sin uso |
| **Render** | Hasta 30 días | La base gratuita expira |

**Cuidado con Neon y los tableros:** como los tableros consultan cada ~10 s mientras haya alguien conectado, la base no se suspende durante el turno. Si usas 0,25 unidades de cómputo (mi suposición) durante 10 horas al día, serían unas 75 horas de cómputo al mes, cerca del límite de 100. Mi estimación. Al superar el límite, la base se suspende hasta el mes siguiente.

**Migrar (probado en local, conserva las funciones SQL):**
```
pg_dump -h localhost -U quero_app -Fc -d quero -f quero.dump
pg_restore --no-owner -d "postgresql://USUARIO:CLAVE@HOST/BASE?sslmode=require" quero.dump
```
Luego cambia `DATABASE_URL` en el `.env` del servidor (con `?sslmode=require` al final si el proveedor lo pide).

## 9. Lista de comprobación antes de la Fase 0
- [ ] `git`, `python`, `psql` responden
- [ ] El repo está clonado y tiene `AGENTS.md`, `schema.sql`, `seed.sql`
- [ ] El entorno virtual está activo y `import flask, psycopg` funciona
- [ ] La BD `quero` existe y `config_local` devuelve una fila
- [ ] El `.env` existe y NO aparece en `git status`
