    # **HEP Analysis Agent — Environment & RL Handover Plan**

**Date:** October 19, 2026 · **Author:** @Chengxi Yang

## **1\. Purpose and Context**

The goal is an open-weight LLM agent, trained with reinforcement learning (RL), that designs ATLAS or CMS physics analyses by editing configuration files of a directed acyclic graph (DAG) analysis framework. The first deliverable is the environment the agent works in; training comes after it is built, tested, and baselined.

The core idea for data: a small number of human-made analyses are not used as training examples directly. They are ported into the framework and used as **oracles** that generate thousands of verifiable tasks (perturbations, injected bugs, injected signals, and sensitivity optimization).

### **Decisions Made with the Project Owner**

* **Config-only agent.** The agent designs the analysis by editing configuration files. It may run code only to inspect data, read-only. It never writes analysis code.  
* **DAG framework.** Every analysis is a standardized configuration compiled into a DAG of typed nodes, executed with content-addressed caching.  
* **Open data only.** The project uses public ATLAS Open Data (CC0) first, with CMS Open Data as a possible later second experiment. Consequently, there is no self-hosting constraint, and the environment, task set, and trained model can be released publicly.  
* **RL with verifiable rewards.** Rewards come from numeric checks against oracle outputs (including dense node-level progress in early tiers) or from expected sensitivity under hard guardrails on a held-out Monte Carlo (MC) split—never from LLM judges.  
* **SFT is optional.** Teacher-trajectory supervised fine-tuning (SFT) is distillation. Skip it if a strong base model has non-zero $pass@k$ on the easiest task tier. If the failures are schema or format errors, prefer format-only SFT on $(spec,config)$ pairs produced by the task generators.  
* **Environment first, Quick Demo early.** No RL training starts before the environment passes golden tests, red-teaming, and a baseline run. However, a **2-week Quick Demo vertical slice (v0.1)** runs first on a single pre-skimmed analysis to validate the schema, expression engine, and tool usability before scaling out batch production.

## **2\. Open Data Scope**

**Decision (October 17, 2026):** ATLAS 2015–16 PHYSLITE is the first experiment. CMS 2016 NanoAOD can follow once the schema is proven experiment-agnostic.

| Dimension | ATLAS Open Data | CMS Open Data |
| :---- | :---- | :---- |
| **Collision data** | 2015–16 $pp$ at $13 TeV$, $36{ fb}^{-1}$, released July 2024 | 2016 $pp$ at $13 TeV$ in NanoAOD, released 2024; 2015 in MiniAOD; partial 2017 release announced |
| **Format** | PHYSLITE: pre-calibrated xAOD, readable with uproot (plus pre-skimmed education/research ntuples for rapid prototyping) | NanoAOD: flat ROOT trees, no CMSSW needed |
| **Systematics** | Produced with public ATLAS AnalysisBase software; dedicated systematic-variation MC samples exist | Depend on which correction inputs the open-data release provides; not yet verified |
| **Metadata** | atlasopenmagic API | Portal records via cernopendata-client |
| **Ready reference pipelines** | AGC $H\rightarrow Z{Z}^{*}\rightarrow 4ℓ$ (ServiceX, coffea, cabinetry, pyhf); education notebooks ($H\rightarrow \gamma \gamma$, $W/Z$, ) | AGC  on 2015 data (coffea, cabinetry) |
| **Extras** | $12.8\times {10}^{9}$generated events in HepMC for truth-level tasks | PocketCoffea and columnflow read NanoAOD natively |
| **Known gaps** | No full track collections, so no long-lived-particle searches | Systematic inputs for open data unverified |

### **Why ATLAS First**

The systematics path is well-defined (dedicated variation samples plus AnalysisBase), metadata comes from a single API (atlasopenmagic), objects are pre-calibrated, and the HepMC samples support additional truth-level tasks. The cost is an AnalysisBase processing stage in Step 1.2 to produce flat Parquet ntuples with systematic variations (PhysLiteToOpenData, the C++ framework that skims PHYSLITE into flat ntuples, serves as the starting template). **For the Quick Demo (Section 4\)**, we bypass AnalysisBase initially by converting existing pre-skimmed AGC / ATLAS Open Data ntuples directly to Parquet.

### **Implications of Open Data**

* **No self-hosting requirement.** Cloud sandboxes through Harbor and hosted tracing are allowed.  
* **Oracles are public pipelines.** Reference analyses are the Analysis Grand Challenge (AGC) pipelines, open-data notebooks, and published 2015–16 results, re-implemented as framework configs by the team.  
* **Contamination risk.** Base models may have seen these notebooks and numbers during pretraining, so training and evaluation rely on perturbed and injected variants (see Section 8).  
* **License.** CC0, with citation of the datasets requested; cite every dataset record used.

**Primary Data Sources:**

* ATLAS Open Data for Research (CDS Record 2921349\)  
* ATLAS PHYSLITE MC Record (CERN Open Data Record 80015\)  
* DPHEP Global Report 2026 (arXiv:2607.06775)  
* ATLAS HepMC Generation Data (arXiv:2605.12229)  
* CMS NanoAOD Getting Started & 2016 NanoAOD Record (CERN Open Data Record 30521\)  
* CMS Open Data at 10 Years (EPS-HEP 2025\)  
* IRIS-HEP Analysis Grand Challenge Repository &  Pipeline Documentation

## **3\. System Architecture & Design Principles**

Everything sits behind a single Model Context Protocol (MCP) tool server: physicists, frontier agents, and the RL trainer reach the analysis exclusively through this server.

\[embed: node/769093a4-287f\]

Base production fills the data layer once, offline, sorted canonically by (runNumber, eventNumber). During an episode, each run call compiles the configuration and executes only uncached DAG nodes; submit sends the outputs to the verifiers (evaluated against held-out splits where applicable), whose reward returns to whichever consumer started the episode.

### **Design Principles and Non-Negotiables**

These constraints came out of the architectural design discussion. Changing any of them requires sign-off from the project owner:

1. **Seconds, not hours.** A run call on the dev tier must return in seconds (target $<2 s$ warm cache, $<10 s$ cold). RL requires on the order of ${10}^{4}$ tool calls per training step, so latency drives every design choice.  
2. **Freeze the expensive part.** Object calibration and systematic variations are computed once in offline base production. Inside the RL loop, the DAG performs only fast columnar operations on Parquet files: object filtering and combinatorics, event defines, selections, weights, histograms, and fits.  
3. **Blinding and holdout splits are enforced by data mounts, not by config.** 

* **Blinding:** Real-data blinded phase space (plus a safety buffer where region boundaries are tunable) is removed from the agent's data view before the episode starts. The agent can never set or unset blinding itself.  
* **Holdout MC Split (Dev-Explore vs. Dev-Verify):** For design and optimization tasks (T4), the dev MC is partitioned into two disjoint splits: Dev-Explore (mounted for inspect and run) and Dev-Verify (never mounted inside the sandbox; used exclusively by submit verifiers). This prevents the agent from running Python in inspect to scan MC arrays, isolate statistical spikes, and hardcode overfitted cuts into edit\_config.

4. **The agent cannot reach reference outputs.** Oracle references and Dev-Verify splits live outside the sandbox. Inspection code (inspect) is stateless, read-only, CPU-time-capped, and nothing it writes feeds the DAG.  
5. **Content-addressed, source-aligned shared cache.** Every node is keyed by a Merkle hash of its canonical config plus upstream hashes, and the cache is shared across all rollouts. Event selection masks are cached as **source-aligned compressed bitmaps (numpy.packbits)** over canonically sorted rows so combining upstream cuts is an $O(1)$ bitwise AND.  
6. **Errors are instructions.** Every validation or runtime error states what is wrong, the exact dotted path in the config, and the valid options.  
7. **Small observations.** Tools return compact summaries and output handles; detailed tables are fetched by ID. Every observation has a hard token budget.  
8. **One environment, three consumers.** Physicists (via an MCP client), frontier agents (via the evaluation harness), and the RL loop use the identical tool server, prompts, AGENTS.md, skills, and context policy. What is trained is what is deployed.  
9. **Extend the framework, not the agent.** When a human analysis cannot be expressed in the schema, add a vetted operator or declarative combinatoric node type. Never give the agent a code escape hatch.  
10. **Determinism and provenance.** Pinned container image, fixed seeds, canonical row ordering, and stable reductions. Every reward is traceable to image digest, schema version, task-set version, data-tier version, and model checkpoint.

**Maturity & Usability Rule:** Prefer mature, community-validated tools with zero daemon overhead for local R\&D and demos (e.g., pure pyarrow \+ awkward over distributed schedulers inside a worker, Python ast expression validation over custom parser generators, and diskcache locally before Redis/S3). A less mature tool is allowed only behind our own thin interface so it can be swapped without touching the rest of the system.

## **4\. Quick Demo Track (2-Week Vertical Slice — v0.1)**

To demonstrate end-to-end usability quickly and validate the schema before running multi-analysis AnalysisBase batch jobs, execute this lightweight vertical slice first:

11. **Data Slice:** Take **one analysis** (AGC / ATLAS Open Data $H\rightarrow Z{Z}^{*}\rightarrow 4ℓ$ pre-skimmed ntuples), convert a $5%$ dev slice directly to canonically sorted Parquet (Dev-Explore and Dev-Verify), and write a minimal Pydantic-validated YAML metadata catalog for those samples.  
12. **Schema & AST Engine:** Implement Pydantic Schema v0 with named dictionary blocks (regions, objects, defines), a Python ast expression validator (whitelisted AST nodes \+ vector Lorentz operators), and a graphlib topological executor backed by local diskcache and numpy.packbits bitmaps.  
13. **Histogram & Fit:** Connect pyarrow $\rightarrow$ awkward $\rightarrow$ hist $\rightarrow$ pyhf (iminuit) to produce the ${m}_{4ℓ}$ invariant mass distribution, cutflow table, and asymptotic expected significance in $<1 s$ warm latency.  
14. **Live Agent Demo:** Expose the 6 MCP tools locally over stdio/SSE, include AGENTS.md, and record an end-to-end trajectory of a frontier coding agent (e.g., Claude Code or Codex) reproducing the $H\rightarrow Z{Z}^{*}\rightarrow 4ℓ$ result and diagnosing/fixing an injected bug (such as a wrong lepton ${p}_{T}$ cut or dropped scale factor).

## **5\. Step-by-Step Build Plan (Phases 0–7)**

The plan has eight phases (0–7); each ends with an exit gate that must pass before dependent phases begin. Phases 1 and 2 can run in parallel once Phase 0 is complete.

### **Phase 0 — Scope and Spikes**

15. 

**0.1 Pick the reference analyses.** Choose 3 ATLAS Open Data analyses with distinct structures:

* **Analysis 1 (Shape fit & 4-body combinatorics):** $H\rightarrow Z{Z}^{*}\rightarrow 4ℓ$ (validates pyhf workspace, systematics, and opposite-sign same-flavor lepton pairing).  
* **Analysis 2 (Data-driven background):** $W/Z+jets$ or  with fake-lepton matrix / fake-factor estimate (validates correctionlib fake maps).  
* **Analysis 3 (Multi-CR likelihood):**  or $H\rightarrow W{W}^{*}/\gamma \gamma$ with multiple control and validation regions.  
* *Tools:* AGC repository and docs; ATLAS Open Data example notebooks; HEPData for published 2015–16 results.  
* *Done when:* The project owner signs off on the list and golden target numbers are recorded with tolerances.

16. 

**0.2 Backend latency spike.** Time a dev-sized Parquet skim ($~{10}^{6}$ events) across three candidates:

* **(a)** Pure pyarrow \+ awkward \+ hist (direct columnar projection, no scheduler overhead),  
* **(b)** coffea (2025+ virtual/Dask arrays), and  
* **(c)** ROOT RDataFrame.  
* *Benchmark workload:* One event selection, ten histograms, followed by one mutated expression. Measure cold run time, warm-cache latency, and expression compilation/JIT cost.  
* *Tools:* pyarrow, awkward, hist, coffea, ROOT RDataFrame.  
* *Done when:* One backend is chosen for the RL loop with measured numbers recorded in the Decision Log (Expected default for single-worker cached DAGs on Parquet: pure pyarrow \+ awkward \+ hist at $<1 s$ warm latency).

17. 

**0.3 Repository, image, and CI.** One repository, one versioned container image with the pinned physics stack, and CI running tests on every change.

* *Tools:* pixi (or conda-lock) using conda-forge packages, Docker build converted to Apptainer, CERN GitLab CI / GitHub Actions, pytest, pre-commit.  
* *Done when:* CI builds the image and runs the test suite automatically.

**Exit Gate 0:** Scope, golden targets, and event-processing backend are decided and recorded in the Decision Log.

### **Phase 1 — Data Foundation**

18. 

**1.1 Metadata catalog.** Every sample's physics process, cross section, $k$\-factor, sum of weights, campaign, and luminosity, plus available systematic variations, frozen into one versioned YAML file per campaign. Its SHA-256 hash enters the DAG.

* *Tools:* YAML catalog validated by Pydantic; atlasopenmagic metadata API; Open Data portal records via cernopendata-client; hepunits; particle.  
* *Done when:* Catalog normalizations reproduce the reference analyses' MC yields.

19. 

**1.2 Base production.** Calibrate objects and write canonically sorted (runNumber, eventNumber) flat/jagged columnar Parquet files with precomputed boolean flags for every working point the agent may choose.

* *Systematic storage optimization:* Store weight variations as compact arrays per working point. For kinematic 4-momentum variations (JES/JER, lepton scale/resolution), expose a **pruned basis of dominant nuisances** (5–10 variations) in the dev tier so Parquet width and I/O latency stay small, reserving the full 100+ nuisance set for full-tier verification.  
* *Tools:* PHYSLITE processed with public AnalysisBase (CP algorithms); PhysLiteToOpenData as reference skimmer; Snakemake for batch submission; uproot; awkward.to\_parquet; fsspec-xrootd for root://eospublic.cern.ch; cernopendata-client.  
* *Done when:* All samples for the reference analyses are produced, canonically sorted, and spot-checked against the inputs of the reference pipelines.

20. 

**1.3 Dev and full tiers (Dev-Explore and Dev-Verify).** Select dev-tier events deterministically by a hash of (runNumber, eventNumber) (a few percent per sample) and partition them into two disjoint splits:

* **Dev-Explore:** Mounted read-only in the agent sandbox for inspect and run.  
* **Dev-Verify:** Unmounted and hidden from the sandbox; used exclusively by submit verifiers to evaluate sensitivity and prevent inspect\-based MC overfitting.  
* *Tools:* pyarrow, numpy, xxhash or blake3.  
* *Done when:* Dev-Explore and Dev-Verify yields scaled up by their inverse sampling fractions agree with full-tier yields within statistical uncertainty.

21. 

**1.4 Blinded data views.** For each blinding definition a task can use, materialize a collision-data view with the blinded signal phase space removed. Include a protective phase-space buffer around the signal region where region cuts are tunable, while keeping sideband and loose-ID events intact for ABCD and fake-factor background estimates.

* *Tools:* pyarrow.dataset with filter expressions; Parquet partitioning by sample and campaign.  
* *Done when:* Automated tests prove zero events from the blinded region exist in the view while control/sideband regions remain intact.

**Exit Gate 1:** Metadata catalog, Dev-Explore, Dev-Verify, full tiers, and blinded views exist for the reference analyses, with verification tests passing in CI.

### **Phase 2 — Schema and Compiler**

22. 

**2.1 Schema v0.** Typed models for samples, object collections (working points, $\Delta R$ overlap removal, and **declarative combinatorics/pairing**), derived variables (defines), regions (keyed by name, with roles SR, CR, VR), observables and binning, background estimates, systematics, and the statistical fit (modeled on cabinetry's YAML specification). Version the schema from day one.

* *Usability rule:* Structure config collections as **named dictionaries** (e.g., regions.SR\_4l.cuts) rather than positional arrays so LLM dotted-path edits never fail on off-by-one list indices.  
* *Tools:* Pydantic (exports JSON Schema), OmegaConf for composition and dotted overrides, ruamel.yaml for round-trip editing that preserves comments and key order.  
* *Done when:* All three reference analyses can be written cleanly as configs without code escape hatches.

23. 

**2.2 Expression language & combinatorics.** Separate **object-level combinatorics** (handled by declarative schema operators like pair\_os\_sf(leptons, rank\_by="closest\_to\_z\_mass") or overlap\_remove(jets, electrons, dr=0.4)) from **mathematical/boolean expressions**.

* *R\&D and Demo implementation:* Parse mathematical and cut expressions using Python's standard library **ast module**, restricted to a strict whitelist of safe AST nodes (BinOp, UnaryOp, Compare, BoolOp, Call, Attribute, Subscript) and a registry of vetted physics operators (invariant\_mass, delta\_r, mt2, transverse\_mass, mva\_eval backed by vector and awkward). Introduce a custom Lark grammar later only if non-Python syntax is needed.  
* *Decoding strategy:* Use standard JSON Schema structured outputs to constrain MCP tool calls at generation time, and rely on the $<50 ms$ validate tool to check AST expression syntax and Arrow column types rather than embedding complex context-free grammars inside the LLM token sampler.  
* *Tools:* Python ast (or Lark), pyarrow schemas, vector.  
* *Done when:* Every expression and combinatoric step in the three reference analyses parses, type-checks against the Parquet schema, and lowers to vectorized array operations.

24. 

**2.3 Semantic validation.** Cross-reference checks (undefined regions or variables, systematics applied to missing samples, fit missing a control region, MeV/GeV unit mismatches, jagged object collection vs. flat event-level broadcasting errors) with error messages written specifically for an LLM reader.

* *Tools:* Pydantic model validators; hepunits.  
* *Done when:* A fixture suite of broken configs each produces one precise, actionable error message in $<50 ms$.

25. $Source\rightarrow ObjectFilter\rightarrow Combine\rightarrow Define\rightarrow EventFilter\rightarrow Weight\rightarrow Vary\rightarrow Histogram\rightarrow Estimate\rightarrow StatModel\rightarrow Fit$Implement common-subexpression elimination (CSE) of shared selection prefixes, dead-node elimination, column pruning (reading only referenced Parquet columns), and single-pass histogram fusion per sample. 

**2.4 Intermediate Representation (IR), lowering, and optimization passes.** Lower validated configs to a compact IR of typed nodes:

* *Tools:* graphlib (stdlib topological sort), networkx (cycle checks, ancestor tracing, and Graphviz visualization).  
* *Done when:* Optimized and unoptimized DAGs produce bit-for-bit identical outputs on the reference analyses.

26. 

**2.5 Merkle hashing.** Compute Merkle-style node keys from canonical JSON of each node's configuration plus upstream node keys, catalog hash, and data-tier split identifier.

* *Tools:* Python json with sorted keys and canonical float formatting, hashed with hashlib SHA-256.  
* *Done when:* Node hashes are deterministic across processes and machines (verified via Hypothesis property tests).

**Exit Gate 2:** The compiler lowers all three reference configs into optimized DAGs; Hypothesis property tests pass in CI.

### **Phase 3 — Executor and Physics Nodes**

27. 

**3.1 Cached executor.** Topological execution that skips any node whose Merkle key is present in the cache. When a subset of histograms misses the cache, fuse only the missing histograms into a single pass over the required columns.

* *Source-aligned bitmap masks:* Cache EventFilter selection masks as **source-aligned compressed bitmaps (numpy.packbits)** of length ${N}_{events}$ matching the canonically sorted Source Parquet file. Combining two cached selection prefixes is then an $O(1)$ vectorized bitwise AND (numpy.bitwise\_and), and binning-only changes skip selection evaluation completely.  
* *Tools:* diskcache (default for Quick Demo and single-node R\&D); Redis \+ S3-compatible object store via fsspec (for multi-node distributed RL workers); numpy.packbits.  
* *Done when:* A cached run matches a fresh run bit-for-bit, and a binning-only modification reruns only histogram fill and fit nodes in $<1 s$.

28. 

**3.2 Histogramming.** One multi-axis histogram per sample with StrCategory axes for region and systematic variation, filled in a single vectorized pass.

* *Tools:* hist (boost-histogram), mplhep for optional plot rendering.  
* *Done when:* Generated histograms match the reference analyses' templates within floating-point precision.

29. 

**3.3 Background-estimate nodes.** Express control-region normalizations, data-driven shapes, and ABCD transfer factors inside the pyhf likelihood where possible. Implement fake-lepton estimates via measured efficiency/fake maps converted to a correctionlib evaluator and applied as event weights.

* *Tools:* pyhf (normfactor, shapefactor), correctionlib (including converters from hist).  
* *Done when:* The reference analysis with a data-driven background reproduces its target estimate.

30. 

**3.4 Statistical model and fit.** Build the statistical workspace, perform maximum-likelihood fits, and report nuisance parameter pulls, impacts, and post-fit yields. Provide fast asymptotic expected significance ($\sqrt{{q}_{0}}$) and $95%{ CL}_{s}$ upper limits on Asimov data for design tasks.

* *Tools:* pyhf with iminuit; cabinetry as an optional diagnostic layer; ROOT RooFit/HistFactory (via HS3 where applicable) as an offline reference cross-check.  
* *Done when:* Fitted signal strengths, uncertainties, and pulls agree with the reference pipelines' fits within agreed tolerances.

31. 

**3.5 Port and validate the reference analyses.** Run all three reference analyses end-to-end on the full tier as golden tests, and cross-check one analysis against FastFrames on the equivalent physics configuration.

* *Tools:* pytest; Snakemake on HTCondor for full-tier batch runs.  
* *Done when:* Golden tests pass in CI and the dev-tier run latency target ($<2 s$ warm, $<10 s$ cold) is met.

**Exit Gate 3:** Three reference analyses reproduce their golden numbers through declarative configs alone.

### **Phase 4 — Agent Interface**

32. 

**4.1 MCP tool server.** Expose six tools via the official MCP Python SDK, keeping the episode workspace under local git:

* inspect: Executes a **stateless, CPU-time-capped ($3 s$), read-only Python snippet** in an isolated subprocess against the Dev-Explore data view and returns truncated stdout/summary statistics. (Using stateless subprocesses instead of persistent jupyter\_client kernels prevents memory leaks, zombie processes, and hidden state across thousands of RL rollouts.)  
* edit\_config: Applies **dotted-path key-value overrides (OmegaConf style) or named section replacements** (with RFC 6902 JSON Patch as an optional fallback), preserving YAML comments and key ordering via ruamel.yaml and committing each revision to git.  
* validate: Runs schema, AST expression, and semantic validation in $<50 ms$, returning structured, prescriptive repair instructions on failure.  
* run: Compiles and executes the DAG (or a specified target subgraph) on Dev-Explore (with an optional subsample fraction argument for rapid previews), returning execution timing, cache hit stats, and output handles.  
* get\_outputs: Retrieves cutflow tables, yield summaries, nuisance pulls, or histogram bin contents by output handle within a strict per-observation token budget.  
* submit: Evaluates the candidate configuration against the external task verifier (Dev-Verify split or oracle reference) and returns the final episode reward.  
* *Tools:* Official MCP Python SDK, OmegaConf, ruamel.yaml, subprocess, git, tenacity.  
* *Done when:* Both a scripted client and a frontier LLM complete a reproduction task using only these six tools.

33. 

**4.2 Sandbox isolation.** Run each episode inside a container with read-only Dev-Explore mounts (Dev-Verify and oracle references are **never mounted** inside the container), no network egress, and cgroup limits on CPU, memory, and wall-clock time.

* *Tools:* Docker locally, Apptainer on batch nodes, or Kubernetes with gVisor; bubblewrap or nsjail for process-level isolation of the stateless inspect runner.  
* *Done when:* Automated security tests verify that escape attempts (network access, writing to the shared cache directly, accessing Dev-Verify or reference files, and inspect CPU/memory bombs) fail cleanly.

34. 

**4.3 Context management policy.** Implement automatic tool-result clearing for superseded validate and get\_outputs observations, a persistent NOTES.md scratchpad in the workspace, output handles, and hard per-observation token budgets with explicit truncation markers.

* *Tools:* Built directly into the environment harness; identical across human evaluation, frontier benchmarking, and RL training.  
* *Done when:* A 40-turn episode stays comfortably within a $32k$ token context budget.

35. 

**4.4 Agent briefing and skills.** Place a concise AGENTS.md in every workspace (documenting coordinate conventions, GeV energy units, blinding policy, and the edit\_config $\rightarrow$ validate $\rightarrow$ run workflow) alongside an Agent Skills directory (SKILL.md progressive disclosure format): one skill per background estimation method, statistical procedure, and ATLAS object working-point recommendation, loaded on demand.

* *Tools:* AGENTS.md standard; Agent Skills (SKILL.md) format.  
* *Done when:* Physicists on the team have reviewed and signed off on every skill document.

36. 

**4.5 Observability.** Emit one OpenTelemetry trace per episode with child spans for every model generation, MCP tool call, and DAG node execution, attaching cache hit ratios and verifier reward breakdowns.

* *Tools:* OpenTelemetry GenAI semantic conventions; **MLflow Tracing** (backed by local SQLite/files during the Quick Demo and a shared tracking server during cluster runs).  
* *Done when:* Any episode rollout can be opened, inspected, and replayed deterministically from its trace.

37. 

**4.6 Dogfooding.** Physicists drive the environment via an MCP client, and a frontier coding agent (e.g., Claude Code) attempts reproduction and bug-repair tasks. Fix unclear error messages, missing combinatoric operators, and latency bottlenecks.

* *Done when:* A frontier agent completes at least one reproduction task and one bug-repair task end-to-end, and physicist feedback is resolved.

**Exit Gate 4:** The environment is usable by both physicists and frontier agents through a single unified MCP interface.

### **Phase 5 — Tasks, Rewards, and Red-Teaming**

38. 

**5.1 Task bundle format.** Store each task in our canonical bundle format: natural-language physics specification, environment image digest, starting config, data-view ID, tool-call budget, verifier specification, and external reference handle. Provide a thin adapter to generate **Harbor** (or **Inspect**) evaluation tasks.

* *Done when:* The evaluation harness runs a frontier agent on a task bundle and scores it automatically.

39. 

**5.2 Procedural task generators.**

* **Perturbation generator:** Varies kinematic cuts, object working points, observables, histogram binning, control-region definitions, and signal mass hypotheses.  
* **Bug-injection generator:** Applies structured mutation operators—wrong working point, dropped scale-factor weight, flipped cut inequality, missing systematic variation, $MeV/GeV$ unit mismatch, or omitted overlap removal (double counting).  
* **Signal-injection generator:** Generates toy/Asimov pseudo-data at a known signal strength $\mu$, as well as event-level mixing of weighted signal MC (including $\mu =0$ null injections).  
* **Design task generator:** Prompts the agent to maximize expected discovery significance or upper-limit sensitivity for a target signal process under strict background-modeling guardrails.  
* *Tools:* OmegaConf, Hypothesis, pyhf.  
* *Done when:* Each generator emits valid, solvable tasks across graded difficulty levels.

40. 

**5.3 Reference computation (DAG-cached).** Compute oracle outputs for all generated tasks on the full tier. Because perturbed and bug-injected tasks share $80%+$ of their upstream DAG nodes with the three base analyses, execute reference generation **through the Phase 3.1 shared content-addressed cache** so only mutated downstream branches are recomputed.

* *Tools:* Cached DAG executor \+ Snakemake on HTCondor for uncached full-tier branches.  
* *Done when:* Verified oracle references exist for the entire task set with their Merkle hashes recorded.

41. 

**5.4 Verifiers and hierarchical reward shaping.**

* **Reproduction & Repair Verifier:** Computes a deterministic, hierarchical score in $[0,1]$ combining: 

42. Schema and semantic validity ($0.10$),  
43. Upstream node-hash and event cutflow agreement within relative tolerance $\leq {10}^{-6}$ ($0.30$),  
44. Histogram bin-by-bin agreement within relative tolerance $\leq {10}^{-4}$ or ${\chi }^{2}/{N}_{dof}<1.05$ ($0.30$), and  
45. Final fitted signal strength agreement $|\Delta \mu |/{\sigma }_{\mu }\leq 0.05$ and nuisance pull agreement within $\pm 0.05\sigma$ ($0.30$). *(Note: Intermediate shaping weights can be annealed toward zero as training progresses from T1 to T2.)*

* **Design Verifier (T4):** Computes asymptotic expected significance on Asimov data evaluated **exclusively on the unmounted Dev-Verify (and Full) MC split**, multiplied by $0.0$ if any hard guardrail fails: 

46. Minimum raw MC events per bin (${N}_{raw}\geq 10$) and maximum relative MC statistical uncertainty per bin (${\sigma }_{stat}/B<0.30$).  
47. All required experimental and theory systematic variations enabled.  
48. Control-region signal contamination $<5%$ and Validation-region data/MC closure within $1\sigma$.

* *Tools:* numpy, scipy.stats, pyhf.  
* *Done when:* Verifier verdicts and rankings agree with human physicist judgment on a 50-task audit sample.

49. 

**5.5 Curriculum tiers.**

* **T0:** Single-node or single-cut edits.  
* **T1:** Staged multi-node assembly (e.g., adding a control region and connecting its normalization factor).  
* **T2:** Full analysis reproduction from a natural-language physics summary.  
* **T3:** Bug diagnosis and repair from discrepant cutflows/plots.  
* **T4:** Open-ended sensitivity optimization under hard guardrails.  
* *Done when:* Every curriculum tier contains at least several hundred verified tasks.

50. 

**5.6 Adversarial red-teaming.** Instruct frontier agents to maximize the verifier reward *without* performing a valid physics analysis (e.g., using inspect to hunt for high-weight MC events, micro-tuning bin edges on statistical fluctuations, dropping subtle nuisance parameters, or leaking signal into control regions). Patch every exploit discovered in the verifiers or sandbox, and repeat.

* *Done when:* A full adversarial red-team round uncovers zero new exploits.

**Exit Gate 5:** A tiered, verified, and red-teamed task set is complete and frozen.

### **Phase 6 — Baseline and RL Readiness**

51. 

**6.1 RL environment wrapper.** Wrap the MCP tool server in a standard **Gymnasium** interface (reset, step, close) with a thin adapter for verl and TRL.

* *Tools:* Gymnasium.  
* *Done when:* Both a random-action client and a scripted oracle client complete full episodes through the Gymnasium wrapper.

52. 

**6.2 Model serving and gateway.** Serve candidate open-weight models using **vLLM** with automatic prefix caching enabled (sharing the system prompt, AGENTS.md, skill descriptions, and schema docs across parallel rollouts) and JSON Schema structured outputs for tool calls via vLLM's OpenAI-compatible API.

* *Tools:* vLLM.  
* *Done when:* Two open-weight models and one frontier API model run through the exact same evaluation harness without code changes.

53. 

**6.3 Base-model bake-off.** Measure $pass@k$ across curriculum tiers T0–T4 for 3–4 open-weight candidates (e.g., Qwen, Llama, and DeepSeek coding/reasoning families) alongside a frontier model ceiling. Categorize failures into **schema/format errors** vs. **physics reasoning errors**.

* *Tools:* Harbor (via task-bundle adapter); MLflow traces from Step 4.5.  
* *Done when:* The $pass@k$ comparison table is complete and the base model is selected. Lock the SFT decision: skip SFT if T0–T1 $pass@k$ is clearly non-zero; run lightweight format-only SFT on synthetic $(spec,config)$ pairs if failures are predominantly syntactic; use teacher trajectory distillation only as a last resort.

54. 

**6.4 Throughput benchmark.** Simulate a full RL training step: $64 tasks\times 8 rollouts\times 25 tool calls$ ($1.28\times {10}^{4}$ tool executions). Measure wall-clock time, shared DAG cache hit rate, and CPU utilization across distributed **Ray** environment workers.

* *Tools:* Ray, shared cache from Step 3.1.  
* *Done when:* One simulated training step finishes in $<10 minutes$ on the target CPU pool (or any resource gap is quantified and budgeted).

55. 

**6.5 RL trainer handoff.** Connect **verl** (or **TRL** for single-node pilots) to the Gymnasium environment wrapper (Step 6.1) and configure MLflow experiment tracking with full provenance logging (container image digest, schema version, task-set hash, data-tier version, and model checkpoint).

* *Tools:* verl or TRL; MLflow.  
* *Done when:* A short pilot RL run on T0–T1 tasks demonstrates rising validation reward with zero reward-hacking exploits in the episode traces.

**Exit Gate 6:** Go/no-go sign-off for full RL training, with the base model, SFT decision, and compute budget locked.

### **Phase 7 — RL Training & Held-Out Evaluation (Outline)**

Train with Group Relative Policy Optimization (GRPO) multi-turn RL across the curriculum ($T0\rightarrow T4$), dynamically promoting tiers as pass rates rise and filtering out tasks with $0%$ or $100%$ pass rates across group rollouts. Run automated adversarial audits on high-reward trajectories at every checkpoint to catch emerging reward hacking early. Perform final evaluation on **held-out physics analyses never ported into training**: reproduce a published result from scratch, diagnose and repair injected bugs, and optimize sensitivity blindly on signal-injected data. Detailed training hyperparameters will be finalized after Exit Gate 6\.

## **6\. Consolidated Tooling Reference (R\&D Agility vs. Long-Term Maintenance)**

### **Rationale for Key Stack Refinements**

* **Pure pyarrow \+ awkward \+ vector \+ hist inside the RL loop (dropping uproot and coffea inside workers):** Because Phase 1.2 outputs columnar Parquet files, uproot is only needed offline. Avoiding coffea/Dask inside the single-node DAG worker eliminates $1–3 s$ of task-graph scheduling overhead per call, keeping warm-cache execution under $0.5 s$ with minimal dependency maintenance.  
* **Python ast whitelist over custom Lark \+ CFG constrained decoding:** LLMs natively write valid Python expressions with near-zero syntax errors. Validating expressions with Python's built-in ast module against a whitelist of operators and column types takes $<5 ms$, requires zero parser maintenance, and avoids brittle token-sampling stalls from embedding context-free grammars inside JSON Patch tool calls.  
* **Named dictionaries \+ OmegaConf dotted overrides over raw RFC 6902 jsonpatch:** LLMs frequently make off-by-one array index errors in JSON Patch (e.g., /regions/2/cuts/1). Keying config sections by name (regions.SR\_4l.cuts) makes edits human-readable and resilient.  
* **Stateless subprocess runner over persistent jupyter\_client kernels:** Managing stateful Jupyter kernels across thousands of parallel RL rollouts leads to zombie processes, memory leaks, and hidden state bugs. Stateless subprocess execution over memory-mapped Arrow/Parquet files is fast, isolated, and $100%$ reproducible.

### **Settled Core Stack**

| Concern | Chosen Tool(s) | Why This Fits Quick Demo \+ Long-Term Maintenance | Step |
| :---- | :---- | :---- | :---- |
| **Environment & Lockfiles** | pixi (or conda-lock) on conda-forge | Resolves mixed Python and C++/ROOT dependencies $10\times$ faster than standard conda while generating strict, reproducible lockfiles. | 0.3 |
| **Metadata Catalog** | Pydantic \+ YAML \+ atlasopenmagic \+ cernopendata-client | Self-documenting, version-controlled in git, zero database server maintenance. | 1.1 |
| **Offline Base Production** | ATLAS AnalysisBase \+ PhysLiteToOpenData \+ uproot \+ pyarrow | Runs once offline to produce canonically sorted Parquet files; completely decoupled from the RL worker codebase. | 1.2 |
| **RL Loop Event Engine** | Pure pyarrow \+ awkward \+ vector \+ hist | Sub-second warm execution on Parquet inputs, zero Dask/Coffea scheduler overhead, rock-solid API stability. | 0.2, 3.2 |
| **Config Schema & Editing** | Pydantic \+ OmegaConf \+ ruamel.yaml | Named dictionary keys \+ dotted overrides (regions.SR\_4l.cuts) eliminate LLM JSON Patch array-indexing errors. | 2.1, 4.1 |
| **Expression Validation** | Python ast whitelist (Demo/R\&D) $\rightarrow$Lark (optional) | Standard library ast requires zero maintenance and leverages native LLM Python syntax fluency. | 2.2 |
| **DAG & Hashing** | graphlib (stdlib) \+ networkx \+ hashlib (SHA-256) | Zero-dependency topological sort (graphlib) paired with networkx for CSE passes and Graphviz debugging. | 2.4–2.5 |
| **Caching Layer** | diskcache \+ numpy.packbits (Local) $\rightarrow$Redis \+ S3 (Cluster) | diskcache needs zero daemon setup for the Quick Demo and single-node R\&D; swaps cleanly to Redis/S3 behind a thin cache interface. | 3.1 |
| **Statistical Fit & Limits** | pyhf (iminuit) \+ correctionlib (cabinetry optional) | Fast, pure-Python likelihood evaluation; ROOT RooFit/HistFactory kept strictly as an offline cross-check. | 3.3–3.4 |
| **Tool Protocol & Inspect** | Official MCP Python SDK \+ stateless subprocess \+ git | Stateless inspect subprocesses inside bubblewrap prevent Jupyter kernel leaks across ${10}^{5}$ RL episodes. | 4.1–4.2 |
| **Agent Briefing** | AGENTS.md \+ Agent Skills (SKILL.md) | Open standards with progressive token disclosure so context stays small. | 4.4 |
| **Observability & Tracking** | OpenTelemetry GenAI spans \+ MLflow | Unified platform for both episode trace debugging and RL training curves; runs on local files for the demo. | 4.5, 6.5 |
| **Task Testing & Fuzzing** | Hypothesis \+ pytest | Property-based testing guarantees Merkle hash stability and catches verifier edge cases. | 2.5, 5.2 |
| **Distributed Env Workers** | Ray | Industry standard used by verl and vLLM for orchestrating parallel CPU rollout workers. | 6.4 |

### **Options to Confirm at Phase Gates**

Tiers reflect maturity as of October 2026: **Established** (long-standing institutional standard), **Mature** (several years of broad production use), **Growing** ($1–3 years$, rapid adoption), **Emerging** (new or experimental; must sit behind our own adapter).

| Concern | Options (Most Mature First) | Recommended Default | Decide At |
| :---- | :---- | :---- | :---- |
| **Batch Reference Runs** | Snakemake (Established) · law (Mature) | **Snakemake** (on HTCondor) | 3.5, 5.3 |
| **Sandboxing** | Docker / Apptainer \+ bubblewrap (Established) · K8s \+ gVisor (Mature) · Modal / E2B (Growing) | **Docker locally, Apptainer on batch \+ bubblewrap** | 4.2 |
| **Evaluation Harness** | Harbor (Growing; runs Claude Code/Codex, exports RL rollouts) · Inspect (Growing) | **Harbor** (behind our task-bundle adapter) | 5.1 |
| **RL Env Interface** | Gymnasium (Established) · OpenEnv (Emerging) | **Gymnasium** | 6.1 |
| **Inference Serving** | vLLM (Mature) · SGLang (Mature) | **vLLM** (with prefix caching \+ JSON Schema outputs) | 6.2 |
| **RL Training Framework** | TRL (Mature) · verl (Growing; standard for multi-turn tool RL) · OpenRLHF (Growing) · SkyRL (Emerging) | **verl** (with TRL for single-node smoke tests) | 6.5 |

## **7\. Risks, Mitigations, and Open Decisions**

| Risk | Effect | Mitigation |
| :---- | :---- | :---- |
| **Reward hacking via inspect or cut tuning** (isolating high-weight MC spikes, tiny bins, signal-contaminated CRs, dropped systematics) | Policy learns to game expected sensitivity on Dev-Explore | Unmounted Dev-Verify MC split for submit scoring; hard guardrails (${N}_{raw}\geq 10$, ${\sigma }_{stat}/B<0.30$, mandatory systematics, CR contamination $<5%$) that zero reward; $3 s$ CPU cap on inspect; red-teaming in Step 5.6. |
| **Schema cannot express real object combinatorics** ($Z$\-candidate pairing, $\Delta R$ overlap removal, $b$\-jet pairing) | Agent capability ceiling or disruptive late redesign | Port all three reference analyses in Step 2.1 before building the executor; include first-class declarative ObjectFilter and Combine nodes. |
| **run latency too high** (wide Parquet files with 100+ kinematic systematics or scheduler overhead) | RL loop becomes too slow or expensive | Pruned kinematic systematic basis in dev tier; column pruning via pyarrow; source-aligned packbits bitmaps; pure awkward \+ hist without Dask overhead. |
| **Sparse reward collapse on multi-stage reproduction** | Agent fails to learn 8-stage full analysis assembly | Hierarchical node-level reward shaping in Step 5.4 (schema $\rightarrow$ cutflow $\rightarrow$ histogram $\rightarrow$ fit), annealed in later curriculum tiers. |
| **Dev-tier results disagree with full tier** | Agent optimizes statistical noise in small samples | Yield scaling agreement check in Step 1.3; final evaluation on full tier. |
| **Base model fails primarily on config format** | Zero reward signal at the start of RL | Named dictionary schema; JSON Schema structured tool outputs; $<50 ms$ prescriptive validate errors; format-only SFT on synthetic generator pairs. |
| **Pretraining contamination** (base models memorized public ATLAS Open Data notebooks and published 2015–16 numbers) | Unmodified reproduction scores overstate reasoning ability | Train and evaluate on perturbed cuts, mutated working points, and blind signal injections whose target numbers do not exist online. |

### **Open-Decision Checklist for Project Owner Sign-Off**

* ☐  **0.1 Reference Analyses:** Confirm the 3 ATLAS 2015–16 PHYSLITE reference analyses (Recommended: AGC $H\rightarrow Z{Z}^{*}\rightarrow 4ℓ$, fake-lepton $W/Z$ or , and multi-CR  or $H\rightarrow W{W}^{*}$).  
* ☐  **0.1 Quick Demo Target:** Confirm $H\rightarrow Z{Z}^{*}\rightarrow 4ℓ$ on pre-skimmed Parquet as the 2-week Quick Demo vertical slice (Section 4).  
* ☐  **0.2 Backend Benchmark:** Run the ${10}^{6}$\-event spike to confirm pure pyarrow \+ awkward \+ hist meets $<2 s$ warm-cache latency.  
* ☐  **5.4 Verifier Tolerances:** Sign off on numerical tolerances (Cutflow relative tolerance $\leq {10}^{-6}$, Histogram bin tolerance $\leq {10}^{-4}$, Fit $|\Delta \mu |/{\sigma }_{\mu }\leq 0.05$, Design guardrails ${N}_{raw}\geq 10$ and ${\sigma }_{stat}/B<0.30$).  
* ☐  **6.4 Compute Layout:** Confirm GPU node allocation for vLLM \+ verl vs. CPU core pool for Ray environment workers.

## **8\. Prior Art & References**

None of the existing HEP agent works below train an open-weight model with RL in a config-only, content-addressed DAG action space; that is this project's core differentiator. **Read the first four references before starting Phase 2\.**

| Reference | Why It Matters Here |
| :---- | :---- |
| **AI Agents Can Already Autonomously Perform Experimental HEP (JFC)** (arXiv:2603.20179v1) | Frontier agent runs full analyses given data, a framework, and literature; argues against narrow scaffolds. |
| **Automating HEP Data Analysis with LLM-Powered Agents** (arXiv:2512.07785) | Agent plus Snakemake workflow manager on ATLAS Open Data; closest architectural prior art to our DAG approach. |
| **Collider-Bench** (arXiv:2605.13950) | LHC reproduction benchmark with containerized sandbox; candidate external evaluation suite. |
| **Reining in an Agentic Harness for HEP** (arXiv:2609.00107) | Harness engineering principles and failure modes for HEP agents. |
| **RooAgent** (arXiv:2605.17318) | Example HEP MCP server implementation. |
| **AgentRivet** (arXiv:2606.13535) | Paper-to-Rivet routine agent; related truth-level task source. |
| **PocketCoffea Configuration** (PocketCoffea Docs) | Declarative CMS analysis configuration close to our target schema. |
| **FastFrames** (Zenodo Record 15280679\) | ATLAS RDataFrame framework steered by YAML; used as our Step 3.5 cross-check. |
| **columnflow** (columnflow Docs) | law \+ order orchestrated columnar HEP framework. |
| **coffea Virtual-Arrays Release** (coffea v2025.7.0) | Current coffea execution modes for comparison in Step 0.2. |
| **OpenEnv & Gymnasium** (Farama Gymnasium / Meta PyTorch OpenEnv) | RL environment interface standards. |
| **Harbor** (harbor-framework/harbor) | Containerized agent evaluation and rollout generation harness. |
| **Agent Skills & Agentic AI Foundation** (agentskills.io / Linux Foundation) | SKILL.md progressive disclosure format and governance of MCP and AGENTS.md. |
| **OpenTelemetry GenAI Spans & Context Engineering Cookbook** (OTel Spec / Anthropic Cookbook) | Tracing conventions for agent runs, tool-result clearing, and compaction patterns. |
| **SkyRL & VerlTool** (UC Berkeley SkyRL / arXiv:2509.01055v2) | Multi-turn agentic tool-use RL built on top of verl. |

## **9\. Handover Instructions & Decision Log**

### **Handover Execution Rules**

56. **Read this document completely**, followed by the first four prior-art papers in Section 8\.  
57. **Resolve the Open-Decision Checklist (Section 7\)** with the project owner before writing production compiler code.  
58. **Execute the 2-Week Quick Demo Track (Section 4\) first** on pre-skimmed $H\rightarrow Z{Z}^{*}\rightarrow 4ℓ$ Parquet data to validate the Pydantic schema, Python ast expression engine, and MCP tools end-to-end before launching bulk AnalysisBase batch jobs.  
59. **Work phase by phase (Phases 0–7).** Do not start a phase that depends on an earlier phase until its Exit Gate passes; record every gate completion date and benchmark number in the Decision Log below.  
60. **Treat the Design Principles (Section 3\) as hard constraints.** If any principle blocks progress, stop and raise it with the project owner rather than working around it.  
61. **Write tests first for anything that computes a Merkle hash or a reward.** Silent bugs in hashing, row ordering, or Dev-Verify isolation become reward-hacking vectors during RL training.  
62. **Verify library compatibility** with the target ATLAS Open Data release before locking versions in pixi.toml / conda-lock.yml.

### **Decision Log**

| Date | Step / Area | Decision | Rationale / Measured Numbers | Agreed By |
| :---- | :---- | :---- | :---- | :---- |
| 2026-10-17 | Scope | Use ATLAS 2015–16 PHYSLITE (CC0) as v1 experiment | Defined systematics path via AnalysisBase, single metadata API (atlasopenmagic), pre-calibrated objects, CC0 license allows public release. | @Chengxi Yang |
| 2026-10-19 | Demo Track | Add 2-week Quick Demo slice on pre-skimmed $H\rightarrow Z{Z}^{*}\rightarrow 4ℓ$ Parquet | Validates schema, AST engine, and MCP loop in 2 weeks before running heavy C++ AnalysisBase batch production. | @Chengxi Yang |
| 2026-10-19 | Data / Security | Split dev tier into Dev-Explore (mounted) and Dev-Verify (unmounted holdout) | Prevents the agent from using the inspect Python runner to overfit cuts to statistical spikes in dev MC. | @Chengxi Yang |
| 2026-10-19 | Schema / Loop | Use pure pyarrow \+ awkward \+ hist, named YAML dicts, Python ast whitelist, and source-aligned packbits masks | Eliminates Dask/Coffea scheduling overhead, custom parser maintenance, and JSON Patch list-index errors; guarantees $O(1)$ bitwise mask fusion. | @Chengxi Yang |
| YYYY-MM-DD | 0.1 | Lock 3 Reference Analyses | *Pending owner sign-off* |  |
| YYYY-MM-DD | 0.2 | Record ${10}^{6}$\-event backend benchmark latencies | *Cold: $[X.X] s$, Warm:$[Y.Y] s$* |  |
| YYYY-MM-DD | 5.4 | Lock Verifier Tolerances | *Pending 50-task audit validation* |  |

