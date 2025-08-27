# Memory Sets & Lazy-Loading Manifest (proposal)

Scop: manifesturi pe domenii + cache local cu sha1 și încărcare la cerere din RAW. Subsetul LITE va folosi doar: manifest-uri (`manifests/*.json`), loader (`tools/mem_tools.py`), sha1 per fișier și per set, evenimente `[SUMMARY]`.

## Draft complet (PRO)
```json
{ "meta": { "name": "Memory Sets & Lazy-Loading Manifest (for AI3DCNC)", "version": "0.3.0", "updated": "2025-08-27", "purpose": "Define domain-scoped manifests and a cache protocol for on-demand loading of knowledge/code bundles from GitHub RAW, with integrity, recency, and minimal bandwidth use." },
  "rationale": { "goals": ["Load only what a task needs (room, hardware, cutouts, decor, render).","Prefer local cache; revalidate via HTTP conditional requests (ETag/Last-Modified).","Integrity by content hash (sha1) recorded per file and aggregated per set.","Determinism via pinned refs (commit SHA) when required; fallback to branch/tag for velocity.","Compact telemetry using single-line [SUMMARY] events."],
                  "non_goals": ["No full-repo checkout.","No long-lived background workers.","No arbitrary path guessing beyond manifest entrypoints/aliases."] },
  "commands": { "manifest": "...", "manifest_domain": "...", "mem_load": "...", "mem_status": "...", "mem_refresh": "...", "mem_clear": "..." },
  "validation": { "manifest_set_required": ["raw_base","entrypoints","aliases","deps","tag","version"],
                  "constraints": { "raw_base": "HTTPS URL ending with '/'", "entrypoints": "bundle files", "aliases": "short→path", "deps": "direct only", "tag": "main or commit SHA", "version": "semver-like" } },
  "cache": { "policy": { "strategy": "LRU","max_sets": 5,"ttl_seconds": 86400,"offline_mode": false,"respect_etag": true,"respect_last_modified": true,"conditional_get": true,"compute_sha1": "sha1(file); sha1(tree)" },
             "revalidate": { "http_headers_out": ["If-None-Match","If-Modified-Since"], "on_304": "keep", "on_200": "replace" },
             "telemetry": { "summary_templates": ["[SUMMARY] manifest OK; sha1=<...>; entrypoints=<n>","[SUMMARY] manifest domain <set>: OK source=<remote|cached> ts=<iso> sha1=<...> files=<n>","[SUMMARY] mem load <set>: OK source=<remote|cached> ts=<iso> sha1=<...> files=<n>"] } },
  "http": { "raw_base": "https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/main/",
            "notes": ["Prefer conditional requests","Use commit-SHA URLs for strict freshness","Avoid cache-busting querystrings"] },
  "integrity": { "file_hash": "sha1(hex)", "set_hash": "sha1(name+\\n+joined(sorted(file_sha1s)))", "report": "[SUMMARY] with top-level sha1" },
  "security": { "principles": ["Least privilege","Never echo tokens","Pin commits for reproducibility"] },
  "sets": [
    { "name":"core","version":"0.1","tag":"main","raw_base":"https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/main/","entrypoints":["parsers_all.py","builders_all.py"],"aliases":{},"deps":[] },
    { "name":"room","version":"0.1","tag":"main","raw_base":"https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/main/","entrypoints":["keros_room_template_en.py"],"aliases":{"room_template_en":"keros_room_template_en.py"},"deps":["core"] },
    { "name":"hardware","version":"0.1","tag":"main","raw_base":"https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/main/","entrypoints":[],"aliases":{},"deps":["core"] },
    { "name":"cutouts","version":"0.1","tag":"main","raw_base":"https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/main/","entrypoints":[],"aliases":{},"deps":["core"] },
    { "name":"decor","version":"0.1","tag":"main","raw_base":"https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/main/","entrypoints":[],"aliases":{},"deps":["core"] },
    { "name":"render","version":"0.1","tag":"main","raw_base":"https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/main/","entrypoints":[],"aliases":{},"deps":["core"] }
  ],
  "examples": { "cli": ["manifest","manifest domain room","mem load room","mem status","mem refresh room","mem clear all"],
                "expected_summaries": ["[SUMMARY] manifest OK; sha1=<...>; entrypoints=3","[SUMMARY] manifest domain room: OK source=remote ts=<iso> sha1=<...> files=1","[SUMMARY] mem load room: OK source=cached ts=<iso> sha1=<...> files=1"] },
  "compatibility": { "pinned_example": { "raw_base": "https://raw.githubusercontent.com/ai3dcnc/ai3dcnc-public/<commit-sha>/" },
                     "fallbacks": ["If conditional GET unsupported, short TTL and manual refresh"] }
}
