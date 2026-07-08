# per_country/

2 country folders (one folder per country). Each contains:

- `<country>.parquet` — all polygons for that country (schema matches the root README).
- `README.md` — country-specific notes (pbf date, source sub-PBFs if any, polygon count).

Pull a single country with:
```python
import pyarrow.parquet as pq
t = pq.read_table("per_country/france/france.parquet")
```
