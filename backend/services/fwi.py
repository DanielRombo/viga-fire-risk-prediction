"""FWI diário clássico; compatibilidade temporária dos endpoints existentes.

As duas funções legadas preservam os resultados públicos. O adaptador diário
é opt-in e não importa xclim até ser executado.
"""
from services.fwi_legado import calcular_fwi, calcular_risco_regiao
from services.fwi_diario import EstadoFWI, QualidadeEstado, ResultadoFWI, calcular_fwi_diario

__all__ = ['calcular_fwi', 'calcular_risco_regiao', 'EstadoFWI',
           'QualidadeEstado', 'ResultadoFWI', 'calcular_fwi_diario']
