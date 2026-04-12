"""
03_vincular_pdf_por_nombre.py
=====================================
Princess Hotels - Central Compras Canarias - Frankus71

REQUISITOS:
    py -m pip install pdfplumber supabase pandas openpyxl

USO:
    py D:\portal-fichas\03_vincular_pdf_por_nombre.py
"""

import os
import re
import math
import json
import unicodedata
import pdfplumber
import pandas as pd
from supabase import create_client, Client

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
SUPABASE_URL  = "https://ifiwuloipapsezmssyda.supabase.co"
SUPABASE_KEY  = "sb_secret_oqmxzawXipoz4d_F376_pg_udU-5TtI"
EXCEL_PATH    = r"D:\portal-fichas\LISTADO CODIGOS DALI - SAP.xlsx"
PDF_ROOT_DIR  = r"T:\maspalomas&tabaibac\Compras-Chef\FT - FS - MCA - DOCUMENTACION"
BUCKET        = "fichas-tecnicas"
UMBRAL        = 0.55
SOLO_SIN_FICHA = True
# ──────────────────────────────────────────────────────────────────────────────

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


STOPWORDS = {
    'DE', 'LA', 'EL', 'LOS', 'LAS', 'EN', 'CON', 'SIN', 'AL', 'UN', 'UNA',
    'Y', 'E', 'O', 'A', 'PAN', 'CONG', 'CONGELADO', 'CONGELADA',
    'ULTRACONGELADO', 'REV', 'ED', 'KG', 'GR', 'GRS', 'ML', 'CL', 'LT',
    'UD', 'UDS', 'BOT', 'PAQ', 'CJ', 'BRK', 'MARCA', 'PRODUCTO', 'FICHA',
    'TECNICA', 'NATURAL', 'VARIOS', 'MINI', 'MAXI', 'SUPER', 'EXTRA',
}

def limpiar_clave(texto):
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = texto.encode('ascii', 'ignore').decode('ascii').upper()
    texto = re.sub(r'\b\d+[\.,]?\d*\s*(KG|GRS|GR|G|ML|CL|LT|L|UDS|UD|UN|X\d+)\b', ' ', texto)
    texto = re.sub(r'\b\d+\b', ' ', texto)
    texto = re.sub(r'[^A-Z\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def palabras_clave(texto):
    return set(limpiar_clave(texto).split()) - STOPWORDS

def similitud(a, b):
    pa = palabras_clave(a)
    pb = palabras_clave(b)
    if not pa or not pb:
        return 0
    comunes = pa & pb
    comunes = pa & pb
    if len(comunes) < 2:
        return 0


def tiene_codigo_dali(nombre_pdf, codigos_dali):
    base = os.path.splitext(nombre_pdf)[0]
    inicio = re.match(r'^[\d\s_]+', base)
    if not inicio:
        return False
    codigos = re.findall(r'\d+', inicio.group(0))
    return any(c in codigos_dali for c in codigos)


def limpiar_nombre_candidato(texto):
    """Limpia un candidato a nombre de artículo quitando códigos y sufijos."""
    # Quitar código numérico del inicio
    texto = re.sub(r'^\d[\d\s]*', '', texto).strip()
    # Quitar sufijos tipo "ed 2", "ed. 2", "- "
    texto = re.sub(r'\s*-\s*$', '', texto)
    texto = re.sub(r'\s+ed\.?\s*\d+\s*$', '', texto, flags=re.IGNORECASE)
    return texto.strip()


def extraer_nombre_pdf(ruta_pdf):
    """Extrae el nombre del artículo del texto del PDF con múltiples estrategias."""
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            if not pdf.pages:
                return None
            texto = pdf.pages[0].extract_text() or ''

        lineas = [l.strip() for l in texto.split('\n') if l.strip()]

        # ── Estrategia 1: línea con patrón CÓDIGO NUMÉRICO + NOMBRE ──────────
        # Ej: "063001 BARRA RUSTIC 240 G -"  o  "2201 SALMON FILETE EXTRA"
        for linea in lineas[:25]:
            match = re.match(r'^\d{3,}\s+([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜA-Z0-9\s\-\.\/\(\)]+)', linea)
            if match:
                candidato = match.group(1).strip()
                candidato = limpiar_nombre_candidato(candidato)
                if len(candidato) >= 5 and not re.match(r'^(WWW|TEL|FAX|CIF|HTTP|EMAIL)', candidato):
                    return candidato

        # ── Estrategia 2: buscar etiqueta NOMBRE seguida del valor ──────────
        for i, linea in enumerate(lineas[:20]):
            if re.search(r'\bNOMBRE\b|\bDENOMINACION\b|\bPRODUCTO\b|\bDESCRIPCION\b', linea.upper()):
                # Buscar en la misma línea después de ":"
                match_inline = re.search(r'[:]\s*([A-ZÁÉÍÓÚÑÜ][^\n]{4,})', linea)
                if match_inline:
                    candidato = limpiar_nombre_candidato(match_inline.group(1))
                    if len(candidato) >= 5:
                        return candidato
                # Buscar en las siguientes líneas
                for j in range(i+1, min(i+4, len(lineas))):
                    sig = lineas[j]
                    # Saltar si es una etiqueta o dato técnico
                    if re.match(r'^(REF|FECHA|WWW|TEL|FAX|CIF|HTTP|EMAIL|MARCA|CODIGO|VERSION)', sig.upper()):
                        continue
                    # Quitar código numérico inicial si lo hay
                    candidato = re.sub(r'^\d[\d\s]*', '', sig).strip()
                    candidato = limpiar_nombre_candidato(candidato)
                    if len(candidato) >= 5:
                        return candidato

        # ── Estrategia 3: buscar "Denominación legal:" o "Nombre comercial:" ─
        for linea in lineas[:30]:
            match = re.search(r'(?:denominaci[oó]n\s+(?:legal|comercial|de\s+venta)|nombre\s+(?:comercial|del\s+producto))[:\s]+([^\n]+)',
                              linea, re.IGNORECASE)
            if match:
                candidato = match.group(1).strip()
                candidato = limpiar_nombre_candidato(candidato)
                if len(candidato) >= 5:
                    return candidato

        # ── Estrategia 4: líneas con texto en mayúsculas sin ser cabecera ────
        for linea in lineas[1:15]:
            if (len(linea) >= 6
                    and linea.isupper()
                    and not re.match(r'^(WWW|TEL|FAX|CIF|HTTP|EMAIL|REF|FECHA|DATOS|FICHA|INGREDIENTES)', linea)
                    and not re.match(r'^\d{5,}$', linea)):
                candidato = limpiar_nombre_candidato(linea)
                if len(candidato) >= 5:
                    return candidato

    except Exception as e:
        pass
    return None


def limpiar_nombre(nombre):
    nombre = unicodedata.normalize('NFKD', nombre)
    nombre = nombre.encode('ascii', 'ignore').decode('ascii')
    nombre = re.sub(r'[^\w\s\-\_\.\(\)]', '_', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    return nombre


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
        print(f"    Error subiendo: {e}")
        return None


def leer_excel(path):
    df = pd.read_excel(path, header=5)
    df.columns = df.iloc[0].tolist()
    df = df.iloc[1:].reset_index(drop=True)
    df = df[['CODIGO DALI', 'CODIGO SAP - TEST', 'DESCRIPCION DALI']].copy()
    df.columns = ['codigo_dali', 'codigo_sap', 'descripcion']
    df['codigo_dali'] = df['codigo_dali'].astype(str).str.strip()
    df['descripcion'] = df['descripcion'].astype(str).str.strip()
    df = df[df['codigo_dali'].str.match(r'^\d+$')].copy()
    df = df.drop_duplicates('codigo_dali').reset_index(drop=True)
    return df


def main():
    print("=" * 60)
    print("  Vinculador PDF por nombre - Princess Supabase")
    print("=" * 60)

    print("\nLeyendo Excel...")
    df = leer_excel(EXCEL_PATH)
    codigos_set = set(df['codigo_dali'].tolist())
    descripciones = df[['codigo_dali', 'descripcion']].values.tolist()
    print(f"   {len(df)} articulos cargados")

    articulos_con_ficha = set()
    if SOLO_SIN_FICHA:
        try:
            resp = supabase.table('articulos').select('codigo_dali').not_.is_('url_ficha_tecnica', 'null').execute()
            articulos_con_ficha = {r['codigo_dali'] for r in (resp.data or [])}
            print(f"   {len(articulos_con_ficha)} ya tienen ficha (se saltaran)")
        except:
            pass

    vinculados = 0
    no_vinculados = []

    print(f"\nProcesando PDFs sin codigo en nombre...")

    for proveedor in sorted(os.listdir(PDF_ROOT_DIR)):
        carpeta = os.path.join(PDF_ROOT_DIR, proveedor)
        if not os.path.isdir(carpeta):
            continue

        pdfs_sin_codigo = [
            f for f in os.listdir(carpeta)
            if f.lower().endswith('.pdf')
            and not tiene_codigo_dali(f, codigos_set)
        ]

        if not pdfs_sin_codigo:
            continue

        print(f"\n  {proveedor} ({len(pdfs_sin_codigo)} PDFs sin codigo)")

        for nombre_pdf in pdfs_sin_codigo:
            ruta = os.path.join(carpeta, nombre_pdf)

            nombre_en_pdf = extraer_nombre_pdf(ruta)
            if not nombre_en_pdf:
                print(f"    NO LEIDO: {nombre_pdf}")
                no_vinculados.append((proveedor, nombre_pdf, 'no_leido'))
                continue

            mejor_sim    = 0
            mejor_codigo = None
            mejor_desc   = None

            for codigo_dali, descripcion in descripciones:
                if codigo_dali in articulos_con_ficha:
                    continue
                sim = similitud(nombre_en_pdf, descripcion)
                if sim > mejor_sim:
                    mejor_sim    = sim
                    mejor_codigo = codigo_dali
                    mejor_desc   = descripcion

            if mejor_sim >= UMBRAL and mejor_codigo:
                url = subir_pdf(ruta, proveedor, nombre_pdf)
                if url:
                    try:
                        supabase.table('articulos').update({
                            'url_ficha_tecnica': url,
                            'nombre_pdf':  nombre_pdf,
                            'proveedor':   proveedor
                        }).eq('codigo_dali', mejor_codigo).execute()
                        articulos_con_ficha.add(mejor_codigo)
                        vinculados += 1
                        print(f"    OK ({mejor_sim:.0%}) '{nombre_en_pdf}' -> DALI {mejor_codigo} '{mejor_desc}'")
                    except Exception as e:
                        print(f"    ERROR Supabase: {e}")
            else:
                sim_str = f"{mejor_sim:.0%}" if mejor_codigo else "0%"
                print(f"    ({sim_str}) '{nombre_en_pdf}' [{nombre_pdf}]")
                no_vinculados.append((proveedor, nombre_pdf, nombre_en_pdf))

    print(f"\n{'='*60}")
    print(f"  Vinculados:     {vinculados}")
    print(f"  Sin vincular:   {len(no_vinculados)}")
    print("=" * 60)
    input("\nPulsa Enter para cerrar...")


if __name__ == "__main__":
    main()
