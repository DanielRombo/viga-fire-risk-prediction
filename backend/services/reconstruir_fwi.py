"""Comando interno explícito; não regista jobs nem disponibiliza endpoints."""
import argparse
import asyncio
import json
import sys
from datetime import date, timedelta


class Argumentos(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('add_help', False)
        super().__init__(*args, **kwargs)
        self._positionals.title = 'Argumentos'
        self._optionals.title = 'Opções'
        self.add_argument('--ajuda', action='help', help='Mostrar esta ajuda e terminar.')

    def error(self, message):
        self.exit(2, 'Argumentos inválidos. Consulte --ajuda.\n')

    def format_usage(self):
        return super().format_usage().replace('usage:', 'Utilização:', 1)

    def format_help(self):
        return super().format_help().replace('usage:', 'Utilização:', 1)


def main(argv=None):
    parser = Argumentos(description='Inicialização e reconstrução histórica FWI, sem publicação operacional.')
    parser.add_argument('operacao', choices=['iniciar', 'continuar', 'estado', 'corrigir'],
                        help='Operação interna a executar.')
    parser.add_argument('--regiao', type=int, required=True, help='Identificador existente da região.')
    parser.add_argument('--data-operacional', type=date.fromisoformat, help='Primeiro dia após a janela histórica (AAAA-MM-DD).')
    parser.add_argument('--data-inicial', type=date.fromisoformat, help='Início explícito da janela (AAAA-MM-DD).')
    parser.add_argument('--janela-dias', type=int, default=365, help='Janela inicial configurável; predefinição: 365 dias.')
    parser.add_argument('--ffmc', type=float, help='FFMC inicial convencional explícito.')
    parser.add_argument('--dmc', type=float, help='DMC inicial convencional explícito.')
    parser.add_argument('--dc', type=float, help='DC inicial convencional explícito.')
    parser.add_argument('--origem-estado', help='Justificação e proveniência da semente convencional.')
    parser.add_argument('--estado-persistido', type=int, help='Alternativa: identificador de um FWI estabelecido persistido.')
    parser.add_argument('--limite-dias', type=int, default=3, help='Dias por execução, entre 1 e 366; predefinição: 3.')
    parser.add_argument('--data', type=date.fromisoformat, help='Dia cuja meteorologia deve ser consultada novamente.')
    parser.add_argument('--motivo', help='Motivo da correção histórica.')
    args = parser.parse_args(argv)
    try:
        from config.database import engine, SessionLocal
        from models.regiao import Regiao
        from models.fwi_diario import FWIDiario
        from services.fwi_diario import EstadoFWI, QualidadeEstado
        from services.persistencia_fwi import restaurar_estado
        from services.processamento_fwi import TERRITORIOS
        from services.regioes_iniciais import normalizar
        from services.reconstrucao_fwi import (preparar_estrutura_historica, iniciar_reconstrucao,
            reconstruir, corrigir_dia_historico, consultar_reconstrucao)
        preparar_estrutura_historica(engine)
        if args.operacao == 'iniciar':
            if args.data_operacional is None:
                raise ValueError('É obrigatório indicar a data operacional.')
            inicio = args.data_inicial or args.data_operacional-timedelta(days=args.janela_dias)
            with SessionLocal() as db:
                regiao = db.get(Regiao, args.regiao)
                if regiao is None:
                    raise ValueError('A região indicada não está preparada.')
                territorio = TERRITORIOS.get(normalizar(regiao.distrito))
                if args.estado_persistido is not None:
                    if any(v is not None for v in (args.ffmc, args.dmc, args.dc, args.origem_estado)):
                        raise ValueError('Escolha uma semente convencional ou um estado persistido, não ambos.')
                    guardado = db.get(FWIDiario, args.estado_persistido)
                    if guardado is None:
                        raise ValueError('O estado persistido indicado não existe.')
                    semente = restaurar_estado(guardado)
                else:
                    semente = EstadoFWI(args.regiao, inicio-timedelta(days=1), args.ffmc,
                        args.dmc, args.dc, QualidadeEstado.CONVENCIONAL, args.origem_estado)
                latitude, longitude = regiao.latitude, regiao.longitude
            resultado = iniciar_reconstrucao(SessionLocal, id_regiao=args.regiao,
                latitude=latitude, longitude=longitude, territorio=territorio,
                data_operacional=args.data_operacional, data_inicial=args.data_inicial,
                janela_dias=args.janela_dias, estado_inicial=semente)
        elif args.operacao == 'continuar':
            resultado = asyncio.run(reconstruir(SessionLocal, args.regiao, limite_dias=args.limite_dias))
        elif args.operacao == 'corrigir':
            resultado = asyncio.run(corrigir_dia_historico(SessionLocal, args.regiao, args.data, motivo=args.motivo))
        else:
            resultado = consultar_reconstrucao(SessionLocal, args.regiao)
        print(json.dumps(resultado, ensure_ascii=False))
        return 1 if resultado['estado'] in ('falha_reconstrucao', 'sem_estado', 'ocupada') else 0
    except ValueError as erro:
        print(f'Erro: {erro}', file=sys.stderr)
        return 1
    except Exception:
        import logging
        logging.exception('Falha na operação histórica FWI.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
