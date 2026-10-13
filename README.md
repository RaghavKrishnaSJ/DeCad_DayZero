# Schematic2SDN

A local circuit workbench with native KiCad editing, real electrical connectivity, post-edit ERC, Git history, connectivity-preserving EDIF/XML export, and circuit simulation. The small local model runs through Ollama; an optional circuit vision adapter can run on a separate GPU server. No paid API key is required.

## Start

1. Install/start Docker Desktop with Docker Compose v2.24 or newer.
2. Double-click **start.command** on macOS, or run `./start.command` in a terminal. On Linux, run the same shell script.
3. On Windows, run `powershell -ExecutionPolicy Bypass -File .\start.ps1` from the extracted folder.
4. Open **http://localhost:3100** and choose **Open Local Workspace**.

The launcher builds the services. Local model downloads and loading are disabled by default. Core editing, simulation, exports and OCR work without a local language or vision model. Keep the terminal open until setup finishes.

For an optional small local language model (requires sufficient Docker memory):

```sh
ENABLE_AI=true ./start.command
```

Stop the services with `./stop.command`. Project data is stored in `backend/workspaces`; stopping/rebuilding containers does not remove it. Server-side sessions live in `backend/.state` and synthetic samples in `backend/datasets`.

Ports are 3100 (workbench), 8100 (API), 6180 (embedded KiCad), and optionally 11434 (Ollama). They bind only to this computer. These differ from the original application's ports so both versions can coexist.

The initial container/model downloads require several GB of disk space. Allow at least 12 GB of free storage. Core services are capped at 1 GiB and 512 MiB. With approximately 4 GiB allocated to Docker, an explicit ENABLE_AI=true can enable the small pretrained qwen3:0.6b model under a 2 GiB cap. Requests run sequentially with 2048 context tokens and two threads, and unload model weights afterward. It does not change Docker Desktop settings.

Image imports default to CPU circuit recognition: Tesseract reads references/values and OpenCV detects clean resistor, capacitor and voltage-source symbols and traces their wire-connected pins. The attachment selector also offers labels-only OCR or a configured vision server. Every recognized graph requires review; unsupported symbols, ambiguous crossings and unmatched closed symbols are rejected. This bounded R/C/V recognizer is not general schematic recognition. Full vision is opt-in: `ENABLE_VISION=true ./start.command` on a Docker allocation of at least 7.5 GB selects vision mode and a configurable 4 GiB model cap. This general vision path has not passed a circuit-accuracy benchmark; see [release gates](RELEASE_GATES.md). `ENABLE_AI=false ./start.command` starts only the core. For a separate Ollama server, set OLLAMA_URL in a root .env file (or export it before running the launcher).

## Four application adapters

Open **Applications & models** in the workbench. KiCad, ngspice, LTspice and Qucs-S each have a portable bundle generated from the circuit's actual pin graph. KiCad uses native schematic/project files. LTspice and ngspice use SPICE; Qucs-S uses a native schematic with a SPICE subcircuit wrapper. ngspice and Qucs-S run inside the workbench. The scope can import uncompressed real transient RAW or CSV results from external simulators (time in seconds; maximum 20,000 samples).

The launcher starts a Python desktop bridge if Python 3 is installed. It has no network listener and opens only registered application artifacts. Install LTspice separately from its vendor; its binary is not redistributed. Set S2SDN_KICAD_PATH, S2SDN_LTSPICE_PATH, S2SDN_QUCS_S_PATH or S2SDN_NGSPICE_PATH for nonstandard installations. Downloaded bundles remain available without the bridge.

## Models and training

**Plan with model** selects between divider and RC templates using the local pretrained language model. Native code parses specified values and constructs connectivity; review the proposal before applying. Three controlled end-to-end planning cases passed; this is not a general design benchmark.

The archive supplied four synthetic pairs across two topology families. Audited records and group-disjoint manifests are in backend/datasets/provided. No custom vision model has been trained. `training/dataset_tools.py` prepares verified paired data; `training/finetune.py` is a separate CUDA LoRA pipeline with preflight gates. It deliberately refuses the included insufficient dataset. See [the training guide](training/README.md) for exact data, GPU training, evaluation and adapter-serving commands. See RELEASE_GATES.md before shipping broader model claims.

## First circuit

Create or select a project, choose **Output software** beside the assistant, then enter:

```text
create a voltage divider
```

This creates V1=5 V, R1=10k and R2=10k with VIN/VOUT/GND pin connections. The saved native schematic appears in **Preview**, and a verified bundle downloads for the selected software. A Download design button remains in the assistant reply. If references conflict with an existing design, a separate project preserves that design. Use **Edit in KiCad** for interactive editing and **Preview** to return. The Nets tab shows actual KiCad netlist nodes. ERC runs after the edit. Waveform Scope runs the circuit and shows VOUT=2.5 V.

Useful commands:

```text
add R3 4.7k
add C1 100nF
add U1 74xx:74LS244
change R3 to 22k
R3 = 10k
remove R3
connect net GND to C1 pin 2
connect R1 pin 2 to C1 pin 1
run ERC
undo
redo
```

Use a new project for `create RC lowpass` or to import files whose references already exist. Duplicate references and unknown device pinouts are rejected rather than silently substituted. Exact symbols use `Library:Symbol`; footprints can be supplied in circuit JSON. Native KiCad remains available for the full graphical editing workflow.

Edits are transactional. Invalid syntax, unknown symbols, bad pin mappings, and conflicting imports leave the previous schematic intact. Undo/redo restores schematic snapshots; the Commit button records the current files in local Git. These operations do not require a GitHub account.

## Import

The Import/Attach buttons accept SPICE `.cir`, `.spice`, `.net`, typed circuit `.json`, component text, PDF/DOCX text, and images. `examples/` contains powered divider, RC step, diode-model, and JSON examples.

Circuit JSON uses:

```json
{
  "components": [{"ref":"R1","value":"10k","library":"Device:R","footprint":"Resistor_SMD:R_0805_2012Metric"}],
  "nets": [{"name":"GND","nodes":[{"ref":"R1","pin":"2"}]}]
}
```

Text/component-list documents supply component values; their pin connections must be specified explicitly. Image/single-page scanned-PDF imports use CPU R/C/V symbol and wire recognition by default, producing component and pin/net proposals for review. Labels-only OCR remains available as an explicit option. Opt-in vision extraction also produces JSON for review. Inspect values, exact library symbols, and pin-to-net assignments against the source before selecting **Apply reviewed circuit**. ERC checks electrical rules; it cannot prove that a recognized diagram matches its source. Unreadable/unsupported inputs produce a visible error, never a fake successful conversion.

Legacy `.doc` files should be saved as `.docx`. SPICE imports support R/C/L/V/I/D/Q devices, values, node names, and `.model` declarations. Arbitrary SPICE scripts, `.include` files, and ambiguous subcircuit-to-symbol mappings are rejected. Supply complex device models and pinouts in native KiCad for workflows beyond these imported device types.

## Editing and exports

- **Schematic:** embedded native KiCad with zoom, grid, save, and fit controls.
- **Source:** read/edit exact `.kicad_sch`; Save Source first asks native KiCad to save its active document, then verifies the new file with KiCad. A failed parse rolls back.
- **BOM:** actual references, values, footprints and specified LCSC fields. Supplier links open searches. Prices/stock are not claimed unless queried from a supplier.
- **Nets:** actual component-pin connections from the native XML netlist.
- **Checks:** actual ERC errors/warnings and explicit unavailable states.
- **History:** actual Git commits. Commit is local; Git Push requires optional OAuth configuration.
- **Scope:** transient simulation using ngspice in Docker. Native installations without ngspice can use the verified linear R/C/L/V/I modified-nodal-analysis solver. Floating/unpowered/unsupported-model circuits fail visibly. Set step/stop with SPICE units, such as `1u` and `5m`. The API limits runs to 20,000 time steps.
- **Downloads:** KiCad source, SVG, XML netlist, EDIF, SPICE, BOM CSV/JSON, nets JSON, ERC JSON, and Git history JSON. The circuit.json sidebar row downloads the full typed graph.

EDIF exports preserve real port-to-instance connectivity. This package does not create native OrCAD `.DSN` files: that operation requires OrCAD Capture, which is not installed here. Native OrCAD import compatibility must be checked on a licensed OrCAD installation before relying on that workflow.

The shared embedded desktop is designed for one local user at a time. Close KiCad modal dialogs before changing projects or running automated edits. Automated edits save the active editor first and reopen the schematic gracefully; an unsaved dialog is never force-killed.

## Optional GitHub

Copy `backend/.env.example` to `backend/.env`. Create a GitHub OAuth app with callback `http://localhost:8100/auth/callback`, and set GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET. Restart the backend. Sign in with GitHub, then push a project; a private `s2sdn-<project>` repository is created if needed.

OAuth state is verified. The browser cookie contains only a random session ID. GitHub tokens remain in the local server session database and are supplied to Git through a temporary askpass helper, not saved in repository URLs. The original ZIP's embedded credentials are not bundled in this package.

Live GitHub authorization/push requires your account and is not part of automated testing. Never expose these local desktop services publicly without adding a proper deployment/authentication layer.

## Verification and development

Backend checks use Python 3.12+ and KiCad CLI 9+ with its symbol libraries installed:

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
```

On macOS the installed KiCad path is detected automatically. Elsewhere set KICAD_CLI/KICAD_SYMBOL_DIR as needed. For a native development server, set OLLAMA_URL=http://localhost:11434, run the backend on port 8100, and run the frontend on port 3100:

```sh
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8100
# In another terminal:
cd frontend
npm ci
npm run dev
```

The frontend uses a same-origin /api proxy. Docker builds route it to the internal kicad service; native development routes it to localhost:8100.

Synthetic generation is authenticated at `POST /datasets/synthetic/generate?count=4`. It generates actual KiCad schematics, native SVG previews, full connectivity JSON, EDIF, and SPICE. Dataset summary reports only generated samples; this package does not claim a fine-tuned model or downloaded research corpus.

Production completion steps: [PRODUCTION_PLAN.md](PRODUCTION_PLAN.md). Run `python tools/check_release.py --output release-status.json` to inspect recorded blockers. Additional AMS-Net data is distributed separately for development and requires annotation/pin-mapping review; it is never loaded on end-user startup. See [training hardware notes](training/HARDWARE.md) for the RTX 3050 assessment.

The requested DSN is clarified as Specctra PCB autorouter DSN. Native KiCad-based export is implemented; see [SPECCTRA.md](SPECCTRA.md). OrCAD schematic DSN remains a separate unsupported format.

## Guided review and PCB export

Image proposals open a component/net editor with a source preview. Edit references, values, exact symbols, net names and physical pin assignments without writing JSON. Renaming a component updates its pin references; duplicate pin assignments block apply. Advanced JSON remains available. Failed requests preserve attachments and text for retry.

Choose Download → Specctra to open the PCB form. Search installed footprints, check physical pad numbers, enter board/routing dimensions and positions, then download the editable PCB and DSN. The placement preview shows origins, not package outlines; inspect the PCB before routing.

The experimental 3B training profile includes a required measured smoke step for 8 GB GPUs. See [hardware setup](training/HARDWARE.md). Training is separate from the normal desktop install and has not been executed on a CUDA machine here.
