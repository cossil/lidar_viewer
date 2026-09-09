# Relatório — Plataforma de Análise e Simulação de Performance LiDAR

**Projeto:** SilvaLab / University of Florida — LiDAR Performance Analysis & Simulation Platform
**Código:** `/opt/data/lidar_platform`
**Autor do relatório:** Hermes Agent
**Data:** 2026-09-08

---

## 1. O que é a aplicação

É uma **aplicação web local de engenharia** (backend REST em Python/FastAPI) para **analisar, comparar e simular a performance de sensores LiDAR** a partir de datasheets de fabricante e parâmetros definidos pelo usuário. O caso de uso central é o **inventário florestal** (terrestre e aéreo): avaliar se um sensor específico consegue **detectar e caracterizar pequenos alvos cilíndricos** — como troncos de árvore — sob condições controladas.

Ela responde perguntas de engenharia do tipo:

- O LiDAR A detecta um tronco de 10 cm de DAP (diâmetro à altura do peito) a 30 m?
- Qual a distância máxima de detecção para um tronco de 10 cm?
- Como o sensor A se compara ao sensor B sob condições idênticas?
- Quantos retornos devem intersetar um tronco numa varredura de 1 segundo?
- Qual a probabilidade de detectar o tronco?
- A partir de que distância a **caracterização confiável** deixa de ser possível?
- Como a performance varia com DAP, refletividade, ângulo de incidência e duração da varredura?
- O sensor é **adequado** para um perfil de aplicação de inventário florestal definido?

A aplicação **não** é — por desenho — um simulador eletromagnético/fotônico completo. É um **modelo de engenharia em camadas e transparente**:

> Modelo do Sensor → Cenário → Padrão de Varredura → Geometria de Raios → Interseção com Alvo → Interação Feixe/Alvo → Intensidade do Retorno → Probabilidade de Detecção → Retornos Estocásticos → Erro de Medição → Nuvem de Pontos → Análise Estatística

Princípios prioritários: **rastreabilidade, reprodutibilidade, transparência do modelo e ausência de falsa precisão**. O sistema distingue explicitamente dados de fabricante vs. dados de usuário vs. quantidades derivadas vs. premissas de engenharia vs. saídas de modelo analítico vs. resultados de Monte Carlo vs. calibração empírica.

---

## 2. Como a aplicação funciona (arquitetura)

O backend vive em `backend/lidar_analysis/`, organizado em módulos em camadas (cada um é uma fase do pipeline):

| Módulo | Responsabilidade |
|---|---|
| `models/` | Schemas Pydantic estritos (sensor, cenário, simulação, resultados, parâmetros com unidade/origem/status, proveniência). Validação `extra="forbid"` + validação de limites (probabilidade 0–1, refletividade, DAP, duração). |
| `geometry/` | Transformações 4×4, alvos (cilindro, caixa), interseção raio-cilindro/caixa (analítica), tamanho angular θ_T, footprint do feixe, ângulo de incidência, direções de raios. |
| `scan/` | Geradores de varredura: `MechanicalSpinningScanner`, `StructuredRasterScanner`, `NonRepetitiveScanner` + canais e pontos de varredura. |
| `physics/` | Feixe/óptica (overlap, intensidade do retorno, área efetiva), detecção (datasheet/analítico/premissa, `insufficient_data`), medição (bias + ruído, conversão de definição de erro 1σ↔2σ↔95%). |
| `simulation/` | `SingleTrialEngine` (raio→interseta→detecta→mede), `MonteCarloEngine` (N tentativas, estatísticas), análise (classificação, varredura de distância, alcances efetivos), `analytical` e `pointcloud`. |
| `analysis/` | Comparação de sensores, avaliação de adequação (suitability), métricas secundárias. |
| `ingestion/` | Extração e validação de datasheets (regex + parser ciente de unidades; nunca fabrica parâmetros; proveniência por parâmetro). |
| `reporting/` | Exportação JSON/CSV e relatório Markdown (14 seções). |
| `api/` | FastAPI app + rotas, store em memória, registro de premissas, envelope de erro padronizado. |

### Armazenamento
MVP usa um **store em memória** (`api/store.py`) — sensores, cenários, simulações e jobs vivem em dicts, pensado para ser substituído por banco na fase 10+. Simulações geram jobs com status (`queued → running → completed/failed`).

### Pipeline de uma simulação
1. `POST /api/sensors` — cria o sensor; `POST /api/scenarios` — cria o cenário (envia `sensor_id`, pose do sensor, alvo cilíndrico).
2. `POST /api/simulations` — monta o scanner a partir dos parâmetros do sensor, constrói o alvo a partir do cenário, `SingleTrialEngine` + modo escolhido (Monte Carlo, analítico ou nuvem de pontos sintética) e registra as premissas usadas.
3. `GET /api/simulations/{id}/results` — recupera o resultado completo.
4. Rotas de análise agregam varreduras (`distance-sweep`, `dbh-sweep`) e comparação entre sensores sob condições idênticas.
5. Rotas de relatório geram Markdown/JSON; rotas de datasheet ingerem e validam specs.

### Comportamentos-chave implementados
- **Nunca fabrica probabilidade de detecção:** se o modelo de detecção requer um parâmetro `unknown`, responde `insufficient_data` (não inventa número).
- **Determinismo:** funções estocásticas usam `rng`/`seed` explícito; a simulação registra a seed usada.
- **Imutabilidade do sensor (Regra 9):** um `PUT` num sensor existente **faz snapshot da versão antiga** antes de substituir e cria uma versão nova snapshotada; uma simulação referencia a versão exata do sensor usada (imutável mesmo se o sensor for editado depois).
- **Registro de premissas (§61):** resultados de simulação carregam uma lista de ids `assumption_<hex>` resolvíveis para a descrição/razão de cada premissa de engenharia (modelo de ruído, fallback de datasheet, divergência default, aproximação de cobertura).
- **Envelope de erro padronizado:** `{"error": {"code", "message", "field", "details"}}` com códigos como `UNKNOWN_SENSOR`, `INSUFFICIENT_DATA`, `SIMULATION_NOT_COMPLETE`.

---

## 3. Como usar (instruções claras)

### Pré-requisitos
- Python 3.11+ (o repo usa 3.13.5 em `.venv/`).
- Dependências já instaladas em `.venv/`: `numpy`, `scipy`, `pydantic`, `fastapi`, `uvicorn`, `jsonschema`, `matplotlib`, `pytest`, `httpx`.

### Subir o servidor
A partir da raiz do projeto:

```bash
cd /opt/data/lidar_platform
PYTHONPATH=backend .venv/bin/python -m uvicorn lidar_analysis.api.app:app --host 0.0.0.0 --port 8000
```

- Interface interativa (Swagger UI): **`http://localhost:8000/docs`**
- OpenAPI/JSON dos endpoints: **`http://localhost:8000/openapi.json`**
- Verificação de saúde: **`GET http://localhost:8000/health`** → `{"status":"ok"}`

*(Verificado ao vivo nesta sessão: todos os 15 caminhos servidos, `/docs` retorna 200.)*

### Usar sem escrever código (Swagger UI)
No `/docs`, cada endpoint tem botão **"Try it out"**. Fluxo recomendado para um primeiro teste ponta-a-ponta:

1. **`POST /api/sensors`** — criar o sensor Hesai QT64 (exemplo pronto nos testes/`sample_sensor_data`).
2. **`POST /api/scenarios`** — criar um cenário apontando para esse `sensor_id` com um alvo cilíndrico (ex.: DAP 0.10 m a 30 m, reflectividade 0.3).
3. **`POST /api/simulations`** — disparar uma simulação (modo `monte_carlo`, `analytical` ou `synthetic_point_cloud`).
4. **`POST /api/reports`** — gerar relatório Markdown/JSON a partir do `simulation_id`.
5. **`POST /api/analysis/distance-sweep`** ou **`/dbh-sweep`** — varreduras de alcance/DAP.
6. **`POST /api/analysis/compare`** — comparar vários sensores sob condições idênticas.

### Endpoints disponíveis (`/api`)
| Método | Caminho | Descrição |
|---|---|---|
| GET/POST | `/sensors`, `/sensors/{id}` | CRUD de sensores |
| PUT/DELETE | `/sensors/{id}` | Atualizar (gera nova versão imutável) / excluir |
| GET | `/sensors/{id}/versions` | Listar snapshots de versão imutáveis (Regra 9) |
| GET/POST | `/scenarios`, `/scenarios/{id}`, PUT `/scenarios/{id}` | CRUD de cenários |
| POST | `/simulations` | Criar simulação (202, status `queued`) |
| GET | `/simulations/{id}` | Status do job |
| GET | `/simulations/{id}/results` | Resultado (200 completo / 409 se não concluído / 404 se desconhecido) |
| POST | `/analysis/distance-sweep` | Varredura de distância + alcances efetivos |
| POST | `/analysis/dbh-sweep` | Varredura de DAP (heatmap P_D=f(DAP,R)) |
| POST | `/analysis/compare` | Comparar sensores sob condições idênticas |
| POST/GET | `/reports`, `/reports/{id}` | Gerar/obter relatórios Markdown/JSON |
| POST | `/datasheets/extract`, `/datasheets/{id}/validate` | Ingestão/validação de datasheet |

### Rodar os testes
```bash
cd /opt/data/lidar_platform
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/unit/ -q
```
Execução atual: **245 testes, todos verdes.**

### Exemplo mínimo de fluxo (curl)
```bash
BASE=http://localhost:8000
# 1) sensor
curl -X POST $BASE/api/sensors -H 'Content-Type: application/json' -d '{
  "sensor_id":"hesai-qt64","sensor_type":"mechanical_spinning","manufacturer":"Hesai","model":"QT64","version":"1.0.0",
  "wavelength":{"value":905,"unit":"nm","origin":"SOURCE","status":"known"},
  "range":{"maximum":{"value":200,"unit":"m","origin":"SOURCE","status":"known"}},
  "scan":{"type":"mechanical_spinning","point_rate":{"value":600000,"unit":"Hz","origin":"SOURCE","status":"known"},
          "rotation_frequency":{"value":10,"unit":"Hz","origin":"SOURCE","status":"known"}},
  "validation":{"status":"validated"}}'
# 2) cenário
curl -X POST $BASE/api/scenarios -H 'Content-Type: application/json' -d '{
  "scenario_id":"tree-01","sensor_id":"hesai-qt64","environment":{"atmosphere":"clear"},
  "sensor_pose":{"position":[0,0,1.5],"orientation":{"yaw":0,"pitch":0,"roll":0}},
  "target":{"type":"cylinder","position":[30,0,0.5],"orientation":[0,0,1],"diameter":0.10,"reflectivity":0.3}}'
# 3) simulação
curl -X POST $BASE/api/simulations -H 'Content-Type: application/json' -d '{
  "scenario_id":"tree-01","mode":"monte_carlo","duration":0.1,
  "monte_carlo":{"enabled":true,"trials":100,"random_seed":42}}'
```

---

## 4. Como acessar a aplicação

Sendo uma **aplicação web local**, há duas formas principais:

1. **Local (recomendado p/ uso de engenharia):** rodar o `uvicorn` acima e abrir `http://localhost:8000/docs` no navegador — toda a API documentada e executável interativamente.
2. **Acesso remoto pela infra já existente do SilvaLab:** o usuário tem um VPS (Hostinger) com **Traefik** como proxy reverso e subdomínios sob `hankell.com.br`. O backend FastAPI pode ser publicado num subdomínio (ex.: `lidar.` ou `api.`) com label do Traefik apontando para o container/porta do backend, espelhando o que já é feito para o site `silvalab.hankell.com.br` (porta 8900) e para o FileBrowser `files.hankell.com.br` (porta 8899). O agente pode auxiliar nessa publicação sob demanda.

**Nota de segurança/Rodagem:** o store é em memória (MVP) — os dados são resetados quando o processo reinicia. Para persistência real, as fases 10+/D008 preveem arquivos JSON em `data/` com versões imutáveis por sensor (`<id>.v<version>.json`).

---

## 5. Como foi feito o desenvolvimento (incrementos e o que melhoraram)

A implementação seguiu o **PRD (Product Requirements Document)** e o **SCHEMAS/API Contract** (em `docs/`), com um log vivo em `PROGRESS.md`. Cada fase foi um **incremento verificável** (camada por camada), sempre com testes. A contagem de testes subiu de 0 → 236 → **245** adicionais com o último incremento.

### Trajetória dos incrementos (em ordem)

1. **Bootstrap / Regras de convenção** — baixou as specs, inicializou git/venv, escreveu `CONVENTIONS.md` (unidades SI, "nunca fabricar detecção", proveniência, estritura Pydantic) e `engineering-decisions.md` (decisões D001–D025 que resolvem ambiguidades das specs). *Melhoria:* alinhou todo código futuro às specs e registrou decisões para não serem relitigadas.

2. **Fase 1 — Modelos de domínio** (`models/`, 29 testes) — schemas Pydantic estritos do sensor/cenário/simulação/resultado + JSON Schemas + validação de limites. *Melhoria:* dados validados na borda, enums exatos da spec, rejeição de campos desconhecidos.

3. **Fase 2 — Motor geométrico** (`geometry/`, 43 testes) — transformações 4×4, alvos cilindro/caixa, interseção analítica raio-cilindro, tamanho angular, footprint do feixe, incidência. *Melhoria:* física da geometria validada contra soluções analíticas conhecidas.

4. **Fase 3 — Motor de varredura** (`scan/`, 15 testes) — 3 tipos de scanner, canais, pontos. *Melhoria:* padrões de varredura realistas e determinísticos.

5. **Fase 4 — Feixe/óptica + detecção + medição** (`physics/`, 27 testes) — overlap, intensidade de retorno, modelos de probabilidade de detecção (incl. `insufficient_data` — nunca fabrica), ruído de medição e conversão 1σ↔2σ↔95%. *Melhoria:* **transparência e ausência de falsa precisão** — desconhecido → insuficiente, não inventado.

6. **Fase 5-6 — Motor de simulação + Monte Carlo** (`simulation/`, 11 testes) — `SingleTrialEngine` e `MonteCarloEngine`, classificação, varredura de distância e alcances efetivos. *Melhoria:* simulação estocástica determinística e reprodutível, validação Nível 2 (P_d=0 → zero detecções; P_d=1 → todas detectadas).

7. **Fase 7-8 — Análise + adequação** (`analysis/`, 8 testes) — comparação de sensores, avaliação de suitability com critérios rastreáveis. *Melhoria:* resposta objetiva "o sensor serve para a aplicação?" com rastreabilidade critério-por-critério.

8. **Fase 9 — Backend API + ingestão** (`api/`, 17 testes) — FastAPI (health, CRUD sensores/cenários, jobs de simulação, análise), store em memória, ingestão de datasheet. *Melhoria:* tornou as fases 1-8 **utilizáveis via HTTP** (acesso web local).

9. **Fase 10 — Relatórios** (`reporting/`, 9 testes) — exportação JSON/CSV e relatório Markdown em 14 seções. *Melhoria:* saída pronta para apresentação/arquivamento dos resultados.

10. **Fase 11 — Fixture canônica ponta-a-ponta + integração** (`test_e2e.py`, 7 testes) — validação sintética Nível 2, pipeline completo, varredura e2e com CSV, determinismo MC, `insufficient_data`. *Melhoria:* garante que **todas as camadas funcionam juntas**, não só isoladas.

11. **Incrementos de fechamento de lacunas (#1–#9)** — modos analítico e nuvem de pontos sintética (§54); prioridade do modelo de detecção (§30–32); varredura de DAP (§44); API de relatórios (§60); contrato da API de simulação (§17–19); `PUT /scenarios` (§16); ingestão/validação de datasheet (§11–15); cobertura geométrica C_g e σ_R (§39–41); varredura de distância + comparação (§20/§22–23). Subiu o conjunto completo para **236 testes verdes**.

12. **Incremento final — Regra 9/10, §61 e §27** (245 testes) — o que acabamos de implementar:
    - **Versionamento imutável de sensor (Regra 9):** `PUT /sensors/{id}` agora preserva a versão antiga como snapshot imutável, resolve uma nova versão (usa a enviada ou incrementa a menor, ex.: `1.0.0 → 1.1.0`) e expõe `GET /sensors/{id}/versions`. Simulações **fixam a versão exata** do sensor usada no resultado (`sensor_version`).
    - **Retenção de seed (Regra 10, todos os modos):** o resultado de toda simulação agora registra a seed (`monte_carlo` usa a configurada; `analytical`/`pointcloud` registram `0`, que é a semente determinística fixa) — permitindo reproduzir qualquer execução.
    - **Registro de premissas (§61 / relação Simulação→Premissas):** novo `api/assumptions.py` com `AssumptionRegistry`; cada simulação registra as premissas canônicas e o resultado carrega seus ids (`result["assumptions"]`), cada uma resolvível para a descrição/razão.
    - **Guarda de dados insuficientes (§27):** `POST /simulations` agora valida se o sensor tem os parâmetros exigidos pelo modelo de detecção (ex.: `range.maximum`, `beam.horizontal_divergence`); se estiverem `unknown`/ausentes, responde `409 {"status":"insufficient_data","missing_parameters":[...]}` em vez de rodar com físico fabricado.

    *O que esse incremento melhorou:* **reprodutibilidade** (seed + versão fixa), **rastreabilidade** (premissas nomeadas) e **honestidade científica** (dados insuficientes → resposta explícita, nunca números inventados — alinhado às convenções do projeto).

---

## 6. Estado atual e próximos passos

- ✅ **245 testes verdes**, servidor FastAPI funcional, todos os 15 endpoints disponíveis.
- ⏳ **Fases 12 (UI web/visualização)** e **13 (README + verificação final)** pendentes no `PROGRESS.md` — são os próximos incrementos naturais.
- ⚠️ Lacunas conhecidas ainda abertas: persistência real (store em memória hoje), conclusão de alguns itens do envelope de erro (§25) e a UI de visualização.

Fontes na própria base: `PROGRESS.md` (log vivo), `CONVENTIONS.md` (regras), `docs/engineering-decisions.md` (decisões D001–D025) e as duas specs em `docs/`.