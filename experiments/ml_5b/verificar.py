"""Verifica integridade e gera distribuições de candidatos, nunca labels."""
import csv
import json
from collections import Counter
from datetime import date

from auditar import ROOT, OUT, sha


def main():
    inventario = json.loads((OUT/'inventario.json').read_text(encoding='utf-8'))
    ficheiros = inventario['csv'] + inventario['artefactos'] + inventario['evidencias_fwi']
    for f in ficheiros:
        p = ROOT/f['ficheiro']
        assert p.stat().st_size == f['bytes'], f['ficheiro']
        assert sha(p) == f['sha256'], f['ficheiro']
    anpc = [r for r in inventario['csv'] if '/anpc-' in r['ficheiro']]
    assert len(inventario['catalogo_ativo']) == 28
    assert len(inventario['csv']) == 42
    assert sum(r['registos'] for r in anpc) == 910783
    for r in anpc:
        assert sum(r['candidatos_por_mes'].values()) == r['candidatos_com_data']
        assert sum(r['candidatos_por_distrito'].values()) == r['candidatos_incendio_filtro_textual_nao_validado']
    with (OUT/'distribuicao_candidatos.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['fonte', 'dimensao', 'grupo', 'eventos_candidatos_nao_labels', 'cobertura_certificada'])
        for r in anpc:
            for chave, dimensao in [('candidatos_por_mes', 'mes'), ('candidatos_por_distrito', 'distrito')]:
                for grupo, n in sorted(r[chave].items()):
                    w.writerow([r['ficheiro'], dimensao, grupo, n, 'nao'])
        concelhos = Counter()
        for r in anpc:
            concelhos.update(r['candidatos_por_nome_concelho_catalogo_sem_validacao_territorial'])
        for regiao in inventario['catalogo_ativo']:
            w.writerow(['ANPC 2016-2020', 'nome_concelho_sem_validacao_territorial', regiao['nome'], concelhos[regiao['nome']], 'nao'])
    horas = dias = 0
    for f in inventario['evidencias_fwi']:
        if 'fwi_fase8/' not in f['ficheiro']:
            continue
        d = json.loads((ROOT/f['ficheiro']).read_text(encoding='utf-8'))
        if f['ficheiro'].endswith('_horas.json'):
            horas += len(d)
            assert len({h['instante_utc'] for h in d}) == len(d)
        if f['ficheiro'].endswith('_observacoes.json'):
            dias += len(d)
            datas = [date.fromisoformat(o['data_referencia']) for o in d]
            assert len(datas) == 1826 and len(set(datas)) == len(datas)
            assert min(datas) == date(2021,10,1) and max(datas) == date(2026,9,30)
    assert horas == 306768 and dias == 12782
    resultado = {'ficheiros_originais_verificados': len(ficheiros), 'sha256_todos_coincidem': True,
        'csv': 42, 'artefactos_preservados': len(inventario['artefactos']), 'pontos_ativos': 28,
        'horas_fase8': horas, 'dias_fase8': dias, 'sobreposicao_anpc_fwi_validado_dias': 0,
        'dataset_elegivel_criado': False, 'labels_positivos': None, 'labels_negativos': None,
        'modelo_treinado': False, 'producao_contactada': False}
    (OUT/'integridade.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(resultado, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
