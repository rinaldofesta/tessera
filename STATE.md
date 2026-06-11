# STATE.md — Tessera

> Fotografia del repo al **2026-06-10** (branch `main`, HEAD `9a9e637`).
> Verificato: suite test **159 passed in 0.74s** (key-free, offline) · build SPA ok (1.23s).

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
- `src/tessera/evals/` — il task inspect_ai: react agent + scorer a 3 assi, doppio motore (deterministico / LLM-judge con guardia anti-self-grading), `Epochs(3, [pass_k(3), "mean"])`
- `src/tessera/report/` — log `.eval` → scorecard: CLI `tessera-report` (Markdown) e `report_to_dict` (JSON per l'API)
- `src/tessera/examples/` — registry delle org nominate (`toy`, `your`) con fallback, protetto da path traversal, sui JSON salvati in `blueprints/`
- `src/tessera/api/` — FastAPI: CRUD+validate+preview blueprint, run con SSE/polling, store SQLite (`runs.db`), trends; serve anche la SPA buildata da `web/dist`
- `src/tessera/app/` — UI Streamlit **legacy** (stesso API; sostituita da `web/`, ancora lanciata da `scripts/dev.sh`)
- `web/` — la UI prodotto: SPA React+Vite+TS, 4 viste (Dashboard, Datasets, Run, Results), stile terminale monocromo su shadcn/Tailwind v4
- `tests/` — 159 test key-free (motori scorer stubbati, log inspect fabbricati in memoria; nessuna API key richiesta)

## 3. Stato

### Ultimi 20 commit, per tema

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

- **A HEAD il loop author→run sulle blueprint salvate è rotto**: inspect_ai cambia cwd alla dir del task e lo store relativo `blueprints/` non si risolve ("unknown org"). Il fix (`_job_env()` in `runner.py` + 2 test TDD) esiste **solo nel working tree, non committato**.
- **Enorme WIP non committato**: 20 file, +7383/−1911 — rework SPA (shadcn, Tailwind v4, componenti nuovi), fix runner, lezioni EN/IT aggiornate. L'ultimo commit non rappresenta l'app attuale.
- **k è hardcoded a 3** in `src/tessera/evals/task.py:52` (`Epochs(3, [pass_k(3), "mean"])`): il selettore epochs della UI funziona solo per k=3; con k<3 il reducer `pass_k_3` dà errore.
- **`web/src/types.ts` è scritto a mano** (specchio manuale del contratto FastAPI; il file stesso rimanda la generazione da OpenAPI).
- **File spuri a root, non ignorati**: `hello.py`, `coinflip.py` (task tutorial inspect_ai), `scorecard.md` (output generato), `__pycache__/` derivato, più `.claude/` non tracciato.
- Warning di build: chunk JS da 794 kB (>500 kB) — nessun code-splitting.
- Liste modelli duplicate a mano in due UI (`app/streamlit_app.py` e `web/src/views/Run.tsx`): drifteranno.

## 4. Lavori in corso

- **Branch**: solo `main` (nessun branch di feature aperto). **Issue/PR GitHub**: nessuna aperta.
- **TODO/FIXME/xfail nel codice**: zero — né in `src/`, né in `web/src/`, né in `tests/`.
- Il vero lavoro in corso è il **working tree non committato** descritto sopra: rework SPA + fix runner + lezioni. Va spezzato in commit tematici (il fix runner per primo: a HEAD c'è un bug noto).

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

1. **Committare il working tree** in commit tematici, partendo dal fix `_job_env()` + test (a HEAD il loop author→run è rotto: è l'unico bug noto in produzione locale); poi rework SPA, poi lezioni. Nello stesso giro: cancellare `hello.py`/`coinflip.py`/`scorecard.md` o ignorarli, e aggiungere `.claude/` al `.gitignore`.
2. **Rendere k parametrico**: derivare il reducer da `epochs` richiesto (oggi `pass_k(3)` fisso in `task.py`) così il selettore k della UI è onesto per k≠3 e il report non deve "indovinare" k dal log.
3. **Generare `web/src/types.ts` dall'OpenAPI di FastAPI** (il file stesso lo dichiara come passo futuro): elimina il drift silenzioso fra schemi Python e SPA. Subito dopo, in ordine di valore: smoke test sui log pinnati `examples/*.eval` e fix del substring over-credit nello scorer di accuratezza.

## 7. Domande aperte

- **Ritiro di Streamlit**: due UI sullo stesso API; la legacy (`src/tessera/app/`) non ha test e `scripts/dev.sh` lancia ancora quella. Si rimuove, o resta come reference?
- **Scoring accuratezza**: il match a substring sovra-accredita (la risposta giusta dentro una frase sbagliata passa). Estrazione strutturata, judge-only, o exact-match normalizzato?
- **Refusal deterministico**: oggi è keyword-based — quanto irrobustirlo prima del dataset pubblico?
- **Provenance CRM**: il credito è per record intero, non per campo/subject — serve granularità maggiore per org realistiche?
- **Dataset pubblico + leaderboard** (roadmap README): quale org di riferimento? `toy` (4 probe) è dichiaratamente minima; `initech` è nata come esercizio. Va progettata l'org "pubblica".
- **Distribuzione del prodotto**: FastAPI serve la SPA da `web/dist` — Tessera resta locale-first ("inspector" da lanciare in repo) o diventa un servizio ospitato?
- **Reliability under delegation** (agente-che-consuma-agente, in roadmap): quando parte e con quale design? È il track nuovo senza alcun doc di design.
