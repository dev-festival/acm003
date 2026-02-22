# ACM Config Editor

Team-facing Streamlit app for reliability engineers to browse and manage the ACM monitoring configuration.

---

## What This Is

The config editor is the front door to the ACM configuration system. It lets the reliability team:

- Browse components and their technology assignments
- Add new components with P/S technology ratings
- Assign components to asset classes
- Submit requests to remove components, technology assignments, or class assignments

**Adds are immediate.** Removals and P↔S updates go to the admin queue for review before anything changes — this protects compliance calculations from unreviewed edits.

---

## Running the App

```bash
# From the project root
conda activate icicle
streamlit run acm_config_editor/app.py
```

---

## How to Use It

**Login** — enter your name. This populates the `requested_by` field on every change you make, so there's a clear audit trail.

**Components page**
- Search and select any component to see its current technology assignments and class memberships
- Use the action tabs to assign a new technology, request a P↔S update, assign to a class, or request removal
- Use the "Add New Component" expander at the bottom to create a new component and optionally assign technologies in one step

**Classes page**
- Search and select any asset class to see its components and derived technology requirements
- Use the "⚠ Remove" button on any component row to submit a removal request
- Use the "Add Component to This Class" widget at the bottom to assign an existing component

---

## What Happens to Requests

Removal requests and P↔S update requests are written to `change_log.csv` with `status = pending`. They do **not** change any data until an admin approves them in the admin app. You'll see a count of your pending requests in the sidebar.

---

## Data Location

All config data lives in:
```
data/st_tbl/normalized_config/
├── components.csv
├── technologies.csv
├── classes.csv
├── component_technology.csv   ← natural keys: component_name × technology_code
├── class_component.csv        ← natural keys: class_name × component_name
└── change_log.csv             ← audit trail of all changes and requests
```

---

## Notes

- The technology list (GM, IR, UL, VI, LU, MC, ZD, CW) is read-only in this app — technology additions are handled by the admin
- If you added a component by mistake, submit a removal request with a note explaining it
- Changes take effect in the ACM pipeline at the next Quarto render
