# Background and Inspiration

## Relation between KEROS and NodeKit

The **NodeKit** project demonstrated that Geometry Nodes (GN) can be exported and represented in JSON format, primarily to support **sharing and versioning** of GN setups between Blender users. In this broader sense, the concept of serializing GN into JSON served as a **source of inspiration** for KEROS.

However, **KEROS pursues a fundamentally different objective**: defining an **industrial data contract** that transforms GN into robust, machine‑readable data for **CNC and AI workflows**. Unlike NodeKit, KEROS introduces:

* **Safe fallback for unknown nodes** (`is_unknown=true`), including capture of RNA properties and default inputs.
* **SHA‑1 fingerprinting** of GN graphs (nodes + links) to ensure reproducibility and detect modifications.
* **Integration with other parsers** (meshes, materials, collections, scene view) to build a full scene export.
* **Industrial focus**: output JSON designed for downstream CNC pipelines (Vitap/TPA), not just human sharing.

### Positioning

* **NodeKit** is oriented towards **collaborative workflows** and asset management in artistic contexts.
* **KEROS** extends the GN→JSON paradigm into the **industrial and AI‑assisted manufacturing domain**, establishing a repeatable, contract‑based pipeline.

### Summary

While both projects share the initial idea of GN→JSON serialization, KEROS differentiates itself by **industrial scope, robustness, and full pipeline integration**. NodeKit remains acknowledged as an early proof that GN data can be structured in JSON, whereas KEROS builds on that concept to deliver a **production‑ready workflow** for CNC and AI.
