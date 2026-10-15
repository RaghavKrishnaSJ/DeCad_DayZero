import re

with open('/tmp/mithun_readme.md', 'r', encoding='utf-8') as f:
    mithun = f.read()

with open('/Users/raghavkrishna/Desktop/DeCad_DayZero/README.md', 'r', encoding='utf-8') as f:
    current = f.read()

# Extract the custom sections we built
idx_workspaces = current.find('## 🎨 Five Distinct Engineering Workspaces')
idx_prereq = current.find('### Prerequisites')
if idx_prereq == -1:
    idx_prereq = current.find('## Quickstart & Installation')
custom_experiences_and_dispatch = current[idx_workspaces:idx_prereq]

# Extract sections from Mithun's README
idx_screens = mithun.find('## 🖼️ Screenshots')
idx_contents = mithun.find('## 📚 Contents')
idx_after_contents = mithun.find('## 🚀 Quick start (60 seconds)')
idx_credits = mithun.find('## 🙌 Credits, third-party software and license')

screens_section = mithun[idx_screens:idx_contents]
rest_of_guide = mithun[idx_after_contents:idx_credits]

header = """<div align="center">

# DeCad
### The "Cursor for Hardware" · AI-Native Circuit IDE · Specctra DSN Routing Engine

[![KiCad](https://img.shields.io/badge/KiCad-v9.0-2f3b82.svg?logo=kicad)](https://www.kicad.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg?logo=next.js)](https://nextjs.org/)
[![Ngspice](https://img.shields.io/badge/Ngspice-Sim-orange.svg)](https://ngspice.sourceforge.io/)
[![Specctra](https://img.shields.io/badge/Specctra-DSN_PCB-purple.svg)](https://en.wikipedia.org/wiki/SPECCTRA)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

<p align="center">
  <b>DeCad is "Cursor for Circuits" — an agentic, AI-first Integrated Development Environment for hardware engineering.</b><br/>
  Just as Cursor and modern developer tooling revolutionized software development through in-context pair programming and autonomous code synthesis, <b>DeCad brings agentic pair-engineering to physical electronics</b>: synthesizing native KiCad schematics, auto-routing via Specctra DSN, executing live electrical rules checks (ERC), running SPICE transient simulations, and sourcing exact components in real time.
</p>

<!-- Live Animated Experience Showcase -->
<p align="center">
  <img src="evidence/experiences/experiences_showcase.gif" alt="DeCad Multi-Experience Animated Showcase" width="100%" style="border-radius: 8px; border: 1px solid #30363d; box-shadow: 0 16px 36px rgba(0,0,0,0.6);" />
  <br/>
  <em>⚡ Dynamic Multi-Workspace Paradigm: Classic EDA · Studio IDE · Canvas · Review Desk · Simulation Lab</em>
</p>

---

</div>

## The Paradigm: "Cursor for Circuits"

For decades, software engineering evolved from raw terminal editors to intelligent IDEs with real-time linting, package management, and neural autocomplete. In contrast, **hardware engineers remained confined to manual, point-and-click graphical EDA suites from the 1990s**.

| Software Engineering (Cursor / Modern IDEs) | Hardware Engineering with **DeCad** |
| :--- | :--- |
| **Natural Language to Code**: Type intent, AI writes functions | **Natural Language to Schematic**: Type *"Add buck converter with 3.3V out"*, DeCad generates symbols & wiring |
| **Multimodal Inputs**: Screenshot a UI &rarr; React Component | **Multimodal Ingestion**: Photo of a whiteboard sketch &rarr; Native KiCad schematic |
| **Real-time Linting**: Red squiggles on syntax errors | **Real-time ERC**: Live KiCad Electrical Rules Check flags floating pins & shorted rails |
| **Package Managers**: `npm install` or `pip install` | **Automated Component Sourcing**: Auto-maps exact LCSC/JLCPCB part numbers, INR pricing & stock |
| **Compilers & Build Tools**: Webpack, GCC, Vite | **Native EDA Compilers**: KiCad S-Expression synthesis + Specctra DSN autorouter output |
| **Git Version Control**: Clean diffs and GitHub synchronization | **EDA Git Sync**: Semantic commit histories, S-expression diffing, and repo sync |

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
"""

credits_section = """---

## 🙌 Credits, Third-Party Software and License

Developed by **Raghav Krishna ([@JRK14](https://github.com/JRK14))** and **[@Mithunjagan](https://github.com/Mithunjagan)**.

DeCad stands on excellent open source engineering:
- **[KiCad](https://www.kicad.org)** (GPL-3.0+) &mdash; Native schematic capture, S-expression engine, and `pcbnew` Python bindings
- **[Ngspice](https://ngspice.sourceforge.io)** (BSD) &mdash; Interactive transient simulation engine
- **[Qucs-S](https://github.com/ra3xdh/qucs_s)** (GPL-2.0+) &mdash; Circuit simulation GUI and compact device modeling
- **[Freerouting](https://github.com/freerouting/freerouting)** &mdash; Specctra DSN autorouter
- **[Ollama](https://github.com/ollama/ollama)** & **[Qwen2.5-VL](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)** &mdash; Local neural multimodal vision-language model
- **[FastAPI](https://fastapi.tiangolo.com)** & **[Next.js 16](https://nextjs.org)** &mdash; Modern reactive full-stack web architecture
- **[OpenCV](https://opencv.org)** & **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)** &mdash; Deterministic CPU topological extraction
- **[noVNC](https://novnc.com)** &mdash; Headless in-browser KiCad virtual desktop streaming
- **[Mona Sans](https://github.com/github/mona-sans)** & **[IBM Plex](https://github.com/IBM/plex)** (SIL OFL 1.1)

**License:** Proprietary / All rights reserved by the authors until an open-source license is formally designated.

<div align="center">
<br>
<sub>⭐ If DeCad saved you hours of manual CAD drafting, star the repository — it helps bring modern AI workflows to physical electronics engineering!</sub>
</div>
"""

# Assemble table of contents
toc = """## 📚 Contents

- [The Paradigm: "Cursor for Circuits"](#the-paradigm-cursor-for-circuits)
- [Architectural Overview](#architectural-overview)
- [Five Distinct Engineering Workspaces](#-five-distinct-engineering-workspaces-zero-cookie-cutter-layouts)
- [Universal Application Mapping & File Dispatch](#-universal-application-mapping--file-dispatch)
- [Visual Screenshots & Interface Gallery](#%EF%B8%8F-screenshots)
- [Quick start (60 seconds)](#-quick-start-60-seconds)
- [Zero to complete guide](#-zero-to-complete-guide)
  - [1. Install the prerequisites](#1-install-the-prerequisites)
  - [2. Get the code](#2-get-the-code)
  - [3. Configure (optional)](#3-configure-optional)
  - [4. Launch](#4-launch)
  - [5. Sign in](#5-sign-in)
  - [6. Your first circuit](#6-your-first-circuit)
  - [7. Import a schematic photo, PDF or netlist](#7-import-a-schematic-photo-pdf-or-netlist)
  - [8. Review, edit and verify](#8-review-edit-and-verify)
  - [9. Simulate](#9-simulate)
  - [10. Export and make a PCB](#10-export-and-make-a-pcb)
  - [11. Commit and push to GitHub](#11-commit-and-push-to-github)
  - [12. Stop, update, uninstall](#12-stop-update-uninstall)
- [The workbench](#-the-workbench)
- [Keyboard shortcuts](#-keyboard-shortcuts)
- [Assistant command reference](#-assistant-command-reference)
- [Import formats](#-import-formats)
- [Export formats](#-export-formats)
- [PCB, Specctra DSN and Freerouting](#-pcb-specctra-dsn-and-freerouting)
- [Simulation](#-simulation)
- [Desktop applications and the bridge](#-desktop-applications-and-the-bridge)
- [GitHub integration](#-github-integration)
- [Local AI and the vision adapter](#-local-ai-and-the-vision-adapter)
- [Configuration reference](#-configuration-reference)
- [Architecture](#-architecture)
- [HTTP API reference](#-http-api-reference)
- [Development](#-development)
- [Testing and CI](#-testing-and-ci)
- [Troubleshooting & FAQ](#-troubleshooting--faq)
- [Security model](#-security-model)
- [Scope and limitations](#-scope-and-limitations)
- [Credits, third-party software and license](#-credits-third-party-software-and-license)

---
"""

full_readme = (
    header +
    custom_experiences_and_dispatch +
    "\n---\n\n" +
    screens_section +
    "\n---\n\n" +
    toc +
    "\n\n" +
    rest_of_guide +
    credits_section
)

with open('/Users/raghavkrishna/Desktop/DeCad_DayZero/README.md', 'w', encoding='utf-8') as f:
    f.write(full_readme)

print(f"Generated ultimate README! Total lines: {len(full_readme.splitlines())}, Bytes: {len(full_readme)}")
