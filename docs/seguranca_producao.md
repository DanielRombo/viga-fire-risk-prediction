# Segurança e robustez — fecho da validação local

Data: 12/10/2026. Sem deploy, commit, consultas à BD real ou alteração de dados de produção. Severidades referem-se ao risco identificado antes da correção; «corrigido» significa código local validado, ainda não instalado. Esta revisão não substitui uma auditoria de vulnerabilidades das dependências nem uma análise de todo o histórico Git.

## Riscos corrigidos

| Severidade | Ficheiro/local | Problema e impacto | Probabilidade/condição | Correção | Risco de regressão e instalação |
|---|---|---|---|---|---|
| Alto | `backend/services/auth.py`, `config/seguranca.py` | Chave JWT pública de fallback permitia falsificar tokens se faltasse configuração | Alta se SECRET_KEY ausente | Chave obrigatória, rejeição do fallback e mínimo de 32 caracteres; comprimento não prova entropia | Arranque recusa configuração fraca; requer chave aleatória e restart. Rotação invalida tokens existentes |
| Alto | `backend/main.py`, `config/seguranca.py`, Compose prod | CORS wildcard com credenciais | Exposição dependente do cliente/origem | Lista explícita; produção same-origin por defeito; Bearer sem cookies | Clientes de outra origem precisam de CORS_ORIGINS; restart |
| Alto | `.dockerignore`, Dockerfile.prod.dockerignore, `.gitignore` | Segredos, dumps e evidências privadas podiam entrar no contexto de build/Git | Condicional à existência dos ficheiros | Exclusões de envs, operações, experiências, dumps e artefactos temporários; preservados os cinco modelos oficiais | Rebuild futuro; não remove segredos eventualmente presentes em imagens/histórico antigos |
| Alto | `docker-compose.yml` | Passwords fixas e portas de desenvolvimento expostas em todas as interfaces | Alta numa máquina acessível em rede | Passwords exigidas por variável; portas limitadas a loopback | Dev exige DB_PASSWORD e PGADMIN_DEFAULT_PASSWORD; recriação futura |
| Alto | `MapaInterativo.jsx`, `utils/html.js` | Texto externo interpolado em HTML Leaflet podia executar marcação maliciosa | Condicional à origem dos nomes/mensagens | Escape antes de inserir no popup | Baixo; build frontend; sem alteração visual intencional |
| Médio | `backend/services/auth.py` | Login de utilizador inativo e erro de verificação de password/hash | Condicional ao estado/entrada | Recusa de utilizador inativo e falha de verificação controlada | Baixo; restart |
| Médio | `http_externo.py`, `open_meteo.py`, `nasa_firms.py`, `ipma.py` | Falhas transitórias sem retry limitado | Provável numa execução contínua | Até três GET para timeout/erro de rede ou 429/502/503/504, espera limitada; erros finais propagados | Aumenta latência máxima; não tenta novamente escritas na BD; restart |
| Médio | `backend/services/scheduler.py` | Exceção da recolha de focos absorvida, execução podia parecer bem-sucedida | Condicional a falha | Propagação após rollback existente; mensagem sem detalhes da fonte | Job passa a ser contabilizado como falha pelo scheduler; restart |
| Médio | `backend/config/database.py` | Ligações ociosas quebradas e espera de conexão sem limites explícitos | Provável após interrupção da BD | pool_pre_ping, pool_timeout e connect_timeout; parâmetros SQL ocultados; driver psycopg2 explícito | Baixo; não garante prazo global para todas as queries; restart |
| Médio | `backend/routes/health.py`, Compose prod | Ausência de healthcheck backend | Permanente na configuração anterior | Liveness e readiness separados; readiness testa BD com prazo SQL; Compose usa readiness | Não verifica completude de schema, scheduler ou cobertura; recriação backend |
| Médio | `docker-compose.prod.yml` | Logs Docker sem rotação explicitamente configurada | Cresce com tempo/carga | Driver local, 10 MB × 3 ficheiros por serviço | Só aplicado ao recriar cada serviço; planear separadamente a BD, sem recriação nesta tarefa |
| Médio | `docker/nginx/nginx.conf` | Versões e falta de headers defensivos/prazos de ligação | Permanente na configuração anterior | Oculta versão, nosniff, DENY, política de referrer, proxy headers e timeouts | DENY impede embedding; reload/recriação nginx futura; não fornece TLS |

## Pendências e limites

| Severidade | Local | Risco/impacto e probabilidade | Recomendação | Regressão / migração / restart |
|---|---|---|---|---|
| Crítico se acessível por rede não confiável | nginx / Compose, HTTP na porta 80 | Passwords e Bearer podem circular sem TLS; depende de existir terminação TLS externa, não verificada aqui | Definir domínio, certificado e terminação HTTPS antes de exposição pública | Configuração/reload; não foi inventado certificado nem ativado HSTS sobre HTTP |
| Alto | `backend/main.py` e preparadores de esquema | DDL/preparação de dados no import/arranque normal exige privilégios amplos e pode falhar/bloquear o arranque | Separar instalação/migração do processo servidor; utilizador de runtime com privilégios mínimos | Decisão operacional e migração controlada; **pendente**, create_all não removido |
| Alto | Autenticação e endpoints públicos que consultam fontes | Sem limitação de tentativas/carga por cliente; brute force e esgotamento de quotas | Limites por rota e cache adequados, sem confundir erro da fonte com zero resultados | Requer política e testes de limites; configuração/restart; sem migração obrigatória |
| Médio | Configuração DATABASE_URL | Construção textual pode interpretar mal caracteres reservados na password | Construir URL com escape/URL.create e validar configuração de instalação | Testar compatibilidade; restart; nenhuma credencial real foi lida |
| Médio | Rotas async com SQLAlchemy síncrono, p.ex. `routes/regioes.py` | Queries podem bloquear o event loop; probabilidade cresce com carga | Medir e deslocar blocos síncronos de forma segura, sem partilhar sessões entre threads | Refactor delimitado e testes; restart |
| Médio | Queries de meteorologia/alertas | Consultas do registo mais recente e scans podem degradar com histórico | EXPLAIN e inventário de índices antes de propor índice composto; evitar duplicados | Nenhum índice/DDL criado; exige ensaio descartável e aprovação antes de produção |
| Médio | Meteorologia e histórico | Crescimento sem política explícita de retenção | Medir volume, definir retenção/arquivo sem apagar histórico científico necessário | Decisão de dados; nenhuma eliminação autorizada/executada |
| Médio | Logging das fontes e scheduler | Sem redação global de URLs; URLs FIRMS contêm chave; sem métricas de última execução bem-sucedida | Redação central e métricas por job/fonte; rever nível dos loggers HTTP | Não se afirma que hide_parameters protege todos os logs; restart |
| Médio | Clientes externos | Retry não respeita Retry-After nem impõe deadline global; fontes não abrangidas pelo helper mantêm política anterior | Definir orçamento global e jitter; validar contratos externos separadamente | Alteração de latência e testes; serviço OpenStreetMap não foi alterado |
| Médio | Scheduler / implantação | Proteção atual depende de uma instância/worker; não é exclusão distribuída | Manter deployment de uma instância e monitorizar jobs; separar scheduler só se necessário | Mudança arquitetural apenas se escalar; não alterada |
| Médio | Nginx upstreams | Resolução estática de nomes pode conservar IP antigo após recriação do backend | Validar descoberta DNS/reload no plano de deploy | Potencial 502 após troca de IP; nenhuma recriação de produção neste trabalho |
| Médio | Registo de utilizadores | Concorrência de registos e limites de entrada/password precisam de testes adicionais | Validar entradas e traduzir conflitos sem detalhes internos | Não alterado; restart futuro |
| Baixo | Frontend/auth | Token em localStorage e logout sem revogação central mantêm risco residual perante XSS/token roubado | Avaliar política de sessão separadamente | Potencial alteração de contrato; não feita |
| Baixo | Docker / nginx frontend | Imagens sem digest, execução como root, cache longo de recursos não versionados | Fixar imagens após verificação, reduzir privilégios e rever cache | Build/recriação; não foi feita auditoria CVE nem alteração de versões |
| Baixo | Observabilidade | Health não cobre todos os serviços; logs não totalmente estruturados | Expandir monitorização com sinais úteis sem expor segredos | Configuração/restart; nenhuma dependência pesada adicionada |
| Baixo | Compose prod | Campo version obsoleto | Remover numa manutenção futura | Aviso apenas; config validada |

As rotas de escrita já protegidas por administrador foram mantidas e testadas. CORS não substitui autorização. Fórmulas FWI, modelos ML, estrutura das tabelas e dados reais não foram alterados. A alteração do scheduler limita-se à propagação de uma exceção já tratada pela transação.

## Validação concluída

- Regressão backend isolada anterior deste bloco: **88 testes executados, 87 aprovados e 1 ignorado** (concorrência dependente de PostgreSQL). Incluiu segurança, autorização de escritas, disponibilidade, focos, arranque, modo temporário, API FWI, FWI diário e atualização meteorológica. Não repetida no fecho.
- Integração final PostgreSQL/PostGIS: **6/6 aprovados**, incluindo o caso de concorrência anteriormente ignorado, idempotência, rollback, persistência/restauro, readiness/PostGIS e recuperação de ligação do pool terminada intencionalmente. Não somar estes resultados como testes únicos: há casos repetidos agora contra PostgreSQL.
- BD exclusiva `viga_fwi_test_security`, no container `viga-security-test-db`, imagem `postgis/postgis:15-3.3`, rede `none`, sem portas, limite 512 MiB. Runner partilhou apenas a rede isolada desse container. Container de teste encerrado/removido no fim. Nenhum serviço de produção foi consultado ou alterado.
- Frontend: **38/38 testes aprovados** (escape HTML, FWI diário, disponibilidade, atualidade e risco); build Vite aprovado. Não repetidos no fecho; não equivale a novo ensaio E2E no navegador.
- Nginx: `nginx -t` aprovado num container efémero, sem rede, upstreams resolvidos localmente para validar sintaxe. Não prova conectividade real entre serviços nem TLS.
- Compose produção: `docker compose --env-file <ficheiro temporário vazio> -f docker-compose.prod.yml config --quiet` aprovado com variáveis fictícias. Sem ler `.env.prod`, iniciar serviços ou divulgar segredos. Aviso apenas sobre version. Uma tentativa preliminar com ficheiro inadequado foi substituída pela validação correta; não houve deploy.
- `git diff --check`: executar no fecho; resultado registado na resposta final.

Comando de integração executado (montagem do backend local só para leitura):

```text
docker run --rm --network container:viga-security-test-db -e PYTHONDONTWRITEBYTECODE=1 -e VIGA_SECURITY_POSTGRES_TEST=1 -e DATABASE_URL=postgresql+psycopg2://postgres@127.0.0.1:5432/viga_fwi_test_security -e VIGA_FWI_TEST_DATABASE_URL=postgresql+psycopg2://postgres@127.0.0.1:5432/viga_fwi_test_security --mount <backend:/repo/backend,readonly> --workdir /repo/backend projeto_final_curso-backend:latest python -m unittest -v tests.test_seguranca_postgresql tests.test_fwi_diario.PersistenciaDiariaTests
```

## Ficheiros deste bloco

- `.gitignore`, `.dockerignore` e `docker/backend/Dockerfile.prod.dockerignore`: exclusões.
- `backend/config/seguranca.py`, `backend/services/auth.py`, `backend/main.py`: configuração, autenticação, CORS e registo de health.
- `backend/config/database.py`, `backend/routes/health.py`: ligações e diagnóstico.
- `backend/services/http_externo.py`, `ipma.py`, `nasa_firms.py`, `open_meteo.py`, `scheduler.py`: resiliência e comunicação de falhas.
- `backend/tests/test_seguranca_producao.py`, `test_seguranca_postgresql.py`, `test_scheduler_focos.py`: testes.
- `docker-compose.yml`, `docker-compose.prod.yml`, `docker/nginx/nginx.conf`: configuração de desenvolvimento/produção.
- `frontend/src/components/MapaInterativo.jsx`, `frontend/src/utils/html.js`, `frontend/tests/html.test.mjs`: escape HTML e testes.
- `docs/seguranca_producao.md`: esta auditoria e evidência de validação.

Ficheiros preexistentes em `operations/` e experiências ML não fazem parte deste bloco. Sem migração de BD necessária para as correções implementadas. Um deploy futuro exige revisão da chave, origens permitidas e configuração; build do backend/frontend e aplicação deliberada das alterações nginx/Compose. Não executar uma recriação global apenas para instalar estas correções.

Mensagem de commit proposta, apenas após revisão: `fix: reforçar segurança e robustez de produção`.
