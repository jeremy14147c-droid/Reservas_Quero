-- =====================================================================
-- Migración 004 · Contacto y marca del local (Fase 3.4)
-- Repetible: se puede ejecutar varias veces sin error.
--
-- Agrega a config_local los datos que la dueña edita en
-- Administración > Configuración > "Contacto y marca".
-- Todos son NULL: si faltan, la web muestra "Pendiente: ..." en lugar
-- de inventar datos.
-- =====================================================================

ALTER TABLE config_local
  ADD COLUMN IF NOT EXISTS whatsapp_numero VARCHAR(15)  NULL,
  ADD COLUMN IF NOT EXISTS direccion       VARCHAR(150) NULL,
  ADD COLUMN IF NOT EXISTS maps_url        VARCHAR(300) NULL,
  ADD COLUMN IF NOT EXISTS instagram_url   VARCHAR(200) NULL,
  ADD COLUMN IF NOT EXISTS facebook_url    VARCHAR(200) NULL,
  ADD COLUMN IF NOT EXISTS eslogan         VARCHAR(150) NULL;

-- Los datos reales del local (los entrega la dueña). Si ya hay valores,
-- no se sobrescriben: solo se rellenan cuando están vacíos.
UPDATE config_local
SET whatsapp_numero = COALESCE(whatsapp_numero, '996908138'),
    direccion       = COALESCE(direccion, 'Av. Inca Garcilaso de la Vega 54, Villa María del Triunfo 15816'),
    maps_url        = COALESCE(maps_url, 'https://maps.app.goo.gl/rATMHp75PEziVzCQ8'),
    instagram_url   = COALESCE(instagram_url, 'https://www.instagram.com/quero_gastrobar'),
    facebook_url    = COALESCE(facebook_url, 'https://www.facebook.com/GastrobarPiqueosTragos/'),
    eslogan         = COALESCE(eslogan, 'El sabor del mar y lo criollo, en un solo lugar.')
WHERE config_id = 1;
