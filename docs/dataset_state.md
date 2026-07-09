# Dataset State (Historical Snapshot)

**Historical reference only.** The numbers below were true at the
time of the 78-country European / African seed snapshot. The
current published dataset has grown beyond that scope (see the
top-of-README summary for the latest published numbers). For the
authoritative counts, consult the published HuggingFace dataset
manifest.

For *why* or *how*, see the other docs in `docs/`
(especially `internal/AGENT_HANDOFF.md`, `architecture.md`,
`PERFORMANCE.md`, `internal/AFRICA_ROLLOUT.md`).

---

## Historical numbers (78-country snapshot)

| Metric                          | Value             |
|---------------------------------|------------------:|
| Total countries                 |          **78**   |
| Total polygons                  |      **7,490,239**|
| Combined parquet size (zstd)    |         ~6.0 GB   |
| Train / val / test split        | 5,992,225 / 747,123 / 750,891 |
| HuggingFace files               |              167 |
| HuggingFace repo                | `NoeFlandre/osm-polygon-selection` |

Historical breakdown by region:

| Region              | Countries | Polygons |
|---------------------|----------:|---------:|
| Europe              |        49 | 7,302,782 |
| North Africa        |         4 |   96,768 |
| Sub-Saharan Africa  |        25 |   90,689 |
| **Total**           |    **78** | **7,490,239** |

(Approximate continent breakdown; per-country numbers are exact.)

---

## Historical coverage (78 countries)

**49 European countries**: albania, andorra, austria, azores,
belarus, belgium, bosnia-herzegovina, bulgaria, croatia, cyprus,
czech-republic, denmark, estonia, faroe-islands, finland, france,
georgia, germany, greece, guernsey-jersey, hungary, iceland,
ireland-and-northern-ireland, isle-of-man, italy, kosovo, latvia,
liechtenstein, lithuania, luxembourg, macedonia, malta, moldova,
monaco, montenegro, netherlands, norway, poland, portugal, romania,
serbia, slovakia, slovenia, spain, sweden, switzerland, turkey,
ukraine, united-kingdom.

**29 African countries**: morocco, tunisia, algeria, libya,
botswana, mayotte, guinea-bissau, sierra-leone, liberia,
togo, benin, mauritania, niger, cape-verde, gabon,
congo-brazzaville, burundi, equatorial-guinea, djibouti, eritrea,
rwanda, namibia, swaziland, seychelles, comores,
sao-tome-and-principe, mauritius, canary-islands,
saint-helena-ascension-and-tristan-da-cunha.

---

## Storage

| Location                                | Size    | Notes               |
|-----------------------------------------|--------:|---------------------|
| `OSM_DATA_ROOT` (maintainer: `/Volumes/Seagate M3/osm-polygon-selection/`) | ~200 GB | Source of truth     |
| `OSM_DATASET_DIR` (maintainer: `/Volumes/Seagate M3/osm-polygon-selection/dataset/`) | per-build | Final dataset dir |

The pipeline reads PBFs and writes parquet to the operator-supplied
HDD path only. Never to the local SSD. Public users consuming the
published dataset on Hugging Face do not need these env vars. See
`docs/internal/AGENT_HANDOFF.md` for the maintainer storage policy.

---

## Test status

| Suite                                  | Tests |
|----------------------------------------|------:|
| Selected passing                       |  505  |
| Deselected (flaky wall-clock)          |    1  |
| **Collected**                          | **506** |

Run:
```bash
uv run pytest tests/ \
  --deselect tests/stages/test_extract_perf.py::TestWallClockCap::test_wall_clock_cap_stops_clean
```

---

## In-progress work

**Africa rollout**: 29 of 55 African countries done. 25 remaining
(Nigeria 678 MB through Central African Republic 94 MB). Their
PBFs are downloaded to the HDD but stage 0 was interrupted;
`processed/<country>/` dirs were cleaned up. See
`docs/internal/AFRICA_ROLLOUT.md` for the queue and the resume plan.

(See git log for recent commits; this section is auto-trimmed to
the latest quality-uplift history.)

---

## How to update this doc

This file is intentionally a historical snapshot. For current
numbers, see the published HuggingFace dataset manifest and the
top-of-README summary. The `manifest.json` and the
auto-generated `dataset/README.md` are the machine-readable
sources of truth at publication time.
