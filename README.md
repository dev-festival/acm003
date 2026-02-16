# ACM Coverage Analysis Project

**Asset Condition Monitoring (ACM) Coverage to Standard**

This project analyzes monitoring technology coverage across organizational assets, tracking seven key technologies (GM, IR, UL, VI, LU, MC, ZD) against implementation standards.

---

## Project Goal

Create fully runnable Quarto document(s) using Python to:
- Execute SQL scripts to extract Maximo data
- Ingest standard reference tables
- Engineer boolean coverage masks per technology
- Generate coverage analysis charts and reports
- Maintain reproducibility with dynamic outputs (no hardcoded numbers)


### The Power of What You Built

Dynamic: Add new tech to techs_def.csv → automatically flows through
Traceable: Asset → Class → Components → Required Tech → Actual Coverage → Gap Judgment
Actionable: MASTER_JUDGE = 0 = critical gaps to address
Repeatable: SQL → Process → Report (all in one Quarto doc)
Documented: README tracks everything
---

## Folder Structure

```
.
├── data/                          # Data storage
│   ├── st_tbl/                   # Standard/static reference tables
│   │   ├── comp_tech_map.csv     # Component to technology mapping (map1)
│   │   └── asset_xref_comp.csv    # Asset cross-reference mapping (map2)
│   └── *.pkl                     # Intermediate pickle files from processing
│
├── query/                         # SQL extraction scripts
│   ├── has_mon-meters.sql    # Extracts 24,091 meter records
│   └── has_mon-routes.sql    # Extracts 2,370 route records
│
├── notebook/                      # Jupyter notebooks (development/troubleshooting)
│   └── (mirrors Quarto docs for fast iteration)
│   └── has_mon-meters.ipynb
│   └── has_mon-routes.ipynb
│   
├── output/                        # Final deliverables
│   ├── charts/                   # Generated visualizations
│   ├── reports/                  # HTML/PDF reports
│   └── tables/                   # Summary CSV exports
│
├── src/                          # Python utilities (if needed)
│
├── ACM003.qmd                    # Main coverage analysis document
├── ACM003-merge.qmd              # Merge strategy document
├── ACM003_revealjs.qmd           # Presentation version
├── .env                          # Database connection credentials
└── README.md                     # This file
```

---

## Data Pipeline Overview

### Data Sources (Maximo SQL)
1. **Meters Table** (`acm_assets_meters-coverage.sql`)
   - 24,091 meter records
   - Tracks General Metering (GM) technology
   - Key field: `LASTREADINGDATE` for recency checks

2. **Routes Table** (`acm_assets_routes-coverage.sql`)
   - 2,370 route-asset records  
   - Tracks IR, UL, VI, LU, MC, ZD technologies
   - Route descriptions follow pattern: `DEPT_TECH_VENDOR`

### Processing Strategy: Unified Pre-Aggregation Merge

**Key Innovation:** Merge raw data sources BEFORE aggregation to use asset master table as single source of truth, avoiding column conflicts (DEPT, CLASS, ASSET_DESC).

#### Step 1: Raw Data Extraction
- Extract meters data → 24,091 records (15 columns)
- Extract routes data → 2,370 records (6 columns)

#### Step 2: Pre-Merge Combination
- **Outer join** on `ASSETNUM` to preserve all meter + route records
- Maintains raw granularity before aggregation

#### Step 3: Unified Aggregation
- Group by `ASSETNUM`
- Take first occurrence for: `DEPT`, `CLASS`, `ASSET_DESC` (from asset master)
- Aggregate technology indicators per asset

#### Step 4: Coverage Logic Application
- **HAS_GM**: `Y` if meter reading within 1 year, else `N`
- **HAS_IR/UL/VI/LU/MC/ZD**: `Y` if technology present in routes, else `N`
- Track vendor details per technology

#### Step 5: Output Generation
- Primary: `meters-routes-coverage.pkl` (~8,223 assets)
- Export: `meters-routes-coverage.csv` for business review
- Detail: `asset-tech-vendor-detail.pkl` for granular analysis

---

## Technology Codes

| Code | Technology | Source |
|------|------------|--------|
| GM   | General Metering | Meters table |
| IR   | Infrared Thermography | Routes table |
| UL   | Ultrasound | Routes table |
| VI   | Vibration Analysis | Routes table |
| LU   | Lubrication | Routes table |
| MC   | Motor Circuit Analysis | Routes table |
| ZD   | Zone Dosimetry | Routes table |

---

## Key Design Decisions

### 1. Reading Date Thresholds Per Technology
**Critical:** Reading date thresholds apply **per technology**, not globally. A stale meter in one technology should not disqualify coverage in another technology.

### 2. Asset Master as Single Source of Truth
By merging raw data before aggregation, we ensure:
- No duplicate columns (DEPT_METERS vs DEPT_ROUTES)
- Consistent asset attributes across all technologies
- Clean many-to-one relationships

### 3. Boolean Coverage Flags
Each asset gets clear Y/N flags per technology:
- `HAS_GM`, `HAS_IR`, `HAS_UL`, `HAS_VI`, `HAS_LU`, `HAS_MC`, `HAS_ZD`
- Enables easy filtering and gap analysis

### 4. Notebook ↔ Quarto Mirroring
- **Jupyter notebooks**: Fast iteration, troubleshooting, data exploration
- **Quarto documents**: Same logic, polished output, slower rendering
- Keep synchronized for reproducibility

---

## File Inventory

### Quarto Documents (Root Directory)

| File | Purpose | Status | Output |
|------|---------|--------|--------|
| `ACM003.qmd` | Main coverage analysis | Development | HTML/PDF report |
| `ACM003-merge.qmd` | Merge strategy documentation | Development | HTML/PDF report |
| `ACM003_revealjs.qmd` | Presentation version | Working | reveal.js slides |

### SQL Scripts (`query/`)

| File | Purpose | Records | Key Fields |
|------|---------|---------|------------|
| `acm_assets_meters-coverage.sql` | Extract meter data | 24,091 | ASSETNUM, METERNAME, LASTREADINGDATE, DEPT, CLASS |
| `acm_assets_routes-coverage.sql` | Extract route assignments | 2,370 | ASSETNUM, ROUTE, ROUTE_DESC, DEPT, CLASS |

### Standard Tables (`data/st_tbl/`)

| File | Purpose | Usage |
|------|---------|-------|
| `comp_tech_map.csv` | Component → Technology mapping | Maps asset components to required technologies |
| `asset_xref_map.csv` | Asset cross-reference mapping | Links related asset identifiers |

### Intermediate Files (`data/`)

| File | Purpose | Records | Columns |
|------|---------|---------|---------|
| `meters_flagged.pkl` | Flagged meter records with null reading detection | 24,091 | Raw + flags |
| `asset-tech-vendor-detail.pkl` | Granular route technology assignments | 2,252 | ASSETNUM, TECH, VENDOR, DEPT |
| `meters-routes-coverage.pkl` | **Primary output**: Unified coverage by asset | ~8,223 | ASSETNUM, DEPT, CLASS, HAS_* flags |

### Export Files (`output/` or `data/`)

| File | Purpose | Usage |
|------|---------|-------|
| `meters-routes-coverage.csv` | Business-friendly coverage report | Excel review, executive summaries |
| `meters_main.csv` | Aggregated meter coverage | Intermediate File |
| `routecoverage.csv` | Aggregated route coverage | Intermediate File |
| `needs_coverage.csv/pkl` | Needs Coverage file configured from 2 input files| Intermediate File |

---

## Quickstart Guide

### Prerequisites
- **Conda environment**: `icicle`
- **Python packages**: pandas, sqlalchemy, python-dotenv, matplotlib, plotly
- **Database access**: Maximo SQL credentials in `.env`

### Setup
```bash
# Activate conda environment
conda activate icicle

# Verify .env file contains database credentials
cat .env
```

### Running the Analysis

#### Option 1: Quarto Document (Production)
```bash
# Render main report
quarto render ACM003.qmd

# Render to specific format
quarto render ACM003.qmd --to html
quarto render ACM003.qmd --to pdf
```

#### Option 2: Jupyter Notebook (Development)
```bash
# Launch Jupyter
jupyter notebook

# Open corresponding notebook from notebook/ folder
# Run cells interactively for troubleshooting
```

### Expected Outputs
- **HTML Report**: `ACM003.html` with embedded charts
- **PDF Report**: `ACM003.pdf` for distribution
- **Data Files**: `data/meters-routes-coverage.pkl` and `.csv`
- **Charts**: Department-level coverage visualizations

---

## Workflow: Notebook → Quarto Sync

1. **Develop in Notebook**
   - Fast iteration in Jupyter
   - Test SQL connections
   - Validate data transformations
   - Generate exploratory charts

2. **Port to Quarto**
   - Copy working code blocks
   - Add narrative text
   - Format for reporting
   - Add dynamic output references

3. **Maintain Sync**
   - Keep notebook as "troubleshooting spine"
   - Quarto remains the production document
   - Update both when logic changes

---

## Next Steps

### Immediate (Organization Phase)
- [ ] Move standard tables to `data/st_tbl/`
- [ ] Verify SQL scripts are in `query/`
- [ ] Create mirrored Jupyter notebooks in `notebook/`
- [ ] Set up output folder structure

### Development Phase
- [ ] Add SQL execution to Quarto docs
- [ ] Implement pre-aggregation merge strategy
- [ ] Generate coverage boolean flags
- [ ] Create department-level visualizations
- [ ] Add summary statistics

### Future Enhancements
- [ ] "Needs Monitoring" analysis (component-based requirements)
- [ ] Failure mode mapping integration
- [ ] Gap analysis methodologies
- [ ] Streamlit dashboard integration

---

## Data Quality Checks

Every processing stage includes:
- **Record counts**: Validate expected volume
- **Null checks**: Flag missing critical fields
- **Date validation**: Ensure LASTREADINGDATE within expected range
- **Duplicate detection**: Check for unexpected many-to-many relationships
- **Technology coverage**: Summary counts per technology

---

## Common Issues & Solutions

### Issue: Quarto rendering takes too long
**Solution**: Use Jupyter notebook for development, only render Quarto for final output

### Issue: Column conflicts during merge (DEPT_METERS vs DEPT_ROUTES)
**Solution**: Use pre-aggregation merge strategy (merge raw data first)

### Issue: Stale meter reading disqualifies other technologies
**Solution**: Apply reading date threshold per technology, not globally

### Issue: Lost track of what files do
**Solution**: Refer to this README's file inventory section

---

## Contact & Support

**Project Owner**: Mike  
**Environment**: `icicle` conda environment  
**Last Updated**: February 11, 2026

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-11 | 1.0 | Initial README creation, project organization |
| 2026-01-26 | 0.9 | Merge strategy development (ACM003-merge.qmd) |
| 2026-02-10 | 0.9.1 | Presentation version created (ACM003_revealjs.qmd) |
