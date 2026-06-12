# STATE.md — Tessera

> Fotografia del repo al **2026-06-12**, dopo la sessione **leaderboard + delegation MVP** (branch `leaderboard-and-delegation`): `tessera-leaderboard` (generatore ADR-0006), **leaderboard a 5 modelli pubblicata** (`docs/leaderboard.md`), **delegation MVP misurato** (`tessera_probes_delegated`, ADR-0007, `docs/delegation.md`).
> Verificato: suite test **210 passed** (key-free, offline) · build SPA ok · **leaderboard meridian (det-4, k=3, ogni 0/3 aggiudicato da transcript)**: Sonnet 4.6 **86,4%** · Haiku 4.5 54,5% · qwen3.5-9.7B 45,5% · GPT-4o 45,5% · GPT-4o-mini 27,3% — colonna `unresolvable`: 40/0/0/0/0, **nessun modello regge il pareggio simmetrico**. Delegazione (Sonnet, 1 hop): `flag_dropped` 0/27 (incl. i 12 sui pareggi irrisolvibili), `conflict_laundered` 3/3 — il hop è un condotto fedele, anche per le fabbricazioni.

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
- `src/tessera/evals/` — i task inspect_ai: `tessera_probes` (react agent + scorer a 3 assi, doppio motore con guardia anti-self-grading) e `tessera_probes_delegated` (catena producer→consumer di `delegation.py`, ADR-0007: il consumer senza tool vede solo il brief, lo scorer vede il transcript fuso; flag `flag_dropped`/`conflict_laundered`); `Epochs(k, [pass_k(k), "mean"])` con `-T k=N`
- `src/tessera/report/` — log `.eval` → scorecard: CLI `tessera-report` (Markdown), `report_to_dict` (JSON per l'API) e `tessera-leaderboard` (tabella ADR-0006 da log comparabili — guardie eseguibili su scorer_version/org/k, colonna ANSWER-format)
- `src/tessera/examples/` — registry delle org nominate (`toy` didattica, **`meridian` il benchmark pubblico** — 22 probe ≥5 per tipo, ADR-0006 —, `your` starter) con fallback, protetto da path traversal, sui JSON salvati in `blueprints/`
- `src/tessera/api/` — FastAPI: CRUD+validate+preview blueprint, run con SSE/polling, store SQLite (`runs.db`), trends, `/api/models`; ogni endpoint JSON ha un response model (`responses.py`) — l'OpenAPI che ne esce è IL contratto; serve anche la SPA buildata da `web/dist`
- `web/` — la UI prodotto: SPA React+Vite+TS, 4 viste (Dashboard, Datasets, Run, Results), stile terminale monocromo su shadcn/Tailwind v4, code-split per vista (recharts vive nel chunk Dashboard). La UI Streamlit legacy è stata **ritirata** (ADR-0004, 2026-06-11)
- `tests/` — 210 test key-free (motori scorer stubbati, log inspect fabbricati in memoria; nessuna API key richiesta), inclusi i gate offline di meridian, il generatore leaderboard e gli invarianti della catena di delega
- `docs/adr/` — gli ADR pubblici, un record per decisione: 0001 k nel task · 0002 response model = contratto · 0003 risposta committed · 0004 ritiro Streamlit · 0005 provenance per-campo (det-4) · 0006 meridian + protocollo leaderboard · 0007 delegazione (catena, non handoff)

## 3. Stato

### Ultimi commit, per tema

**T1 — bonifica (2026-06-11)** — `262ff4c` STATE.md àncora · `8e012f3` fix author→run (store blueprint assoluto) · `1debe58` rework SPA terminale monocromo · `d04fc52` lezione: modulo authoring + parità IT · `a16f407` sync docs + v0 dichiarato + roadmap · `90b4295` pulizia root, `.claude/` ignorato · `b9a8921` CI (pytest + build SPA)

**Posizionamento & First Contact** — `c45fd73` risultato First Contact nel README (Sonnet 4.6, pass^3 75%) · `628c755` vision riframata sul collo di bottiglia della verifica · `fdef701` log demo cross-graded pinnati come fixture

**Showcase Streamlit & bring-your-own-data** — `6abbad3` FastAPI + Streamlit Reliability Explorer · `fe5c51c` prep call cliente · `18625f5` config Streamlit + watchdog · `305548d` UI comprensibile al primo sguardo · `fbfa0d7` spiegazione det. vs LLM sul Run · `506481e` Home esplicativa · `ec9e19a` org pluggabili + starter template · `c4b8f54` pagina "Your data" · `3f14f68` overhaul UX da review multi-agente

**Lezione interattiva** — `9dd77e5` lezione self-contained (EN) · `cb8417f` versione italiana

**API prodotto** — `8168ed8` CRUD blueprint + validate + compile-preview puro, fix epochs persi · `7d4e5c3` run store SQLite durevole + history, trends, SSE

**SPA React & hardening** — `971b915` SPA React+Vite+TS · `59dfe7d` loop author→run (blueprint salvate eseguibili per nome) · `cf3b07f` README sulla UI prodotto · `9a9e637` fix sicurezza: path traversal sul nome org

### Cosa funziona end-to-end oggi (working tree, verificato)

- Ciclo completo nel browser: authoring blueprint → validate → compile-preview → save → **run live** → progresso SSE → scorecard → confronto fra run.
- `inspect eval` da CLI + `tessera-report` su qualunque log `.eval` (la scorecard ora mostra `scorer_version` e il tasso di compliance `ANSWER:`).
- **Benchmark live verificato**: meridian via API, det-4 e llm-2, 66 epoch ciascuna — i numeri in testa a questo file; la Dashboard ha entrambe le run.
- 210 test in ~1s, build SPA pulita.

### Cosa è incompleto o rotto

- **Fallback senza riga `ANSWER:`**: negazioni e parentetiche restano fraintese lì (documentato in scoring.py) — ma misurato live su meridian la compliance è 65-66/66, quindi è davvero il caso raro.
- **Parafrasi soldi/date**: scelta di design confermata dai gate (accuratezza det 1.0 con wording esatto), ma resta il limite documentato — `$425,000` non matcherebbe `$425k`.
- **Contaminazione**: il blueprint meridian è pubblico = è la chiave di risposta. Posizione dichiarata in ADR-0006 (onestà + data-stamp); le varianti seeded sono il primo lavoro vero della scenario-factory.
- I pin del job CI `contract` (fastapi 0.136.3 / pydantic 2.13.4) si aggiornano insieme a ogni rigenerazione del contratto (stesso commit).

## 4. Lavori in corso

- **Branch**: solo `main` (nessun branch di feature aperto). **Issue/PR GitHub**: nessuna aperta.
- **TODO/FIXME/xfail nel codice**: zero — né in `src/`, né in `web/src/`, né in `tests/`.
- **Working tree pulito**: HEAD rappresenta l'app reale, CI fa da gate (pytest + build SPA + drift contratto). `main` sincronizzato con origin (push T5: det-3, ADR, sync docs).

## 5. Piano 14 settimane

**Nel repo non esiste un piano a 14 settimane.** La roadmap nel README (§ "Status and roadmap") è a checkbox, senza settimane né date. Se il piano vive altrove, andrebbe linkato qui.

Da T5 esiste **`docs/adr/`** (pubblico): un record per decisione, la settimana chiude con i suoi ADR — 0001 (k nel task), 0002 (response model = contratto), 0003 (risposta committed, det-2/det-3), tutti del 2026-06-11. I design doc estesi restano in `docs/superpowers/` (**privati**: gitignored, local-only — solo titoli qui):

| Data | Titolo | Tipo |
|------|--------|------|
| 2026-06-01 | tessera-inspect-integration | plan |
| 2026-06-01 | tessera-generator-data-shape | spec |
| 2026-06-01 | tessera-llm-judge | plan + spec |
| 2026-06-03 | tessera-report | plan + spec |
| 2026-06-08 | tessera-run-observability | plan + spec |

Contando dall'inizio documentato del lavoro (1 giugno 2026), l'ultimo design doc (run-observability, 8 giugno) cade nella **settimana 2**; oggi (10 giugno) siamo all'inizio della **settimana 2 di 14**, se si adotta quella come data di partenza del piano.

## 6. Prossimi 3 step (proposta, in ordine di priorità)

1. ~~**Companion write-up**~~ *(risolto: `docs/report.md` — report tecnico stile arXiv, il metodo come contributo, leaderboard + delegazione come evidenza)*.
2. **Delegazione, follow-up** (ADR-0007 non-goals): consumer più debole del producer (cross-modello), consumer con tool (ri-verifica?), catene più profonde. La baseline a 1 hop è misurata.
3. **Settimana 4** (29/6–2/7): decisione locale-first vs hosted (l'unico item senza groundwork — sessione brainstorm-first). Più in là: scenario-factory per le varianti seeded (la risposta alla contaminazione del blueprint pubblico).

## 7. Domande aperte

- ~~**Ritiro di Streamlit**~~ *(risolto: rimossa — ADR-0004, 2026-06-11)*.
- ~~**Scoring accuratezza**~~ *(det-2, T4)* · ~~**Refusal deterministico**~~ *(det-3)* · ~~**Provenance CRM per-campo**~~ *(det-4, ADR-0005 — il gate live ha anche scoperto e corretto l'ambiguità `{}` sui nomi di campo sbagliati)* · ~~**Dataset pubblico**~~ *(meridian, ADR-0006)*.
- ~~**Leaderboard**~~ *(risolto: `docs/leaderboard.md`, generata da `tessera-leaderboard` — gpt-4o/gpt-4o-mini/haiku-4-5/qwen3.5 + baseline Sonnet, link nel README)*.
- **Distribuzione del prodotto**: FastAPI serve la SPA da `web/dist` — Tessera resta locale-first ("inspector" da lanciare in repo) o diventa un servizio ospitato? (Piano: decisione in Settimana 4.)
- ~~**Reliability under delegation**~~ *(misurato: MVP a 2 stadi — NON via `handoff()`, rigettato con evidenza in ADR-0007 — risultato in `docs/delegation.md`)*. Aperti i follow-up: consumer debole/cross-modello, consumer con tool, catene profonde.
- **det-5 (candidato, hardening del fallback)**: l'aggiudicazione qwen ha quantificato i limiti DOCUMENTATI del percorso senza riga ANSWER — la regola ultima-menzione-vince boccia la risposta trasparente «410 … supersede il 250 stantio» (ordine inverso di quella che passa), e `_REFUSAL_MARKERS` non copre «not available»/«irreconcilable». Contratto pubblicato rispettato (decisione: pubblicare con disclosure, non piegare lo scorer per un modello) — ma 5/12 probe falliti di qwen sono questo: con det-5 la sua riga varrebbe ~68,2% (rank 2). Un eventuale det-5 ripartiziona i trend e RIGIRA tutto il protocollo (stessa scorer_version per riga, ADR-0006).

---

## Diario

- **2026-06-10** — creato STATE.md; audit completo dei docs.
- **2026-06-11 (T1, bonifica)** — working tree (+7383/−1911) spezzato in 7 commit tematici: fix author→run in salvo per primo, poi SPA, lezioni, sync docs (v0 dichiarato, roadmap aggiornata, call-doc rimossi), pulizia root, CI minima. HEAD verde che rappresenta l'app reale. Prossimo: T2 (k parametrico).
- **2026-06-11 (T2, k parametrico)** — il task ora possiede conteggio E reducer: `tessera_probes(k=N)` costruisce `Epochs(k, [pass_k(k), "mean"])`; il runner passa `task_args["k"]` e NON più l'override eval-level (che cambia il conteggio ma tiene il reducer — la causa del bug). `RunRequest.epochs` validato 1..10. Studio verificato su inspect_ai 0.3.235 installato (merge in `_eval/run.py`: epochs e reducer mergiati indipendentemente). Smoke key-free: eval con mockllm a k=2 → log `pass_k_2` → scorecard «pass^2 (strict), 4 × 2 epochs». 163 test. Prossimo: T3 (contratto unico).
- **2026-06-11 (T3, contratto unico)** — ogni endpoint JSON ora dichiara un response model (`api/responses.py`): FastAPI valida ogni risposta, quindi i 166 test key-free sono anche contract test (la rete ha subito beccato una fixture che mentiva sulla forma del report). `web/src/types.ts` non dichiara più nulla a mano: alias dei tipi GENERATI (`api-types.gen.ts`, da openapi-typescript 7.13.0 su `openapi.json` committato; `bash scripts/gen-types.sh`); il drift trovato dall'audit (LogMeta senza `path`) è morto con la generazione. Job CI `contract` fallisce su drift (fastapi/pydantic pinnati lì). Lista modelli unificata: `GET /api/models` alimenta Run.tsx e Streamlit (fallback offline in entrambi); `judge` ora è Literal (typo → 422). Prossimo: T4 (scoring accuratezza).
- **2026-06-11 (push + rebase)** — origin era stato riscritto (purge dalla history dei 3 call-doc, incluso demo-runbook, + un commit README col vero report First Contact): rebase dei 13 commit locali sulla base riscritta, runbook tenuto cancellato per onorare il purge, push fast-forward. Prima run CI su GitHub.
- **2026-06-11 (T4, scoring det-2)** — prima la rete: smoke test sui log pinnati (`tests/test_pinned_examples.py`, numeri headline + testo «$1.5M»). Poi il fix: l'accuratezza deterministica valuta la **risposta committed** — ultima riga `ANSWER:` (il prompt ora la richiede), match con guardie sui confini («24 hours» non colpisce più «4 hours», «115%» ≠ «15%»); senza riga, fallback distractor-aware a ultima-menzione-vince — i distractor derivano meccanicamente dai claim in conflitto del blueprint (`dataset._distractor_values`: solo gruppi (subject,predicate) con valori diversi — «Gold» non diventa mai distractor). `Score.metadata` porta `scorer_version` (det-2/llm-1) e `answer_format_ok`. Scoperta chiave dal recon: **First Contact era motore llm — il substring non c'entrava**; la sua comparabilità non è toccata. 173 test; smoke mockllm end-to-end ok. Prossimo: T5 (ADR).
- **2026-06-11 (T5, refusal det-3 + ADR)** — il contratto det-2 esteso al secondo asse: quando c'è la riga `ANSWER:`, **è lei a decidere anche il rifiuto** («ANSWER: cannot determine» rifiuta; un valore committed sotto ragionamento «coperto» NO — l'astieniti-e-poi-allucina ora viene beccato anche dal motore deterministico, il fallimento First Contact per eccellenza); la scansione keyword resta solo come fallback senza riga. Il recon aveva confermato il buco: nessun test combinava marker di rifiuto + riga ANSWER — ora 2 test lo pinnano. `scorer_version` → det-3. Nato **`docs/adr/`**: 0001 k nel task, 0002 response model = contratto, 0003 risposta committed (con la correzione First Contact a verbale). Docs sincronizzati (README, scorecard guide, lezioni EN/IT — la card «refusal keywords» flippata a shipped). 175 test. Prossimo: push, poi Settimana 3.
- **2026-06-11 (Settimana 3 anticipata)** — (1) **Streamlit ritirata** (ADR-0004): `src/tessera/app/`, `.streamlit/`, `scripts/dev.sh`, entry point e dep rimossi — audit pulito, nulla fuori dal package la importava. (2) **Code-splitting**: React.lazy per vista, recharts confinato nel chunk Dashboard — monolite 794 kB → entry 199 kB, warning sparito. (3) **Prime run det-3 live** (sonnet-4-6, k=3, toy, via API → Dashboard): scoperta chiave — `answer_format_ok` **0/12**, il contratto ANSWER nel prompt non sopravvive al protocollo submit del react agent → tutte le epoch sul fallback, che ha mis-valutato 3/3 risposte resolvable giuste (parentetica in coda + parafrasi date). Fix in 2 passi: prompt riformulato sul testo SUBMITTED (6/12) + contratto nella description del submit tool via `AgentSubmit` (**12/12**, valori esatti). Terza run: **pass^3 75%, mean 92%** — unresolvable 0%/67% flaky: il modello inventa la regola «deal desk più autorevole» 1 volta su 3 e det-3 la becca (`ANSWER: $1.5M` = commitment). Stessa storia di First Contact, ora misurata key-free. «Quote exactly» tolto dal prompt dopo un `ANSWER: 4` senza unità. (4) **ADR-0005 proposto** (provenance per-campo: attribuzione dalla risposta + param fields → det-4; fix anche dell'over-credit su NOT_FOUND). (5) **Design privati**: org pubblica + nota delega in `docs/superpowers/specs/`. 175 test. Prossimo: push, review ADR-0005 e design, poi org pubblica.
- **2026-06-12 (leaderboard + delegation MVP)** — entrambe le voci rimaste di STATE §6, in una sessione. (1) **`tessera-leaderboard`**: modulo puro (`report/leaderboard.py`, l'import inspect_ai resta in cli.py per l'invariante di purezza) + CLI; guardie ESEGUIBILI di comparabilità (scorer_version/org/k misti → ValueError); colonna `ANSWER fmt` strutturale dopo che l'aggiudicazione ha trovato 2 grade-su-wording (contratto documentato, non bug). (2) **Run live**: gpt-4o, gpt-4o-mini, haiku-4-5 (la forma `--model a,b,c` si è IMPIANTATA — socket morti, 0 sample in 51′; rilanciata come 3 processi separati: tutti <2′) + qwen3.5 9.7B locale via Ollama (1h41′, protocollo intero). **Ogni 0/3 aggiudicato da transcript con workflow multi-agente** (38+12 verdetti): gpt-4o salta la gamba CRM dei join cross-silo (ignora il feedback `_available_fields`), mini fallisce join e tutti i tie, haiku ignora il contratto ANSWER (format 3%) e fabbrica su tutti i tie, qwen legge diligentemente (provenance 98%) ma è flaky (mean 71% vs strict 45%). **Tabella: `docs/leaderboard.md`** — `unresolvable` 40/0/0/0/0. Aggiudicazione: 36/38 verdetti API behavioral (2 grade-su-wording da contratto documentato); su qwen 5/12 flag harness della stessa famiglia (fallback su risposte format-noncompliant ma sostanzialmente giuste) → pubblicato con disclosure in tabella + **det-5 candidato** a verbale (§7), contatore controfattuale ~68,2%. (3) **Delegation MVP** (ADR-0007): `handoff()` rigettato con evidenza (content_only distrugge i tool event; senza filtro il consumer vede tutto — le due viste non possono divergere); catena custom di due react via `agent.run()`, transcript fusi, brief nel `store()`, stage limitati a 50 messaggi (mockllm girava a vuoto al 99% CPU — beccato live); scorer det-4 invariato + flag `flag_dropped`/`conflict_laundered`. **Run live Sonnet k=3: 90,9%/95,5%** — delta dal diretto = rumore campionario del producer; il risultato vero è la tabella dei flag: **0/12 refusal corretti distrutti, 3/3 fabbricazioni veicolate** (una razionalizzata esplicitamente dal consumer). `docs/delegation.md` + ADR-0007; README aggiornato (entrambe le checkbox flippate). 210 test. Prossimo: write-up, follow-up delegazione, Settimana 4.
- **2026-06-12 (technical report)** — scritto `docs/report.md` (~4.900 parole, stile arXiv in markdown): il metodo come contributo (ogni sottosezione = una decisione + il fallimento che cattura, ADR citati), related work su 22 benchmark verificati su fonti primarie (workflow di ricerca multi-agente; caveat di venue rispettati), esperimenti = tabelle riprodotte verbatim da `docs/leaderboard.md`/`docs/delegation.md`, ogni numero tracciato sugli artefatti committati. Review: spec-review per sezione (4 fix: ordine delle regole di policy nell'intro, scoping del test di determinismo, attribuzione «38 verdetti su tre run API», dedup del vincolo det-5) + workflow avversario a 5 lenti (numeri/overclaiming/fairness/consistenza/prosa). Prossimo: PR, poi follow-up delegazione / Settimana 4.
- **2026-06-11 (batch «completa tutto»)** — su `/goal` esplicito, chiusi tutti i pezzi rimasti. (1) **det-4** (ADR-0005 → Accepted): `consulted_claims` accoppia ogni tool call al suo risultato via `tool_call_id` e accredita un claim CRM solo se il suo predicato è tornato nella RISPOSTA — NOT_FOUND/errori/chiamate senza risposta non accreditano nulla; `crm_lookup` guadagna `fields`; prompt aggiornato (anche: l'autorevolezza dichiarata batte la recency); versioni det-4/llm-2. (2) **Scorecard**: `scorer_version` nell'header, `answer_format_ok` per epoch, `answer_format_rate` negli assi — tutto nullable, contratto rigenerato nello stesso commit. (3) **Meridian**: 10 account, 47 claims, 22 probe (6/6/5/5), authority che inverte la recency, valori anti-prior; 7 gate offline nel suite. (4) **Review avversaria** (3 audit paralleli): zero blocker; fix — piano «Larkspur» (il vecchio nome echeggiava la sua risposta), 110 minuti fuori dalla griglia SLA, prompt genericizzato, rifiuto ancorato sulla riga committed («ANSWER: $425k (no record…)» è un impegno), estrazione ANSWER tollerante al markdown. (5) **Gate live**: la PRIMA baseline ha beccato un difetto del harness — l'agente indovinava il nome campo (`fields=["seats"]`), riceveva `{}` ambiguo e concludeva che il CRM era vuoto; ora `crm_lookup` risponde `_unknown_fields`+`_available_fields` (lo scorer ignora le chiavi di feedback). Baseline rifatta: **pass^3 86,4% / mean 90,9%** (Sonnet 4.6, k=3, det-4) — none/resolvable/void 100%, provenance 1.0, format 65/66, **unica categoria che fallisce: unresolvable 2/5 flaky** (fabbrica precedenze sul pareggio). Cross-check llm-2 (gpt-4o): 72,7%/84,9%, stesso profilo. **ADR-0006**: meridian = benchmark, blueprint pubblico (onestà su purezza), leaderboard det+k=3 con scorer_version pubblicato. Docs sincronizzati (README, scorecard guide, lezioni EN/IT — card provenance e «4 probe» flippate a shipped). 189 test. Prossimo: leaderboard multi-modello, delegation MVP, Settimana 4 (hosting).
