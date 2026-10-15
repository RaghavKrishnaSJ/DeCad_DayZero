<div align="center">

# DeCad
### The "Cursor for Hardware" &middot; AI-Native Circuit IDE &middot; Specctra DSN Routing Engine

[![KiCad](https://img.shields.io/badge/KiCad-v9.0-2f3b82.svg?logo=kicad)](https://www.kicad.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg?logo=next.js)](https://nextjs.org/)
[![Ngspice](https://img.shields.io/badge/Ngspice-Sim-orange.svg)](https://ngspice.sourceforge.io/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

<p align="center">
  <b>DeCad is "Cursor for Circuits" &mdash; an agentic, AI-first Integrated Development Environment for hardware engineering.</b><br/>
  Just as Cursor and Antigravity modernized software development through in-context pair programming and autonomous code synthesis, <b>DeCad brings agentic pair-engineering to physical electronics</b>: synthesizing native KiCad schematics, auto-routing via Specctra DSN, running simulation checks, and sourcing real components in real time.
</p>

<!-- Live Animated Experience Showcase -->
<p align="center">
  <img src="evidence/experiences/experiences_showcase.gif" alt="DeCad Multi-Experience Animated Showcase" width="100%" style="border-radius: 8px; border: 1px solid #30363d; box-shadow: 0 16px 36px rgba(0,0,0,0.6);" />
  <br/>
  <em>⚡ Dynamic Workspace Experiences: Classic EDA &middot; Studio IDE &middot; Canvas &middot; Review Desk &middot; Simulation Lab</em>
</p>

---

</div>

## The Paradigm: "Cursor for Circuits"

For decades, software development had modern IDEs with autocomplete, linting, and AI pair-programmers, while **hardware designers remained trapped in manual, point-and-click graphical EDA suites from the 1990s**.

| Software Engineering (Cursor / Antigravity) | Hardware Engineering with **DeCad** |
| :--- | :--- |
| **Natural Language to Code**: Type what you want, AI generates functions | **Natural Language to Schematic**: Type *"Add buck converter with 3.3V out"*, DeCad generates symbols & wiring |
| **Multimodal Inputs**: Screenshot a Figma UI &rarr; React Component | **Multimodal Ingestion**: Photo of a whiteboard sketch &rarr; Native KiCad schematic |
| **Real-time Linting**: Red squiggles on syntax errors | **Real-time ERC**: Live KiCad Electrical Rules Check flags floating pins & shorted rails |
| **Package Managers**: `npm install` or `pip install` | **Automated Component Sourcing**: Auto-maps exact LCSC/JLCPCB part numbers, INR pricing & stock |
| **Compilers & Build Tools**: Webpack, GCC, Vite | **Native EDA Compilers**: KiCad S-Expression synthesis + Specctra DSN autorouter output |
| **Git Version Control**: Clean diffs and GitHub synchronization | **EDA Git Sync**: Semantic commit histories and direct repository synchronization |

---

## Architectural Overview

Traditional circuit engineering suffers from severe fragmentation: schematic capture, netlist generation, simulation, routing, and component procurement occur in disparate, incompatible tools. **DeCad solves this by providing a unified pipeline from initial multimodal concept to DRC-clean PCB fabrication files.**

```mermaid
flowchart TD
    subgraph INGESTION["1. Multimodal Ingestion Layer"]
        A1["Hand-drawn Sketches / PNG / JPG"] --> B1["Dual Vision Engine"]
        A2["Engineering Schematics / Multi-page PDF"] --> B1
        A3["Natural Language Prompt / Chat"] --> B2["NLP EDA Synthesizer"]
        A4["Legacy SPICE Netlist / CSV"] --> B3["Deterministic Parser"]
    end

    subgraph ENGINE["2. Core Synthesis & Validation Engine"]
        B1 --> C["Circuit Graph Representation<br/>(Components, Pins, Nets)"]
        B2 --> C
        B3 --> C
        C --> D["Interactive Review Gate<br/>(Visual Sanity & Net Verification)"]
        D --> E["KiCad S-Expression Engine<br/>(engine.py / pcbnew bindings)"]
        E --> F["KiCad Native ERC<br/>(Electrical Rules Checker CLI)"]
    end

    subgraph OUTPUTS["3. Output & Handoff Ecosystem"]
        F --> G1["KiCad Schematic (.kicad_sch)"]
        F --> G2["KiCad PCB (.kicad_pcb)"]
        F --> G3["Specctra DSN Autorouter (.dsn)"]
        F --> G4["LCSC / JLCPCB BOM (Pricing & Stock)"]
        F --> G5["Ngspice Interactive Waveform Scope"]
        F --> G6["Git Revision Sync (Private GitHub Repo)"]
    end

    style INGESTION fill:#1e222a,stroke:#4a5568,color:#fff
    style ENGINE fill:#161b22,stroke:#58a6ff,color:#fff
    style OUTPUTS fill:#0d1117,stroke:#3fb950,color:#fff
```

---

## How Complex EDA Workflows Are Simplified

### 1. Optical Schematic to Clean Netlists (Eliminating OCR Hallucinations)
- **The Challenge**: Standard Computer Vision or Large Multimodal Models (LMMs) hallucinate connections, blend intersecting wires, and misread component subscripts.
- **DeCad's Solution**: A hybrid dual-engine architecture:
  - **Deterministic CPU Tier**: OpenCV morphological contour analysis detects symbol geometry (resistors, caps, diodes, IC packages) while Tesseract OCR isolates reference designators.
  - **Fine-Tuned Qwen2.5-VL LoRA Tier**: A 4-bit LoRA vision-language model trained on audited topological netlist pairs (`training/prepared_amsnet`) for complex multi-gate ICs.
  - **The Circuit Review Gate**: Neural outputs are never written directly to the CAD file. DeCad renders an interactive side-by-side reconciliation dialog (`CircuitReview.js`) allowing engineers to verify physical pin mappings before CAD commit.

### 2. Auto-Bounding & S-Expression Synthesis
- **The Challenge**: Programmatically generated KiCad schematic symbols often drift out of sheet borders or overlap pin coordinates, causing catastrophic ERC failures.
- **DeCad's Solution**: The backend placement algorithm (`engine.py`) automatically maps component bounding boxes across row/column grids bounded to standard A4 sheet dimensions ($X \in [38, 230]\text{ mm}, Y \in [35, 175]\text{ mm}$), wrapping dynamically as part density scales.

### 3. Native Specctra DSN PCB Export (Direct Freerouting Bridge)
- **The Challenge**: Converting schematic nets into physical board autorouting formats usually requires tedious manual footprint assignment, board edge definition, and footprint loading in separate GUI applications.
- **DeCad's Solution**: Uses Debian's native `pcbnew` Python engine (`specctra_worker.py`) directly inside Docker to auto-generate board outlines, assign physical packages from the 37,000+ official KiCad footprint library, establish net topology, and emit standard Specctra `.dsn` files with single-click download.

```mermaid
sequenceDiagram
    autonumber
    participant U as User / Engineer
    participant FE as DeCad Workbench (Next.js)
    participant BE as FastAPI EDA Core
    participant KC as KiCad CLI / pcbnew
    participant DB as Components DB (46k symbols)

    U->>FE: Upload sketch / prompt "Place 74LS240 buffer"
    FE->>BE: POST /projects/{pid}/assistant/chat
    BE->>DB: Query footprint & pinout specification
    DB-->>BE: Package_DIP:DIP-20_W7.62mm + Pin Map
    BE->>KC: Generate S-Expression & Execute ERC
    KC-->>BE: 0 Violations, Netlist Verified
    BE-->>FE: Vector SVG Render + Sourced BOM + DSN Ready
    FE-->>U: Live Schematic Canvas & Downloadable .DSN
```

---

## Key Capabilities & Feature Matrix

| Feature | DeCad Implementation | Industry Standard / Competitors |
| :--- | :--- | :--- |
| **CAD Format** | Native KiCad 9 `.kicad_sch` & `.kicad_pcb` | Proprietary closed formats or lossy SVG |
| **Autorouter Export** | Specctra DSN (`.dsn`) via native `pcbnew` | Requires manual footprint assignment & export |
| **Component Catalog** | Auto-enriched from 46,501 symbols + real LCSC Part IDs | Manual BOM typing and web lookup |
| **Electrical Checking** | Real-time KiCad CLI ERC with violation badge counts | Simple visual display without electrical rule verification |
| **Simulation** | Interactive Ngspice scope (transient analysis) | Separate desktop SPICE installation required |
| **Version Control** | Integrated per-project Git with GitHub OAuth Sync | Manual file duplication / ZIP archives |
| **Theme Engine** | 10 live UI engineering themes (Forge, Monokai, CRT Matrix, etc.) | Fixed single theme |

---

## Workbench Interface Map

```text
+----------------------------------------------------------------------------------------+
|  DeCad WORKBENCH   Test1 / rev 6c9eb70   [Theme: Forge v]   o KiCad ready  o CPU ready  |
+---------------+--------------------------------------------------------+---------------+
|  PROJECTS     |  [Schematic] [Source] [BOM (26)] [Nets] [Checks] [Scope] |  AI ASSISTANT |
|  > Test1      +--------------------------------------------------------+  "Add 10k R1" |
|  > Demo       |                                                        |  [Attachment] |
|               |             KICAD VECTOR SCHEMATIC CANVAS              |               |
|  FILES        |                                                        |  Uploaded:    |
|  * board.sch  |                  [U1: 74LS240 Buffer]                  |  [Image Card] |
|  * board.pcb  |                         |                              |  (Double-click|
|  * board.dsn  |                    (Net: DATA_0)                       |   to zoom)    |
|               |                         |                              |               |
|  LIBRARIES    |                  [R1: 10k Resistor]                    |  [Apply Net]  |
|  * Import Doc |                                                        |               |
+---------------+--------------------------------------------------------+---------------+
```

---

## 🎨 Five Distinct Engineering Workspaces (Zero Cookie-Cutter Layouts)

Unlike standard software tools that simply toggle CSS color variables, **DeCad re-architects the layout, tool rails, diagnostics docks, and interaction models for each engineering phase**:

<table>
  <tr>
    <td width="50%">
      <h3 align="center">1. Classic EDA (Engineering Desktop)</h3>
      <a href="evidence/experiences/experience-classic.png"><img src="evidence/experiences/experience-classic.png" alt="Classic EDA Desktop" width="100%"/></a>
      <p><b>Focus:</b> Capture &middot; Inspect &middot; Build</p>
      <ul>
        <li>Authentic light engineering aesthetic modeled after Cadence OrCAD / Altium Designer.</li>
        <li>Dual-tier command ribbons with persistent physical pin property inspector.</li>
        <li>Split-pane build output, console netlist explorer, and quick prompt execution dock.</li>
      </ul>
    </td>
    <td width="50%">
      <h3 align="center">2. Studio IDE (Developer Dark Flow)</h3>
      <a href="evidence/experiences/experience-ide.png"><img src="evidence/experiences/experience-ide.png" alt="Studio IDE" width="100%"/></a>
      <p><b>Focus:</b> Explore &middot; Edit &middot; Diagnose</p>
      <ul>
        <li>Full dark document workspace with project hierarchy explorer and breadcrumbs.</li>
        <li>Dockable real-time diagnostic problems panel with ERC violation tracking.</li>
        <li>Direct integration with AI prompt engineering sidebar and automated model routing.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3 align="center">3. Canvas (Distraction-Free Drafting)</h3>
      <a href="evidence/experiences/experience-canvas.png"><img src="evidence/experiences/experience-canvas.png" alt="Canvas Workspace" width="100%"/></a>
      <p><b>Focus:</b> Draw &middot; Navigate &middot; Focus</p>
      <ul>
        <li>Maximized high-resolution vector canvas with radial grid backdrop.</li>
        <li>Floating vertical tool rail for instant placement, routing, and symbol selection.</li>
        <li>On-demand modal assistant drawer that minimizes automatically during deep CAD drafting.</li>
      </ul>
    </td>
    <td width="50%">
      <h3 align="center">4. Review Desk (Dual Verification Gate)</h3>
      <a href="evidence/experiences/experience-review.png"><img src="evidence/experiences/experience-review.png" alt="Review Desk" width="100%"/></a>
      <p><b>Focus:</b> Compare &middot; Correct &middot; Approve</p>
      <ul>
        <li>Side-by-side synchronized comparison of original input (PDF/image) vs synthesized KiCad circuit.</li>
        <li>4-point verification checklist (faint parts, reference designators, rail polarity, pin connections).</li>
        <li>Zero-blind-commit guarantee: review net differences before committing to CAD.</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td colspan="2">
      <h3 align="center">5. Simulation Lab (Hardware Testbench)</h3>
      <p align="center"><a href="evidence/experiences/experience-lab.png"><img src="evidence/experiences/experience-lab.png" alt="Simulation Lab" width="90%"/></a></p>
      <p align="center"><b>Focus:</b> Measure &middot; Simulate &middot; Analyze</p>
      <ul>
        <li>Integrated interactive transient analyzer with embedded multi-channel digital oscilloscope.</li>
        <li>Live signal probe readings ($V_{\text{IN}}$, $V_{\text{OUT}}$) and real-time waveform acquisition.</li>
        <li>Seamless one-click dispatch to native external simulators (Ngspice, LTspice, Qucs-S).</li>
      </ul>
    </td>
  </tr>
</table>

---

## ⚡ Universal Application Mapping & File Dispatch

DeCad features an automated file association engine that inspects uploaded attachments or workspace files, automatically recommending the native EDA desktop application while allowing full engineer override:

```mermaid
graph LR
    File["Input File (.kicad_sch, .cir, .asc, .sch, .dsn)"] --> Detection["Format & Extension Analyzer"]
    Detection --> AutoMap{"Recommended Application"}
    AutoMap -->|*.kicad_sch / *.kicad_pcb| App1["KiCad 9.0 Suite"]
    AutoMap -->|*.cir / *.sp / *.net| App2["Ngspice Interactive"]
    AutoMap -->|*.asc / *.raw| App3["LTspice Simulator"]
    AutoMap -->|*.sch (Qucs) / *.dpl| App4["Qucs-S Universal GUI"]
    AutoMap -->|*.dsn| App5["Freerouting Autorouter"]
    Detection --> Override["Manual Engineer Selection & Format Conversion"]
```

* **Direct Original Launch**: Launch the exact file in its dedicated native host application via the Desktop Bridge.
* **Intelligent Circuit Handoff**: Synthesize and translate current project schematics to any external tool on the fly.

---

### Prerequisites
- [Docker Desktop](https://www.docker.com/) (allocated with at least 4 GB RAM)
- Git command line tools

### Launch in 2 Steps
```bash
# 1. Clone repository
git clone https://github.com/JRK14/DeCad.git
cd DeCad

# 2. Build and launch containers
docker compose up -d --build
```

Access the application in your browser:
- **Workbench Interface**: [http://localhost:3100](http://localhost:3100)
- **FastAPI Core Docs**: [http://localhost:8100/docs](http://localhost:8100/docs)
- **Headless KiCad Virtual Desktop**: [http://localhost:6180](http://localhost:6180)

---

## Directory Structure

```text
DeCad/
├── backend/
│   ├── app/
│   │   ├── main.py            # RESTful API, BOM enrichment, DSN export
│   │   ├── engine.py          # KiCad S-Expression symbol placement & bounds
│   │   ├── specctra.py        # Specctra DSN export orchestrator
│   │   └── specctra_worker.py # pcbnew Python bindings for .dsn export
│   └── workspaces/            # User project files and Git histories
├── frontend/
│   └── app/
│       ├── page.js            # Main EDA workbench application
│       ├── globals.css        # Responsive styling and 10 design themes
│       └── BoardExport.js     # PCB planning and layout configurator
├── checkpoints/
│   └── circuit-lora/adapter/  # Qwen2.5-VL 4-bit LoRA adapter weights
├── training/
│   ├── Train_DeCad_Colab.ipynb  # GPU fine-tuning notebook
│   ├── finetune.py            # CUDA LoRA training pipeline
│   └── evaluate.py            # Test split benchmark evaluator
├── libraries/                 # 46k+ KiCad symbols and SQLite database
├── docker-compose.yml         # Container configuration
└── TEAMMATE_GUIDE.txt         # Teammate onboarding and feature guide
```

---

## License & Attribution

Developed by **Raghav Krishna ([@JRK14](https://github.com/JRK14))**. All rights reserved.
Built on top of KiCad EDA, Ngspice, and Qwen Vision Architecture.
