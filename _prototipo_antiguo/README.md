# Prototipo antiguo (Node.js + Express + PostgreSQL)

Esta carpeta **NO forma parte del sistema entregado**. Se conserva solo como
referencia histórica del primer intento de la aplicación, hecho con JavaScript
del lado del servidor (Express) antes de pasar a Python + Flask.

- **Sistema vigente:** todo el proyecto real está en `app/` (Flask), `schema.sql`,
  `seed.sql`, `migraciones/` y `tests/`. Se ejecuta con:
  `.venv\Scripts\python.exe -m flask --app manage run`
- **No ejecutar estos archivos:** el prototipo está incompleto (le faltan las
  carpetas `services/` y `public/`) y su base de datos era otra (`bd_reservas.sql`).
- **Logo antiguo:** `logo.png` aquí es el logo "Quero Sabor & Gestión". El logo
  actual del local debe guardarse en `app/static/img/logo.png`.

Se movió aquí para no confundir a quien revise el repositorio (por ejemplo, en
la sustentación) con dos backends distintos.
