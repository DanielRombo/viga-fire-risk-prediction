"""Contrato experimental de labels; exige evidência externa, não a presume."""
from datetime import timedelta, timezone

def target_24h(t, eventos_confirmados, cobertura):
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError('O instante T deve incluir fuso horário.')
    t = t.astimezone(timezone.utc)
    fim = t + timedelta(hours=24)
    # Lista previamente adjudicada para o município; evento confirmado basta para y=1.
    for instante in eventos_confirmados:
        if instante.tzinfo is None or instante.utcoffset() is None:
            raise ValueError('Ocorrência sem fuso certificado.')
        if t < instante <= fim:
            return 1
    requisitos = ('fonte', 'snapshot_sha256', 'documento_cobertura',
                  'taxonomia_validada', 'territorio_validado', 'timestamp_validado',
                  'extracao_integral', 'consolidado', 'sem_ambiguidades')
    if not cobertura or not all(cobertura.get(k) for k in requisitos):
        return None
    inicio = cobertura.get('inicio')
    final = cobertura.get('fim')
    if inicio is None or final is None or inicio.tzinfo is None or final.tzinfo is None:
        return None
    return 0 if inicio <= t and final >= fim else None
