import { Router } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { db } from '../db/database.js';

const router = Router();
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const uploadsBase = path.join(__dirname, '..', '..', 'uploads');

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const proveedor = (req.body.proveedor || 'GENERAL').toString().trim().replaceAll(' ', '_');
    const dir = path.join(uploadsBase, proveedor);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    cb(null, dir);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname) || '.pdf';
    const base = (req.body.dali || req.body.sap || req.body.referencia || 'documento')
      .toString()
      .trim()
      .replace(/[^a-zA-Z0-9_-]/g, '_');
    cb(null, `${Date.now()}_${base}${ext}`);
  }
});

const upload = multer({ storage });

router.get('/', (req, res) => {
  const q = (req.query.q || '').toString().trim();
  const dali = (req.query.dali || '').toString().trim();
  const sap = (req.query.sap || '').toString().trim();
  const proveedor = (req.query.proveedor || '').toString().trim();
  const referencia = (req.query.referencia || '').toString().trim();

  let sql = `
    SELECT *
    FROM referencias
    WHERE 1=1
  `;
  const params = [];

  if (q) {
    sql += `
      AND (
        dali LIKE ?
        OR sap LIKE ?
        OR proveedor LIKE ?
        OR referencia LIKE ?
      )
    `;
    const like = `%${q}%`;
    params.push(like, like, like, like);
  }

  if (dali) {
    sql += ` AND dali LIKE ?`;
    params.push(`%${dali}%`);
  }

  if (sap) {
    sql += ` AND sap LIKE ?`;
    params.push(`%${sap}%`);
  }

  if (proveedor) {
    sql += ` AND proveedor LIKE ?`;
    params.push(`%${proveedor}%`);
  }

  if (referencia) {
    sql += ` AND referencia LIKE ?`;
    params.push(`%${referencia}%`);
  }

  sql += ` ORDER BY id DESC`;

  db.all(sql, params, (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

router.get('/sin-ficha', (req, res) => {
  db.all(
    `
    SELECT *
    FROM referencias
    WHERE tiene_ficha = 0 OR ficha_pdf IS NULL OR ficha_pdf = ''
    ORDER BY id DESC
    `,
    [],
    (err, rows) => {
      if (err) return res.status(500).json({ error: err.message });
      res.json(rows);
    }
  );
});

router.post('/', (req, res) => {
  const {
    dali,
    sap,
    proveedor,
    referencia
  } = req.body;

  if (!referencia || !referencia.trim()) {
    return res.status(400).json({ error: 'Referencia obligatoria' });
  }

  db.run(
    `
    INSERT INTO referencias (dali, sap, proveedor, referencia, tiene_ficha)
    VALUES (?, ?, ?, ?, 0)
    `,
    [
      dali || null,
      sap || null,
      proveedor || null,
      referencia.trim()
    ],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      res.status(201).json({ id: this.lastID, message: 'Referencia creada' });
    }
  );
});

router.post('/:id/ficha', upload.single('ficha'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No se recibió ningún archivo' });
  }

  const filePath = req.file.path.replaceAll('\\', '/');

  db.run(
    `
    UPDATE referencias
    SET ficha_pdf = ?, tiene_ficha = 1
    WHERE id = ?
    `,
    [filePath, req.params.id],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      res.json({ ok: true, ficha_pdf: filePath });
    }
  );
});

export default router;
