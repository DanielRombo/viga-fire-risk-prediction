# Artefactos ML de produção

A localização oficial é `backend/ml_models`, independente da pasta de execução.
O conjunto aprovado acompanha o Git: não é necessário executar o treino num clone novo.
Os cinco binários devem ser incluídos juntamente com o código no próximo commit;
a exceção no `.gitignore` não adiciona ficheiros ao Git automaticamente.

| Ficheiro obrigatório | Função |
| --- | --- |
| `modelo_kaggle.joblib` | Classificador meteorológico, 10 entradas |
| `scaler_kaggle.joblib` | Normalização das 10 entradas meteorológicas |
| `modelo_anpc.joblib` | Classificador histórico, 7 entradas |
| `scaler_anpc.joblib` | Normalização das 7 entradas históricas |
| `encoder_distrito_anpc.joblib` | Codificação dos distritos do modelo ANPC |

`manifesto.json` regista SHA-256 e versões do ambiente validado, também fixadas em
`backend/requirements.txt`. Não constitui uma assinatura de autenticidade: usar apenas
artefactos de origem de confiança, pois Joblib desserializa objetos Python.

## Instalação limpa

Na raiz de um clone que inclua os cinco binários:

```sh
python -m pip install -r backend/requirements.txt
python backend/services/artefactos_ml.py
docker build -f docker/backend/Dockerfile.prod -t viga-backend .
```

O validador verifica todos os hashes antes de carregar qualquer ficheiro, os tipos,
as dimensões, as classes, o encoder e uma chamada técnica de previsão.
O build de produção executa o mesmo validador. A API carrega o conjunto validado ao
importar `services.modelo_ml`, antes de servir pedidos. Um ficheiro em falta,
alterado, ilegível ou incompatível termina o comando/arranque com erro; não existe
arranque parcial com apenas um modelo. Isto não altera features, pesos ou fórmulas.

## Treino e publicação

O notebook mantém `ml/models` como pasta de trabalho. Não é uma segunda pasta de
produção. Para instalar uma cópia do conjunto **já aprovado** a partir dessa pasta:

```sh
python backend/services/artefactos_ml.py --origem ml/models
```

A origem completa é validada antes de copiar os cinco ficheiros para a localização
oficial. Não há procura automática nem fallback para ficheiros genéricos. Um treino
novo não é publicado automaticamente: requer revisão dos cinco artefactos, dos hashes
do manifesto e das versões das bibliotecas, seguida dos testes e do build.
Não atualizar hashes apenas para contornar uma falha de validação.

## Artefactos antigos

Não foram apagados. `modelo_risco.joblib` é uma cópia do modelo ANPC;
`backend/ml_models/scaler.joblib` é uma cópia do scaler Kaggle, enquanto
`ml/models/scaler.joblib` é uma cópia do scaler ANPC. Não são intercambiáveis.
`modelo_icnf.joblib`, `scaler_icnf.joblib` e `encoder_distrito.joblib` pertencem à
exploração ICNF e não são usados pelo backend. As cópias dos cinco artefactos em
`ml/models` também não são carregadas pela API.

Só os cinco `.joblib` oficiais são admitidos pelo `.gitignore` e pelo ficheiro de
exclusões específico do Dockerfile de produção. O Dockerfile de desenvolvimento
mantém o comportamento anterior.
