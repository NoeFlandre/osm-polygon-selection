# Africa rollout — /africa/ loop status

The user's standing instruction: **keep adding African countries
until the whole Geofabrik `/africa/` subtree is processed**.

This document tracks the state of that loop, the queue of
remaining countries, and the partial-extraction cleanup.

For conventions + storage policy, see `docs/AGENT_HANDOFF.md`.
For per-country timings, see `docs/PERFORMANCE.md`.

---

## Status as of 2 July 2026

| Metric                    | Value           |
|---------------------------|----------------:|
| African countries done    |       **28 / 55** |
| Total polygons (Africa)   |       197,359   |
| Total countries (dataset) |       **77**    |
| Total polygons (dataset)  |     7,484,912   |

The 28 done = 3 prior (morocco, tunisia, algeria) + 24 from
batches 1+2 + 1 most recent (mayotte).

---

## What's done (28 African countries)

**North Africa (5)**:
- morocco (231 MB PBF, 42,623 polygons)
- tunisia (80 MB PBF, 8,498 polygons)
- algeria (284 MB PBF, 32,601 polygons)
- libya (73 MB PBF, 13,046 polygons)
- egypt — IN QUEUE (PBFs downloaded, not extracted)

**West Africa (16)**:
- senegal-and-gambia — IN QUEUE
- guinea-bissau (10.6 MB, 2,109 polygons)
- guinea — IN QUEUE
- sierra-leone (40.7 MB, 3,366 polygons)
- liberia (35.5 MB, 2,342 polygons)
- ivory-coast — IN QUEUE
- ghana — IN QUEUE
- togo (59 MB, 3,408 polygons)
- benin (45.5 MB, 4,614 polygons)
- burkina-faso — IN QUEUE
- mali — IN QUEUE
- mauritania (29 MB, 9,040 polygons)
- niger (71 MB, 14,606 polygons)
- cape-verde (11.1 MB, 2,417 polygons)
- nigeria — IN QUEUE

**Central Africa (6)**:
- cameroon — IN QUEUE
- central-african-republic — IN QUEUE
- chad — IN QUEUE
- congo-brazzaville (30.7 MB, 6,643 polygons)
- congo-democratic-republic — IN QUEUE
- equatorial-guinea (6.2 MB, 1,004 polygons)
- gabon (24.1 MB, 3,843 polygons)

**East Africa (5)**:
- burundi (44 MB, 4,659 polygons)
- comores (3.8 MB, 395 polygons)
- djibouti (6.7 MB, 576 polygons)
- eritrea (29.5 MB, 3,278 polygons)
- ethiopia — IN QUEUE
- kenya — IN QUEUE
- rwanda (62 MB, 3,976 polygons)
- seychelles (2.6 MB, 264 polygons)
- somalia — IN QUEUE
- south-sudan — IN QUEUE
- sudan — IN QUEUE
- tanzania — IN QUEUE
- uganda — IN QUEUE
- mayotte (10 MB, 606 polygons) — French Indian Ocean territory

**Southern Africa (8)**:
- angola — IN QUEUE
- botswana — IN QUEUE
- lesotho — IN QUEUE
- malawi — IN QUEUE
- mozambique — IN QUEUE
- namibia (51 MB, 9,316 polygons)
- south-africa — IN QUEUE
- swaziland (29.1 MB, 4,113 polygons)
- zambia — IN QUEUE
- zimbabwe — IN QUEUE

**Islands (4)**:
- canary-islands (57 MB, 2,560 polygons) — Spanish, in /africa/
- sao-tome-and-principe (1.2 MB, 190 polygons)
- saint-helena-ascension-and-tristan-da-cunha (848 KB, 174 polygons) — smallest in dataset
- mauritius (9 MB, 1,863 polygons)

---

## Queue (26 African countries pending)

Sorted by PBF size (smallest first to make early progress visible):

| # | Country                       | PBF size | Status            |
|---|-------------------------------|---------:|-------------------|
| 1 | central-african-republic      |   94 MB  | PBFs downloaded   |
| 2 | ivory-coast                   |   85 MB  | PBFs downloaded   |
| 3 | botswana                      |   84 MB  | PBFs downloaded   |
| 4 | burkina-faso                  |   81 MB  | PBFs downloaded   |
| 5 | angola                        |   81 MB  | PBFs downloaded   |
| 6 | guinea                        |  111 MB  | PBFs downloaded   |
| 7 | ghana                         |  107 MB  | PBFs downloaded   |
| 8 | senegal-and-gambia            |  100 MB  | PBFs downloaded   |
| 9 | lesotho                       |  120 MB  | PBFs downloaded   |
| 10 | chad                         |  128 MB  | PBFs downloaded   |
| 11 | south-sudan                  |  131 MB  | PBFs downloaded   |
| 12 | ethiopia                     |  132 MB  | PBFs downloaded   |
| 13 | malawi                       |  147 MB  | PBFs downloaded   |
| 14 | somalia                      |  156 MB  | PBFs downloaded   |
| 15 | mali                         |  164 MB  | PBFs downloaded   |
| 16 | zimbabwe                     |  170 MB  | PBFs downloaded   |
| 17 | egypt                        |  169 MB  | PBFs downloaded   |
| 18 | sudan                        |  193 MB  | PBFs downloaded   |
| 19 | cameroon                     |  213 MB  | PBFs downloaded   |
| 20 | zambia                       |  240 MB  | PBFs downloaded   |
| 21 | mozambique                   |  243 MB  | PBFs downloaded   |
| 22 | kenya                        |  331 MB  | PBFs downloaded   |
| 23 | uganda                       |  353 MB  | PBFs downloaded   |
| 24 | south-africa                 |  396 MB  | PBFs downloaded   |
| 25 | congo-democratic-republic    |  393 MB  | PBFs downloaded   |
| 26 | nigeria                      |  678 MB  | PBFs downloaded   |

All 26 PBFs are already in `/Volumes/Seagate M3/osm-polygon-selection/raw/`.
Their `processed/<country>/` directories were cleaned up after the
parallel-stage-0 saturation incident (see `docs/PERFORMANCE.md`).
Stage 0 must be re-run from scratch for all 26.

---

## TDD plan to resume the rollout

For each country in the queue (in order, smallest PBF first):

1. **Add TDD test** in `tests/test_pbf_meta.py` if not already
   present (the queue countries all already have entries in
   `NON_EUROPE_COUNTRIES`; just verify the tests are there).

2. **Add COUNTRY_NOTES blurb** in `scripts/organize_dataset.py`'s
   `COUNTRY_NOTES` dict (already done for all 26).

3. **Stage 0** (the only slow step):
   ```bash
   OSM_DATA_ROOT=/Volumes/Seagate\ M3/osm-polygon-selection \
     uv run scripts/stage0_extract.py \
       /Volumes/Seagate\ M3/osm-polygon-selection/raw/<country>-latest.osm.pbf \
       /Volumes/Seagate\ M3/osm-polygon-selection/processed/<country>/01_extracted.jsonl
   ```
   For the big PBFs (Nigeria, Tanzania, South Africa, DRC, Kenya,
   Uganda), use `--max-seconds 1800` to cap at 30 min and resume
   if needed:
   ```bash
   uv run scripts/stage0_extract.py \
     /Volumes/Seagate\ M3/osm-polygon-selection/raw/<country>-latest.osm.pbf \
     /Volumes/Seagate\ M3/osm-polygon-selection/processed/<country>/01_extracted.jsonl \
     --max-seconds 1800
   ```
   Then re-run without `--max-seconds` to resume.

4. **Stages 2 + 3** (fast):
   ```bash
   OSM_DATA_ROOT=/Volumes/Seagate\ M3/osm-polygon-selection \
     uv run scripts/stage2_filter.py \
       $OSM_DATA_ROOT/processed/<country>/01_extracted.jsonl \
       $OSM_DATA_ROOT/whitelist.json \
       $OSM_DATA_ROOT/processed/<country>/02_filtered.jsonl

   OSM_DATA_ROOT=/Volumes/Seagate\ M3/osm-polygon-selection \
     uv run scripts/stage3_classify.py \
       $OSM_DATA_ROOT/processed/<country>/02_filtered.jsonl \
       data/reference/natural_earth/ne_110m_admin_0_countries.shp \
       $OSM_DATA_ROOT/processed/<country>/03_classified.jsonl
   ```

5. **Build + organize + sample + split + render + upload** (run
   once at the end after a batch of countries, not per-country).

6. **Commit + push** with the standard commit message format.

---

## Lessons from the parallel-stage-0 incident

Commit `e251cdb` ran 27 stage 0 extracts in parallel. The HDD
saturated, the user's MacBook became unresponsive, and the user
had to interrupt. The 26 partial `processed/<country>/` dirs were
left in a half-extracted state with partial JSONLs and WALs.

**Recovery (already done in commit `9de694a`):**
```bash
# 1. Kill all stage 0 processes (none were running after the interrupt)
ps -ef | grep stage0_extract | grep -v grep

# 2. Identify partial dirs (no 01_extracted.jsonl.run.json)
for c in angola botswana central-african-republic ...; do
  if [ ! -f "/Volumes/Seagate M3/osm-polygon-selection/processed/$c/01_extracted.jsonl.run.json" ]; then
    echo "PARTIAL: $c"
  fi
done

# 3. Clean them up
rm -rf /Volumes/Seagate M3/osm-polygon-selection/processed/<partial>
```

**Going forward: 2-3 parallel stage 0 is fine. More than that
saturates the HDD.** See `docs/PERFORMANCE.md` for details.

---

## Future Africa rollout goals

- **All 55 African countries**: 28 done, 26 queued.
- **Estimated total time**: ~6-10 hours of wall-clock (mostly stage 0
  for the big PBFs).
- **Dataset will reach 103 countries, ~9-10M polygons**.
- **Combined parquet** will grow from 6.0 GB to ~8-9 GB.

Once Africa is done, the next regional rollout could be:
- Asia (Geofabrik `/asia/`)
- Americas (Geofabrik `/north-america/` + `/south-america/`)
- Oceania (Geofabrik `/australia-oceania/`)
- Antarctica (Geofabrik `/antarctica/`)

But the user's current instruction is **finish Africa first**.
