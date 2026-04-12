"""
05_subir_alcruz.py
==================
Sube PDFs de ALCRUZ usando el codigo del proveedor para encontrar el DALI correcto.
Los PDFs de ALCRUZ tienen el codigo del proveedor en el nombre (ej: 114.pdf = DALI 2007)
"""

import os
import re
from supabase import create_client

SUPABASE_URL = "https://ifiwuloipapsezmssyda.supabase.co"
SUPABASE_KEY = "sb_secret_oqmxzawXipoz4d_F376_pg_udU-5TtI"
BUCKET       = "fichas-tecnicas"
CARPETA      = r"T:\maspalomas&tabaibac\Compras-Chef\FT - FS - MCA - DOCUMENTACION\ALCRUZ CANARIAS"
PROVEEDOR    = "ALCRUZ CANARIAS"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Mapeo COD.PROV -> DALI extraido del Excel ALCRUZ_2026.xlsx
COD_PROV_A_DALI = {
    '9904': '3',
    '452': '1434',
    '547': '2004',
    '114': '2007',
    '169': '2008',
    '167': '2009',
    '319': '2010',
    '545': '2013',
    '174': '2014',
    '173': '2016',
    '266': '2094',
    '580': '2095',
    '190': '2097',
    '193': '2098',
    '283': '2099',
    '268': '2100',
    '1288': '2101',
    '191': '2103',
    '231': '2105',
    '278': '2106',
    '282': '2107',
    '217': '2109',
    '243': '2110',
    '255': '2113',
    '196': '2114',
    '257': '2116',
    '1255': '2123',
    '120': '2125',
    '1254': '2126',
    '63': '2181',
    '823': '2184',
    '817': '2272',
    '956': '3235',
    '12': '3254',
    '634': '3255',
    '222': '3318',
    '1421': '3601',
    '689': '3612',
    '284': '4518',
    '133': '4571',
    '130': '4573',
    '844': '4574',
    '9906': '6227',
    '783': '6283',
    '314': '6863',
    '184': '8686',
    '615': '8777',
    '1534': '12125',
    '928': '13761',
    '727': '14001',
    '280': '14298',
    '934': '20265',
    '568': '20895',
    '724': '20903',
    '1070': '21131',
    '571': '21139',
    '275': '21956',
    '51': '24223',
    '910': '24414',
    '645': '24658',
    '750': '24709',
    '466': '25012',
    '476': '25094',
    '320': '25126',
    '363': '26019',
    '1059': '26594',
    '232': '26769',
    '987': '27757',
    '146': '28285',
    '148': '28286',
    '154': '28287',
    '155': '28288',
    '156': '28289',
    '213': '28290',
    '214': '28291',
    '219': '28292',
    '338': '28592',
    '70': '29494',
}

print("=" * 55)
print("  Subiendo PDFs ALCRUZ a Supabase")
print("=" * 55)

pdfs = [f for f in os.listdir(CARPETA) if f.lower().endswith('.pdf')]
print(f"\n  {len(pdfs)} PDFs encontrados en ALCRUZ\n")

vinculados = 0
no_encontrados = []

for nombre_pdf in pdfs:
    # Extraer primer numero del nombre del PDF
    base = os.path.splitext(nombre_pdf)[0].strip()
    match = re.match(r'^(\d+)', base)
    if not match:
        print(f"  SIN NUMERO: {nombre_pdf}")
        continue

    cod_prov = match.group(1)

    # Buscar DALI en el mapeo
    dali = COD_PROV_A_DALI.get(cod_prov)
    if not dali:
        no_encontrados.append(f"{nombre_pdf} (COD.PROV {cod_prov})")
        continue

    # Subir PDF al Storage
    ruta = os.path.join(CARPETA, nombre_pdf)
    storage_path = f"{PROVEEDOR}/{nombre_pdf}"

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

    # Vincular en Supabase
    try:
        resp = supabase.table('articulos').update({
            'url_ficha_tecnica': url,
            'nombre_pdf': nombre_pdf,
            'proveedor': PROVEEDOR
        }).eq('codigo_dali', dali).execute()

        if resp.data:
            desc = resp.data[0].get('descripcion', '')
            print(f"  OK DALI {dali} | COD.PROV {cod_prov} | {desc}")
            vinculados += 1
        else:
            print(f"  NO ENCONTRADO DALI {dali} en Supabase")
    except Exception as e:
        print(f"  ERROR Supabase DALI {dali}: {e}")

print(f"\n{'='*55}")
print(f"  Vinculados: {vinculados}")
if no_encontrados:
    print(f"\n  Sin mapeo ({len(no_encontrados)}):")
    for f in no_encontrados:
        print(f"    - {f}")
print("=" * 55)
input("\nPulsa Enter para cerrar...")


