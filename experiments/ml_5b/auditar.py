"""Auditoria local só de leitura. Não constrói labels nem treina modelos.

Executar: python experiments/ml_5b/auditar.py
Saída: inventario.json (agregados, sem copiar ocorrências individuais).
"""
import csv
import hashlib
import json
import math
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b''):
            h.update(bloco)
    return h.hexdigest()


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s.lower()) if not unicodedata.combining(c)).strip()


def data(s):
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    return None


def numero(s):
    try:
        x = float(s.replace(',', '.'))
        return x if math.isfinite(x) else None
    except (ValueError, AttributeError):
        return None


def csv_stats(p, catalogo):
    n = 0
    faltas, distritos, naturezas, meses, concelhos = [Counter() for _ in range(5)]
    inicio = fim = None
    invalidas = fogo = fogo_data = fogo_geo = duplicados = malformadas = 0
    ids = set()
    anpc = p.name.startswith('anpc')
    with p.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        campos = reader.fieldnames
        for r in reader:
            n += 1
            if None in r or any(v is None for v in r.values()):
                malformadas += 1
            for k in campos:
                if r.get(k) is None or r[k].strip().lower() in ('', 'nan', 'null', 'none'):
                    faltas[k] += 1
            dt = data(r.get('DataOcorrencia') or r.get('data_inicio') or r.get('data_alerta') or '')
            if dt:
                inicio = min(inicio, dt) if inicio else dt
                fim = max(fim, dt) if fim else dt
            else:
                invalidas += 1
            if anpc:
                ident = r.get('Numero')
                if ident:
                    duplicados += ident in ids
                    ids.add(ident)
                natureza = r.get('Natureza') or ''
                naturezas[natureza] += 1
                # Diagnóstico apenas: não é a taxonomia final do target.
                if 'incendio' in norm(natureza):
                    fogo += 1
                    distrito = r.get('Distrito') or 'AUSENTE'
                    distritos[distrito] += 1
                    if dt:
                        fogo_data += 1
                        meses[dt.strftime('%Y-%m')] += 1
                    lat, lon = numero(r.get('Latitude')), numero(r.get('Longitude'))
                    if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180 and (lat, lon) != (0, 0):
                        fogo_geo += 1
                    conc = norm(r.get('Concelho') or '')
                    if conc in catalogo:
                        concelhos[catalogo[conc]] += 1
    return {'ficheiro': p.relative_to(ROOT).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size,
            'registos': n, 'campos': campos, 'ausentes_por_campo': dict(faltas),
            'primeira_data': inicio.isoformat() if inicio else None, 'ultima_data': fim.isoformat() if fim else None,
            'datas_nao_interpretadas': invalidas, 'linhas_malformadas': malformadas,
            'ids_repetidos_no_ficheiro': duplicados if anpc else None,
            'candidatos_incendio_filtro_textual_nao_validado': fogo if anpc else None,
            'candidatos_com_data': fogo_data if anpc else None,
            'candidatos_coordenadas_numericamente_validas': fogo_geo if anpc else None,
            'candidatos_por_distrito': dict(distritos), 'candidatos_por_mes': dict(sorted(meses.items())),
            'candidatos_por_nome_concelho_catalogo_sem_validacao_territorial': dict(concelhos),
            'naturezas': dict(naturezas)}


def main():
    cat = json.loads((ROOT/'backend/data/regioes_principais.json').read_text(encoding='utf-8'))
    ativos = [r for r in cat if r.get('recolha_automatica')]
    catalogo = {norm(r['nome']): r['nome'] for r in ativos}
    fontes = []
    for p in sorted((ROOT/'ml').rglob('*.csv')):
        fontes.append(csv_stats(p, catalogo))
        print(p.name, fontes[-1]['registos'], flush=True)
    artefactos = [{'ficheiro': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                  for pasta in ('ml/models', 'backend/ml_models') for p in sorted((ROOT/pasta).glob('*.joblib'))]
    referencia = []
    for pasta in ('experiments/fwi_fase6/evidencias', 'experiments/fwi_fase7/evidencias', 'experiments/fwi_fase8/evidencias'):
        for p in sorted((ROOT/pasta).glob('*.json')):
            if not any(x in p.name for x in ('_horas', '_observacoes', '_dias', 'manifesto', 'resumo')):
                continue
            d = json.loads(p.read_text(encoding='utf-8-sig'))
            referencia.append({'ficheiro': p.relative_to(ROOT).as_posix(), 'sha256': sha(p),
                'bytes': p.stat().st_size, 'elementos': len(d), 'tipo': type(d).__name__,
                'campos': list(d[0]) if isinstance(d,list) and d and isinstance(d[0],dict) else list(d) if isinstance(d,dict) else []})
    resultado = {'aviso': 'Contagens de eventos candidatos não são labels região/dia; ausência não foi convertida em zero.',
                 'catalogo_ativo': ativos, 'csv': fontes, 'artefactos': artefactos, 'evidencias_fwi': referencia}
    (OUT/'inventario.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
