import logging

logger = logging.getLogger(__name__)


def calcular_fwi(temperatura: float, humidade: float, vento: float, precipitacao: float) -> dict:
    """
    Calculo simplificado do Fire Weather Index (FWI)
    baseado no sistema canadiano de risco de incendio.
    """

    # Componente de humidade do combustivel fino
    # Humidade baixa = combustivel mais seco = maior risco
    ffmc = max(0, (temperatura * 0.5) +
               ((100 - humidade) * 0.4) - (precipitacao * 2))

    # Componente de vento
    # Vento forte propaga o fogo mais rapidamente
    isi = ffmc * (vento / 10)

    # Indice final FWI
    fwi = (ffmc * 0.6) + (isi * 0.4)

    # Classificacao do risco
    if fwi <= 5:
        nivel = "Baixo"
    elif fwi <= 10:
        nivel = "Medio"
    elif fwi <= 20:
        nivel = "Alto"
    elif fwi <= 30:
        nivel = "Muito Alto"
    elif fwi <= 45:
        nivel = "Extremo"
    else:
        nivel = "Muito Extremo"

    return {
        "fwi": round(fwi, 2),
        "nivel_risco": nivel,
        "componentes": {
            "ffmc": round(ffmc, 2),
            "isi": round(isi, 2)
        }
    }


def calcular_risco_regiao(dados_meteorologicos: dict) -> dict:
    temperatura = dados_meteorologicos.get("temperatura", 20)
    humidade = dados_meteorologicos.get("humidade", 50)
    vento = dados_meteorologicos.get("velocidade_vento", 0)
    precipitacao = dados_meteorologicos.get("precipitacao", 0)

    resultado = calcular_fwi(temperatura, humidade, vento, precipitacao)
    logger.info(
        f"FWI calculado: {resultado['fwi']} - Risco: {resultado['nivel_risco']}")
    return resultado
