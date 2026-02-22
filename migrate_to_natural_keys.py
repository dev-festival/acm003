"""
ACM Config Migration: Integer Keys → Natural Keys
==================================================
Converts the five normalized config CSVs from integer foreign keys
to natural key format (component_name, class_name directly in junction tables).

Also initializes change_log.csv.

Run once. Safe to re-run — it will not overwrite if output already exists
unless --force flag is passed.

Usage:
    python migrate_to_natural_keys.py --source <dir> --output <dir>
    python migrate_to_natural_keys.py --source data/st_tbl --output data/st_tbl/normalized_config

Known data issue flagged during migration:
    component_technology.csv contains technology_code 'CH' (Chain Drives / Chain Links)
    but technologies.csv defines the code as 'CW'.
    This script will flag those rows and write them to a review file.
    You must resolve before the pipeline will treat those rows as valid.
"""

import pandas as pd
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_sources(source_dir: Path) -> dict:
    """Load all five source CSVs. Raises clearly if any are missing."""
    required = ['components.csv', 'technologies.csv', 'classes.csv',
                'component_technology.csv', 'class_component.csv']
    frames = {}
    for fname in required:
        fpath = source_dir / fname
        if not fpath.exists():
            print(f"  ✗ Missing: {fpath}")
            sys.exit(1)
        frames[fname.replace('.csv', '')] = pd.read_csv(fpath)
        print(f"  ✓ Loaded {fname:40s} ({len(frames[fname.replace('.csv','')]):>4} rows)")
    return frames


def validate_sources(frames: dict) -> list:
    """Run pre-migration integrity checks. Returns list of warning strings."""
    warnings = []
    comp_ids = set(frames['components']['component_id'])
    class_ids = set(frames['classes']['class_id'])
    tech_codes_master = set(frames['technologies']['technology_code'])

    # comp_tech: orphaned component IDs
    orphan_comp = set(frames['component_technology']['component_id']) - comp_ids
    if orphan_comp:
        warnings.append(f"component_technology has unknown component_ids: {sorted(orphan_comp)}")

    # class_comp: orphaned class/component IDs
    orphan_class = set(frames['class_component']['class_id']) - class_ids
    if orphan_class:
        warnings.append(f"class_component has unknown class_ids: {sorted(orphan_class)}")

    orphan_comp2 = set(frames['class_component']['component_id']) - comp_ids
    if orphan_comp2:
        warnings.append(f"class_component has unknown component_ids: {sorted(orphan_comp2)}")

    # tech code mismatch (CH vs CW)
    used_tech_codes = set(frames['component_technology']['technology_code'])
    unknown_tech = used_tech_codes - tech_codes_master
    if unknown_tech:
        warnings.append(
            f"component_technology contains technology codes not in technologies.csv: {sorted(unknown_tech)}\n"
            f"  → These rows will be written to 'review_unknown_tech_codes.csv' for your attention."
        )

    return warnings


# ── Migration ─────────────────────────────────────────────────────────────────

def migrate_component_technology(frames: dict, tech_codes_master: set) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convert component_technology: drop integer IDs, use component_name as key.
    Returns (clean_df, flagged_df) where flagged rows have unknown tech codes.
    """
    ct = frames['component_technology'].copy()
    comp_lookup = frames['components'].set_index('component_id')['component_name']

    # Resolve component_name
    ct['component_name'] = ct['component_id'].map(comp_lookup)

    # Split clean vs flagged
    flagged = ct[~ct['technology_code'].isin(tech_codes_master)].copy()
    clean = ct[ct['technology_code'].isin(tech_codes_master)].copy()

    # Final columns: natural key only
    clean = clean[['component_name', 'technology_code', 'application_type']].reset_index(drop=True)
    flagged = flagged[['component_name', 'technology_code', 'application_type']].reset_index(drop=True)

    return clean, flagged


def migrate_class_component(frames: dict) -> pd.DataFrame:
    """Convert class_component: drop integer IDs, use class_name + component_name."""
    cc = frames['class_component'].copy()
    comp_lookup = frames['components'].set_index('component_id')['component_name']
    class_lookup = frames['classes'].set_index('class_id')['class_name']

    cc['class_name'] = cc['class_id'].map(class_lookup)
    cc['component_name'] = cc['component_id'].map(comp_lookup)

    return cc[['class_name', 'component_name']].reset_index(drop=True)


def make_change_log() -> pd.DataFrame:
    """Initialize an empty change_log with the correct schema."""
    return pd.DataFrame(columns=[
        'log_id',           # incrementing integer, assigned at write time
        'timestamp',        # ISO 8601 UTC
        'entity_type',      # 'component', 'class', 'component_technology', 'class_component'
        'action',           # 'add', 'remove_request', 'remove_approved', 'remove_rejected'
        'entity_key',       # human-readable identifier of what changed
        'payload',          # JSON string with full detail of the change
        'notes',            # free-text from the requester
        'requested_by',     # name/username from Streamlit input
        'status',           # 'applied', 'pending', 'approved', 'rejected'
        'reviewed_by',      # admin name, filled on approval/rejection
        'reviewed_at',      # ISO 8601 UTC, filled on approval/rejection
    ])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Migrate ACM config to natural keys')
    parser.add_argument('--source', default='.',
                        help='Directory containing the five source CSVs')
    parser.add_argument('--output', default='normalized_config',
                        help='Output directory for migrated files')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite output directory if it already exists')
    args = parser.parse_args()

    source_dir = Path(args.source)
    output_dir = Path(args.output)

    print("\n" + "="*60)
    print("  ACM CONFIG MIGRATION: Integer Keys → Natural Keys")
    print("="*60)

    # ── Guard: don't overwrite without --force
    change_log_path = output_dir / 'change_log.csv'
    if change_log_path.exists() and not args.force:
        print(f"\n  Output already exists at {output_dir}")
        print("  Pass --force to overwrite. Exiting.")
        sys.exit(0)

    # ── Load
    print(f"\nLoading source files from: {source_dir}")
    frames = load_sources(source_dir)

    # ── Validate
    print("\nRunning pre-migration checks...")
    warnings = validate_sources(frames)
    if warnings:
        print("\n  ⚠ WARNINGS (migration will continue, review flagged files):")
        for w in warnings:
            for line in w.split('\n'):
                print(f"    {line}")
    else:
        print("  ✓ All integrity checks passed")

    # ── Migrate
    print(f"\nMigrating to natural keys...")
    tech_codes_master = set(frames['technologies']['technology_code'])

    comp_tech_clean, comp_tech_flagged = migrate_component_technology(frames, tech_codes_master)
    class_comp_migrated = migrate_class_component(frames)
    change_log = make_change_log()

    # Pass-through files (structure unchanged, just re-saved cleanly)
    components_clean = frames['components'][['component_id', 'component_name']].copy()
    technologies_clean = frames['technologies'][['technology_id', 'technology_code']].copy()
    classes_clean = frames['classes'][['class_id', 'class_name']].copy()

    # ── Write
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting output to: {output_dir}")

    # Master tables (unchanged structure)
    components_clean.to_csv(output_dir / 'components.csv', index=False)
    print(f"  ✓ components.csv              ({len(components_clean):>4} rows)")

    technologies_clean.to_csv(output_dir / 'technologies.csv', index=False)
    print(f"  ✓ technologies.csv            ({len(technologies_clean):>4} rows)")

    classes_clean.to_csv(output_dir / 'classes.csv', index=False)
    print(f"  ✓ classes.csv                 ({len(classes_clean):>4} rows)")

    # Junction tables (migrated to natural keys)
    comp_tech_clean.to_csv(output_dir / 'component_technology.csv', index=False)
    print(f"  ✓ component_technology.csv    ({len(comp_tech_clean):>4} rows, natural keys)")

    class_comp_migrated.to_csv(output_dir / 'class_component.csv', index=False)
    print(f"  ✓ class_component.csv         ({len(class_comp_migrated):>4} rows, natural keys)")

    # Change log (new)
    change_log.to_csv(output_dir / 'change_log.csv', index=False)
    print(f"  ✓ change_log.csv              (initialized, empty)")

    # Flagged rows
    if len(comp_tech_flagged) > 0:
        review_path = output_dir / 'review_unknown_tech_codes.csv'
        comp_tech_flagged.to_csv(review_path, index=False)
        print(f"\n  ⚠ review_unknown_tech_codes.csv  ({len(comp_tech_flagged):>4} rows — ACTION REQUIRED)")
        print(f"    These rows used technology_code 'CH' which is not in technologies.csv.")
        print(f"    technologies.csv defines 'CW' (Chain Wear Monitoring).")
        print(f"    Decide: rename 'CH' → 'CW' in the review file, then manually merge back,")
        print(f"    or update technologies.csv to add 'CH' if it's intentionally different.")

    # ── Summary
    print("\n" + "="*60)
    print("  MIGRATION COMPLETE")
    print("="*60)
    print(f"\n  component_technology.csv : {len(comp_tech_clean)} clean rows, {len(comp_tech_flagged)} flagged")
    print(f"  class_component.csv      : {len(class_comp_migrated)} rows")
    print(f"\n  Next step: update ACMConfig() to point at '{output_dir}'")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
