"""Offline checks of module manifests, Python syntax, XML, and ACL structure."""
import ast
import csv
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
modules = sorted(root.glob("flousflow_auditlog*"))
count = 0
for module in modules:
    manifest_path = module / "__manifest__.py"
    if not manifest_path.is_file():
        continue
    manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"].startswith("20.0."), manifest_path
    assert manifest["license"] == "AGPL-3", manifest_path
    for item in manifest.get("data", []):
        assert (module / item).is_file(), (module, item)
    for path in module.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count += 1
    for path in module.rglob("*.xml"):
        ET.parse(path)
        count += 1
    for path in module.rglob("*.js"):
        node = shutil.which("node")
        if not node:
            raise AssertionError("Node.js is required to validate JavaScript syntax")
        subprocess.run([node, "--check", str(path)], check=True)
        count += 1
    access_files = (
        path for path in module.rglob("*.csv")
        if path.name in {"ir.model.access.csv", "ir.access.csv"}
    )
    for path in access_files:
        with path.open(encoding="utf-8", newline="") as stream:
            rows = csv.DictReader(line for line in stream if line.strip())
            ids = set()
            for row in rows:
                assert None not in row and all(value is not None for value in row.values()), (path, row)
                assert row["id"] not in ids, (path, row["id"])
                ids.add(row["id"])
                if "operation" in row:
                    assert set(row["operation"]) <= set("crud"), (path, row)
                    assert row["operation"], (path, row)
                    assert row["model_id"], (path, row)
                    assert row["group_id/id"] == "" or "." in row["group_id/id"], (path, row)
                else:
                    for col in ("perm_read", "perm_write", "perm_create", "perm_unlink"):
                        assert row[col] in ("0", "1"), (path, row)
        count += 1
print(f"Checked {count} Python, XML and ACL files")
