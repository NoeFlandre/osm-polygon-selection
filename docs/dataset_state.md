# Dataset State (live)

**This document is updated on every commit that changes the dataset.**

It captures the current numbers; for *why* or *how*, see the other
docs in `docs/` (especially `AGENT_HANDOFF.md`, `ARCHITECTURE.md`,
`PERFORMANCE.md`, `AFRICA_ROLLOUT.md`).

---

## Current numbers (as of commit pending, 3 July 2026)

| Metric                          | Value             |
|---------------------------------|------------------:|
| Total countries                 |          **78**   |
| Total polygons                  |      **7,490,239**|
| Combined parquet size (zstd)    |         ~6.0 GB   |
| Train / val / test split        | 5,992,225 / 747,123 / 750,891 |
| HuggingFace files               |              167 |
| HuggingFace repo                | `NoeFlandre/osm-polygon-selection` |

Breakdown by region:

| Region              | Countries | Polygons |
|---------------------|----------:|---------:|
| Europe              |        49 | 7,302,782 |
| North Africa        |         4 |   96,768 |
| Sub-Saharan Africa  |        25 |   90,689 |
| **Total**           |    **78** | **7,490,239** |

(Approximate continent breakdown; per-country numbers are exact.
See `dataset/manifest.json` for the machine-readable source.)

---

## Coverage (78 countries)

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

(See `dataset/manifest.json` for the authoritative list.)

---

## Storage

| Location                                | Size    | Notes               |
|-----------------------------------------|--------:|---------------------|
| `/Volumes/Seagate M3/osm-polygon-selection/` | ~200 GB | Source of truth     |
| `/Users/noeflandre/osm-polygon-selection/data/` | <100 MB | Reference data only |

The pipeline reads PBFs and writes parquet to the HDD only. Never
to local SSD. See `docs/AGENT_HANDOFF.md` for the storage policy.

---

## Test status

| Suite                                  | Tests |
|----------------------------------------|------:|
| Full suite (without flaky wall-clock)  |  279  |
| Flaky wall-clock test (deselected)     |    1  |
| **Total**                              | **281** |

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
`docs/AFRICA_ROLLOUT.md` for the queue and the resume plan.

---

## Recent commits

- pending feat(botswana): add Botswana + 29th African country (TDD red-green)
- `9de694a` feat(mayotte): add Mayotte + 28th African country (TDD red-green)
- `e251cdb` feat(africa): add 24 African countries + bootstrap full /africa/ support
- `cec4b7c` feat(algeria): add Algeria + third North-African country
- `1edc041` perf(make_split): skip per-country parquet rewrites
- `4320910` feat(tunisia): add Tunisia + second North-African country
- `7380f95` feat(morocco): add Morocco + non-European country support
- `0510996` perf(extract): fast lon/lat area pre-filter + C-level vertex count
- `fd39de2` perf(build_dataset): pa.json C-level parser + zstd compression
- `2b1b773` perf(build_dataset): streaming JSONL -> parquet writer

---

## How to update this doc

When adding/removing a country, edit the relevant numbers here AND
the corresponding sections in `README.md`, `AGENT_HANDOFF.md`,
`PERFORMANCE.md`, `AFRICA_ROLLOUT.md`. The `manifest.json` and the
auto-generated `dataset/README.md` are the machine-readable sources
of truth.
