# monaco

2 polygons from `monaco-latest.osm.pbf` on Geofabrik
([source](https://download.geofabrik.de/europe/monaco.html)), filtered by the
[22,075-tag whitelist](https://github.com/NoeFlandre/osm-stats) and
classified by continent + size bin.

| field | value |
|-------|-------|
| country | `monaco` |
| polygons | **2** |
| extract_status | **clean** |
| pbf_date | 2026-01-01 |
| source | `monaco-latest.osm.pbf` |
| Geofabrik extract | <https://download.geofabrik.de/europe/monaco.html> |

## Geometry

The parquet file in this folder (`monaco.parquet`) has the same schema as
the combined `combined/all_world.parquet`. Each row carries the polygon
**geometry as WKT** (default), plus centroid + area + the whitelist-matched tag.

Load with:
```python
import pyarrow.parquet as pq
table = pq.read_table("per_country/monaco/monaco.parquet")
df = table.to_pandas()
```

## Notes

The smallest country in the dataset by polygon count. Only 2 polygons survive the [0.1, 100] km² area filter — Monaco's land area is 2.02 km², so most of the country fits in one large polygon.
