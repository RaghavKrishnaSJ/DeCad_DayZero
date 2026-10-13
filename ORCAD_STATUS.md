The requested .DSN has since been clarified as Specctra PCB autorouter format. See SPECCTRA.md for the implemented exporter. The following describes the separate OrCAD schematic format.

# PDF/image recognition and OrCAD output

## Current result

Native editable OrCAD `.DSN` generation is **not available**. This package does not contain a verified OrCAD writer, Capture installation, or validated Capture conversion service. Do not rename EDIF, JSON or KiCad files to `.DSN`.

Default CPU OCR proposes component labels/values for review; it does not establish wire connectivity. Optional vision proposes components and physical pin/net connections, but general recognition accuracy has not passed a benchmark. Image and PDF data are untrusted source content, not instructions. Every proposal needs source review before applying it. Vision PDF imports support one page per request until page hierarchy/net merging is validated. OCR PDF imports are bounded to ten pages; raster sizes are checked before allocation.

Reviewed graphs can generate editable native KiCad designs and connectivity exports. The Nets download menu includes an OrCAD handoff ZIP with circuit JSON, connectivity EDIF, SHA256 manifest and instructions. Its EDIF contains NETLIST views, **not graphical schematic views**. Capture EDIF support does not establish that this particular connectivity-only file will create an editable schematic.

## Required native DSN completion

Provide a licensed Windows OrCAD Capture environment and its version. Implement and validate a Capture-side adapter against that installation's documented APIs or supported graphical import format: map library symbols and physical pins, create pages/placements/wires/properties, save native DSN, reopen it in Capture, then compare exported component/value/pin/net data against the reviewed source graph. Include hierarchy, junction/crossover, reference ambiguity and unsupported symbol cases. Do not mark conversion supported until real saved/reopened files pass those tests.

This work is additional to training and platform/UI acceptance. User machines can use a separately hosted conversion service, but that requires an actual configured/licensed host; no service is deployed by this package. Without it, KiCad is the currently implemented editable format.

Primary sources:
- Cadence EDIF import discussion: https://community.cadence.com/cadence_technology_forums/pcb-design/f/allegro-x-capture-cis/51987/import-third-party-designs-to-orcad-capture/1385543
- Cadence discussion demonstrating netlist-only EDIF can yield no schematic: https://community.cadence.com/cadence_technology_forums/pcb-design/f/pcb-design/40964/importing-mentor-graphics-dxdesigner-schematics-into-orcad-v17-2/1358530

These establish the need for actual graphical/native conversion acceptance; they do not validate this package's output in Capture.
