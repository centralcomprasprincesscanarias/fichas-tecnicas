import sqlite3 from 'sqlite3';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dataDir = path.join(__dirname, '..', '..', 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbPath = path.join(dataDir, 'database.sqlite');
export const db = new sqlite3.Database(dbPath);

export function initDatabase() {
  db.serialize(() => {
    db.run(`
      CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    db.run(`
      CREATE TABLE IF NOT EXISTS referencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dali TEXT,
        sap TEXT,
        proveedor TEXT,
        referencia TEXT NOT NULL,
        descripcion TEXT,
        proveedor_id INTEGER,
        fabricante TEXT,
        categoria TEXT,
        subcategoria TEXT,
        codigo_fabrica TEXT,
        formato TEXT,
        unidad TEXT,
        peso TEXT,
        alergenos TEXT,
        conservacion TEXT,
        tiene_ficha INTEGER DEFAULT 0,
        ficha_pdf TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    db.all(`PRAGMA table_info(referencias)`, [], (err, rows) => {
      if (err) return;
      const columnas = rows.map(r => r.name);
      if (!columnas.includes('proveedor')) {
        db.run(`ALTER TABLE referencias ADD COLUMN proveedor TEXT`);
      }
    });
  });
}
