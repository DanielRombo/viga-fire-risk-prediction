# Decisões Técnicas — VIGA
## Vigilância Inteligente e Gestão de Alertas

**Projeto Final de Curso — ISTEC**  
**Autor:** Daniel Rombo  
**Data:** Julho 2026

---

## 1. Visão Geral do Sistema

O VIGA (Vigilância Inteligente e Gestão de Alertas) é um sistema de predição de risco de incêndio florestal para Portugal. Integra dados meteorológicos em tempo real provenientes de múltiplas fontes, focos de incêndio detetados por satélite e modelos de machine learning treinados com dados históricos portugueses, apresentando tudo numa interface web interativa com mapa por distrito.

O sistema foi desenvolvido como projeto final de curso, com foco em dados reais e arquitetura production-ready.

### Arquitetura Geral

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Nginx       │────▶│    Backend      │
│  React + Vite   │     │  Reverse Proxy  │     │    FastAPI      │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
│
┌───────────────────────────┤
│                           │
┌─────────▼──────┐         ┌─────────▼──────┐
│  PostgreSQL    │         │  APIs Externas  │
│  + PostGIS     │         │  Open-Meteo     │
└────────────────┘         │  NASA FIRMS     │
                           │  IPMA           │
                           └────────────────┘

---

## 2. Stack Tecnológica

### 2.1 Backend — FastAPI + Python

**Decisão:** FastAPI em vez de Flask ou Django REST Framework.

**Justificação:**
- Suporte nativo a operações assíncronas (`async/await`), essencial para chamadas paralelas às APIs externas sem bloquear o servidor
- Geração automática de documentação interativa OpenAPI (disponível em `/docs`)
- Validação automática de dados de entrada com Pydantic, reduzindo código de validação manual
- Performance superior ao Flask em cenários de I/O intensivo, como as chamadas a APIs meteorológicas
- Tipagem estática que facilita a manutenção e deteção de erros em tempo de desenvolvimento

### 2.2 Base de Dados — PostgreSQL + PostGIS

**Decisão:** PostgreSQL com extensão PostGIS em vez de SQLite ou MongoDB.

**Justificação:**
- PostGIS adiciona suporte nativo a dados geoespaciais (coordenadas, polígonos de distritos), necessário para operações de proximidade geográfica
- PostgreSQL é robusto para séries temporais — os dados meteorológicos são recolhidos de hora em hora e acumulam rapidamente
- SQLAlchemy como ORM permite queries tipadas, migrações controladas e abstração da base de dados
- Suporte a queries geoespaciais como `ST_Within` para verificar se um ponto está dentro de um polígono de distrito

### 2.3 Frontend — React + Vite

**Decisão:** React com Vite em vez de Next.js ou Vue.js.

**Justificação:**
- React oferece um ecossistema maduro com grande comunidade e muitas bibliotecas disponíveis
- Vite tem Hot Module Replacement significativamente mais rápido que o Create React App, agilizando o desenvolvimento
- Componentes reutilizáveis (Navbar, Sidebar, MapaInterativo, PainelAlertas, PainelML) facilitam a manutenção
- React Router para navegação SPA sem recarregamento de página, proporcionando uma experiência mais fluida

### 2.4 Mapa Interativo — Leaflet.js

**Decisão:** Leaflet em vez de Google Maps ou Mapbox.

**Justificação:**
- Open-source e completamente gratuito, sem limites de chamadas API nem custos
- Suporte nativo a GeoJSON para renderizar os polígonos dos 18 distritos de Portugal com cores dinâmicas
- Camadas sobreponíveis e configuráveis (temperatura, FWI, focos ativos, satélite Esri)
- Leve e com boa performance, mesmo com muitos marcadores de focos de incêndio

### 2.5 Machine Learning — Ensemble XGBoost

**Decisão:** Ensemble de dois modelos XGBoost independentes em vez de um único modelo ou redes neuronais.

**Justificação:**
- XGBoost tem excelente performance em dados tabulares com features meteorológicas, superando frequentemente redes neuronais neste tipo de dados
- Combinar dois modelos treinados em datasets distintos reduz o viés individual de cada um
- O modelo ANPC (81% de accuracy) foi treinado exclusivamente com dados históricos de Portugal, tornando-o mais relevante geograficamente
- O modelo Kaggle (60% de accuracy) complementa com features do sistema FWI globalmente validadas
- A ponderação 60% ANPC + 40% Kaggle reflete a maior relevância dos dados portugueses para o contexto nacional

**Datasets utilizados:**
| Dataset | Registos | Período | Uso |
|---------|----------|---------|-----|
| ANPC | 54.402 ocorrências rurais | 2016–2020 | Modelo principal (60%) |
| Kaggle Forest Fires | 517 registos FWI | Histórico | Modelo complementar (40%) |
| ICNF | 274.986 ocorrências | 1980–2015 | Documentado, não usado no ensemble (sem coordenadas) |

### 2.6 Infraestrutura — Docker Compose

**Decisão:** Docker Compose em vez de deployment manual ou Kubernetes.

**Justificação:**
- Ambiente completamente reproduzível em qualquer máquina com Docker instalado
- Isolamento de serviços — backend, frontend, base de dados e nginx correm em containers independentes
- Dois perfis distintos: `docker-compose.yml` para desenvolvimento (com hot reload) e `docker-compose.prod.yml` para produção
- Multi-stage builds no Dockerfile de produção reduzem significativamente o tamanho das imagens finais

---

## 3. APIs Externas Integradas

### 3.1 Open-Meteo

**URL:** `https://api.open-meteo.com/v1/forecast`  
**Dados recolhidos:** Temperatura, humidade relativa, velocidade do vento, precipitação  
**Frequência de recolha:** De hora em hora via scheduler automático  
**Motivo de escolha:** Completamente gratuita, sem necessidade de chave API, cobertura global com dados em tempo real e históricos

### 3.2 NASA FIRMS

**Nome completo:** Fire Information for Resource Management System  
**URL:** `https://firms.modaps.eosdis.nasa.gov/api/area/csv`  
**Dados recolhidos:** Focos de incêndio ativo detetados por satélite, com coordenadas e timestamp  
**Satélite utilizado:** VIIRS SNPP NRT (Near Real Time)

Um problema identificado durante o desenvolvimento foi que a bounding box rectangular da API incluía parte de Espanha. Foi implementado um filtro geográfico por coordenadas para garantir que só aparecem focos em território português:

```python
def is_portugal(lat, lon):
    # Portugal continental
    if 36.8 <= lat <= 42.2 and -9.6 <= lon <= -6.1:
        return True
    # Açores
    if 36.8 <= lat <= 40.0 and -31.3 <= lon <= -24.8:
        return True
    # Madeira
    if 32.4 <= lat <= 33.2 and -17.3 <= lon <= -16.2:
        return True
    return False
```

### 3.3 IPMA

**Nome completo:** Instituto Português do Mar e da Atmosfera  
**Dados recolhidos:** Previsões meteorológicas oficiais portuguesas por município  
**Motivo de escolha:** Fonte oficial portuguesa, com dados localizados e validados

### 3.4 OpenStreetMap / Overpass API

**Dados recolhidos:** 3.258 regiões e localidades de Portugal  
**Uso no sistema:** Pesquisa de localidades na sidebar com animação flyTo no mapa para as coordenadas selecionadas

---

## 4. Índice FWI (Fire Weather Index)

O FWI é o sistema canadiano de avaliação de perigo de incêndio florestal, adotado internacionalmente e utilizado em Portugal pela ANPC. No VIGA, é calculado localmente a partir dos dados meteorológicos recolhidos em tempo real.

### Componentes calculados

| Componente | Nome completo | Descrição |
|------------|---------------|-----------|
| FFMC | Fine Fuel Moisture Code | Humidade de combustíveis finos (folhas, erva seca) |
| DMC | Duff Moisture Code | Humidade de detritos orgânicos no solo |
| DC | Drought Code | Nível de seca profunda do solo |
| ISI | Initial Spread Index | Velocidade esperada de propagação inicial do fogo |
| BUI | Build-Up Index | Quantidade total de combustível disponível |
| **FWI** | **Fire Weather Index** | **Índice final que combina todos os anteriores** |

### Classificação de risco adotada

| FWI | Nível de Risco |
|-----|----------------|
| < 5.2 | Baixo |
| 5.2 – 11.2 | Moderado |
| 11.2 – 21.3 | Alto |
| 21.3 – 38.0 | Muito Alto |
| > 38.0 | Extremo |

---

## 5. Autenticação JWT

**Decisão:** JSON Web Tokens em vez de sessões guardadas no servidor.

**Justificação:**
- Stateless — o servidor não precisa de manter estado de sessão, simplificando a arquitetura
- Escalável — múltiplas instâncias do backend podem validar o mesmo token sem partilhar estado
- Token guardado no `localStorage` do browser com expiração de 24 horas

**Fluxo de autenticação:**

Utilizador envia email + senha → POST /api/auth/login
Backend valida credenciais na base de dados
Backend gera JWT assinado com {sub: email, exp: 24h}
Frontend guarda token no localStorage
Todos os pedidos seguintes incluem: Authorization: Bearer <token>
Backend valida o token em cada pedido protegido via dependency injection

**Nota técnica sobre dependências:** Durante o desenvolvimento foi identificada uma incompatibilidade entre versões recentes do `bcrypt` e o `passlib`. A solução foi fixar versões específicas:

passlib[bcrypt]==1.7.4
bcrypt==4.0.1

---

## 6. Scheduler de Recolha de Dados

### Problema encontrado

O uvicorn em modo de desenvolvimento usa um processo de reload que reinicia o processo filho quando deteta alterações nos ficheiros. O `asyncio.create_task` executado no evento `startup` do FastAPI era perdido neste processo de reinício, fazendo com que o scheduler parasse silenciosamente.

### Solução implementada

A solução foi dividida em duas partes complementares:

**Arranque inicial (`iniciar.py`):**
Corre antes do uvicorn e garante que os dados são recolhidos imediatamente ao ligar o sistema, sem depender do scheduler:
```python
asyncio.run(atualizar_dados_meteorologicos())
```

**Scheduler periódico (`BackgroundScheduler`):**
O APScheduler com `BackgroundScheduler` corre numa thread separada, independente do ciclo de vida do uvicorn:
```python
scheduler.add_job(
    atualizar_dados_meteorologicos_sync,
    'interval',
    hours=1
)
```

A função `atualizar_dados_meteorologicos_sync` cria um novo event loop por execução, necessário porque as threads do `BackgroundScheduler` não têm um event loop asyncio associado:
```python
def atualizar_dados_meteorologicos_sync():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_atualizar_dados())
    finally:
        loop.close()
```

---

## 7. Mapa GeoJSON — Correspondência de Distritos

### Problema encontrado

O ficheiro GeoJSON dos distritos de Portugal usa nomes com acentos (`"Évora"`, `"Bragança"`, `"Setúbal"`) enquanto a base de dados armazena os nomes sem acentos (`"Evora"`, `"Braganca"`, `"Setubal"`). Isto causava falhas na correspondência, deixando distritos sem cor no mapa.

### Solução implementada

Função de normalização Unicode que remove diacríticos antes de comparar os nomes:

```javascript
const normalizar = (str) => str?.toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim() || ""

const encontrarCidade = (nomeDistrito) => {
    const nomeNorm = normalizar(nomeDistrito)
    return riscosCidades.find(c => {
        const cidadeNorm = normalizar(c.nome)
        return nomeNorm === cidadeNorm ||
               nomeNorm.includes(cidadeNorm) ||
               cidadeNorm.includes(nomeNorm)
    })
}
```

---

## 8. Estrutura do Projeto

viga/
├── backend/
│   ├── config/
│   │   └── database.py           # Conexão SQLAlchemy (suporta DATABASE_URL ou variáveis individuais)
│   ├── models/
│   │   ├── dado_meteorologico.py
│   │   ├── ocorrencia.py
│   │   ├── regiao.py
│   │   └── utilizador.py
│   ├── routes/
│   │   ├── auth.py               # JWT: login, registar, me, logout
│   │   ├── meteorologia.py       # Dados meteorológicos + atualizar-agora
│   │   ├── incendios.py          # Focos NASA FIRMS
│   │   ├── regioes.py            # 3258 regiões + pesquisa
│   │   ├── risco.py              # Cálculo de risco combinado FWI + ML
│   │   ├── alertas.py            # Alertas prioritários
│   │   └── ipma.py               # Previsões IPMA
│   ├── services/
│   │   ├── auth.py               # JWT helpers (hash, criar token, verificar)
│   │   ├── open_meteo.py         # Integração Open-Meteo
│   │   ├── nasa_firms.py         # Integração NASA FIRMS com filtro Portugal
│   │   ├── fwi.py                # Cálculo local do índice FWI
│   │   ├── modelo_ml.py          # Ensemble ML (ANPC 60% + Kaggle 40%)
│   │   └── scheduler.py          # BackgroundScheduler hora a hora
│   ├── ml_models/
│   │   ├── modelo_anpc.joblib    # XGBoost treinado com dados ANPC (81% accuracy)
│   │   ├── modelo_kaggle.joblib  # XGBoost treinado com dados Kaggle (60% accuracy)
│   │   ├── scaler_anpc.joblib
│   │   ├── scaler_kaggle.joblib
│   │   └── encoder_distrito_anpc.joblib
│   ├── iniciar.py                # Recolha inicial de dados antes do servidor arrancar
│   ├── main.py                   # App FastAPI + routers + startup
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── portugal_distritos.json   # GeoJSON com 18 distritos de Portugal
│   └── src/
│       ├── components/
│       │   ├── MapaInterativo.jsx    # Mapa Leaflet com 6 camadas
│       │   ├── PainelAlertas.jsx     # Lista de alertas com scroll
│       │   ├── PainelML.jsx          # Resultados do ensemble ML + FWI
│       │   ├── Navbar.jsx            # Barra de navegação com relógio e utilizador
│       │   ├── Sidebar.jsx           # Condições atuais, pesquisa, distritos
│       │   └── RotaProtegida.jsx     # Redirect para /login se não autenticado
│       ├── pages/
│       │   ├── Dashboard.jsx         # Página principal do sistema
│       │   ├── DetalheRegiao.jsx     # Detalhe por região com histórico
│       │   └── Login.jsx             # Página de login e registo
│       └── services/
│           ├── api.js                # Axios com todas as chamadas à API
│           └── auth.js               # login, registar, logout, token
├── docker/
│   ├── backend/
│   │   ├── Dockerfile            # Imagem de desenvolvimento
│   │   └── Dockerfile.prod       # Imagem de produção (2 workers)
│   ├── frontend/
│   │   └── Dockerfile.prod       # Multi-stage: build Vite + Nginx
│   └── nginx/
│       ├── nginx.conf            # Reverse proxy principal
│       └── nginx-frontend.conf   # Servidor estático com SPA fallback
├── ml/
│   └── notebooks/                # Jupyter notebooks de treino dos modelos
├── database/
│   └── seeds/                    # Scripts SQL de população inicial
├── docker-compose.yml            # Ambiente de desenvolvimento
├── docker-compose.prod.yml       # Ambiente de produção com Nginx
├── Makefile                      # Atalhos para comandos Docker
└── docs/
└── decisoes_tecnicas.md      # Este documento

---

## 9. Decisões de Segurança

| Aspeto | Decisão | Justificação |
|--------|---------|--------------|
| Passwords | Hash bcrypt | Algoritmo lento por design, resistente a ataques de força bruta |
| Tokens | JWT com expiração 24h | Limita a janela de ataque em caso de token comprometido |
| CORS | `allow_origins=["*"]` em dev | Em produção deve ser restrito ao domínio específico |
| Variáveis sensíveis | Ficheiros `.env` e `.env.prod` | Nunca versionados no repositório git |
| Chaves API | Variáveis de ambiente | Nunca hardcoded no código fonte |
| Rotas protegidas | `RotaProtegida` no frontend | Redirect automático para login se token ausente |

---

## 10. Ambientes de Execução

O sistema suporta dois ambientes distintos:

| Aspeto | Desenvolvimento | Produção |
|--------|----------------|----------|
| Comando | `docker compose up -d` | `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d` |
| Frontend | Vite dev server (porta 5173) | Build estático servido pelo Nginx (porta 80) |
| Backend | Uvicorn com 1 worker | Uvicorn com 2 workers |
| Hot reload | Sim | Não |
| URL | `http://localhost:5173` | `http://localhost` |

---

## 11. Desafios e Soluções

| Desafio | Causa | Solução Implementada |
|---------|-------|---------------------|
| Scheduler parava silenciosamente | uvicorn --reload reinicia o processo filho, perdendo o `asyncio.create_task` | `BackgroundScheduler` em thread separada + `iniciar.py` para dados iniciais |
| Focos de incêndio de Espanha no mapa | Bounding box rectangular da NASA FIRMS inclui território espanhol | Filtro geográfico `is_portugal()` com bounding boxes por região |
| Distritos sem cor no mapa | GeoJSON usa nomes com acentos, BD usa sem acentos | Normalização Unicode antes de comparar nomes |
| Erro de autenticação bcrypt | Incompatibilidade entre versões recentes de `bcrypt` e `passlib` | Pin de versões: `passlib==1.7.4` + `bcrypt==4.0.1` |
| CMD Windows não suporta multiline | Limitação do terminal CMD para scripts Python inline | Script `iniciar.py` separado executado antes do uvicorn |
| Dados desatualizados ao abrir browser | `iniciar.py` só corria uma vez no arranque sem scheduler ativo | `BackgroundScheduler` de hora em hora + `iniciar.py` garante dados frescos no arranque |
| BD de produção vazia | Nova instância PostgreSQL sem dados de regiões | Dump da BD de desenvolvimento importado para produção via `pg_dump` |
| `DATABASE_URL` não reconhecida em produção | `database.py` construía URL a partir de variáveis individuais | Suporte a `DATABASE_URL` direta com fallback para variáveis individuais |