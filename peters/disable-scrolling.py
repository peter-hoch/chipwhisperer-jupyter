#!/bin/python

import json

path = "GlitchTimingExample-interactive-timing-example.ipynb"
with open(path, encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        cell.setdefault("metadata", {})["scrolled"] = False

with open(path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write("\n")

