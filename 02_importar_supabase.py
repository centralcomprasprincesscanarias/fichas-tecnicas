"""
02_importar_supabase.py
=======================
Princess Hotels - Central Compras Canarias - Frankus71
"""

import os
import re
import math
import json
import unicodedata
import pandas as pd
from supabase import create_client, Client

SUPABASE_URL = "https://ifiwuloipapsezmssyda.supabase.co"
SUPABASE_KEY = "sb_secret_oqmxzawXipoz4d_F376_pg_udU-5TtI"
EXCEL_PATH   = r"D:\portal-fichas\LISTADO CODIGOS DALI - SAP.xlsx"
PDF_ROOT_DIR = r"T:\maspalomas&tabaibac\Compras-Chef\FT - FS - MCA - DOCUMENTACION"
BUCKET       = "fichas-tecnicas"
BATCH        = 500

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def limpiar_nombre(nombre):
    nombre = unicodedata.normalize('NFKD', nombre)
    nombre = nombre.encode('ascii', 'ignore').decode('ascii')
    nombre = re.sub(r'[^\w\s\-\_\.\(\)]', '_', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    return nombre


def safe_val(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, str) and v.strip().lower() in ('nan', 'none', 'nat', ''):
        return None
    return v


def leer_excel(path):
    df = pd.read_excel(path, header=5)
    df.columns = df.iloc[0].tolist()
    df = df.iloc[1:].reset_index(drop=True)
    df = df[['CODIGO DALI', 'CODIGO SAP - TEST', 'DESCRIPCION DALI']].copy()
    df.columns = ['codigo_dali', 'codigo_sap', 'descripcion']
    df['codigo_dali'] = df['codigo_dali'].astype(str).str.strip()
    df['codigo_sap']  = df['codigo_sap'].apply(
        lambda x: str(int(float(x))) if pd.notna(x) and str(x) not in ('nan', '') else None
    )
    df['descripcion'] = df['descripcion'].astype(str).str.strip()
    df = df[df['codigo_dali'].str.match(r'^\d+$')].copy()
    df = df.drop_duplicates('codigo_dali').reset_index(drop=True)
    df.insert(0, 'codigo_generico', [f"GEN-{str(i+1).zfill(5)}" for i in range(len(df))])
    df['proveedor']         = None
    df['url_ficha_tecnica'] = None
    df['nombre_pdf']        = None
    return df


def extraer_codigos_dali(nombre_pdf):
    base = os.path.splitext(nombre_pdf)[0]
    inicio = re.match(r'^[\d\s_]+', base)
    if not inicio:
        return []
    return re.findall(r'\d+', inicio.group(0))


def subir_pdf(ruta_local, proveedor, nombre_pdf):
    prov_limpio   = limpiar_nombre(proveedor)
    nombre_limpio = limpiar_nombre(nombre_pdf)
    storage_path  = f"{prov_limpio}/{nombre_limpio}"
    try:
        with open(ruta_local, 'rb') as f:
            data = f.read()
        supabase.storage.from_(BUCKET).upload(
            path=storage_path,
            file=data,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        return supabase.storage.from_(BUCKET).get_public_url(storage_path)
    except Exception as e:
        print(f"  ERROR: {nombre_pdf}: {e}")
        return None


def preparar_lote(registros):
    limpios = []
    for r in registros:
        limpio = {k: safe_val(v) for k, v in r.items()}
        limpios.append(limpio)
    json.dumps(limpios, default=str)
    return limpios


def main():
    print("=" * 60)
    print("  Importador Princess - Supabase")
    print("=" * 60)

    print("\nLeyendo Excel...")
    df = leer_excel(EXCEL_PATH)
    print(f"   {len(df)} articulos")

    dali_a_idx = {row['codigo_dali']: i for i, row in df.iterrows()}
    pdfs_vinculados = 0

    print(f"\nEscaneando PDFs...")
    for proveedor in sorted(os.listdir(PDF_ROOT_DIR)):
        carpeta = os.path.join(PDF_ROOT_DIR, proveedor)
        if not os.path.isdir(carpeta):
            continue
        pdfs = [f for f in os.listdir(carpeta) if f.lower().endswith('.pdf')]
        if not pdfs:
            continue
        print(f"\n  {proveedor} ({len(pdfs)} PDFs)")
        for nombre_pdf in pdfs:
            codigos = extraer_codigos_dali(nombre_pdf)
            coincidencias = [c for c in codigos if c in dali_a_idx]
            if not coincidencias:
                continue
            ruta = os.path.join(carpeta, nombre_pdf)
            url = subir_pdf(ruta, proveedor, nombre_pdf)
            if not url:
                continue
            for codigo in coincidencias:
                idx = dali_a_idx[codigo]
                df.at[idx, 'proveedor']         = proveedor
                df.at[idx, 'url_ficha_tecnica'] = url
                df.at[idx, 'nombre_pdf']        = nombre_pdf
                pdfs_vinculados += 1
                print(f"    OK {codigo} -> {nombre_pdf}")

    print(f"\n   PDFs vinculados: {pdfs_vinculados}")

    print("\nSubiendo a Supabase...")
    registros = df.to_dict('records')
    total = len(registros)
    ok = 0

    for i in range(0, total, BATCH):
        lote_raw = registros[i:i+BATCH]
        try:
            lote = preparar_lote(lote_raw)
            supabase.table('articulos').upsert(
                lote, on_conflict='codigo_generico'
            ).execute()
            ok += len(lote)
            print(f"   Lote {i//BATCH+1}: {len(lote)} OK ({ok}/{total})")
        except Exception as e:
            print(f"   ERROR lote {i//BATCH+1}: {e}")

    print(f"\nCompletado: {ok} articulos en Supabase.")
    print("=" * 60)
    input("Pulsa Enter para cerrar...")


if __name__ == "__main__":
    main()
