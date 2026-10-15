"""Inventário estrutural e hashes; leitura incremental, sem modelos ou alterações aos originais."""
import csv
import hashlib
import json
import platform
import sqlite3
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
DATA=ROOT/'data/prdf'

def main():
    resultado={'fase':'inspeção inicial; auditoria suspensa por semântica do target',
               'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'ficheiros':{}}
    for nome in ('fogos.gpkg','fogos-metadata.csv','METEO.csv','FRP.csv','PBA.gpkg'):
        p=DATA/nome;antes=p.stat()
        with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        r={'bytes':antes.st_size,'sha256':digest,'mtime_ns':antes.st_mtime_ns}
        if p.suffix=='.gpkg':
            with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as c:
                c.execute('PRAGMA query_only=ON')
                r['layers']=[]
                for table,kind,identifier,srs in c.execute('select table_name,data_type,identifier,srs_id from gpkg_contents'):
                    quoted='"'+table.replace('"','""')+'"'
                    schema=[dict(zip(('cid','name','type','notnull','default','pk'),row)) for row in c.execute('PRAGMA table_info('+quoted+')')]
                    r['layers'].append(dict(table=table,type=kind,identifier=identifier,srs_id=srs,schema=schema))
                r['geometry_columns']=c.execute('select * from gpkg_geometry_columns').fetchall()
        else:
            with p.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.reader(f,delimiter=';' if nome=='fogos-metadata.csv' else ',')
                r['header']=next(reader)
                if nome=='fogos-metadata.csv':r['metadata']=list(reader)
                else:r['amostra_inicial']=next(reader)
        depois=p.stat()
        assert (antes.st_size,antes.st_mtime_ns)==(depois.st_size,depois.st_mtime_ns)
        resultado['ficheiros'][nome]=r
    (OUT/'inventario_inicial.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Cinco hashes registados; originais com tamanho/mtime inalterados.')

if __name__=='__main__':main()
