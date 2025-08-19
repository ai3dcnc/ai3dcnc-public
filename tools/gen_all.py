# tools/gen\_all.py

# Concatenate parsers/ and builders/ into parsers\_all.py and builders\_all.py

# AUTO-GENERATED SCRIPT

import datetime

PARSERS = \[
"parsers/parser\_mesh.py",
"parsers/parser\_scene.py",
"parsers/parser\_materials.py",
"parsers/parser\_collections.py",
"parsers/parser\_boolops.py",
"parsers/parser\_gn.py",
"parsers/parser\_scene\_view\.py",
]

BUILDERS = \[
"builders/builder\_mesh.py",
"builders/builder\_scene\_import.py",
"builders/builder\_scene\_view\.py",
"builders/builder\_materials.py",
"builders/builder\_collections.py",
"builders/builder\_gn\_overrides.py",
"builders/builder\_boolops.py",
]

HEADER = "# AUTO-GENERATED. DO NOT EDIT.\n# UTC: {}\n"

def concat(files, out\_file):
with open(out\_file, "w", encoding="utf-8") as out:
out.write(HEADER.format(datetime.datetime.utcnow().isoformat()))
for f in files:
out.write(f"\n# ===== file: {f} =====\n")
with open(f, "r", encoding="utf-8") as src:
out.write(src.read())
out.write(f"\n# ===== end {f} =====\n")

if **name** == "**main**":
concat(PARSERS, "parsers\_all.py")
concat(BUILDERS, "builders\_all.py")
print("\[SUMMARY] parsers\_all.py and builders\_all.py generated.")
