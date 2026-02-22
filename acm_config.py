"""
ACM Configuration Manager
==========================
Manages the five normalized config CSVs that define monitoring requirements:

    components.csv              — master list of monitorable component types
    technologies.csv            — master list of technology codes
    classes.csv                 — master list of asset classes (from Maximo)
    component_technology.csv    — junction: component_name × technology_code × application_type
    class_component.csv         — junction: class_name × component_name

Junction tables use natural keys (component_name, class_name) — no integer
foreign key lookups required.

All mutations (add, remove) are logged to change_log.csv.
Removals are never executed immediately — they are written as pending requests
and must be approved via the admin app before any data is changed.
"""

import json
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────────

VALID_APPLICATION_TYPES = {'Primary', 'Secondary'}
VALID_STATUSES = {'applied', 'pending', 'approved', 'rejected'}


# ── ACMConfig ─────────────────────────────────────────────────────────────────

class ACMConfig:
    """
    Manager for Asset Condition Monitoring configuration data.

    Parameters
    ----------
    config_dir : str | Path
        Directory containing the six CSV files. Defaults to 'normalized_config'.
    """

    def __init__(self, config_dir: str | Path = 'data/st_tbl/normalized_config'):
        self.config_dir = Path(config_dir)
        self._load_all()
        print(f"✓ ACMConfig loaded from '{self.config_dir}'")

    # ── Load ──────────────────────────────────────────────────────────────────

    def _load_all(self):
        """Load all config files from disk."""
        self.components          = self._load_csv('components.csv')
        self.technologies        = self._load_csv('technologies.csv')
        self.classes             = self._load_csv('classes.csv')
        self.component_technology = self._load_csv('component_technology.csv')
        self.class_component     = self._load_csv('class_component.csv')
        self.change_log          = self._load_csv('change_log.csv')

    def _load_csv(self, filename: str) -> pd.DataFrame:
        path = self.config_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        return pd.read_csv(path)

    def reload(self):
        """Reload all files from disk. Call after external edits."""
        self._load_all()
        print("✓ Configuration reloaded from disk")

    # ── Lookup helpers ────────────────────────────────────────────────────────

    @property
    def component_names(self) -> list[str]:
        return sorted(self.components['component_name'].tolist())

    @property
    def technology_codes(self) -> list[str]:
        return sorted(self.technologies['technology_code'].tolist())

    @property
    def class_names(self) -> list[str]:
        return sorted(self.classes['class_name'].tolist())

    def _assert_component_exists(self, name: str):
        if name not in self.components['component_name'].values:
            raise ValueError(f"Component not found: '{name}'")

    def _assert_class_exists(self, name: str):
        if name not in self.classes['class_name'].values:
            raise ValueError(f"Asset class not found: '{name}'")

    def _assert_tech_exists(self, code: str):
        if code not in self.technologies['technology_code'].values:
            raise ValueError(f"Technology code not found: '{code}'")

    # ── Component queries ─────────────────────────────────────────────────────

    def get_component_technologies(self, component_name: str) -> pd.DataFrame:
        """
        Get all technologies assigned to a component.

        Returns
        -------
        DataFrame with columns: technology_code, application_type
        """
        self._assert_component_exists(component_name)
        return (
            self.component_technology[
                self.component_technology['component_name'] == component_name
            ][['technology_code', 'application_type']]
            .sort_values('technology_code')
            .reset_index(drop=True)
        )

    def get_component_classes(self, component_name: str) -> list[str]:
        """Get all asset class names that include this component."""
        self._assert_component_exists(component_name)
        return sorted(
            self.class_component[
                self.class_component['component_name'] == component_name
            ]['class_name'].tolist()
        )

    # ── Technology queries ────────────────────────────────────────────────────

    def get_technology_components(self, tech_code: str,
                                  application_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get all components monitored by a technology.

        Parameters
        ----------
        tech_code : str
            e.g. 'VI', 'IR'
        application_type : str, optional
            Filter to 'Primary' or 'Secondary' only.

        Returns
        -------
        DataFrame with columns: component_name, application_type
        """
        self._assert_tech_exists(tech_code)
        result = self.component_technology[
            self.component_technology['technology_code'] == tech_code
        ].copy()
        if application_type:
            if application_type not in VALID_APPLICATION_TYPES:
                raise ValueError(f"application_type must be one of {VALID_APPLICATION_TYPES}")
            result = result[result['application_type'] == application_type]
        return (
            result[['component_name', 'application_type']]
            .sort_values('component_name')
            .reset_index(drop=True)
        )

    # ── Class queries ─────────────────────────────────────────────────────────

    def get_class_components(self, class_name: str) -> list[str]:
        """Get all component names in an asset class."""
        self._assert_class_exists(class_name)
        return sorted(
            self.class_component[
                self.class_component['class_name'] == class_name
            ]['component_name'].tolist()
        )

    def get_class_technologies(self, class_name: str) -> pd.DataFrame:
        """
        Get all technologies applicable to an asset class, with application type.
        If a technology is driven by multiple components, the highest priority wins
        (Primary > Secondary).

        Returns
        -------
        DataFrame with columns: technology_code, application_type, driving_components
        """
        self._assert_class_exists(class_name)
        components = self.get_class_components(class_name)
        if not components:
            return pd.DataFrame(columns=['technology_code', 'application_type', 'driving_components'])

        ct = self.component_technology[
            self.component_technology['component_name'].isin(components)
        ].copy()

        if ct.empty:
            return pd.DataFrame(columns=['technology_code', 'application_type', 'driving_components'])

        # Highest priority wins: Primary > Secondary
        priority = {'Primary': 1, 'Secondary': 2}
        ct['_priority'] = ct['application_type'].map(priority)

        # Group by technology: take best priority, collect driving component names
        def agg_tech(grp):
            best_idx = grp['_priority'].idxmin()
            return pd.Series({
                'application_type': grp.loc[best_idx, 'application_type'],
                'driving_components': ', '.join(sorted(grp['component_name'].tolist()))
            })

        result = (
            ct.groupby('technology_code')
            .apply(agg_tech)
            .reset_index()
            .sort_values('technology_code')
        )
        return result

    # ── Add operations (immediate, logged as 'applied') ───────────────────────

    def add_component(self, component_name: str, requested_by: str = 'system') -> bool:
        """
        Add a new component to the master list.

        Returns True if added, False if already exists.
        """
        if component_name in self.components['component_name'].values:
            print(f"  Component already exists: '{component_name}'")
            return False

        new_row = pd.DataFrame({'component_name': [component_name]})

        # Preserve component_id if it exists as a column (for backwards compat)
        if 'component_id' in self.components.columns:
            next_id = int(self.components['component_id'].max()) + 1
            new_row.insert(0, 'component_id', next_id)

        self.components = pd.concat([self.components, new_row], ignore_index=True)
        self._save('components.csv', self.components)

        self._log_change(
            entity_type='component',
            action='add',
            entity_key=component_name,
            payload={'component_name': component_name},
            requested_by=requested_by,
            status='applied',
        )
        print(f"  ✓ Added component: '{component_name}'")
        return True

    def add_class(self, class_name: str, requested_by: str = 'system') -> bool:
        """Add a new asset class. Returns True if added, False if already exists."""
        if class_name in self.classes['class_name'].values:
            print(f"  Asset class already exists: '{class_name}'")
            return False

        new_row = pd.DataFrame({'class_name': [class_name]})
        if 'class_id' in self.classes.columns:
            next_id = int(self.classes['class_id'].max()) + 1
            new_row.insert(0, 'class_id', next_id)

        self.classes = pd.concat([self.classes, new_row], ignore_index=True)
        self._save('classes.csv', self.classes)

        self._log_change(
            entity_type='class',
            action='add',
            entity_key=class_name,
            payload={'class_name': class_name},
            requested_by=requested_by,
            status='applied',
        )
        print(f"  ✓ Added class: '{class_name}'")
        return True

    def assign_technology_to_component(self, component_name: str, tech_code: str,
                                       application_type: str,
                                       requested_by: str = 'system') -> bool:
        """
        Assign a technology to a component.

        Parameters
        ----------
        application_type : str
            'Primary' or 'Secondary'

        Returns True if assigned, False if already exists.
        """
        self._assert_component_exists(component_name)
        self._assert_tech_exists(tech_code)
        if application_type not in VALID_APPLICATION_TYPES:
            raise ValueError(f"application_type must be one of {VALID_APPLICATION_TYPES}")

        exists = (
            (self.component_technology['component_name'] == component_name) &
            (self.component_technology['technology_code'] == tech_code)
        ).any()

        if exists:
            print(f"  Assignment already exists: {component_name} — {tech_code}")
            return False

        new_row = pd.DataFrame({
            'component_name': [component_name],
            'technology_code': [tech_code],
            'application_type': [application_type],
        })
        self.component_technology = pd.concat([self.component_technology, new_row], ignore_index=True)
        self._save('component_technology.csv', self.component_technology)

        self._log_change(
            entity_type='component_technology',
            action='add',
            entity_key=f"{component_name} → {tech_code}",
            payload={
                'component_name': component_name,
                'technology_code': tech_code,
                'application_type': application_type,
            },
            requested_by=requested_by,
            status='applied',
        )
        print(f"  ✓ Assigned {tech_code} ({application_type}) → '{component_name}'")
        return True

    def update_application_type(self, component_name: str, tech_code: str,
                                 new_application_type: str,
                                 requested_by: str = 'system') -> bool:
        """Change the application_type (Primary ↔ Secondary) for an existing assignment."""
        self._assert_component_exists(component_name)
        self._assert_tech_exists(tech_code)
        if new_application_type not in VALID_APPLICATION_TYPES:
            raise ValueError(f"application_type must be one of {VALID_APPLICATION_TYPES}")

        mask = (
            (self.component_technology['component_name'] == component_name) &
            (self.component_technology['technology_code'] == tech_code)
        )
        if not mask.any():
            raise ValueError(f"No assignment found: {component_name} — {tech_code}")

        old_type = self.component_technology.loc[mask, 'application_type'].iloc[0]
        if old_type == new_application_type:
            print(f"  No change needed: already '{new_application_type}'")
            return False

        self.component_technology.loc[mask, 'application_type'] = new_application_type
        self._save('component_technology.csv', self.component_technology)

        self._log_change(
            entity_type='component_technology',
            action='update',
            entity_key=f"{component_name} → {tech_code}",
            payload={
                'component_name': component_name,
                'technology_code': tech_code,
                'old_application_type': old_type,
                'new_application_type': new_application_type,
            },
            requested_by=requested_by,
            status='applied',
        )
        print(f"  ✓ Updated {component_name} — {tech_code}: {old_type} → {new_application_type}")
        return True

    def assign_component_to_class(self, class_name: str, component_name: str,
                                   requested_by: str = 'system') -> bool:
        """
        Assign a component to an asset class.
        Returns True if assigned, False if already exists.
        """
        self._assert_class_exists(class_name)
        self._assert_component_exists(component_name)

        exists = (
            (self.class_component['class_name'] == class_name) &
            (self.class_component['component_name'] == component_name)
        ).any()

        if exists:
            print(f"  Assignment already exists: {class_name} ← {component_name}")
            return False

        new_row = pd.DataFrame({
            'class_name': [class_name],
            'component_name': [component_name],
        })
        self.class_component = pd.concat([self.class_component, new_row], ignore_index=True)
        self._save('class_component.csv', self.class_component)

        self._log_change(
            entity_type='class_component',
            action='add',
            entity_key=f"{class_name} ← {component_name}",
            payload={'class_name': class_name, 'component_name': component_name},
            requested_by=requested_by,
            status='applied',
        )
        print(f"  ✓ Assigned '{component_name}' → class '{class_name}'")
        return True

    # ── Remove requests (never immediate — always pending) ────────────────────

    def request_remove_component(self, component_name: str,
                                  notes: str, requested_by: str) -> int:
        """
        Submit a request to remove a component from the master list.
        Does NOT delete anything — writes a pending entry to the change log.

        Returns the log_id of the pending request.
        """
        self._assert_component_exists(component_name)

        # Gather impact summary for the admin review
        assigned_classes = self.get_component_classes(component_name)
        assigned_techs = self.get_component_technologies(component_name).to_dict('records')

        log_id = self._log_change(
            entity_type='component',
            action='remove_request',
            entity_key=component_name,
            payload={
                'component_name': component_name,
                'impact': {
                    'assigned_to_classes': assigned_classes,
                    'technology_assignments': assigned_techs,
                }
            },
            notes=notes,
            requested_by=requested_by,
            status='pending',
        )
        print(f"  ⏳ Removal request submitted for '{component_name}' (log_id={log_id})")
        return log_id

    def request_remove_component_from_class(self, class_name: str, component_name: str,
                                             notes: str, requested_by: str) -> int:
        """
        Submit a request to remove a component↔class assignment.
        Does NOT delete anything — writes a pending entry to the change log.
        """
        self._assert_class_exists(class_name)
        self._assert_component_exists(component_name)

        exists = (
            (self.class_component['class_name'] == class_name) &
            (self.class_component['component_name'] == component_name)
        ).any()
        if not exists:
            raise ValueError(f"Assignment not found: {class_name} ← {component_name}")

        log_id = self._log_change(
            entity_type='class_component',
            action='remove_request',
            entity_key=f"{class_name} ← {component_name}",
            payload={'class_name': class_name, 'component_name': component_name},
            notes=notes,
            requested_by=requested_by,
            status='pending',
        )
        print(f"  ⏳ Removal request submitted: {class_name} ← {component_name} (log_id={log_id})")
        return log_id

    def request_remove_technology_from_component(self, component_name: str, tech_code: str,
                                                  notes: str, requested_by: str) -> int:
        """
        Submit a request to remove a component↔technology assignment.
        Does NOT delete anything — writes a pending entry to the change log.
        """
        self._assert_component_exists(component_name)
        self._assert_tech_exists(tech_code)

        exists = (
            (self.component_technology['component_name'] == component_name) &
            (self.component_technology['technology_code'] == tech_code)
        ).any()
        if not exists:
            raise ValueError(f"Assignment not found: {component_name} — {tech_code}")

        log_id = self._log_change(
            entity_type='component_technology',
            action='remove_request',
            entity_key=f"{component_name} → {tech_code}",
            payload={'component_name': component_name, 'technology_code': tech_code},
            notes=notes,
            requested_by=requested_by,
            status='pending',
        )
        print(f"  ⏳ Removal request submitted: {component_name} — {tech_code} (log_id={log_id})")
        return log_id

    # ── Admin: approve / reject removals ──────────────────────────────────────

    def approve_removal(self, log_id: int, reviewed_by: str) -> bool:
        """
        Approve a pending removal request. Executes the deletion and updates the log.

        Parameters
        ----------
        log_id : int
        reviewed_by : str

        Returns True on success.
        """
        row = self._get_pending_request(log_id)
        payload = json.loads(row['payload'])
        entity_type = row['entity_type']
        action = row['action']

        if action != 'remove_request':
            raise ValueError(f"log_id {log_id} is not a remove_request (action='{action}')")

        # Execute the deletion
        if entity_type == 'component':
            name = payload['component_name']
            self.components = self.components[self.components['component_name'] != name]
            self.component_technology = self.component_technology[
                self.component_technology['component_name'] != name]
            self.class_component = self.class_component[
                self.class_component['component_name'] != name]
            self._save('components.csv', self.components)
            self._save('component_technology.csv', self.component_technology)
            self._save('class_component.csv', self.class_component)
            print(f"  ✓ Removed component '{name}' and all its assignments")

        elif entity_type == 'class_component':
            mask = (
                (self.class_component['class_name'] == payload['class_name']) &
                (self.class_component['component_name'] == payload['component_name'])
            )
            self.class_component = self.class_component[~mask]
            self._save('class_component.csv', self.class_component)
            print(f"  ✓ Removed class↔component assignment: "
                  f"{payload['class_name']} ← {payload['component_name']}")

        elif entity_type == 'component_technology':
            mask = (
                (self.component_technology['component_name'] == payload['component_name']) &
                (self.component_technology['technology_code'] == payload['technology_code'])
            )
            self.component_technology = self.component_technology[~mask]
            self._save('component_technology.csv', self.component_technology)
            print(f"  ✓ Removed component↔technology assignment: "
                  f"{payload['component_name']} — {payload['technology_code']}")

        else:
            raise ValueError(f"Unknown entity_type for removal: '{entity_type}'")

        # Update log entry
        self._update_log_status(log_id, 'approved', reviewed_by)
        return True

    def reject_removal(self, log_id: int, reviewed_by: str) -> bool:
        """Reject a pending removal request. No data is changed."""
        self._get_pending_request(log_id)   # validates it exists and is pending
        self._update_log_status(log_id, 'rejected', reviewed_by)
        print(f"  ✗ Rejected removal request log_id={log_id}")
        return True

    def get_pending_requests(self) -> pd.DataFrame:
        """Return all pending removal requests."""
        return self.change_log[
            self.change_log['status'] == 'pending'
        ].reset_index(drop=True)

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self) -> bool:
        """
        Run integrity checks. Prints any issues found.
        Returns True if no issues, False otherwise.
        """
        issues = []

        # Components with no technology assignments
        assigned_comps = set(self.component_technology['component_name'])
        unassigned = [c for c in self.component_names if c not in assigned_comps]
        if unassigned:
            issues.append(f"Components with no technology assignments ({len(unassigned)}): "
                          f"{unassigned}")

        # Components not in any class
        in_class = set(self.class_component['component_name'])
        orphans = [c for c in self.component_names if c not in in_class]
        if orphans:
            issues.append(f"Components not in any class ({len(orphans)}): {orphans}")

        # Classes with no components
        has_comp = set(self.class_component['class_name'])
        empty_classes = [c for c in self.class_names if c not in has_comp]
        if empty_classes:
            issues.append(f"Classes with no components ({len(empty_classes)}): {empty_classes}")

        # Junction table refs that don't match master lists
        unknown_comps_ct = set(self.component_technology['component_name']) - set(self.component_names)
        if unknown_comps_ct:
            issues.append(f"component_technology references unknown components: {unknown_comps_ct}")

        unknown_techs = set(self.component_technology['technology_code']) - set(self.technology_codes)
        if unknown_techs:
            issues.append(f"component_technology references unknown tech codes: {unknown_techs}")

        unknown_classes_cc = set(self.class_component['class_name']) - set(self.class_names)
        if unknown_classes_cc:
            issues.append(f"class_component references unknown classes: {unknown_classes_cc}")

        unknown_comps_cc = set(self.class_component['component_name']) - set(self.component_names)
        if unknown_comps_cc:
            issues.append(f"class_component references unknown components: {unknown_comps_cc}")

        print("\n" + "="*60)
        print("  ACM CONFIG VALIDATION")
        print("="*60)
        if issues:
            print(f"\n  ⚠ {len(issues)} issue(s) found:\n")
            for issue in issues:
                print(f"  • {issue}\n")
        else:
            print("\n  ✓ All checks passed — configuration is valid")
        print("="*60 + "\n")

        return len(issues) == 0

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self):
        """Print a brief configuration summary."""
        pending = len(self.get_pending_requests())
        print("\n" + "="*60)
        print("  ACM CONFIGURATION SUMMARY")
        print("="*60)
        print(f"  Components                    : {len(self.components)}")
        print(f"  Technologies                  : {len(self.technologies)}")
        print(f"  Asset Classes                 : {len(self.classes)}")
        print(f"  Component-Technology Assignments: {len(self.component_technology)}")
        print(f"  Class-Component Assignments   : {len(self.class_component)}")
        print(f"  Change Log Entries            : {len(self.change_log)}")
        print(f"  Pending Removal Requests      : {pending}")
        print("="*60)
        print(f"\n  Technologies : {', '.join(self.technology_codes)}")
        print(f"  Config dir   : {self.config_dir.resolve()}")
        print()

    # ── Export (backwards compatibility for pipeline) ─────────────────────────

    def export_comp_xref_tech(self, output_file: str = 'comp_xref_tech_export.csv') -> pd.DataFrame:
        """
        Export component_technology in the legacy cross-tab format
        (component_name as index, tech codes as columns, P/S as values).
        Used by the Quarto pipeline needs-monitoring logic.
        """
        pivot = self.component_technology.pivot_table(
            index='component_name',
            columns='technology_code',
            values='application_type',
            aggfunc='first'
        )
        pivot = pivot.applymap(
            lambda x: 'S' if x == 'Secondary' else ('P' if x == 'Primary' else '')
        ).fillna('')
        pivot = pivot.reset_index()
        pivot.to_csv(output_file, index=False)
        print(f"✓ Exported legacy comp_xref_tech → {output_file}")
        return pivot

    def export_class_xref_comp(self, output_file: str = 'class_xref_comp_export.csv') -> pd.DataFrame:
        """
        Export class_component in the legacy cross-tab format
        (class_name as index, component_names as columns, 'x' as values).
        """
        all_components = self.component_names
        rows = []
        for class_name in self.class_names:
            comps_in_class = set(self.get_class_components(class_name))
            row = {'class_name': class_name}
            for comp in all_components:
                row[comp] = 'x' if comp in comps_in_class else ''
            rows.append(row)
        result = pd.DataFrame(rows)
        result.to_csv(output_file, index=False)
        print(f"✓ Exported legacy class_xref_comp → {output_file}")
        return result

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _save(self, filename: str, df: pd.DataFrame):
        """Write a DataFrame back to its CSV file."""
        df.to_csv(self.config_dir / filename, index=False)

    def _next_log_id(self) -> int:
        if self.change_log.empty or 'log_id' not in self.change_log.columns:
            return 1
        valid = self.change_log['log_id'].dropna()
        return int(valid.max()) + 1 if not valid.empty else 1

    def _log_change(self, entity_type: str, action: str, entity_key: str,
                    payload: dict, requested_by: str, status: str,
                    notes: str = '') -> int:
        """Append one row to the change log and persist it. Returns the new log_id."""
        log_id = self._next_log_id()
        new_row = pd.DataFrame([{
            'log_id': log_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'entity_type': entity_type,
            'action': action,
            'entity_key': entity_key,
            'payload': json.dumps(payload),
            'notes': notes,
            'requested_by': requested_by,
            'status': status,
            'reviewed_by': '',
            'reviewed_at': '',
        }])
        self.change_log = pd.concat([self.change_log, new_row], ignore_index=True)
        self._save('change_log.csv', self.change_log)
        return log_id

    def _update_log_status(self, log_id: int, status: str, reviewed_by: str):
        """Update status, reviewed_by, and reviewed_at for a log entry."""
        mask = self.change_log['log_id'] == log_id
        self.change_log.loc[mask, 'status'] = status
        self.change_log.loc[mask, 'reviewed_by'] = reviewed_by
        self.change_log.loc[mask, 'reviewed_at'] = datetime.now(timezone.utc).isoformat()
        self._save('change_log.csv', self.change_log)

    def _get_pending_request(self, log_id: int) -> pd.Series:
        """Fetch a pending log row, raising clearly if not found or not pending."""
        matches = self.change_log[self.change_log['log_id'] == log_id]
        if matches.empty:
            raise ValueError(f"No change log entry found with log_id={log_id}")
        row = matches.iloc[0]
        if row['status'] != 'pending':
            raise ValueError(
                f"log_id={log_id} is not pending (status='{row['status']}'). "
                f"Only pending requests can be approved or rejected."
            )
        return row
