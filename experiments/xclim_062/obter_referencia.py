"""Obtém apenas a referência científica fixada; nunca é usado pelo VIGA."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

COMMIT = "4364ce8f491dfbe18fb22542104644c1c498ddab"  # cffdrs v1.9.2
BASE = f"https://raw.githubusercontent.com/cffdrs/cffdrs_r/{COMMIT}/"
DESTINO = Path(__file__).parent / "referencia"
FICHEIROS = ["data/test_fwi.csv", "tests/testthat/data/fwi_01.csv", "tests/testthat/test_fwi.r",
             "R/fwi.r", "R/fine_fuel_moisture_code.r", "R/duff_moisture_code.r",
             "R/drought_code.r", "R/initial_spread_index.r", "R/buildup_index.r",
             "R/fire_weather_index.r", "DESCRIPTION"]
DESTINO.mkdir(exist_ok=True)
manifesto = {"commit": COMMIT, "ficheiros": {}}
for nome in FICHEIROS:
    dados = urlopen(BASE + nome, timeout=30).read()
    (DESTINO / Path(nome).name).write_bytes(dados)
    manifesto["ficheiros"][nome] = {"url": BASE + nome, "sha256": hashlib.sha256(dados).hexdigest()}
(DESTINO / "origem.json").write_text(json.dumps(manifesto, indent=2), encoding="utf-8")
print("Referência cffdrs obtida e identificada por commit e SHA-256.")

# Variante clássica com constante FFMC 147,2, também mantida sem alterações.
antigo = "9481404cad25387292c1d8692bdb126bbe514d9c"  # v1.8.17
destino_antigo = Path(__file__).parent / 'referencia_1_8_17'
destino_antigo.mkdir(exist_ok=True)
manifesto_antigo = {'commit':antigo,'ficheiros':{}}
for nome in ['R/ffmcCalc.R','R/dmcCalc.R','R/dcCalc.R','R/ISIcalc.r','R/buiCalc.R','R/fwiCalc.R','R/fwi.r','DESCRIPTION']:
    url = f'https://raw.githubusercontent.com/cffdrs/cffdrs_r/{antigo}/{nome}'
    dados = urlopen(url,timeout=30).read()
    (destino_antigo/Path(nome).name).write_bytes(dados)
    manifesto_antigo['ficheiros'][nome] = {'url':url,'sha256':hashlib.sha256(dados).hexdigest()}
(destino_antigo/'origem.json').write_text(json.dumps(manifesto_antigo,indent=2),encoding='utf-8')
print('Variante cffdrs 1.8.17 obtida sem alterar o código de referência.')
