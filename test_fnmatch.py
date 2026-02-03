
import fnmatch
from pathlib import Path

patterns = ["dashboard/**", "package/dist/**", "dist/**"]
paths = [
    "dashboard/node_modules/error.js",
    "package/dist/error.js",
    "package/lib/error.d.ts",
    "dist/utils.js"
]

print("Testing fnmatch:")
for p in paths:
    for pat in patterns:
        match = fnmatch.fnmatch(p, pat)
        print(f"fnmatch('{p}', '{pat}') = {match}")

print("\nTesting Path.match:")
for p in paths:
    path_obj = Path(p)
    for pat in patterns:
        try:
            match = path_obj.match(pat)
            print(f"Path('{p}').match('{pat}') = {match}")
        except Exception as e:
            print(f"Path('{p}').match('{pat}') failed: {e}")
