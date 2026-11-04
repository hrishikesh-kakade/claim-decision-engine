# Reranker diagnostics

- Queries: 30
- Candidate pool: 15
- Evaluated ranking depth: 5
- Production: hybrid
- Experimental reranker: lexical-overlap-rerank-v1

## Aggregate comparison

| Metric | Hybrid RRF | Hybrid + reranker |
|---|---:|---:|
| Hit@3 | 0.833 | 0.767 |
| Hit@5 | 0.867 | 0.767 |
| Recall@3 | 0.733 | 0.661 |
| Recall@5 | 0.789 | 0.672 |
| MRR@5 | 0.725 | 0.678 |
| nDCG@5 | 0.725 | 0.629 |

## Relevant chunk movement

| Movement | Count |
|---|---:|
| moved_up | 10 |
| moved_down | 20 |
| unchanged | 16 |
| not_in_candidate_pool | 4 |
| missing_after_reranking | 0 |

## Per-query comparison

### P01 — pipeline

**Query:** initial 30 day waiting period exception continuous coverage

**Relevant chunks:** ['EXCLUSIONS-005']

**Hybrid top 5:** ['DEFINITIONS-019', 'EXCLUSIONS-001', 'EXCLUSIONS-005', 'DEFINITIONS-042', 'STANDARD_TERMS-017']

**Reranked top 5:** ['EXCLUSIONS-001', 'EXCLUSIONS-006', 'EXCLUSIONS-005', 'DEFINITIONS-042', 'DEFINITIONS-019']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-005 | 3 | 3 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-001 | 2 | 1 | 0.4000 | 0.15 | 0.0635 | 0.664340 |
| EXCLUSIONS-006 | 6 | 2 | 0.3000 | 0.15 | 0.0594 | 0.560353 |
| EXCLUSIONS-005 | 3 | 3 | 0.2000 | 0.15 | 0.0622 | 0.485325 |
| DEFINITIONS-042 | 4 | 4 | 0.3000 | 0.00 | 0.0608 | 0.480710 |
| DEFINITIONS-019 | 1 | 5 | 0.3000 | 0.00 | 0.0640 | 0.469208 |
| DEFINITIONS-003 | 7 | 6 | 0.2000 | 0.00 | 0.0581 | 0.378927 |
| STANDARD_TERMS-018 | 12 | 7 | 0.2000 | 0.00 | 0.0299 | 0.318281 |
| STANDARD_TERMS-017 | 5 | 8 | 0.2000 | 0.00 | 0.0600 | 0.301458 |
| EXCLUSIONS-004 | 15 | 9 | 0.0000 | 0.15 | 0.0290 | 0.293928 |
| EXCLUSIONS-003 | 10 | 10 | 0.0000 | 0.15 | 0.0303 | 0.262439 |
| STANDARD_TERMS-001 | 8 | 11 | 0.1000 | 0.00 | 0.0308 | 0.257485 |
| STANDARD_TERMS-015 | 9 | 12 | 0.1000 | 0.00 | 0.0308 | 0.252969 |
| STANDARD_TERMS-005 | 13 | 13 | 0.1000 | 0.00 | 0.0294 | 0.223751 |
| STANDARD_TERMS-011 | 11 | 14 | 0.1000 | 0.00 | 0.0299 | 0.216870 |
| DEFINITIONS-013 | 14 | 15 | 0.1000 | 0.00 | 0.0290 | 0.192545 |

### P02 — pipeline

**Query:** definition of Hospital registered minimum criteria in-patient beds

**Relevant chunks:** ['DEFINITIONS-021']

**Hybrid top 5:** ['DEFINITIONS-021', 'DEFINITIONS-013', 'DEFINITIONS-020', 'SCOPE_OF_COVER-001', 'SCOPE_OF_COVER-003']

**Reranked top 5:** ['DEFINITIONS-021', 'DEFINITIONS-013', 'DEFINITIONS-020', 'DEFINITIONS-033', 'DEFINITIONS-024']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| DEFINITIONS-021 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| DEFINITIONS-021 | 1 | 1 | 0.6125 | 0.15 | 0.0656 | 0.899545 |
| DEFINITIONS-013 | 2 | 2 | 0.5250 | 0.15 | 0.0640 | 0.802563 |
| DEFINITIONS-020 | 3 | 3 | 0.3500 | 0.15 | 0.0640 | 0.680396 |
| DEFINITIONS-033 | 9 | 4 | 0.2625 | 0.15 | 0.0582 | 0.560689 |
| DEFINITIONS-024 | 8 | 5 | 0.1750 | 0.15 | 0.0583 | 0.512171 |
| DEFINITIONS-043 | 6 | 6 | 0.1750 | 0.15 | 0.0590 | 0.510211 |
| DEFINITIONS-003 | 14 | 7 | 0.1750 | 0.15 | 0.0286 | 0.474417 |
| DEFINITIONS-030 | 7 | 8 | 0.1750 | 0.15 | 0.0585 | 0.473495 |
| DEFINITIONS-046 | 13 | 9 | 0.1750 | 0.15 | 0.0290 | 0.461996 |
| DEFINITIONS-015 | 11 | 10 | 0.1750 | 0.15 | 0.0299 | 0.452017 |
| DEFINITIONS-035 | 10 | 11 | 0.0875 | 0.15 | 0.0568 | 0.396350 |
| DEFINITIONS-040 | 15 | 12 | 0.0875 | 0.15 | 0.0286 | 0.393460 |
| SCOPE_OF_COVER-003 | 5 | 13 | 0.2625 | 0.00 | 0.0602 | 0.377274 |
| DEFINITIONS-038 | 12 | 14 | 0.0875 | 0.15 | 0.0290 | 0.367581 |
| SCOPE_OF_COVER-001 | 4 | 15 | 0.1750 | 0.00 | 0.0602 | 0.341943 |

### P03 — pipeline

**Query:** pre-existing diseases waiting period 48 months portability reduction

**Relevant chunks:** ['DEFINITIONS-036', 'EXCLUSIONS-001']

**Hybrid top 5:** ['EXCLUSIONS-001', 'DEFINITIONS-036', 'STANDARD_TERMS-011', 'DEFINITIONS-037', 'EXCLUSIONS-006']

**Reranked top 5:** ['EXCLUSIONS-001', 'EXCLUSIONS-006', 'DEFINITIONS-019', 'STANDARD_TERMS-011', 'STANDARD_TERMS-018']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| DEFINITIONS-036 | 2 | 10 | moved_down |
| EXCLUSIONS-001 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-001 | 1 | 1 | 0.5000 | 0.15 | 0.0640 | 0.764852 |
| EXCLUSIONS-006 | 5 | 2 | 0.4000 | 0.15 | 0.0607 | 0.661665 |
| DEFINITIONS-019 | 9 | 3 | 0.4000 | 0.00 | 0.0328 | 0.537958 |
| STANDARD_TERMS-011 | 3 | 4 | 0.2000 | 0.15 | 0.0621 | 0.499128 |
| STANDARD_TERMS-018 | 6 | 5 | 0.2000 | 0.15 | 0.0584 | 0.496828 |
| EXCLUSIONS-005 | 7 | 6 | 0.2000 | 0.15 | 0.0556 | 0.478725 |
| STANDARD_TERMS-005 | 11 | 7 | 0.2000 | 0.15 | 0.0308 | 0.475109 |
| STANDARD_TERMS-013 | 8 | 8 | 0.1000 | 0.15 | 0.0556 | 0.418881 |
| DEFINITIONS-037 | 4 | 9 | 0.2000 | 0.00 | 0.0620 | 0.378186 |
| DEFINITIONS-036 | 2 | 10 | 0.2000 | 0.00 | 0.0631 | 0.375978 |
| EXCLUSIONS-023 | 13 | 11 | 0.1000 | 0.15 | 0.0299 | 0.370144 |
| DEFINITIONS-042 | 14 | 12 | 0.2000 | 0.00 | 0.0294 | 0.349292 |
| EXCLUSIONS-021 | 12 | 13 | 0.0000 | 0.15 | 0.0303 | 0.322821 |
| EXCLUSIONS-022 | 15 | 14 | 0.0000 | 0.15 | 0.0286 | 0.320920 |
| DEFINITIONS-003 | 10 | 15 | 0.1000 | 0.00 | 0.0312 | 0.252096 |

### P04 — pipeline

**Query:** first year waiting period specified diseases cataract eye surgery

**Relevant chunks:** ['EXCLUSIONS-006']

**Hybrid top 5:** ['EXCLUSIONS-006', 'EXCLUSIONS-001', 'DEFINITIONS-036', 'EXCLUSIONS-005', 'DEFINITIONS-046']

**Reranked top 5:** ['EXCLUSIONS-006', 'EXCLUSIONS-001', 'EXCLUSIONS-005', 'DEFINITIONS-019', 'EXCLUSIONS-023']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-006 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-006 | 1 | 1 | 0.6222 | 0.15 | 0.0656 | 0.888730 |
| EXCLUSIONS-001 | 2 | 2 | 0.3111 | 0.15 | 0.0640 | 0.575963 |
| EXCLUSIONS-005 | 4 | 3 | 0.2333 | 0.15 | 0.0598 | 0.516281 |
| DEFINITIONS-019 | 7 | 4 | 0.3111 | 0.00 | 0.0323 | 0.448540 |
| EXCLUSIONS-023 | 14 | 5 | 0.1556 | 0.15 | 0.0290 | 0.424835 |
| DEFINITIONS-036 | 3 | 6 | 0.1556 | 0.00 | 0.0625 | 0.330959 |
| DEFINITIONS-020 | 6 | 7 | 0.1556 | 0.00 | 0.0569 | 0.328825 |
| EXCLUSIONS-021 | 8 | 8 | 0.0000 | 0.15 | 0.0312 | 0.323768 |
| EXCLUSIONS-022 | 11 | 9 | 0.0000 | 0.15 | 0.0299 | 0.322200 |
| DEFINITIONS-046 | 5 | 10 | 0.1556 | 0.00 | 0.0585 | 0.322038 |
| EXCLUSIONS-009 | 9 | 11 | 0.0000 | 0.15 | 0.0308 | 0.321120 |
| DEFINITIONS-042 | 13 | 12 | 0.1556 | 0.00 | 0.0294 | 0.304847 |
| EXCLUSIONS-004 | 15 | 13 | 0.0000 | 0.15 | 0.0290 | 0.293928 |
| STANDARD_TERMS-015 | 10 | 14 | 0.0778 | 0.00 | 0.0303 | 0.230280 |
| DEFINITIONS-003 | 12 | 15 | 0.0778 | 0.00 | 0.0294 | 0.228035 |

### P05 — pipeline

**Query:** day care treatment less than 24 hours specified procedures Eye Surgery Dialysis

**Relevant chunks:** ['SCOPE_OF_COVER-003', 'DEFINITIONS-013']

**Hybrid top 5:** ['DEFINITIONS-013', 'SCOPE_OF_COVER-003', 'DEFINITIONS-020', 'DEFINITIONS-024', 'EXCLUSIONS-019']

**Reranked top 5:** ['SCOPE_OF_COVER-003', 'DEFINITIONS-021', 'DEFINITIONS-013', 'DEFINITIONS-020', 'DEFINITIONS-024']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| SCOPE_OF_COVER-003 | 2 | 1 | moved_up |
| DEFINITIONS-013 | 1 | 3 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-003 | 2 | 1 | 0.5727 | 0.00 | 0.0640 | 0.691351 |
| DEFINITIONS-021 | 7 | 2 | 0.4455 | 0.00 | 0.0586 | 0.575573 |
| DEFINITIONS-013 | 1 | 3 | 0.4455 | 0.00 | 0.0645 | 0.573547 |
| DEFINITIONS-020 | 3 | 4 | 0.3818 | 0.00 | 0.0636 | 0.561766 |
| DEFINITIONS-024 | 4 | 5 | 0.2545 | 0.00 | 0.0611 | 0.444511 |
| DEFINITIONS-046 | 6 | 6 | 0.2545 | 0.00 | 0.0597 | 0.422271 |
| EXCLUSIONS-023 | 11 | 7 | 0.2545 | 0.00 | 0.0299 | 0.374690 |
| EXCLUSIONS-019 | 5 | 8 | 0.1909 | 0.00 | 0.0607 | 0.360860 |
| EXCLUSIONS-006 | 14 | 9 | 0.2545 | 0.00 | 0.0286 | 0.334051 |
| EXCLUSIONS-010 | 8 | 10 | 0.1273 | 0.00 | 0.0564 | 0.326004 |
| DEFINITIONS-033 | 13 | 11 | 0.1909 | 0.00 | 0.0286 | 0.309503 |
| DEFINITIONS-043 | 12 | 12 | 0.1273 | 0.00 | 0.0290 | 0.282441 |
| EXCLUSIONS-022 | 9 | 13 | 0.0636 | 0.00 | 0.0323 | 0.238243 |
| EXCLUSIONS-016 | 10 | 14 | 0.0636 | 0.00 | 0.0299 | 0.232215 |
| DEFINITIONS-003 | 15 | 15 | 0.0636 | 0.00 | 0.0282 | 0.212651 |

### P06 — pipeline

**Query:** domiciliary treatment definition room unavailable sub-limit

**Relevant chunks:** ['DEFINITIONS-015', 'SCOPE_OF_COVER-003']

**Hybrid top 5:** ['DEFINITIONS-015', 'EXCLUSIONS-020', 'SCOPE_OF_COVER-003', 'DEFINITIONS-013', 'SCOPE_OF_COVER-001']

**Reranked top 5:** ['SCOPE_OF_COVER-003', 'DEFINITIONS-015', 'SCOPE_OF_COVER-001', 'DEFINITIONS-013', 'DEFINITIONS-033']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| DEFINITIONS-015 | 1 | 2 | moved_down |
| SCOPE_OF_COVER-003 | 3 | 1 | moved_up |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-003 | 3 | 1 | 0.3500 | 0.30 | 0.0611 | 0.765721 |
| DEFINITIONS-015 | 1 | 2 | 0.3500 | 0.15 | 0.0656 | 0.662740 |
| SCOPE_OF_COVER-001 | 5 | 3 | 0.1167 | 0.30 | 0.0577 | 0.581129 |
| DEFINITIONS-013 | 4 | 4 | 0.2333 | 0.15 | 0.0597 | 0.506607 |
| DEFINITIONS-033 | 14 | 5 | 0.2333 | 0.15 | 0.0290 | 0.502341 |
| DEFINITIONS-043 | 6 | 6 | 0.1167 | 0.15 | 0.0565 | 0.449367 |
| DEFINITIONS-024 | 10 | 7 | 0.1167 | 0.15 | 0.0312 | 0.426810 |
| EXCLUSIONS-013 | 7 | 8 | 0.2333 | 0.00 | 0.0323 | 0.386437 |
| DEFINITIONS-021 | 13 | 9 | 0.1167 | 0.15 | 0.0290 | 0.367123 |
| EXTENSIONS-001 | 8 | 10 | 0.2333 | 0.00 | 0.0317 | 0.350610 |
| EXCLUSIONS-020 | 2 | 11 | 0.1167 | 0.00 | 0.0630 | 0.320374 |
| PREAMBLE-001 | 15 | 12 | 0.2333 | 0.00 | 0.0286 | 0.312882 |
| DEFINITIONS-020 | 9 | 13 | 0.0000 | 0.15 | 0.0317 | 0.298138 |
| EXCLUSIONS-016 | 12 | 14 | 0.1167 | 0.00 | 0.0294 | 0.284807 |
| STANDARD_TERMS-021 | 11 | 15 | 0.0000 | 0.00 | 0.0308 | 0.102626 |

### P07 — pipeline

**Query:** room boarding nursing expenses sub-limit surgeon fees limit sum insured

**Relevant chunks:** ['SCOPE_OF_COVER-001', 'SCOPE_OF_COVER-002', 'SCOPE_OF_COVER-003']

**Hybrid top 5:** ['SCOPE_OF_COVER-001', 'SCOPE_OF_COVER-002', 'EXTENSIONS-001', 'SCOPE_OF_COVER-003', 'EXCLUSIONS-002']

**Reranked top 5:** ['SCOPE_OF_COVER-001', 'SCOPE_OF_COVER-003', 'SCOPE_OF_COVER-002', 'EXTENSIONS-001', 'EXCLUSIONS-002']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| SCOPE_OF_COVER-001 | 1 | 1 | unchanged |
| SCOPE_OF_COVER-002 | 2 | 3 | moved_down |
| SCOPE_OF_COVER-003 | 4 | 2 | moved_up |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-001 | 1 | 1 | 0.4900 | 0.30 | 0.0656 | 0.962335 |
| SCOPE_OF_COVER-003 | 4 | 2 | 0.4200 | 0.30 | 0.0630 | 0.837616 |
| SCOPE_OF_COVER-002 | 2 | 3 | 0.2800 | 0.30 | 0.0645 | 0.773271 |
| EXTENSIONS-001 | 3 | 4 | 0.4200 | 0.00 | 0.0630 | 0.568527 |
| EXCLUSIONS-002 | 5 | 5 | 0.3500 | 0.00 | 0.0615 | 0.480188 |
| CLAIMS_PROCEDURE-002 | 8 | 6 | 0.2100 | 0.00 | 0.0585 | 0.390053 |
| EXCLUSIONS-004 | 6 | 7 | 0.2100 | 0.00 | 0.0597 | 0.384657 |
| DEFINITIONS-043 | 7 | 8 | 0.1400 | 0.00 | 0.0588 | 0.325019 |
| STANDARD_TERMS-023 | 11 | 9 | 0.1400 | 0.00 | 0.0290 | 0.303214 |
| DEFINITIONS-035 | 14 | 10 | 0.1400 | 0.00 | 0.0282 | 0.270210 |
| DEFINITIONS-040 | 13 | 11 | 0.0700 | 0.00 | 0.0286 | 0.225960 |
| EXCLUSIONS-013 | 10 | 12 | 0.0700 | 0.00 | 0.0294 | 0.220258 |
| EXCLUSIONS-020 | 9 | 13 | 0.0000 | 0.00 | 0.0299 | 0.170531 |
| EXCLUSIONS-016 | 15 | 14 | 0.0000 | 0.00 | 0.0278 | 0.166506 |
| EXCLUSIONS-012 | 12 | 15 | 0.0000 | 0.00 | 0.0286 | 0.164318 |

### P08 — pipeline

**Query:** cosmetic aesthetic treatment exclusion

**Relevant chunks:** ['EXCLUSIONS-008']

**Hybrid top 5:** ['EXCLUSIONS-008', 'DEFINITIONS-012', 'EXCLUSIONS-010', 'DEFINITIONS-005', 'DEFINITIONS-049']

**Reranked top 5:** ['EXCLUSIONS-008', 'EXCLUSIONS-005', 'EXCLUSIONS-001', 'DEFINITIONS-012', 'EXCLUSIONS-010']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-008 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-008 | 1 | 1 | 0.5250 | 0.15 | 0.0656 | 0.845837 |
| EXCLUSIONS-005 | 7 | 2 | 0.3500 | 0.15 | 0.0317 | 0.604872 |
| EXCLUSIONS-001 | 9 | 3 | 0.3500 | 0.15 | 0.0312 | 0.582097 |
| DEFINITIONS-012 | 2 | 4 | 0.3500 | 0.00 | 0.0626 | 0.531609 |
| EXCLUSIONS-010 | 3 | 5 | 0.1750 | 0.15 | 0.0608 | 0.528178 |
| EXCLUSIONS-022 | 6 | 6 | 0.1750 | 0.15 | 0.0576 | 0.524906 |
| EXCLUSIONS-021 | 14 | 7 | 0.1750 | 0.15 | 0.0294 | 0.496930 |
| EXCLUSIONS-014 | 12 | 8 | 0.1750 | 0.15 | 0.0299 | 0.471130 |
| DEFINITIONS-049 | 5 | 9 | 0.1750 | 0.00 | 0.0578 | 0.354254 |
| DEFINITIONS-005 | 4 | 10 | 0.1750 | 0.00 | 0.0584 | 0.336240 |
| DEFINITIONS-015 | 11 | 11 | 0.1750 | 0.00 | 0.0303 | 0.302469 |
| STANDARD_TERMS-002 | 13 | 12 | 0.0000 | 0.00 | 0.0299 | 0.139041 |
| STANDARD_TERMS-016 | 8 | 13 | 0.0000 | 0.00 | 0.0312 | 0.121748 |
| STANDARD_TERMS-018 | 15 | 14 | 0.0000 | 0.00 | 0.0294 | 0.117842 |
| STANDARD_TERMS-024 | 10 | 15 | 0.0000 | 0.00 | 0.0308 | 0.101649 |

### P09 — pipeline

**Query:** maternity pregnancy self injury alcohol war terrorism exclusion

**Relevant chunks:** ['EXCLUSIONS-014', 'EXCLUSIONS-011', 'EXCLUSIONS-007']

**Hybrid top 5:** ['EXCLUSIONS-024', 'EXCLUSIONS-007', 'EXCLUSIONS-014', 'EXCLUSIONS-011', 'DEFINITIONS-023']

**Reranked top 5:** ['EXCLUSIONS-007', 'EXCLUSIONS-024', 'EXCLUSIONS-011', 'EXCLUSIONS-015', 'EXCLUSIONS-014']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-014 | 3 | 5 | moved_down |
| EXCLUSIONS-011 | 4 | 3 | moved_up |
| EXCLUSIONS-007 | 2 | 1 | moved_up |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-007 | 2 | 1 | 0.2625 | 0.15 | 0.0650 | 0.596829 |
| EXCLUSIONS-024 | 1 | 2 | 0.1750 | 0.15 | 0.0650 | 0.527660 |
| EXCLUSIONS-011 | 4 | 3 | 0.1750 | 0.15 | 0.0603 | 0.503544 |
| EXCLUSIONS-015 | 6 | 4 | 0.0875 | 0.15 | 0.0588 | 0.429374 |
| EXCLUSIONS-014 | 3 | 5 | 0.0875 | 0.15 | 0.0625 | 0.416294 |
| EXCLUSIONS-013 | 15 | 6 | 0.0875 | 0.15 | 0.0290 | 0.387331 |
| EXCLUSIONS-008 | 12 | 7 | 0.0875 | 0.15 | 0.0303 | 0.373066 |
| EXCLUSIONS-005 | 14 | 8 | 0.0875 | 0.15 | 0.0294 | 0.340038 |
| EXCLUSIONS-021 | 9 | 9 | 0.0000 | 0.15 | 0.0312 | 0.323768 |
| EXCLUSIONS-020 | 13 | 10 | 0.0000 | 0.15 | 0.0299 | 0.320531 |
| DEFINITIONS-023 | 5 | 11 | 0.0875 | 0.00 | 0.0589 | 0.265015 |
| DEFINITIONS-002 | 7 | 12 | 0.0875 | 0.00 | 0.0568 | 0.259916 |
| DEFINITIONS-036 | 8 | 13 | 0.0875 | 0.00 | 0.0544 | 0.254832 |
| DEFINITIONS-051 | 10 | 14 | 0.0875 | 0.00 | 0.0312 | 0.236860 |
| CLAIMS_PROCEDURE-002 | 11 | 15 | 0.0000 | 0.00 | 0.0303 | 0.151884 |

### P10 — pipeline

**Query:** unproven experimental treatment medically necessary definition

**Relevant chunks:** ['DEFINITIONS-049', 'DEFINITIONS-030']

**Hybrid top 5:** ['DEFINITIONS-049', 'DEFINITIONS-030', 'EXCLUSIONS-008', 'DEFINITIONS-015', 'EXCLUSIONS-022']

**Reranked top 5:** ['DEFINITIONS-049', 'DEFINITIONS-030', 'DEFINITIONS-013', 'DEFINITIONS-015', 'DEFINITIONS-012']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| DEFINITIONS-049 | 1 | 1 | unchanged |
| DEFINITIONS-030 | 2 | 2 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| DEFINITIONS-049 | 1 | 1 | 0.3500 | 0.15 | 0.0656 | 0.687031 |
| DEFINITIONS-030 | 2 | 2 | 0.3500 | 0.15 | 0.0645 | 0.654539 |
| DEFINITIONS-013 | 9 | 3 | 0.2333 | 0.15 | 0.0308 | 0.477662 |
| DEFINITIONS-015 | 4 | 4 | 0.1167 | 0.15 | 0.0593 | 0.423095 |
| DEFINITIONS-012 | 13 | 5 | 0.1167 | 0.15 | 0.0294 | 0.415126 |
| DEFINITIONS-036 | 10 | 6 | 0.1167 | 0.15 | 0.0308 | 0.410324 |
| DEFINITIONS-006 | 12 | 7 | 0.1167 | 0.15 | 0.0299 | 0.405907 |
| DEFINITIONS-005 | 7 | 8 | 0.1167 | 0.15 | 0.0312 | 0.400744 |
| EXCLUSIONS-008 | 3 | 9 | 0.2333 | 0.00 | 0.0620 | 0.400646 |
| DEFINITIONS-022 | 15 | 10 | 0.1167 | 0.15 | 0.0290 | 0.366407 |
| EXCLUSIONS-022 | 5 | 11 | 0.1167 | 0.00 | 0.0567 | 0.315756 |
| CLAIMS_PROCEDURE-001 | 8 | 12 | 0.1167 | 0.00 | 0.0312 | 0.272917 |
| EXCLUSIONS-014 | 14 | 13 | 0.1167 | 0.00 | 0.0290 | 0.261931 |
| STANDARD_TERMS-021 | 11 | 14 | 0.1167 | 0.00 | 0.0303 | 0.218826 |
| EXCLUSIONS-011 | 6 | 15 | 0.0000 | 0.00 | 0.0317 | 0.149973 |

### P11 — pipeline

**Query:** pre hospitalisation post hospitalisation days maximum

**Relevant chunks:** ['EXCLUSIONS-002', 'DEFINITIONS-035', 'DEFINITIONS-038']

**Hybrid top 5:** ['EXCLUSIONS-021', 'EXCLUSIONS-002', 'DEFINITIONS-035', 'EXCLUSIONS-020', 'DEFINITIONS-038']

**Reranked top 5:** ['EXCLUSIONS-002', 'EXCLUSIONS-021', 'EXCLUSIONS-019', 'EXCLUSIONS-003', 'SCOPE_OF_COVER-003']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-002 | 2 | 1 | moved_up |
| DEFINITIONS-035 | 3 | 7 | moved_down |
| DEFINITIONS-038 | 5 | 8 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-002 | 2 | 1 | 0.7000 | 0.00 | 0.0640 | 0.832654 |
| EXCLUSIONS-021 | 1 | 2 | 0.4200 | 0.00 | 0.0650 | 0.627563 |
| EXCLUSIONS-019 | 7 | 3 | 0.2800 | 0.00 | 0.0317 | 0.421036 |
| EXCLUSIONS-003 | 13 | 4 | 0.2800 | 0.00 | 0.0294 | 0.391547 |
| SCOPE_OF_COVER-003 | 11 | 5 | 0.2800 | 0.00 | 0.0303 | 0.364923 |
| EXCLUSIONS-020 | 4 | 6 | 0.1400 | 0.00 | 0.0598 | 0.340435 |
| DEFINITIONS-035 | 3 | 7 | 0.1400 | 0.00 | 0.0611 | 0.303142 |
| DEFINITIONS-038 | 5 | 8 | 0.1400 | 0.00 | 0.0576 | 0.298724 |
| EXCLUSIONS-013 | 8 | 9 | 0.1400 | 0.00 | 0.0312 | 0.292096 |
| CLAIMS_PROCEDURE-002 | 15 | 10 | 0.1400 | 0.00 | 0.0286 | 0.290152 |
| EXTENSIONS-001 | 14 | 11 | 0.1400 | 0.00 | 0.0290 | 0.254517 |
| EXCLUSIONS-001 | 9 | 12 | 0.1400 | 0.00 | 0.0308 | 0.221617 |
| DEFINITIONS-020 | 6 | 13 | 0.0000 | 0.00 | 0.0328 | 0.149179 |
| DEFINITIONS-021 | 10 | 14 | 0.0000 | 0.00 | 0.0303 | 0.101774 |
| DEFINITIONS-013 | 12 | 15 | 0.0000 | 0.00 | 0.0294 | 0.092971 |

### P12 — pipeline

**Query:** portability continuous coverage waiting period reduction previous insurer

**Relevant chunks:** ['STANDARD_TERMS-011', 'DEFINITIONS-037']

**Hybrid top 5:** ['EXCLUSIONS-001', 'STANDARD_TERMS-011', 'DEFINITIONS-037', 'DEFINITIONS-019', 'EXCLUSIONS-005']

**Reranked top 5:** ['EXCLUSIONS-001', 'EXCLUSIONS-006', 'EXCLUSIONS-005', 'STANDARD_TERMS-018', 'STANDARD_TERMS-017']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| STANDARD_TERMS-011 | 2 | 6 | moved_down |
| DEFINITIONS-037 | 3 | 10 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-001 | 1 | 1 | 0.5250 | 0.15 | 0.0640 | 0.789852 |
| EXCLUSIONS-006 | 7 | 2 | 0.5250 | 0.15 | 0.0606 | 0.786498 |
| EXCLUSIONS-005 | 5 | 3 | 0.3500 | 0.15 | 0.0606 | 0.633746 |
| STANDARD_TERMS-018 | 6 | 4 | 0.2625 | 0.15 | 0.0606 | 0.561536 |
| STANDARD_TERMS-017 | 8 | 5 | 0.2625 | 0.15 | 0.0598 | 0.513744 |
| STANDARD_TERMS-011 | 2 | 6 | 0.1750 | 0.15 | 0.0622 | 0.474218 |
| DEFINITIONS-042 | 9 | 7 | 0.2625 | 0.00 | 0.0586 | 0.441027 |
| DEFINITIONS-019 | 4 | 8 | 0.2625 | 0.00 | 0.0612 | 0.428829 |
| STANDARD_TERMS-013 | 10 | 9 | 0.0875 | 0.15 | 0.0585 | 0.409361 |
| DEFINITIONS-037 | 3 | 10 | 0.1750 | 0.00 | 0.0621 | 0.353275 |
| STANDARD_TERMS-024 | 12 | 11 | 0.0875 | 0.15 | 0.0290 | 0.337366 |
| DEFINITIONS-003 | 11 | 12 | 0.1750 | 0.00 | 0.0290 | 0.324831 |
| EXCLUSIONS-004 | 13 | 13 | 0.0000 | 0.15 | 0.0286 | 0.293514 |
| DEFINITIONS-031 | 15 | 14 | 0.0875 | 0.00 | 0.0282 | 0.236759 |
| DEFINITIONS-025 | 14 | 15 | 0.0000 | 0.00 | 0.0282 | 0.155829 |

### N01 — natural

**Query:** how much of the sum insured is paid for the hospital room

**Relevant chunks:** ['SCOPE_OF_COVER-001']

**Hybrid top 5:** ['SCOPE_OF_COVER-001', 'SCOPE_OF_COVER-003', 'DEFINITIONS-043', 'EXTENSIONS-001', 'EXCLUSIONS-002']

**Reranked top 5:** ['SCOPE_OF_COVER-003', 'SCOPE_OF_COVER-001', 'EXTENSIONS-001', 'DEFINITIONS-033', 'EXCLUSIONS-001']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| SCOPE_OF_COVER-001 | 1 | 2 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-003 | 2 | 1 | 0.5091 | 0.00 | 0.0636 | 0.627267 |
| SCOPE_OF_COVER-001 | 1 | 2 | 0.4455 | 0.00 | 0.0645 | 0.616749 |
| EXTENSIONS-001 | 4 | 3 | 0.4455 | 0.00 | 0.0625 | 0.593486 |
| DEFINITIONS-033 | 8 | 4 | 0.4455 | 0.00 | 0.0323 | 0.567735 |
| EXCLUSIONS-001 | 12 | 5 | 0.4455 | 0.00 | 0.0299 | 0.526153 |
| DEFINITIONS-015 | 9 | 6 | 0.3818 | 0.00 | 0.0317 | 0.510730 |
| EXCLUSIONS-002 | 5 | 7 | 0.3818 | 0.00 | 0.0598 | 0.510223 |
| EXCLUSIONS-005 | 7 | 8 | 0.3818 | 0.00 | 0.0541 | 0.509008 |
| DEFINITIONS-043 | 3 | 9 | 0.3182 | 0.00 | 0.0626 | 0.506926 |
| CLAIMS_PROCEDURE-002 | 6 | 10 | 0.3182 | 0.00 | 0.0567 | 0.496503 |
| EXCLUSIONS-003 | 14 | 11 | 0.3182 | 0.00 | 0.0294 | 0.429729 |
| DEFINITIONS-025 | 10 | 12 | 0.1909 | 0.00 | 0.0303 | 0.348872 |
| SCOPE_OF_COVER-002 | 15 | 13 | 0.1273 | 0.00 | 0.0290 | 0.285014 |
| EXCLUSIONS-020 | 11 | 14 | 0.0636 | 0.00 | 0.0299 | 0.234167 |
| EXCLUSIONS-016 | 13 | 15 | 0.0636 | 0.00 | 0.0294 | 0.231776 |

### N02 — natural

**Query:** cap on surgeon and consultant fees

**Relevant chunks:** ['SCOPE_OF_COVER-002']

**Hybrid top 5:** ['SCOPE_OF_COVER-002', 'EXCLUSIONS-012', 'DEFINITIONS-029', 'EXCLUSIONS-006', 'EXCLUSIONS-014']

**Reranked top 5:** ['SCOPE_OF_COVER-002', 'SCOPE_OF_COVER-003', 'EXCLUSIONS-012', 'EXCLUSIONS-014', 'DEFINITIONS-043']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| SCOPE_OF_COVER-002 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-002 | 1 | 1 | 0.3500 | 0.15 | 0.0656 | 0.694329 |
| SCOPE_OF_COVER-003 | 7 | 2 | 0.2333 | 0.15 | 0.0323 | 0.470211 |
| EXCLUSIONS-012 | 2 | 3 | 0.2333 | 0.00 | 0.0616 | 0.430677 |
| EXCLUSIONS-014 | 5 | 4 | 0.2333 | 0.00 | 0.0563 | 0.405962 |
| DEFINITIONS-043 | 12 | 5 | 0.2333 | 0.00 | 0.0299 | 0.389367 |
| STANDARD_TERMS-007 | 14 | 6 | 0.2333 | 0.00 | 0.0290 | 0.369175 |
| DEFINITIONS-005 | 9 | 7 | 0.2333 | 0.00 | 0.0312 | 0.367411 |
| DEFINITIONS-029 | 3 | 8 | 0.2333 | 0.00 | 0.0606 | 0.367244 |
| STANDARD_TERMS-006 | 6 | 9 | 0.2333 | 0.00 | 0.0323 | 0.365675 |
| DEFINITIONS-009 | 13 | 10 | 0.2333 | 0.00 | 0.0294 | 0.348582 |
| EXCLUSIONS-006 | 4 | 11 | 0.2333 | 0.00 | 0.0602 | 0.344448 |
| EXCLUSIONS-002 | 15 | 12 | 0.2333 | 0.00 | 0.0290 | 0.330969 |
| EXCLUSIONS-016 | 10 | 13 | 0.1167 | 0.00 | 0.0312 | 0.286645 |
| EXCLUSIONS-013 | 8 | 14 | 0.1167 | 0.00 | 0.0317 | 0.269259 |
| EXCLUSIONS-020 | 11 | 15 | 0.0000 | 0.00 | 0.0308 | 0.171449 |

### N03 — natural

**Query:** limit on medicines, oxygen, blood and operation theatre charges

**Relevant chunks:** ['SCOPE_OF_COVER-003']

**Hybrid top 5:** ['SCOPE_OF_COVER-003', 'SCOPE_OF_COVER-002', 'SCOPE_OF_COVER-001', 'DEFINITIONS-041', 'EXTENSIONS-001']

**Reranked top 5:** ['SCOPE_OF_COVER-003', 'SCOPE_OF_COVER-001', 'SCOPE_OF_COVER-002', 'EXTENSIONS-001', 'EXCLUSIONS-002']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| SCOPE_OF_COVER-003 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-003 | 1 | 1 | 0.7000 | 0.15 | 0.0656 | 0.970194 |
| SCOPE_OF_COVER-001 | 3 | 2 | 0.2333 | 0.15 | 0.0616 | 0.551692 |
| SCOPE_OF_COVER-002 | 2 | 3 | 0.1556 | 0.15 | 0.0617 | 0.495981 |
| EXTENSIONS-001 | 5 | 4 | 0.3111 | 0.00 | 0.0597 | 0.456297 |
| EXCLUSIONS-002 | 6 | 5 | 0.3111 | 0.00 | 0.0571 | 0.436904 |
| DEFINITIONS-013 | 14 | 6 | 0.3111 | 0.00 | 0.0303 | 0.404973 |
| EXCLUSIONS-006 | 8 | 7 | 0.2333 | 0.00 | 0.0556 | 0.339823 |
| DEFINITIONS-021 | 12 | 8 | 0.2333 | 0.00 | 0.0308 | 0.335574 |
| DEFINITIONS-041 | 4 | 9 | 0.1556 | 0.00 | 0.0602 | 0.324388 |
| EXCLUSIONS-012 | 9 | 10 | 0.1556 | 0.00 | 0.0317 | 0.323048 |
| EXCLUSIONS-019 | 7 | 11 | 0.1556 | 0.00 | 0.0565 | 0.321363 |
| EXCLUSIONS-016 | 10 | 12 | 0.0778 | 0.00 | 0.0312 | 0.247756 |
| EXCLUSIONS-013 | 13 | 13 | 0.0778 | 0.00 | 0.0303 | 0.228927 |
| EXCLUSIONS-004 | 15 | 14 | 0.0778 | 0.00 | 0.0294 | 0.222132 |
| EXCLUSIONS-020 | 11 | 15 | 0.0000 | 0.00 | 0.0308 | 0.171449 |

### N04 — natural

**Query:** is treatment at home paid and up to what amount

**Relevant chunks:** ['SCOPE_OF_COVER-003', 'DEFINITIONS-015']

**Hybrid top 5:** ['SCOPE_OF_COVER-003', 'DEFINITIONS-015', 'DEFINITIONS-005', 'EXCLUSIONS-005', 'EXCLUSIONS-016']

**Reranked top 5:** ['SCOPE_OF_COVER-003', 'DEFINITIONS-015', 'DEFINITIONS-005', 'EXCLUSIONS-005', 'EXTENSIONS-001']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| SCOPE_OF_COVER-003 | 1 | 1 | unchanged |
| DEFINITIONS-015 | 2 | 2 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-003 | 1 | 1 | 0.4900 | 0.00 | 0.0630 | 0.607616 |
| DEFINITIONS-015 | 2 | 2 | 0.4200 | 0.00 | 0.0617 | 0.578836 |
| DEFINITIONS-005 | 3 | 3 | 0.3500 | 0.00 | 0.0572 | 0.510017 |
| EXCLUSIONS-005 | 4 | 4 | 0.3500 | 0.00 | 0.0552 | 0.478322 |
| EXTENSIONS-001 | 6 | 5 | 0.3500 | 0.00 | 0.0328 | 0.468318 |
| EXCLUSIONS-002 | 8 | 6 | 0.3500 | 0.00 | 0.0317 | 0.450396 |
| DEFINITIONS-014 | 15 | 7 | 0.2800 | 0.00 | 0.0299 | 0.432550 |
| DEFINITIONS-039 | 11 | 8 | 0.2800 | 0.00 | 0.0308 | 0.420760 |
| EXCLUSIONS-019 | 12 | 9 | 0.2800 | 0.00 | 0.0303 | 0.419593 |
| EXCLUSIONS-012 | 7 | 10 | 0.2100 | 0.00 | 0.0323 | 0.378005 |
| EXCLUSIONS-014 | 9 | 11 | 0.2100 | 0.00 | 0.0312 | 0.357529 |
| EXCLUSIONS-022 | 13 | 12 | 0.0700 | 0.00 | 0.0303 | 0.242652 |
| EXCLUSIONS-016 | 5 | 13 | 0.0700 | 0.00 | 0.0328 | 0.241515 |
| DEFINITIONS-010 | 10 | 14 | 0.0700 | 0.00 | 0.0308 | 0.217501 |
| EXCLUSIONS-020 | 14 | 15 | 0.0000 | 0.00 | 0.0299 | 0.170531 |

### N05 — natural

**Query:** maximum payable for ambulance and daily cash allowance

**Relevant chunks:** ['EXCLUSIONS-002']

**Hybrid top 5:** ['EXCLUSIONS-002', 'EXTENSIONS-001', 'SCOPE_OF_COVER-003', 'CLAIMS_PROCEDURE-002', 'EXCLUSIONS-020']

**Reranked top 5:** ['EXCLUSIONS-002', 'EXTENSIONS-001', 'SCOPE_OF_COVER-003', 'SCOPE_OF_COVER-001', 'SCOPE_OF_COVER-002']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-002 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-002 | 1 | 1 | 0.6125 | 0.00 | 0.0656 | 0.746724 |
| EXTENSIONS-001 | 2 | 2 | 0.4375 | 0.00 | 0.0608 | 0.583860 |
| SCOPE_OF_COVER-003 | 3 | 3 | 0.2625 | 0.15 | 0.0597 | 0.526775 |
| SCOPE_OF_COVER-001 | 8 | 4 | 0.1750 | 0.15 | 0.0312 | 0.463012 |
| SCOPE_OF_COVER-002 | 14 | 5 | 0.0875 | 0.15 | 0.0299 | 0.396106 |
| DEFINITIONS-021 | 11 | 6 | 0.2625 | 0.00 | 0.0303 | 0.364274 |
| DEFINITIONS-013 | 13 | 7 | 0.2625 | 0.00 | 0.0299 | 0.355910 |
| STANDARD_TERMS-010 | 6 | 8 | 0.1750 | 0.00 | 0.0317 | 0.335640 |
| DEFINITIONS-045 | 7 | 9 | 0.1750 | 0.00 | 0.0312 | 0.323897 |
| STANDARD_TERMS-018 | 10 | 10 | 0.1750 | 0.00 | 0.0308 | 0.294200 |
| CLAIMS_PROCEDURE-002 | 4 | 11 | 0.0875 | 0.00 | 0.0572 | 0.266235 |
| EXCLUSIONS-020 | 5 | 12 | 0.0875 | 0.00 | 0.0317 | 0.259926 |
| PREAMBLE-001 | 15 | 13 | 0.1750 | 0.00 | 0.0294 | 0.255389 |
| EXCLUSIONS-004 | 12 | 14 | 0.0875 | 0.00 | 0.0303 | 0.232746 |
| EXCLUSIONS-016 | 9 | 15 | 0.0000 | 0.00 | 0.0308 | 0.169498 |

### N06 — natural

**Query:** can I claim for tests done a month before admission

**Relevant chunks:** ['EXCLUSIONS-002', 'DEFINITIONS-035']

**Hybrid top 5:** ['CLAIMS_PROCEDURE-001', 'STANDARD_TERMS-005', 'STANDARD_TERMS-011', 'STANDARD_TERMS-024', 'DEFINITIONS-020']

**Reranked top 5:** ['STANDARD_TERMS-005', 'DEFINITIONS-035', 'STANDARD_TERMS-022', 'STANDARD_TERMS-021', 'DEFINITIONS-022']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-002 | Not retrieved | Not retrieved | not_in_candidate_pool |
| DEFINITIONS-035 | 7 | 2 | moved_up |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| STANDARD_TERMS-005 | 2 | 1 | 0.2625 | 0.00 | 0.0591 | 0.415983 |
| DEFINITIONS-035 | 7 | 2 | 0.2625 | 0.00 | 0.0323 | 0.396799 |
| STANDARD_TERMS-022 | 11 | 3 | 0.2625 | 0.00 | 0.0308 | 0.376314 |
| STANDARD_TERMS-021 | 14 | 4 | 0.2625 | 0.00 | 0.0303 | 0.364659 |
| DEFINITIONS-022 | 10 | 5 | 0.2625 | 0.00 | 0.0312 | 0.364505 |
| DEFINITIONS-042 | 15 | 6 | 0.1750 | 0.00 | 0.0299 | 0.324731 |
| DEFINITIONS-020 | 5 | 7 | 0.1750 | 0.00 | 0.0328 | 0.324179 |
| STANDARD_TERMS-024 | 4 | 8 | 0.1750 | 0.00 | 0.0556 | 0.301479 |
| STANDARD_TERMS-016 | 8 | 9 | 0.1750 | 0.00 | 0.0323 | 0.297756 |
| CLAIMS_PROCEDURE-001 | 1 | 10 | 0.0875 | 0.00 | 0.0591 | 0.271643 |
| EXCLUSIONS-001 | 12 | 11 | 0.1750 | 0.00 | 0.0308 | 0.256617 |
| STANDARD_TERMS-011 | 3 | 12 | 0.0875 | 0.00 | 0.0565 | 0.231037 |
| CLAIMS_PROCEDURE-003 | 9 | 13 | 0.0875 | 0.00 | 0.0312 | 0.226181 |
| EXCLUSIONS-005 | 6 | 14 | 0.0875 | 0.00 | 0.0328 | 0.193413 |
| STANDARD_TERMS-015 | 13 | 15 | 0.0000 | 0.00 | 0.0303 | 0.152503 |

### N07 — natural

**Query:** claim made soon after buying the policy

**Relevant chunks:** ['EXCLUSIONS-005']

**Hybrid top 5:** ['DEFINITIONS-034', 'CLAIMS_PROCEDURE-001', 'STANDARD_TERMS-016', 'STANDARD_TERMS-009', 'STANDARD_TERMS-020']

**Reranked top 5:** ['STANDARD_TERMS-009', 'STANDARD_TERMS-016', 'STANDARD_TERMS-020', 'CLAIMS_PROCEDURE-001', 'DEFINITIONS-034']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-005 | Not retrieved | Not retrieved | not_in_candidate_pool |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| STANDARD_TERMS-009 | 4 | 1 | 0.4000 | 0.00 | 0.0589 | 0.564838 |
| STANDARD_TERMS-016 | 3 | 2 | 0.4000 | 0.00 | 0.0598 | 0.550319 |
| STANDARD_TERMS-020 | 5 | 3 | 0.4000 | 0.00 | 0.0584 | 0.505903 |
| CLAIMS_PROCEDURE-001 | 2 | 4 | 0.3000 | 0.00 | 0.0607 | 0.485732 |
| DEFINITIONS-034 | 1 | 5 | 0.3000 | 0.00 | 0.0630 | 0.482193 |
| STANDARD_TERMS-017 | 11 | 6 | 0.4000 | 0.00 | 0.0312 | 0.472672 |
| EXCLUSIONS-004 | 7 | 7 | 0.3000 | 0.00 | 0.0552 | 0.470118 |
| CLAIMS_PROCEDURE-003 | 6 | 8 | 0.3000 | 0.00 | 0.0570 | 0.464400 |
| STANDARD_TERMS-001 | 14 | 9 | 0.3000 | 0.00 | 0.0299 | 0.456567 |
| DEFINITIONS-006 | 13 | 10 | 0.3000 | 0.00 | 0.0303 | 0.439692 |
| DEFINITIONS-038 | 9 | 11 | 0.3000 | 0.00 | 0.0328 | 0.433882 |
| DEFINITIONS-025 | 10 | 12 | 0.2000 | 0.00 | 0.0317 | 0.359406 |
| STANDARD_TERMS-015 | 8 | 13 | 0.2000 | 0.00 | 0.0328 | 0.354986 |
| STANDARD_TERMS-004 | 15 | 14 | 0.2000 | 0.00 | 0.0299 | 0.315443 |
| GRIEVANCES-001 | 12 | 15 | 0.2000 | 0.00 | 0.0308 | 0.253070 |

### N08 — natural

**Query:** illness that existed before the policy started

**Relevant chunks:** ['DEFINITIONS-036', 'EXCLUSIONS-001']

**Hybrid top 5:** ['DEFINITIONS-022', 'DEFINITIONS-003', 'DEFINITIONS-036', 'DEFINITIONS-035', 'STANDARD_TERMS-011']

**Reranked top 5:** ['DEFINITIONS-022', 'STANDARD_TERMS-011', 'STANDARD_TERMS-008', 'EXCLUSIONS-004', 'DEFINITIONS-035']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| DEFINITIONS-036 | 3 | 10 | moved_down |
| EXCLUSIONS-001 | 7 | 11 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| DEFINITIONS-022 | 1 | 1 | 0.5000 | 0.00 | 0.0645 | 0.635288 |
| STANDARD_TERMS-011 | 5 | 2 | 0.4000 | 0.00 | 0.0317 | 0.518766 |
| STANDARD_TERMS-008 | 11 | 3 | 0.4000 | 0.00 | 0.0299 | 0.496554 |
| EXCLUSIONS-004 | 9 | 4 | 0.3000 | 0.00 | 0.0308 | 0.445712 |
| DEFINITIONS-035 | 4 | 5 | 0.3000 | 0.00 | 0.0323 | 0.434299 |
| DEFINITIONS-005 | 6 | 6 | 0.3000 | 0.00 | 0.0312 | 0.434078 |
| DEFINITIONS-015 | 8 | 7 | 0.3000 | 0.00 | 0.0308 | 0.427935 |
| STANDARD_TERMS-022 | 14 | 8 | 0.3000 | 0.00 | 0.0294 | 0.412457 |
| DEFINITIONS-003 | 2 | 9 | 0.2000 | 0.00 | 0.0626 | 0.383407 |
| DEFINITIONS-036 | 3 | 10 | 0.2000 | 0.00 | 0.0328 | 0.345675 |
| EXCLUSIONS-001 | 7 | 11 | 0.2000 | 0.00 | 0.0312 | 0.282097 |
| EXCLUSIONS-021 | 10 | 12 | 0.0000 | 0.00 | 0.0303 | 0.172821 |
| EXCLUSIONS-012 | 15 | 13 | 0.0000 | 0.00 | 0.0290 | 0.164732 |
| EXCLUSIONS-007 | 12 | 14 | 0.0000 | 0.00 | 0.0299 | 0.149135 |
| EXCLUSIONS-023 | 13 | 15 | 0.0000 | 0.00 | 0.0294 | 0.119705 |

### N09 — natural

**Query:** is plastic surgery for looks covered

**Relevant chunks:** ['EXCLUSIONS-008']

**Hybrid top 5:** ['EXCLUSIONS-008', 'EXCLUSIONS-010', 'DEFINITIONS-012', 'DEFINITIONS-046', 'STANDARD_TERMS-016']

**Reranked top 5:** ['SCOPE_OF_COVER-003', 'EXCLUSIONS-008', 'STANDARD_TERMS-016', 'EXCLUSIONS-001', 'STANDARD_TERMS-020']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-008 | 1 | 2 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-003 | 8 | 1 | 0.4667 | 0.15 | 0.0573 | 0.728617 |
| EXCLUSIONS-008 | 1 | 2 | 0.3500 | 0.00 | 0.0656 | 0.520837 |
| STANDARD_TERMS-016 | 5 | 3 | 0.3500 | 0.00 | 0.0598 | 0.500319 |
| EXCLUSIONS-001 | 10 | 4 | 0.3500 | 0.00 | 0.0557 | 0.456500 |
| STANDARD_TERMS-020 | 7 | 5 | 0.3500 | 0.00 | 0.0585 | 0.456053 |
| DEFINITIONS-046 | 4 | 6 | 0.2333 | 0.00 | 0.0602 | 0.401525 |
| STANDARD_TERMS-007 | 9 | 7 | 0.2333 | 0.00 | 0.0572 | 0.397438 |
| DEFINITIONS-024 | 11 | 8 | 0.2333 | 0.00 | 0.0312 | 0.393477 |
| EXCLUSIONS-006 | 6 | 9 | 0.2333 | 0.00 | 0.0597 | 0.343922 |
| EXCLUSIONS-010 | 2 | 10 | 0.1167 | 0.00 | 0.0635 | 0.322507 |
| DEFINITIONS-012 | 3 | 11 | 0.1167 | 0.00 | 0.0604 | 0.296141 |
| EXCLUSIONS-009 | 12 | 12 | 0.0000 | 0.00 | 0.0303 | 0.170654 |
| EXCLUSIONS-012 | 14 | 13 | 0.0000 | 0.00 | 0.0294 | 0.165158 |
| EXCLUSIONS-013 | 15 | 14 | 0.0000 | 0.00 | 0.0290 | 0.149831 |
| EXCLUSIONS-014 | 13 | 15 | 0.0000 | 0.00 | 0.0299 | 0.146130 |

### N10 — natural

**Query:** is childbirth covered

**Relevant chunks:** ['EXCLUSIONS-014']

**Hybrid top 5:** ['EXCLUSIONS-014', 'EXCLUSIONS-001', 'STANDARD_TERMS-016', 'DEFINITIONS-035', 'SCOPE_OF_COVER-003']

**Reranked top 5:** ['SCOPE_OF_COVER-003', 'STANDARD_TERMS-016', 'STANDARD_TERMS-007', 'EXCLUSIONS-001', 'STANDARD_TERMS-020']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-014 | 1 | 7 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| SCOPE_OF_COVER-003 | 5 | 1 | 0.4667 | 0.15 | 0.0569 | 0.728164 |
| STANDARD_TERMS-016 | 3 | 2 | 0.4667 | 0.00 | 0.0597 | 0.616879 |
| STANDARD_TERMS-007 | 10 | 3 | 0.4667 | 0.00 | 0.0312 | 0.604773 |
| EXCLUSIONS-001 | 2 | 4 | 0.4667 | 0.00 | 0.0630 | 0.580541 |
| STANDARD_TERMS-020 | 8 | 5 | 0.4667 | 0.00 | 0.0317 | 0.545919 |
| STANDARD_TERMS-017 | 13 | 6 | 0.4667 | 0.00 | 0.0294 | 0.537501 |
| EXCLUSIONS-014 | 1 | 7 | 0.2333 | 0.00 | 0.0656 | 0.415186 |
| DEFINITIONS-024 | 7 | 8 | 0.2333 | 0.00 | 0.0323 | 0.394485 |
| DEFINITIONS-035 | 4 | 9 | 0.2333 | 0.00 | 0.0588 | 0.394147 |
| DEFINITIONS-038 | 6 | 10 | 0.2333 | 0.00 | 0.0565 | 0.390946 |
| DEFINITIONS-049 | 15 | 11 | 0.2333 | 0.00 | 0.0290 | 0.383776 |
| EXCLUSIONS-020 | 9 | 12 | 0.0000 | 0.00 | 0.0312 | 0.171930 |
| EXCLUSIONS-021 | 14 | 13 | 0.0000 | 0.00 | 0.0290 | 0.171503 |
| EXCLUSIONS-013 | 12 | 14 | 0.0000 | 0.00 | 0.0303 | 0.151149 |
| EXCLUSIONS-006 | 11 | 15 | 0.0000 | 0.00 | 0.0308 | 0.081703 |

### N11 — natural

**Query:** injury caused by drinking alcohol or deliberately hurting oneself

**Relevant chunks:** ['EXCLUSIONS-011']

**Hybrid top 5:** ['DEFINITIONS-023', 'EXCLUSIONS-015', 'DEFINITIONS-002', 'EXCLUSIONS-007', 'DEFINITIONS-001']

**Reranked top 5:** ['EXCLUSIONS-015', 'DEFINITIONS-023', 'EXCLUSIONS-007', 'DEFINITIONS-002', 'EXCLUSIONS-017']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-011 | 8 | 10 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-015 | 2 | 1 | 0.3111 | 0.00 | 0.0636 | 0.507705 |
| DEFINITIONS-023 | 1 | 2 | 0.3111 | 0.00 | 0.0645 | 0.494221 |
| EXCLUSIONS-007 | 4 | 3 | 0.3111 | 0.00 | 0.0635 | 0.493903 |
| DEFINITIONS-002 | 3 | 4 | 0.3111 | 0.00 | 0.0635 | 0.490226 |
| EXCLUSIONS-017 | 9 | 5 | 0.2333 | 0.00 | 0.0577 | 0.410556 |
| DEFINITIONS-036 | 10 | 6 | 0.2333 | 0.00 | 0.0569 | 0.403099 |
| DEFINITIONS-046 | 14 | 7 | 0.2333 | 0.00 | 0.0286 | 0.369916 |
| DEFINITIONS-001 | 5 | 8 | 0.1556 | 0.00 | 0.0625 | 0.350814 |
| EXCLUSIONS-013 | 11 | 9 | 0.1556 | 0.00 | 0.0561 | 0.332480 |
| EXCLUSIONS-011 | 8 | 10 | 0.1556 | 0.00 | 0.0580 | 0.331802 |
| EXCLUSIONS-008 | 6 | 11 | 0.1556 | 0.00 | 0.0585 | 0.319291 |
| DEFINITIONS-022 | 7 | 12 | 0.1556 | 0.00 | 0.0584 | 0.284708 |
| DEFINITIONS-015 | 15 | 13 | 0.1556 | 0.00 | 0.0278 | 0.280499 |
| EXCLUSIONS-010 | 13 | 14 | 0.0778 | 0.00 | 0.0286 | 0.248698 |
| EXCLUSIONS-024 | 12 | 15 | 0.0000 | 0.00 | 0.0290 | 0.166600 |

### N12 — natural

**Query:** claims arising from war, riots or nuclear events

**Relevant chunks:** ['EXCLUSIONS-007', 'EXCLUSIONS-024']

**Hybrid top 5:** ['EXCLUSIONS-024', 'EXCLUSIONS-007', 'EXCLUSIONS-015', 'STANDARD_TERMS-003', 'DEFINITIONS-051']

**Reranked top 5:** ['EXCLUSIONS-007', 'EXCLUSIONS-024', 'EXCLUSIONS-014', 'EXCLUSIONS-015', 'EXCLUSIONS-005']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-007 | 2 | 1 | moved_up |
| EXCLUSIONS-024 | 1 | 2 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-007 | 2 | 1 | 0.3500 | 0.00 | 0.0645 | 0.533800 |
| EXCLUSIONS-024 | 1 | 2 | 0.2625 | 0.00 | 0.0656 | 0.465688 |
| EXCLUSIONS-014 | 7 | 3 | 0.2625 | 0.00 | 0.0317 | 0.410525 |
| EXCLUSIONS-015 | 3 | 4 | 0.1750 | 0.00 | 0.0630 | 0.371034 |
| EXCLUSIONS-005 | 14 | 5 | 0.2625 | 0.00 | 0.0290 | 0.364612 |
| DEFINITIONS-051 | 5 | 6 | 0.1750 | 0.00 | 0.0585 | 0.351657 |
| STANDARD_TERMS-003 | 4 | 7 | 0.1750 | 0.00 | 0.0588 | 0.348340 |
| CLAIMS_PROCEDURE-003 | 15 | 8 | 0.1750 | 0.00 | 0.0286 | 0.311002 |
| EXCLUSIONS-008 | 11 | 9 | 0.1750 | 0.00 | 0.0303 | 0.310566 |
| CLAIMS_PROCEDURE-004 | 6 | 10 | 0.0875 | 0.00 | 0.0576 | 0.277531 |
| STANDARD_TERMS-025 | 13 | 11 | 0.1750 | 0.00 | 0.0294 | 0.270346 |
| GRIEVANCES-001 | 8 | 12 | 0.1750 | 0.00 | 0.0312 | 0.228551 |
| STANDARD_TERMS-006 | 10 | 13 | 0.0875 | 0.00 | 0.0303 | 0.217886 |
| DEFINITIONS-001 | 9 | 14 | 0.0000 | 0.00 | 0.0308 | 0.163513 |
| CLAIMS_PROCEDURE-001 | 12 | 15 | 0.0000 | 0.00 | 0.0299 | 0.154851 |

### N13 — natural

**Query:** treatment from a doctor of alternative medicine

**Relevant chunks:** ['EXCLUSIONS-017']

**Hybrid top 5:** ['DEFINITIONS-005', 'DEFINITIONS-028', 'DEFINITIONS-003', 'DEFINITIONS-029', 'EXCLUSIONS-023']

**Reranked top 5:** ['DEFINITIONS-005', 'DEFINITIONS-029', 'DEFINITIONS-003', 'EXCLUSIONS-014', 'DEFINITIONS-028']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| EXCLUSIONS-017 | Not retrieved | Not retrieved | not_in_candidate_pool |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| DEFINITIONS-005 | 1 | 1 | 0.4667 | 0.00 | 0.0656 | 0.635068 |
| DEFINITIONS-029 | 4 | 2 | 0.4667 | 0.00 | 0.0589 | 0.598896 |
| DEFINITIONS-003 | 3 | 3 | 0.3500 | 0.00 | 0.0589 | 0.529784 |
| EXCLUSIONS-014 | 7 | 4 | 0.3500 | 0.00 | 0.0312 | 0.497529 |
| DEFINITIONS-028 | 2 | 5 | 0.2333 | 0.00 | 0.0595 | 0.420517 |
| EXCLUSIONS-010 | 14 | 6 | 0.2333 | 0.00 | 0.0294 | 0.405094 |
| DEFINITIONS-040 | 13 | 7 | 0.2333 | 0.00 | 0.0299 | 0.390573 |
| STANDARD_TERMS-015 | 11 | 8 | 0.2333 | 0.00 | 0.0303 | 0.385836 |
| EXCLUSIONS-008 | 15 | 9 | 0.2333 | 0.00 | 0.0294 | 0.368008 |
| STANDARD_TERMS-006 | 6 | 10 | 0.2333 | 0.00 | 0.0317 | 0.365163 |
| EXCLUSIONS-023 | 5 | 11 | 0.2333 | 0.00 | 0.0323 | 0.355885 |
| DEFINITIONS-033 | 10 | 12 | 0.2333 | 0.00 | 0.0303 | 0.353659 |
| EXCLUSIONS-021 | 9 | 13 | 0.1167 | 0.00 | 0.0308 | 0.289954 |
| EXCLUSIONS-022 | 12 | 14 | 0.1167 | 0.00 | 0.0299 | 0.288866 |
| DEFINITIONS-049 | 8 | 15 | 0.1167 | 0.00 | 0.0312 | 0.269374 |

### N14 — natural

**Query:** transferring my policy from another insurer

**Relevant chunks:** ['STANDARD_TERMS-011', 'DEFINITIONS-037']

**Hybrid top 5:** ['DEFINITIONS-037', 'STANDARD_TERMS-019', 'DEFINITIONS-034', 'STANDARD_TERMS-018', 'DEFINITIONS-047']

**Reranked top 5:** ['DEFINITIONS-037', 'DEFINITIONS-047', 'STANDARD_TERMS-011', 'EXCLUSIONS-005', 'STANDARD_TERMS-019']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| STANDARD_TERMS-011 | 6 | 3 | moved_up |
| DEFINITIONS-037 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| DEFINITIONS-037 | 1 | 1 | 0.4667 | 0.00 | 0.0640 | 0.646870 |
| DEFINITIONS-047 | 5 | 2 | 0.3500 | 0.00 | 0.0323 | 0.505083 |
| STANDARD_TERMS-011 | 6 | 3 | 0.3500 | 0.00 | 0.0317 | 0.468766 |
| EXCLUSIONS-005 | 15 | 4 | 0.3500 | 0.00 | 0.0294 | 0.452538 |
| STANDARD_TERMS-019 | 2 | 5 | 0.2333 | 0.00 | 0.0594 | 0.395668 |
| DEFINITIONS-008 | 12 | 6 | 0.2333 | 0.00 | 0.0299 | 0.392774 |
| DEFINITIONS-006 | 10 | 7 | 0.2333 | 0.00 | 0.0303 | 0.373026 |
| STANDARD_TERMS-018 | 4 | 8 | 0.2333 | 0.00 | 0.0323 | 0.354022 |
| STANDARD_TERMS-020 | 7 | 9 | 0.2333 | 0.00 | 0.0317 | 0.312585 |
| STANDARD_TERMS-017 | 14 | 10 | 0.2333 | 0.00 | 0.0294 | 0.304167 |
| GRIEVANCES-001 | 11 | 11 | 0.2333 | 0.00 | 0.0303 | 0.285937 |
| DEFINITIONS-034 | 3 | 12 | 0.1167 | 0.00 | 0.0328 | 0.268619 |
| DEFINITIONS-031 | 8 | 13 | 0.1167 | 0.00 | 0.0308 | 0.268526 |
| EXCLUSIONS-004 | 9 | 14 | 0.1167 | 0.00 | 0.0308 | 0.262378 |
| DEFINITIONS-025 | 13 | 15 | 0.0000 | 0.00 | 0.0299 | 0.157510 |

### N15 — natural

**Query:** what happens if the policyholder gives false information or commits fraud

**Relevant chunks:** ['STANDARD_TERMS-003', 'STANDARD_TERMS-002']

**Hybrid top 5:** ['STANDARD_TERMS-003', 'DEFINITIONS-016', 'STANDARD_TERMS-004', 'STANDARD_TERMS-019', 'STANDARD_TERMS-016']

**Reranked top 5:** ['STANDARD_TERMS-003', 'DEFINITIONS-016', 'STANDARD_TERMS-019', 'STANDARD_TERMS-004', 'PREAMBLE-001']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| STANDARD_TERMS-003 | 1 | 1 | unchanged |
| STANDARD_TERMS-002 | 6 | 12 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| STANDARD_TERMS-003 | 1 | 1 | 0.2545 | 0.00 | 0.0656 | 0.434623 |
| DEFINITIONS-016 | 2 | 2 | 0.1909 | 0.00 | 0.0630 | 0.372047 |
| STANDARD_TERMS-019 | 4 | 3 | 0.1909 | 0.00 | 0.0552 | 0.349021 |
| STANDARD_TERMS-004 | 3 | 4 | 0.1909 | 0.00 | 0.0616 | 0.338054 |
| PREAMBLE-001 | 9 | 5 | 0.2545 | 0.00 | 0.0312 | 0.336773 |
| STANDARD_TERMS-016 | 5 | 6 | 0.1909 | 0.00 | 0.0533 | 0.334740 |
| STANDARD_TERMS-017 | 14 | 7 | 0.2545 | 0.00 | 0.0294 | 0.325379 |
| EXTENSIONS-001 | 12 | 8 | 0.1909 | 0.00 | 0.0299 | 0.306291 |
| STANDARD_TERMS-015 | 11 | 9 | 0.1273 | 0.00 | 0.0303 | 0.279775 |
| DEFINITIONS-034 | 15 | 10 | 0.1273 | 0.00 | 0.0294 | 0.275850 |
| DEFINITIONS-010 | 7 | 11 | 0.1273 | 0.00 | 0.0317 | 0.275750 |
| STANDARD_TERMS-002 | 6 | 12 | 0.1273 | 0.00 | 0.0323 | 0.268721 |
| DEFINITIONS-039 | 10 | 13 | 0.1273 | 0.00 | 0.0308 | 0.268033 |
| GRIEVANCES-001 | 8 | 14 | 0.1909 | 0.00 | 0.0317 | 0.244956 |
| STANDARD_TERMS-022 | 13 | 15 | 0.1273 | 0.00 | 0.0299 | 0.240168 |

### N16 — natural

**Query:** how long do I have to cancel the policy after buying it and get a refund

**Relevant chunks:** ['STANDARD_TERMS-014', 'STANDARD_TERMS-015', 'STANDARD_TERMS-016']

**Hybrid top 5:** ['STANDARD_TERMS-004', 'STANDARD_TERMS-024', 'STANDARD_TERMS-005', 'STANDARD_TERMS-016', 'STANDARD_TERMS-015']

**Reranked top 5:** ['STANDARD_TERMS-020', 'STANDARD_TERMS-016', 'STANDARD_TERMS-024', 'STANDARD_TERMS-011', 'STANDARD_TERMS-005']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| STANDARD_TERMS-014 | Not retrieved | Not retrieved | not_in_candidate_pool |
| STANDARD_TERMS-015 | 5 | 9 | moved_down |
| STANDARD_TERMS-016 | 4 | 2 | moved_up |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| STANDARD_TERMS-020 | 6 | 1 | 0.4000 | 0.00 | 0.0328 | 0.480293 |
| STANDARD_TERMS-016 | 4 | 2 | 0.3000 | 0.00 | 0.0589 | 0.449436 |
| STANDARD_TERMS-024 | 2 | 3 | 0.3000 | 0.00 | 0.0620 | 0.432899 |
| STANDARD_TERMS-011 | 13 | 4 | 0.3000 | 0.00 | 0.0294 | 0.416431 |
| STANDARD_TERMS-005 | 3 | 5 | 0.2500 | 0.00 | 0.0599 | 0.404255 |
| STANDARD_TERMS-021 | 7 | 6 | 0.3000 | 0.00 | 0.0317 | 0.403602 |
| STANDARD_TERMS-004 | 1 | 7 | 0.2500 | 0.00 | 0.0645 | 0.400108 |
| STANDARD_TERMS-018 | 10 | 8 | 0.2500 | 0.00 | 0.0303 | 0.368733 |
| STANDARD_TERMS-015 | 5 | 9 | 0.2000 | 0.00 | 0.0328 | 0.354986 |
| EXCLUSIONS-005 | 14 | 10 | 0.2500 | 0.00 | 0.0294 | 0.352538 |
| DEFINITIONS-022 | 9 | 11 | 0.2500 | 0.00 | 0.0303 | 0.351058 |
| DEFINITIONS-003 | 11 | 12 | 0.2000 | 0.00 | 0.0299 | 0.350697 |
| DEFINITIONS-017 | 15 | 13 | 0.2000 | 0.00 | 0.0290 | 0.341767 |
| STANDARD_TERMS-017 | 8 | 14 | 0.2500 | 0.00 | 0.0312 | 0.322672 |
| CLAIMS_PROCEDURE-003 | 12 | 15 | 0.1500 | 0.00 | 0.0299 | 0.287281 |

### N17 — natural

**Query:** extra sum insured earned for not making claims

**Relevant chunks:** ['DEFINITIONS-011', 'EXCLUSIONS-003']

**Hybrid top 5:** ['EXTENSIONS-001', 'EXCLUSIONS-005', 'EXCLUSIONS-003', 'STANDARD_TERMS-023', 'DEFINITIONS-010']

**Reranked top 5:** ['EXCLUSIONS-005', 'EXTENSIONS-001', 'DEFINITIONS-010', 'EXCLUSIONS-004', 'EXCLUSIONS-001']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| DEFINITIONS-011 | 6 | 11 | moved_down |
| EXCLUSIONS-003 | 3 | 7 | moved_down |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| EXCLUSIONS-005 | 2 | 1 | 0.4375 | 0.00 | 0.0640 | 0.574663 |
| EXTENSIONS-001 | 1 | 2 | 0.3500 | 0.00 | 0.0645 | 0.500047 |
| DEFINITIONS-010 | 5 | 3 | 0.2625 | 0.00 | 0.0586 | 0.437879 |
| EXCLUSIONS-004 | 7 | 4 | 0.2625 | 0.00 | 0.0580 | 0.435426 |
| EXCLUSIONS-001 | 14 | 5 | 0.3500 | 0.00 | 0.0290 | 0.429833 |
| STANDARD_TERMS-020 | 10 | 6 | 0.3500 | 0.00 | 0.0303 | 0.427809 |
| EXCLUSIONS-003 | 3 | 7 | 0.2625 | 0.00 | 0.0625 | 0.407151 |
| SCOPE_OF_COVER-001 | 11 | 8 | 0.2625 | 0.00 | 0.0299 | 0.399112 |
| STANDARD_TERMS-022 | 15 | 9 | 0.2625 | 0.00 | 0.0286 | 0.374116 |
| STANDARD_TERMS-023 | 4 | 10 | 0.1750 | 0.00 | 0.0616 | 0.370825 |
| DEFINITIONS-011 | 6 | 11 | 0.1750 | 0.00 | 0.0582 | 0.363460 |
| CLAIMS_PROCEDURE-004 | 9 | 12 | 0.1750 | 0.00 | 0.0303 | 0.337753 |
| CLAIMS_PROCEDURE-002 | 8 | 13 | 0.1750 | 0.00 | 0.0328 | 0.329367 |
| DEFINITIONS-025 | 12 | 14 | 0.0875 | 0.00 | 0.0294 | 0.244571 |
| STANDARD_TERMS-002 | 13 | 15 | 0.0000 | 0.00 | 0.0290 | 0.138176 |

### N18 — natural

**Query:** what qualifies as a hospital in terms of beds and staff

**Relevant chunks:** ['DEFINITIONS-021']

**Hybrid top 5:** ['DEFINITIONS-021', 'DEFINITIONS-013', 'SCOPE_OF_COVER-001', 'DEFINITIONS-027', 'SCOPE_OF_COVER-003']

**Reranked top 5:** ['DEFINITIONS-021', 'DEFINITIONS-013', 'SCOPE_OF_COVER-001', 'PREAMBLE-001', 'STANDARD_TERMS-013']

| Relevant chunk | Hybrid rank | Reranked rank | Movement |
|---|---:|---:|---|
| DEFINITIONS-021 | 1 | 1 | unchanged |

| Candidate | Hybrid rank | Reranked rank | Coverage | Prior | Fused contribution | Final score |
|---|---:|---:|---:|---:|---:|---:|
| DEFINITIONS-021 | 1 | 1 | 0.4900 | 0.00 | 0.0656 | 0.627045 |
| DEFINITIONS-013 | 2 | 2 | 0.4200 | 0.00 | 0.0640 | 0.547563 |
| SCOPE_OF_COVER-001 | 3 | 3 | 0.3500 | 0.00 | 0.0611 | 0.517834 |
| PREAMBLE-001 | 8 | 4 | 0.4200 | 0.00 | 0.0312 | 0.502227 |
| STANDARD_TERMS-013 | 7 | 5 | 0.3500 | 0.00 | 0.0317 | 0.495060 |
| EXTENSIONS-001 | 10 | 6 | 0.3500 | 0.00 | 0.0308 | 0.466300 |
| SCOPE_OF_COVER-003 | 5 | 7 | 0.3500 | 0.00 | 0.0565 | 0.461137 |
| CLAIMS_PROCEDURE-001 | 14 | 8 | 0.2800 | 0.00 | 0.0290 | 0.433986 |
| DEFINITIONS-027 | 4 | 9 | 0.2800 | 0.00 | 0.0573 | 0.433638 |
| DEFINITIONS-034 | 13 | 10 | 0.2800 | 0.00 | 0.0294 | 0.428578 |
| DEFINITIONS-039 | 11 | 11 | 0.2800 | 0.00 | 0.0299 | 0.419842 |
| DEFINITIONS-043 | 9 | 12 | 0.2100 | 0.00 | 0.0312 | 0.367433 |
| DEFINITIONS-020 | 6 | 13 | 0.2100 | 0.00 | 0.0323 | 0.358650 |
| DEFINITIONS-024 | 12 | 14 | 0.1400 | 0.00 | 0.0294 | 0.298305 |
| DEFINITIONS-038 | 15 | 15 | 0.1400 | 0.00 | 0.0290 | 0.270081 |
