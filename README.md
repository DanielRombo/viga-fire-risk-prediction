# 🔥 VIGA — Intelligent Surveillance and Alert Management

A wildfire risk prediction system for Portugal that integrates real-time weather data, satellite-detected fire hotspots, and machine learning models trained on historical Portuguese data — all presented through an interactive web dashboard with a district-level map.

Developed as a **Final Year Project — ISTEC** (2026).

---

## 📸 Screenshots

![Dashboard](docs/screenshots/Dashboard.png)


![Interactive Map](docs/screenshots/Cidade_Detalhes.png)


![Login](docs/screenshots/Login.png)


---

## ✨ Features

- 🗺️ **Interactive map** of Portugal's 18 districts with real-time fire risk levels
- 🛰️ **Active fire hotspots** via satellite (NASA FIRMS), filtered to Portuguese territory
- 🌡️ **Real-time weather data** (temperature, humidity, wind, precipitation) updated hourly
- 🤖 **Machine learning ensemble** (two XGBoost models) combining historical data from ANPC and Kaggle
- 🔥 **Fire Weather Index (FWI) calculation**, the Canadian wildfire danger rating system used by ANPC
- 🔍 **Location search** across 3,258 regions in Portugal
- 🔐 **JWT authentication** with protected routes
- 🐳 **Fully dockerized**, with separate development and production environments

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend      │────▶│      Nginx      │────▶│     Backend      │
│  React + Vite    │     │  Reverse Proxy  │     │     FastAPI      │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                            │
                                        ┌───────────────────┴───────────────────┐
                                        │                                       │
                                ┌───────▼────────┐                    ┌────────▼────────┐
                                │   PostgreSQL     │                    │  External APIs   │
                                │   + PostGIS      │                    │  Open-Meteo      │
                                └─────────────────┘                    │  NASA FIRMS      │
                                                                        │  IPMA            │
                                                                        └─────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | **FastAPI** (Python) | Async support, automatic validation with Pydantic, native OpenAPI docs |
| Database | **PostgreSQL + PostGIS** | Native geospatial support, robust for time-series data |
| Frontend | **React + Vite** | Mature ecosystem, fast hot reload |
| Map | **Leaflet.js** | Open-source, GeoJSON support, no API costs |
| Machine Learning | **XGBoost Ensemble** | Best performance on tabular weather data |
| Infrastructure | **Docker Compose** | Reproducible environment, separate dev/prod profiles |
| Authentication | **JWT** | Stateless and scalable |

---

## 🤖 Machine Learning Models

The system combines two independent XGBoost models, weighted by geographic relevance:

| Model | Dataset | Records | Weight | Accuracy |
|-------|---------|---------|--------|----------|
| ANPC | Rural fire occurrences in Portugal (2016–2020) | 54,402 | 60% | 81% |
| Kaggle | Forest Fires (FWI) | 517 | 40% | 60% |

The **ICNF** dataset (274,986 occurrences, 1980–2015) was analyzed but excluded from the ensemble due to missing geographic coordinates.

---

## 🌐 External APIs

- **[Open-Meteo](https://open-meteo.com/)** — real-time weather data, free and no API key required
- **[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)** — satellite fire hotspots via VIIRS SNPP (Near Real Time)
- **[IPMA](https://www.ipma.pt/)** — official Portuguese weather forecasts
- **OpenStreetMap / Overpass API** — 3,258 regions and localities across Portugal

---

## 🚀 Running the Project

### Development

```bash
docker compose up -d
```

Access at `http://localhost:5173`

### Production

As variáveis de produção são carregadas de `.env.prod` através de `--env-file`; o Compose não carrega este ficheiro automaticamente. Defina `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SECRET_KEY` e `NASA_FIRMS_KEY` nesse ficheiro local, que está excluído do Git. O `.env` usa as variáveis `DB_*` de desenvolvimento e não substitui o `.env.prod`.

No arranque, o backend prepara as regiões antes de iniciar a recolha. O catálogo principal é `backend/data/regioes_principais.json`, baseado nas 30 cidades de `database/seeds/cidades_principais.sql`; a marca `recolha_automatica` mantém as 28 regiões recolhidas pelo scheduler. Os IDs são atribuídos pela BD e resolvidos por nome e distrito normalizados e coordenadas exatas do catálogo, sem depender dos IDs do dump histórico `regioes_seed.sql`. Não é necessário importar os ficheiros SQL numa instalação nova. Os registos correspondentes são reutilizados sem alterar os seus campos; duplicados históricos não são removidos. Se não existir o ponto exato, a preparação cria-o sem modificar outros pontos da mesma localidade. Mais de uma correspondência exata interrompe a preparação, sem inserções parciais; nunca se escolhe apenas o primeiro ID.

Esta preparação não substitui a lista de IDs ainda existente no mapa do frontend; essa lista não deve ser usada como catálogo de inicialização.

As observações NASA são deduplicadas na BD por produto (`VIIRS_SNPP_NRT`), data/hora de aquisição e coordenadas, sem arredondamento adicional. No arranque, a adaptação transacional do esquema permite uma região nula e acrescenta uma chave única nullable. Para registos históricos da fonte `NASA FIRMS - VIIRS`, apenas um representante de cada observação recebe a chave; nenhum duplicado é apagado e as associações antigas ficam marcadas como `legado_nao_validado`. Outros registos históricos permanecem sem chave, pois não é possível inferir com segurança o produto de origem.

A associação de novos focos usa polígonos válidos com SRID conhecido, através de PostGIS: `poligono` quando há uma única correspondência, `nao_determinada` quando não há e `ambigua` quando há várias. Nos dois últimos casos, `id_regiao` é nulo. Coordenadas de cidades e o GeoJSON de distritos do frontend não são tratados como limites administrativos das regiões. A rota `/api/incendios/guardar` deixa de aceitar uma região imposta por `id_regiao` (HTTP 422) e devolve `focos_guardados`, `focos_duplicados` e `focos_sem_regiao`; esta última contagem refere-se apenas aos novos registos. A importação de polígonos e a revisão das associações históricas não são realizadas automaticamente.

O filtro territorial inicial da NASA usa `backend/data/portugal_distritos.geojson`, uma cópia integral do GeoJSON já existente em `frontend/public/portugal_distritos.json`. Shapely verifica a inclusão nos polígonos, sem acesso à BD. Os retângulos de consulta são calculados separadamente para continente, Açores e Madeira, incluindo as ilhas representadas no ficheiro (também Porto Santo, Desertas e Selvagens); servem apenas para obter candidatos. Pontos fora dos polígonos são rejeitados. A precisão fica limitada à resolução deste GeoJSON, que não substitui cartografia administrativa de maior detalhe. Este filtro nacional não determina a região de uma ocorrência.

Só há sucesso após respostas válidas das três áreas: uma falha ou timeout mantém o erro HTTP, sem devolver uma lista parcial como cobertura nacional. Observações repetidas entre áreas são removidas da resposta usando a mesma identidade NASA; a deduplicação persistente na BD mantém-se inalterada.

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Access at `http://localhost`

---

## 📁 Project Structure

```
viga/
├── backend/          # FastAPI: routes, services, ML models
├── frontend/         # React + Vite: dashboard, map, authentication
├── docker/           # Development and production Dockerfiles
├── ml/notebooks/     # Model training notebooks
├── database/seeds/   # Initial seed SQL scripts
└── docs/             # Detailed technical documentation
```

---

## 🧩 Technical Challenges Solved

Several real engineering problems were identified and resolved during development, including:

- A scheduler that silently stopped due to uvicorn's `--reload` mode restarting the child process
- Fire hotspots from Spain appearing on the map due to the API's rectangular bounding box
- Version incompatibility between `bcrypt` and `passlib`
- Failed district-name matching between accented GeoJSON names and unaccented database entries

📄 The full breakdown of technical decisions, architecture, and challenges is documented in [`docs/decisoes_tecnicas.md`](docs/decisoes_tecnicas.md).

---

## 👤 Author

**Daniel Rombo**
Final Year Project — ISTEC, 2026
