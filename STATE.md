# STATE.md — Tessera

> Fotografia del repo al **2026-06-11**, dopo T1 (bonifica) e T2 (k parametrico) (branch `main`).
> Verificato: suite test **163 passed** (key-free, offline) · build SPA ok · smoke end-to-end k=2 via mockllm · CI attiva.

---

## 1. In parole semplici

Tessera misura se un agente AI enterprise è **affidabile** quando la conoscenza aziendale è frammentata, contraddittoria e sparsa in silos raggiunti via MCP.
Scrivi un **Blueprint** — claims (fatti atomici, uno per silo) + probes (domande-test con comportamento atteso) — e un compilatore deterministico lo trasforma in una finta organizzazione: un CRM (`db.json`) e documenti prose, più un `manifest.json` che mappa ogni claim alla sua posizione.
Un agente inspect_ai interroga quell'organizzazione con tool MCP e viene valutato su **3 assi**: accuratezza, **provenance** (sempre meccanica: tool call confrontate col manifest, mai giudicate da un modello) e **rifiuto corretto** quando i dati sono irreconciliabili — il tutto ripetuto k volte con **pass^k severo** (giusto a ogni ripetizione, o fallito).
Il risultato che giustifica tutto: al First Contact Sonnet 4.6 ha fatto 100% su accuratezza e provenance, ma sul conflitto irrisolvibile **ha inventato una regola di business pur di non rifiutare**, 3 volte su 3.
Oggi intorno all'eval c'è un prodotto locale: API FastAPI + SPA React per autorare dataset, lanciare run live e leggere/confrontare scorecard.

## 2. Architettura attuale

- `src/tessera/models.py` — modelli Pydantic (Blueprint, Claim, Probe) con i validatori di coerenza (refuse⇒answer null, resolvable⇒resolution_rule, void⇒no references, ecc.)
- `src/tessera/compiler.py` — Blueprint → `crm/db.json` + `docs/*.md` + `manifest.json`, deterministico e puro (`build_artifacts` alimenta anche il preview dell'API)
- `src/tessera/silos/` + `src/tessera/mcp/` — layer di lettura puro + due server MCP stdio (`crm_lookup`; `docs_search`/`docs_get_file`)
- `src/tessera/evals/` — il task inspect_ai: react agent + scorer a 3 assi, doppio motore (deterministico / LLM-judge con guardia anti-self-grading), `Epochs(k, [pass_k(k), "mean"])` con `-T k=N`
- `src/tessera/report/` — log `.eval` → scorecard: CLI `tessera-report` (Markdown) e `report_to_dict` (JSON per l'API)
- `src/tessera/examples/` — registry delle org nominate (`toy`, `your`) con fallback, protetto da path traversal, sui JSON salvati in `blueprints/`
- `src/tessera/api/` — FastAPI: CRUD+validate+preview blueprint, run con SSE/polling, store SQLite (`runs.db`), trends; serve anche la SPA buildata da `web/dist`
- `src/tessera/app/` — UI Streamlit **legacy** (stesso API; sostituita da `web/`, ancora lanciata da `scripts/dev.sh`)
- `web/` — la UI prodotto: SPA React+Vite+TS, 4 viste (Dashboard, Datasets, Run, Results), stile terminale monocromo su shadcn/Tailwind v4
- `tests/` — 159 test key-free (motori scorer stubbati, log inspect fabbricati in memoria; nessuna API key richiesta)

## 3. Stato

### Ultimi commit, per tema

**T1 — bonifica (2026-06-11)** — `262ff4c` STATE.md àncora · `8e012f3` fix author→run (store blueprint assoluto) · `1debe58` rework SPA terminale monocromo · `d04fc52` lezione: modulo authoring + parità IT · `a16f407` sync docs + v0 dichiarato + roadmap · `90b4295` pulizia root, `.claude/` ignorato · `b9a8921` CI (pytest + build SPA)

**Posizionamento & First Contact** — `c45fd73` risultato First Contact nel README (Sonnet 4.6, pass^3 75%) · `628c755` vision riframata sul collo di bottiglia della verifica · `fdef701` log demo cross-graded pinnati come fixture

**Showcase Streamlit & bring-your-own-data** — `6abbad3` FastAPI + Streamlit Reliability Explorer · `fe5c51c` prep call Dedalo · `18625f5` config Streamlit + watchdog · `305548d` UI comprensibile al primo sguardo · `fbfa0d7` spiegazione det. vs LLM sul Run · `506481e` Home esplicativa · `ec9e19a` org pluggabili + starter template · `c4b8f54` pagina "Your data" · `3f14f68` overhaul UX da review multi-agente

**Lezione interattiva** — `9dd77e5` lezione self-contained (EN) · `cb8417f` versione italiana

**API prodotto** — `8168ed8` CRUD blueprint + validate + compile-preview puro, fix epochs persi · `7d4e5c3` run store SQLite durevole + history, trends, SSE

**SPA React & hardening** — `971b915` SPA React+Vite+TS · `59dfe7d` loop author→run (blueprint salvate eseguibili per nome) · `cf3b07f` README sulla UI prodotto · `9a9e637` fix sicurezza: path traversal sul nome org

### Cosa funziona end-to-end oggi (working tree, verificato)

- Ciclo completo nel browser: authoring blueprint → validate → compile-preview → save → **run live** → progresso SSE → scorecard → confronto fra run. Provato con l'org `initech`: probe `authority_wins` 3/3.
- `inspect eval` da CLI + `tessera-report` su qualunque log `.eval`.
- 159 test in 0.74s, build SPA pulita.

### Cosa è incompleto o rotto

- **`web/src/types.ts` è scritto a mano** (specchio manuale del contratto FastAPI; il file stesso rimanda la generazione da OpenAPI). → T3
- **Scoring accuratezza a substring**: sovra-accredita (la risposta giusta dentro una frase sbagliata passa). → T4
- Warning di build: chunk JS da 794 kB (>500 kB) — nessun code-splitting.
- Liste modelli duplicate a mano in due UI (`app/streamlit_app.py` e `web/src/views/Run.tsx`): drifteranno. → T3

## 4. Lavori in corso

- **Branch**: solo `main` (nessun branch di feature aperto). **Issue/PR GitHub**: nessuna aperta.
- **TODO/FIXME/xfail nel codice**: zero — né in `src/`, né in `web/src/`, né in `tests/`.
- **Working tree pulito** dopo la bonifica T1: HEAD rappresenta l'app reale, CI fa da gate (pytest + build SPA). Push verso origin da fare.

## 5. Piano 14 settimane

**Nel repo non esiste un piano a 14 settimane.** Nessuna cartella `adr/`; la roadmap nel README (§ "Status and roadmap") è a checkbox, senza settimane né date. Se il piano vive altrove, andrebbe linkato qui.

Il ruolo degli ADR è svolto dai design doc in `docs/superpowers/` (**privati**: gitignored, local-only — solo titoli qui):

| Data | Titolo | Tipo |
|------|--------|------|
| 2026-06-01 | tessera-inspect-integration | plan |
| 2026-06-01 | tessera-generator-data-shape | spec |
| 2026-06-01 | tessera-llm-judge | plan + spec |
| 2026-06-03 | tessera-report | plan + spec |
| 2026-06-08 | tessera-run-observability | plan + spec |

Contando dall'inizio documentato del lavoro (1 giugno 2026), l'ultimo design doc (run-observability, 8 giugno) cade nella **settimana 2**; oggi (10 giugno) siamo all'inizio della **settimana 2 di 14**, se si adotta quella come data di partenza del piano.

## 6. Prossimi 3 step (proposta, in ordine di priorità)

1. **T3 — contratto unico** (mar 16/6): generare `web/src/types.ts` dall'OpenAPI di FastAPI con check anti-drift in CI; unificare la lista modelli duplicata (Streamlit / Run.tsx) in un'unica fonte.
2. **T4 — scoring accuratezza** (mer 17/6): prima lo smoke test sui log pinnati `examples/*.eval` (rete di sicurezza), poi la mattina di design: estrazione strutturata vs exact-match normalizzato vs judge-only, guardando gli scorer di inspect_evals. Nota: cambiare lo scorer invalida la comparabilità col First Contact (pass^3 75% era a substring) — versionare lo scorer e re-misurare, da mettere nell'ADR di giovedì.
3. **T5 — hardening + ADR** (gio 18/6): valutazione del refusal keyword-based; ADR della settimana (decisione scoring + k parametrico — incluso il perché k vive nel task: un override eval-level cambia il conteggio ma non il reducer).

## 7. Domande aperte

- **Ritiro di Streamlit**: due UI sullo stesso API; la legacy (`src/tessera/app/`) non ha test e `scripts/dev.sh` lancia ancora quella. Si rimuove, o resta come reference?
- **Scoring accuratezza**: il match a substring sovra-accredita (la risposta giusta dentro una frase sbagliata passa). Estrazione strutturata, judge-only, o exact-match normalizzato?
- **Refusal deterministico**: oggi è keyword-based — quanto irrobustirlo prima del dataset pubblico?
- **Provenance CRM**: il credito è per record intero, non per campo/subject — serve granularità maggiore per org realistiche?
- **Dataset pubblico + leaderboard** (roadmap README): quale org di riferimento? `toy` (4 probe) è dichiaratamente minima; `initech` è nata come esercizio. Va progettata l'org "pubblica".
- **Distribuzione del prodotto**: FastAPI serve la SPA da `web/dist` — Tessera resta locale-first ("inspector" da lanciare in repo) o diventa un servizio ospitato?
- **Reliability under delegation** (agente-che-consuma-agente, in roadmap): quando parte e con quale design? È il track nuovo senza alcun doc di design.

---

## Diario

- **2026-06-10** — creato STATE.md; audit completo dei docs.
- **2026-06-11 (T1, bonifica)** — working tree (+7383/−1911) spezzato in 7 commit tematici: fix author→run in salvo per primo, poi SPA, lezioni, sync docs (v0 dichiarato, roadmap aggiornata, call-doc rimossi), pulizia root, CI minima. HEAD verde che rappresenta l'app reale. Prossimo: T2 (k parametrico).
- **2026-06-11 (T2, k parametrico)** — il task ora possiede conteggio E reducer: `tessera_probes(k=N)` costruisce `Epochs(k, [pass_k(k), "mean"])`; il runner passa `task_args["k"]` e NON più l'override eval-level (che cambia il conteggio ma tiene il reducer — la causa del bug). `RunRequest.epochs` validato 1..10. Studio verificato su inspect_ai 0.3.235 installato (merge in `_eval/run.py`: epochs e reducer mergiati indipendentemente). Smoke key-free: eval con mockllm a k=2 → log `pass_k_2` → scorecard «pass^2 (strict), 4 × 2 epochs». 163 test. Prossimo: T3 (contratto unico).
