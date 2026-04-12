-- ============================================================
--  FICHAS TÉCNICAS - Princess Hotels & Resorts
--  Central Compras Canarias - Frankus71
--  PASO 1: Ejecutar en Supabase SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS articulos (
    codigo_generico     TEXT PRIMARY KEY,   -- Clave permanente del artículo (NUNCA cambia)
    descripcion         TEXT NOT NULL,      -- Nombre del artículo
    codigo_dali         TEXT,               -- Puede cambiar
    codigo_sap          TEXT,               -- Puede cambiar
    proveedor           TEXT,               -- Puede cambiar
    url_ficha_tecnica   TEXT,               -- Puede cambiar (nueva edición del PDF)
    nombre_pdf          TEXT,               -- Nombre del archivo PDF
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Índices de búsqueda
CREATE INDEX IF NOT EXISTS idx_codigo_dali     ON articulos (codigo_dali);
CREATE INDEX IF NOT EXISTS idx_codigo_sap      ON articulos (codigo_sap);
CREATE INDEX IF NOT EXISTS idx_proveedor       ON articulos (proveedor);
CREATE INDEX IF NOT EXISTS idx_descripcion_fts ON articulos
    USING GIN (to_tsvector('spanish', COALESCE(descripcion, '') || ' ' || COALESCE(proveedor, '')));

-- Trigger updated_at automático
CREATE OR REPLACE FUNCTION fn_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_updated_at ON articulos;
CREATE TRIGGER trg_updated_at
    BEFORE UPDATE ON articulos
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();

-- ============================================================
-- STORAGE BUCKET para los PDFs
-- ============================================================
INSERT INTO storage.buckets (id, name, public)
VALUES ('fichas-tecnicas', 'fichas-tecnicas', true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "lectura_publica_storage" ON storage.objects
    FOR SELECT USING (bucket_id = 'fichas-tecnicas');

-- ============================================================
-- RLS
-- ============================================================
ALTER TABLE articulos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "select_publico" ON articulos FOR SELECT USING (true);
CREATE POLICY "write_service"  ON articulos FOR ALL   USING (auth.role() = 'service_role');

-- ============================================================
-- BÚSQUEDA UNIFICADA
-- SELECT * FROM buscar('GEN-001');
-- SELECT * FROM buscar('salmon');
-- SELECT * FROM buscar('ahumados');
-- ============================================================
CREATE OR REPLACE FUNCTION buscar(termino TEXT)
RETURNS SETOF articulos AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM articulos
    WHERE
        codigo_generico   ILIKE '%' || termino || '%'
        OR descripcion    ILIKE '%' || termino || '%'
        OR codigo_dali    ILIKE '%' || termino || '%'
        OR codigo_sap     ILIKE '%' || termino || '%'
        OR proveedor      ILIKE '%' || termino || '%'
    ORDER BY
        CASE
            WHEN codigo_generico = termino THEN 0
            WHEN codigo_dali     = termino THEN 1
            WHEN codigo_sap      = termino THEN 2
            ELSE 3
        END,
        descripcion
    LIMIT 200;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- HISTORIAL: registra cambios de proveedor y ficha técnica
-- El artículo es permanente, pero proveedor/ficha pueden cambiar
-- ============================================================
CREATE TABLE IF NOT EXISTS articulos_historial (
    id              BIGSERIAL PRIMARY KEY,
    codigo_generico TEXT NOT NULL REFERENCES articulos(codigo_generico),
    campo           TEXT NOT NULL,
    valor_anterior  TEXT,
    valor_nuevo     TEXT,
    cambiado_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION fn_registrar_cambios()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.proveedor IS DISTINCT FROM NEW.proveedor THEN
        INSERT INTO articulos_historial (codigo_generico, campo, valor_anterior, valor_nuevo)
        VALUES (NEW.codigo_generico, 'proveedor', OLD.proveedor, NEW.proveedor);
    END IF;
    IF OLD.url_ficha_tecnica IS DISTINCT FROM NEW.url_ficha_tecnica THEN
        INSERT INTO articulos_historial (codigo_generico, campo, valor_anterior, valor_nuevo)
        VALUES (NEW.codigo_generico, 'url_ficha_tecnica', OLD.url_ficha_tecnica, NEW.url_ficha_tecnica);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_historial ON articulos;
CREATE TRIGGER trg_historial
    AFTER UPDATE ON articulos
    FOR EACH ROW EXECUTE FUNCTION fn_registrar_cambios();
