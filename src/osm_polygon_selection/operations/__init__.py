"""Maintainer-only operational helpers for HDD-side pipelines.

These functions are used by the ``scripts/operations/*.py`` shell
and Python entry points. They are NOT part of the public data-
processing API.

Submodules:

- :mod:`.downloads` — PBF download helpers (curl wrappers).
- :mod:`.subprocesses` — subprocess helpers for stage0/2/3 invocation.
- :mod:`.europe_loop` — multi-country European union orchestration.
- :mod:`.regions` — regional sub-PBF batch processing.
"""
