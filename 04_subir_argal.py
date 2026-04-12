"""
04_subir_argal.py
=================
Sube solo los PDFs de ARGAL que tienen codigo DALI en el nombre
y los vincula en Supabase.
"""

import os
import re
import unicodedata
from supabase import create_client

SUPABASE_URL = "https://ifiwuloipapsezmssyda.supabase.co"
SUPABASE_KEY = "sb_secret_oqmxzawXipoz4d_F376_pg_udU-5TtI"
BUCKET       = "fichas-tecnicas"
CARPETA      = r"T:\maspalomas&tabaibac\Compras-Chef\FT - FS - MCA - DOCUMENTACION\ARGAL"
PROVEEDOR    = "ARGAL"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def limpiar_nombre(nombre):
    nombre = unicodedata.normalize('NFKD', nombre)
    nombre = nombre.encode('ascii', 'ignore').decode('ascii')
    nombre = re.sub(r'[^\w\s\-\_\.\(\)]', '_', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    return nombre

def extraer_codigos(nombre_pdf):
    base = os.path.splitext(nombre_pdf)[0]
    # Solo el PRIMER numero = codigo DALI
    match = re.match(r'^(\d+)', base.strip())
    if match:
        return [match.group(1)]
    return []

print("=" * 50)
print("  Subiendo PDFs ARGAL a Supabase")
print("=" * 50)

pdfs = [f for f in os.listdir(CARPETA) if f.lower().endswith('.pdf')]
print(f"\n  {len(pdfs)} PDFs encontrados en ARGAL\n")

vinculados = 0

for nombre_pdf in pdfs:
    ruta = os.path.join(CARPETA, nombre_pdf)
    codigos = extraer_codigos(nombre_pdf)

    if not codigos:
        print(f"  SIN CODIGO: {nombre_pdf}")
        continue

    # Subir PDF al Storage
    nombre_limpio = limpiar_nombre(nombre_pdf)
    storage_path = f"{PROVEEDOR}/{nombre_limpio}"

    try:
        with open(ruta, 'rb') as f:
            data = f.read()
        supabase.storage.from_(BUCKET).upload(
            path=storage_path,
            file=data,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        url = supabase.storage.from_(BUCKET).get_public_url(storage_path)
    except Exception as e:
        print(f"  ERROR subiendo {nombre_pdf}: {e}")
        continue

    # Vincular cada código DALI encontrado
    for codigo in codigos:
        try:
            resp = supabase.table('articulos').update({
                'url_ficha_tecnica': url,
                'nombre_pdf': nombre_pdf,
                'proveedor': PROVEEDOR
            }).eq('codigo_dali', codigo).execute()

            if resp.data:
                desc = resp.data[0].get('descripcion', '')
                print(f"  OK {codigo} -> {nombre_pdf} | {desc}")
                vinculados += 1
            else:
                print(f"  NO ENCONTRADO DALI {codigo} en [{nombre_pdf}]")
        except Exception as e:
            print(f"  ERROR Supabase DALI {codigo}: {e}")

print(f"\n{'='*50}")
print(f"  Vinculados: {vinculados}")
print("=" * 50)
input("\nPulsa Enter para cerrar...")
