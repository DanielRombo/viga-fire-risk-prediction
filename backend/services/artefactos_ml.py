"""Validação e instalação do conjunto aprovado de artefactos de produção."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import warnings

import joblib
import numpy as np
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

PASTA_MODELOS = Path(__file__).resolve().parents[1] / 'ml_models'
NOMES = ('modelo_kaggle.joblib', 'scaler_kaggle.joblib', 'modelo_anpc.joblib',
         'scaler_anpc.joblib', 'encoder_distrito_anpc.joblib')


def carregar_artefactos(pasta=PASTA_MODELOS):
    pasta = Path(pasta)
    try:
        manifesto = json.loads((PASTA_MODELOS / 'manifesto.json').read_text(encoding='utf-8'))
        # Verificar todo o conjunto antes de desserializar qualquer ficheiro.
        for nome in NOMES:
            ficheiro = pasta / nome
            if not ficheiro.is_file():
                raise ValueError(f'Artefacto ML obrigatório em falta: {nome}')
            if hashlib.sha256(ficheiro.read_bytes()).hexdigest() != manifesto['sha256'][nome]:
                raise ValueError(f'Checksum ML inválido: {nome}')
        with warnings.catch_warnings():
            warnings.simplefilter('error', InconsistentVersionWarning)
            artefactos = [joblib.load(pasta / nome) for nome in NOMES]
        for modelo, scaler, dimensao in ((artefactos[0], artefactos[1], 10), (artefactos[2], artefactos[3], 7)):
            if not isinstance(modelo, XGBClassifier) or not isinstance(scaler, StandardScaler):
                raise ValueError('Tipos de modelo ou scaler incompatíveis')
            if modelo.n_features_in_ != dimensao or scaler.n_features_in_ != dimensao:
                raise ValueError('Dimensões do modelo e scaler incompatíveis')
            if list(modelo.classes_) != [0, 1]:
                raise ValueError('Classes do modelo incompatíveis')
            # Teste técnico do carregamento; não altera features, pesos ou previsões.
            probabilidades = modelo.predict_proba(scaler.transform(np.zeros((1, dimensao))))
            if probabilidades.shape != (1, 2) or not np.isfinite(probabilidades).all() or not ((probabilidades >= 0) & (probabilidades <= 1)).all():
                raise ValueError('O modelo não produz probabilidades válidas')
        encoder = artefactos[4]
        if not isinstance(encoder, LabelEncoder) or len(encoder.classes_) == 0:
            raise ValueError('Encoder de distrito incompatível ou vazio')
        encoder.transform(encoder.classes_)
        return tuple(artefactos)
    except Exception as erro:
        raise RuntimeError(f'Artefactos ML indisponíveis ou incompatíveis: {erro}') from erro


def main():
    parser = argparse.ArgumentParser(description='Validar os artefactos ML de produção.')
    parser.add_argument('--origem', type=Path, help='Instalar o conjunto aprovado a partir desta pasta.')
    args = parser.parse_args()
    if args.origem is not None:
        carregar_artefactos(args.origem)
        for nome in NOMES:
            if (args.origem / nome).resolve() != (PASTA_MODELOS / nome).resolve():
                shutil.copy2(args.origem / nome, PASTA_MODELOS / nome)
    carregar_artefactos()
    print('Artefactos ML de produção validados: 5 ficheiros.')


if __name__ == '__main__':
    main()
