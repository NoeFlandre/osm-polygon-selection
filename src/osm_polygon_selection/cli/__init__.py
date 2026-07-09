"""Canonical CLI modules.

Each public script (``scripts/*.py``) is a thin wrapper around
one :mod:`cli` module. The wrapper just imports ``main`` and
calls it; the actual argparse parsing + business logic lives here.

Submodules:

- :mod:`build_dataset`
- :mod:`make_split`
- :mod:`organize_dataset`
- :mod:`sample_for_map`
- :mod:`split_parquets`
- :mod:`stage0_extract`
- :mod:`stage1_build_whitelist`
- :mod:`stage2_filter`
- :mod:`stage3_classify`
- :mod:`upload_to_hf`
- :mod:`visualize`
"""
