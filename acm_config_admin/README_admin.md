# ACM Config Admin

Admin-only Streamlit app for reviewing and actioning configuration change requests submitted via the ACM Config Editor.

---

## What This Is

The admin app is the review layer of the ACM configuration system. Every removal request and P↔S update request submitted by the reliability team lands here as a pending item before any data changes. This ensures that nothing affecting compliance calculations goes through unreviewed.

---

## Running the App

```bash
# From the project root
conda activate icicle
streamlit run acm_config_admin/app.py
```

Password is loaded from `.env`:
```
ACM_ADMIN_PASSWORD=your-password-here
```

---

## Pages

**⏳ Pending Requests**

The main working view. Each pending request renders as a card showing:
- What changed (entity key, entity type, action)
- Who submitted it and when
- Their stated reason
- Impact summary (for removals: how many tech assignments and classes are affected)
- Full payload detail in an expander

Approve or reject individually, or use the bulk action bar to clear a queue of the same type at once.

- **Approving a removal** — deletes the record and all dependent assignments, marks log as `approved`
- **Approving an update request** — applies the P↔S change, marks log as `approved`
- **Rejecting** — marks log as `rejected`, no data changes

**📋 Change History**

Full filterable audit log of every change ever made — adds, requests, approvals, rejections. Filter by entity type, action, status, or user. Exportable to CSV. Useful for answering "why did the compliance numbers change between runs?"

**❤️ Config Health**

Runs integrity checks across the config:
- Components with no technology assignments
- Components not assigned to any class
- Classes with no components defined
- Dangling references in junction tables

Also renders the full component × technology coverage heatmap so you can see at a glance where assignments are sparse. Run this periodically or after a batch of approvals.

---

## Data Location

```
data/st_tbl/normalized_config/
├── components.csv
├── technologies.csv
├── classes.csv
├── component_technology.csv
├── class_component.csv
└── change_log.csv             ← source of truth for the pending queue
```

---

## Notes

- Keep the `.env` file out of version control — the password should never be committed
- Approvals are irreversible from the UI — if something was approved in error, edit the CSV directly and log the correction manually
- The health check "Classes with no components" is expected for asset classes that haven't been configured yet — use the editor to assign components as the team works through them
- After a significant batch of approvals, re-run the Quarto pipeline so the coverage report reflects the updated config
