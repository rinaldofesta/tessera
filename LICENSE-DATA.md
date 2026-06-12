# Data license — CC-BY-4.0

The **synthetic datasets** in this repository are available under
[Creative Commons Attribution 4.0 International (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/),
in addition to the code license (Apache-2.0, see [LICENSE](LICENSE)).

How the two licenses divide the repository:

- The org definition files in `src/tessera/examples/` (`toy_org.py`,
  `meridian_org.py`, `your_org.py`) are **dual-licensed**: as Python source they
  are Apache-2.0 like the rest of the code; the blueprint *content* they express —
  claims, probes, expected answers, the meridian answer key — is additionally
  available under CC-BY-4.0. The registry module (`__init__.py`) is code only,
  Apache-2.0.
- Blueprint JSON exported from those orgs (e.g. through the API's blueprint store)
  and the artifacts the compiler materializes into its **output directory**
  (`<out>/crm/db.json`, `<out>/docs/*.md`, `<out>/manifest.json`) are data,
  CC-BY-4.0. (This does not refer to this repository's own `docs/` directory,
  which is documentation under Apache-2.0.)
- The pinned example logs and reports in [`examples/`](examples/) are data,
  CC-BY-4.0.

Attribution: **"Tessera (Rinaldo Festa), https://github.com/rinaldofesta/tessera"**.

All of it is synthetic — generated for this benchmark, describing organizations that
do not exist. No real client or company data enters the public datasets, ever
(see "Integrity and limitations" in the [README](README.md)).
