"""Backwards-compat launcher for ``scripts/dataset/build_dataset.py``.

The root ``scripts/build_dataset.py`` module is the **same**
module object that downstream tests mutate (``bd.HDD``,
``bd.PROC``, etc.). To preserve that behavior, the launcher
executes the canonical ``scripts/dataset/build_dataset.py``
source in the root module's own namespace, so module-level
``HDD``/``PROC``/``GEOMETRY_ENCODING`` reassignments in tests
take effect at call time.

When invoked as ``__main__``, the launcher forwards to the
canonical module via :func:`runpy.run_path`.
"""

from __future__ import annotations

import runpy
from pathlib import Path

_CANONICAL = Path(__file__).resolve().parent / "dataset" / "build_dataset.py"

# Execute the canonical source in THIS module's namespace so
# that ``import scripts.build_dataset as bd`` returns the same
# object, and ``bd.HDD = tmp_path`` affects ``bd.pbf_date_for``.
_source = _CANONICAL.read_text()
_code = compile(_source, str(_CANONICAL), "exec")
exec(_code, globals())

if __name__ == "__main__":
    runpy.run_path(str(_CANONICAL), run_name="__main__")
