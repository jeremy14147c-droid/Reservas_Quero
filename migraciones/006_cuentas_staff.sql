-- Migracion 006: cuentas de staff por defecto (admin y mozo)
-- Idempotente: no duplica si ya existen. Ejecutar una vez en la base (Neon/local).

INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave)
SELECT 'Admin Quero', 'admin@quero.pe',
       'scrypt:32768:8:1$CUsd8EC3cYmDfv6y$a70eb1f40db259aa1ad52724eb3bef500729926529195e592d60b24de42b3578031e8af7a4cd772263bcb1d159e0ed60ccc0cdc3e0ba3d2286234a44bf686192',
       'admin', TRUE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM personal WHERE lower(correo) = 'admin@quero.pe');

INSERT INTO personal (nombre, correo, password_hash, rol, activo, debe_cambiar_clave)
SELECT 'Mozo 1', 'mozo1@quero.pe',
       'scrypt:32768:8:1$fWPmtWXkWqcVAl5v$b35bb7e50ade669b707230cf5f7ea0359c4b0fee1709945550a2d78e7d92334c9c9b008700ed159b689fd7ff5fcd72b37369d08bd006cd6a82f30d847e33561d',
       'empleado', TRUE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM personal WHERE lower(correo) = 'mozo1@quero.pe');
