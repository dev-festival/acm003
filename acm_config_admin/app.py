"""
ACM Configuration Admin
========================
Admin-only Streamlit app for reviewing and actioning pending configuration
change requests submitted via the ACM Config Editor.

Run:
    streamlit run acm_config_admin/app.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from acm_config import ACMConfig

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ACM Admin",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stApp { background-color: #0c0e14; color: #cbd5e1; }

section[data-testid="stSidebar"] {
    background-color: #111318;
    border-right: 1px solid #1e2330;
}

/* Header */
.admin-header {
    background: linear-gradient(135deg, #150a0a 0%, #0c0e14 100%);
    border: 1px solid #3a1a1a;
    border-left: 4px solid #ef4444;
    border-radius: 4px;
    padding: 16px 24px;
    margin-bottom: 24px;
}
.admin-header h1 {
    font-family: 'DM Mono', monospace;
    font-size: 1.2rem;
    font-weight: 500;
    color: #f1f5f9;
    margin: 0;
    letter-spacing: 0.08em;
}
.admin-header p {
    color: #64748b;
    font-size: 0.75rem;
    margin: 4px 0 0 0;
    font-family: 'DM Mono', monospace;
}

/* Section labels */
.section-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    font-weight: 500;
    color: #ef4444;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    border-bottom: 1px solid #1e2330;
    padding-bottom: 8px;
    margin: 24px 0 16px 0;
}

/* Stat cards */
.stat-card {
    background: #111318;
    border: 1px solid #1e2330;
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 10px;
}
.stat-card .label {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 4px;
}
.stat-card .value {
    font-size: 1.6rem;
    font-weight: 600;
    color: #f1f5f9;
    font-family: 'DM Mono', monospace;
}
.stat-card .value.warn { color: #f59e0b; }
.stat-card .value.danger { color: #ef4444; }
.stat-card .value.ok { color: #22c55e; }

/* Request cards */
.req-card {
    background: #111318;
    border: 1px solid #1e2330;
    border-radius: 6px;
    padding: 18px 22px;
    margin-bottom: 16px;
}
.req-card.remove { border-left: 3px solid #ef4444; }
.req-card.update  { border-left: 3px solid #f59e0b; }

.req-card .req-type {
    font-family: 'DM Mono', monospace;
    font-size: 0.6rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.req-card.remove .req-type { color: #ef4444; }
.req-card.update  .req-type { color: #f59e0b; }

.req-card .req-key {
    font-size: 1rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 4px;
}
.req-card .req-meta {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    color: #475569;
}
.req-card .req-notes {
    background: #0c0e14;
    border: 1px solid #1e2330;
    border-radius: 3px;
    padding: 8px 12px;
    font-size: 0.8rem;
    color: #94a3b8;
    margin: 10px 0;
    font-style: italic;
}
.req-card .impact {
    font-size: 0.8rem;
    color: #fca5a5;
    margin: 8px 0;
}

/* Badge */
.badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    padding: 2px 8px;
    border-radius: 3px;
    margin: 2px;
}
.badge.pending  { background:#1a1500; color:#f59e0b; border:1px solid #854d0e; }
.badge.approved { background:#0a1f0a; color:#22c55e; border:1px solid #166534; }
.badge.rejected { background:#1a0a0a; color:#f87171; border:1px solid #7f1d1d; }
.badge.applied  { background:#0f1a2a; color:#60a5fa; border:1px solid #1e3a5f; }
.badge.remove   { background:#1a0a0a; color:#f87171; border:1px solid #7f1d1d; }
.badge.update   { background:#1a1500; color:#fbbf24; border:1px solid #92400e; }
.badge.add      { background:#0f1a2a; color:#60a5fa; border:1px solid #1e3a5f; }

/* Health issue rows */
.health-issue {
    background: #150f00;
    border: 1px solid #854d0e;
    border-radius: 4px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 0.82rem;
    color: #fbbf24;
    font-family: 'DM Mono', monospace;
}
.health-ok {
    background: #0a1a0a;
    border: 1px solid #166534;
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 0.82rem;
    color: #22c55e;
    font-family: 'DM Mono', monospace;
}

hr { border-color: #1e2330; }
</style>
""", unsafe_allow_html=True)


# ── Auth ──────────────────────────────────────────────────────────────────────

# Replace with this
import os
from dotenv import load_dotenv

load_dotenv()
ADMIN_PASSWORD = os.getenv("ACM_ADMIN_PASSWORD")

def init_state():
    if 'admin_auth' not in st.session_state:
        st.session_state.admin_auth = False
    if 'admin_user' not in st.session_state:
        st.session_state.admin_user = None
    if 'admin_page' not in st.session_state:
        st.session_state.admin_page = 'pending'

init_state()


# ── Config ────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_config() -> ACMConfig:
    return ACMConfig()

def reload_config():
    st.cache_resource.clear()


# ── Login ─────────────────────────────────────────────────────────────────────

def login_screen():
    st.markdown("""
    <div style="max-width:400px; margin:80px auto 0 auto;">
        <div class="admin-header">
            <h1>🛡 ACM ADMIN</h1>
            <p>Configuration Management · Admin Access Only</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        name = st.text_input("Your name", placeholder="e.g. Mike",
                             label_visibility="collapsed",
                             key="login_name")
        pwd = st.text_input("Admin password", type="password",
                            label_visibility="collapsed",
                            placeholder="Password",
                            key="login_pwd")
        if st.button("Enter →", use_container_width=True, type="primary"):
            if pwd == ADMIN_PASSWORD and name.strip():
                st.session_state.admin_auth = True
                st.session_state.admin_user = name.strip()
                st.rerun()
            else:
                st.error("Invalid credentials.")


# ── Sidebar ───────────────────────────────────────────────────────────────────

def sidebar(config: ACMConfig):
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:8px 0 16px 0;">
            <div style="font-family:'DM Mono',monospace; font-size:0.85rem;
                        font-weight:500; color:#f1f5f9; margin-bottom:4px;">
                🛡 ACM ADMIN
            </div>
            <div style="font-family:'DM Mono',monospace; font-size:0.65rem;
                        color:#64748b;">
                {st.session_state.admin_user}
            </div>
        </div>
        """, unsafe_allow_html=True)

        pending_n = len(config.get_pending_requests())

        st.markdown('<div class="section-label">Navigate</div>',
                    unsafe_allow_html=True)

        pages = {
            'pending':  f"⏳ Pending Requests ({pending_n})",
            'history':  "📋 Change History",
            'health':   "❤️ Config Health",
        }

        for key, label in pages.items():
            is_active = st.session_state.admin_page == key
            if st.button(label, use_container_width=True,
                         type="primary" if is_active else "secondary",
                         key=f"nav_{key}"):
                st.session_state.admin_page = key
                st.rerun()

        st.markdown('<div class="section-label">Live Stats</div>',
                    unsafe_allow_html=True)

        st.markdown(f"""
        <div class="stat-card">
            <div class="label">Pending</div>
            <div class="value {'warn' if pending_n > 0 else 'ok'}">{pending_n}</div>
        </div>
        <div class="stat-card">
            <div class="label">Total Log Entries</div>
            <div class="value">{len(config.change_log)}</div>
        </div>
        <div class="stat-card">
            <div class="label">Components</div>
            <div class="value">{len(config.components)}</div>
        </div>
        <div class="stat-card">
            <div class="label">Tech Assignments</div>
            <div class="value">{len(config.component_technology)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.admin_auth = False
            st.session_state.admin_user = None
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def action_badge(action: str) -> str:
    if 'remove' in action:
        return f'<span class="badge remove">⚠ {action}</span>'
    elif 'update' in action:
        return f'<span class="badge update">↕ {action}</span>'
    else:
        return f'<span class="badge add">+ {action}</span>'

def status_badge(status: str) -> str:
    return f'<span class="badge {status}">{status}</span>'

def format_payload(payload_str: str) -> str:
    """Render payload JSON as readable lines."""
    try:
        p = json.loads(payload_str)
        lines = []
        for k, v in p.items():
            if isinstance(v, dict):
                lines.append(f"<strong>{k}:</strong>")
                for k2, v2 in v.items():
                    lines.append(f"&nbsp;&nbsp;{k2}: {v2}")
            elif isinstance(v, list):
                lines.append(f"<strong>{k}:</strong> {', '.join(str(x) for x in v)}")
            else:
                lines.append(f"<strong>{k}:</strong> {v}")
        return '<br>'.join(lines)
    except Exception:
        return payload_str


# ── Page: Pending Requests ────────────────────────────────────────────────────

def page_pending(config: ACMConfig):
    admin = st.session_state.admin_user

    st.markdown("""
    <div class="admin-header">
        <h1>⏳ PENDING REQUESTS</h1>
        <p>Review and action change requests submitted by the reliability team</p>
    </div>
    """, unsafe_allow_html=True)

    pending = config.get_pending_requests()

    if pending.empty:
        st.markdown("""
        <div class="health-ok">
            ✓ No pending requests — configuration is up to date.
        </div>
        """, unsafe_allow_html=True)
        return

    # Summary counts
    remove_n = pending['action'].str.contains('remove').sum()
    update_n = pending['action'].str.contains('update').sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="label">Total Pending</div>
            <div class="value warn">{len(pending)}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="label">Removal Requests</div>
            <div class="value danger">{remove_n}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="label">Update Requests</div>
            <div class="value warn">{update_n}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-label">Action Queue</div>',
                unsafe_allow_html=True)

    # Bulk action bar
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        filter_action = st.selectbox(
            "Filter by type", ["All", "remove_request", "update_request"],
            label_visibility="collapsed", key="pending_filter"
        )
    with col2:
        if st.button("✅ Approve All Visible", use_container_width=True):
            st.session_state['bulk_approve_confirm'] = True
    with col3:
        if st.button("❌ Reject All Visible", use_container_width=True):
            st.session_state['bulk_reject_confirm'] = True

    # Bulk confirm dialogs
    if st.session_state.get('bulk_approve_confirm'):
        st.warning("⚠ Approve ALL visible pending requests? This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, approve all", type="primary", key="confirm_bulk_approve"):
                filtered = pending if filter_action == "All" else \
                    pending[pending['action'] == filter_action]
                count = 0
                for _, row in filtered.iterrows():
                    try:
                        config.approve_removal(int(row['log_id']), reviewed_by=admin)
                        count += 1
                    except Exception as e:
                        st.error(f"Error on log #{row['log_id']}: {e}")
                st.success(f"✓ Approved {count} request(s)")
                st.session_state['bulk_approve_confirm'] = False
                reload_config()
                st.rerun()
        with c2:
            if st.button("Cancel", key="cancel_bulk_approve"):
                st.session_state['bulk_approve_confirm'] = False
                st.rerun()

    if st.session_state.get('bulk_reject_confirm'):
        st.warning("Reject ALL visible pending requests?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, reject all", type="primary", key="confirm_bulk_reject"):
                filtered = pending if filter_action == "All" else \
                    pending[pending['action'] == filter_action]
                count = 0
                for _, row in filtered.iterrows():
                    try:
                        config.reject_removal(int(row['log_id']), reviewed_by=admin)
                        count += 1
                    except Exception as e:
                        st.error(f"Error on log #{row['log_id']}: {e}")
                st.success(f"✓ Rejected {count} request(s)")
                st.session_state['bulk_reject_confirm'] = False
                reload_config()
                st.rerun()
        with c2:
            if st.button("Cancel", key="cancel_bulk_reject"):
                st.session_state['bulk_reject_confirm'] = False
                st.rerun()

    st.markdown("---")

    # Individual request cards
    display = pending if filter_action == "All" else \
        pending[pending['action'] == filter_action]

    for _, row in display.iterrows():
        log_id = int(row['log_id'])
        is_remove = 'remove' in row['action']
        card_class = "remove" if is_remove else "update"
        action_label = "REMOVAL REQUEST" if is_remove else "UPDATE REQUEST"

        # Parse payload for impact detail
        try:
            payload = json.loads(row['payload'])
        except Exception:
            payload = {}

        # Build impact line
        # Build impact line (removal only — goes inside card HTML)
        impact_html = ''
        if is_remove and 'impact' in payload:
            imp = payload['impact']
            n_classes = len(imp.get('assigned_to_classes', []))
            n_techs = len(imp.get('technology_assignments', []))
            impact_html = f"""
            <div class="impact">
                ⚠ Impact: removes {n_techs} tech assignment(s),
                affects {n_classes} class(es)
            </div>"""

        notes_html = ''
        if row.get('notes'):
            notes_html = f'<div class="req-notes">"{row["notes"]}"</div>'

        st.markdown(f"""
        <div class="req-card {card_class}">
            <div class="req-type">#{log_id} · {action_label}</div>
            <div class="req-key">{row['entity_key']}</div>
            <div class="req-meta">
                {row['entity_type']} &nbsp;·&nbsp;
                Submitted by <strong style="color:#94a3b8">{row['requested_by']}</strong>
                &nbsp;·&nbsp; {str(row['timestamp'])[:19].replace('T',' ')} UTC
            </div>
            {notes_html}
            {impact_html}
        </div>
        """, unsafe_allow_html=True)

        # Update direction rendered separately (avoids HTML escaping in f-string)
        if row['action'] == 'update_request':
            old_type = payload.get('old_application_type', '?')
            new_type = payload.get('new_application_type', '?')
            st.markdown(
                f'<div style="color:#fbbf24; font-size:0.85rem; '
                f'margin: -8px 0 12px 0; padding: 6px 22px;">'
                f'↕ &nbsp;<strong>{old_type}</strong> → <strong>{new_type}</strong></div>',
                unsafe_allow_html=True
            )

        # Payload expander
        with st.expander(f"Full detail — log #{log_id}"):
            st.markdown(
                f'<div style="font-family:DM Mono,monospace; font-size:0.75rem; '
                f'color:#94a3b8; line-height:1.8">'
                f'{format_payload(row["payload"])}</div>',
                unsafe_allow_html=True
            )

        # Approve / Reject buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button(f"✅ Approve", key=f"approve_{log_id}", type="primary"):
                try:
                    config.approve_removal(log_id, reviewed_by=admin)
                    st.success(f"✓ Approved log #{log_id}")
                    reload_config()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        with col2:
            if st.button(f"❌ Reject", key=f"reject_{log_id}"):
                try:
                    config.reject_removal(log_id, reviewed_by=admin)
                    st.warning(f"Rejected log #{log_id}")
                    reload_config()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")


# ── Page: Change History ──────────────────────────────────────────────────────

def page_history(config: ACMConfig):
    st.markdown("""
    <div class="admin-header">
        <h1>📋 CHANGE HISTORY</h1>
        <p>Full audit log of all configuration changes and requests</p>
    </div>
    """, unsafe_allow_html=True)

    log = config.change_log.copy()

    if log.empty:
        st.info("No change history yet.")
        return

    # ── Filters ────────────────────────────────────────────────────────────

    st.markdown('<div class="section-label">Filters</div>',
                unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        all_entities = ['All'] + sorted(log['entity_type'].unique().tolist())
        f_entity = st.selectbox("Entity type", all_entities, key="hist_entity")
    with col2:
        all_actions = ['All'] + sorted(log['action'].unique().tolist())
        f_action = st.selectbox("Action", all_actions, key="hist_action")
    with col3:
        all_statuses = ['All'] + sorted(log['status'].unique().tolist())
        f_status = st.selectbox("Status", all_statuses, key="hist_status")
    with col4:
        all_users = ['All'] + sorted(log['requested_by'].dropna().unique().tolist())
        f_user = st.selectbox("Requested by", all_users, key="hist_user")

    # Apply filters
    if f_entity != 'All':
        log = log[log['entity_type'] == f_entity]
    if f_action != 'All':
        log = log[log['action'] == f_action]
    if f_status != 'All':
        log = log[log['status'] == f_status]
    if f_user != 'All':
        log = log[log['requested_by'] == f_user]

    st.markdown(f'<div class="section-label">{len(log)} entries</div>',
                unsafe_allow_html=True)

    # ── Activity chart ─────────────────────────────────────────────────────

    if len(log) > 1:
        log['date'] = pd.to_datetime(log['timestamp']).dt.date
        daily = log.groupby(['date', 'action']).size().reset_index(name='count')
        fig = px.bar(
            daily, x='date', y='count', color='action',
            color_discrete_map={
                'add': '#3b82f6',
                'remove_request': '#ef4444',
                'update_request': '#f59e0b',
                'remove_approved': '#22c55e',
                'remove_rejected': '#94a3b8',
            },
            labels={'count': 'Changes', 'date': '', 'action': 'Action'},
        )
        fig.update_layout(
            plot_bgcolor='#0c0e14',
            paper_bgcolor='#0c0e14',
            font_color='#94a3b8',
            height=220,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            xaxis=dict(gridcolor='#1e2330'),
            yaxis=dict(gridcolor='#1e2330'),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Log table ──────────────────────────────────────────────────────────

    display_log = log[[
        'log_id', 'timestamp', 'entity_type', 'action',
        'entity_key', 'requested_by', 'status', 'reviewed_by', 'notes'
    ]].sort_values('log_id', ascending=False).reset_index(drop=True)

    # Format timestamp
    display_log['timestamp'] = pd.to_datetime(
        display_log['timestamp']
    ).dt.strftime('%Y-%m-%d %H:%M UTC')

    st.dataframe(
        display_log,
        use_container_width=True,
        height=500,
        column_config={
            'log_id':       st.column_config.NumberColumn('ID', width=60),
            'timestamp':    st.column_config.TextColumn('Timestamp', width=160),
            'entity_type':  st.column_config.TextColumn('Entity', width=160),
            'action':       st.column_config.TextColumn('Action', width=140),
            'entity_key':   st.column_config.TextColumn('Key', width=260),
            'requested_by': st.column_config.TextColumn('By', width=100),
            'status':       st.column_config.TextColumn('Status', width=90),
            'reviewed_by':  st.column_config.TextColumn('Reviewed By', width=100),
            'notes':        st.column_config.TextColumn('Notes', width=200),
        }
    )

    # Export
    csv = display_log.to_csv(index=False)
    st.download_button(
        "⬇ Export filtered log (CSV)",
        data=csv,
        file_name=f"acm_change_log_export_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


# ── Page: Config Health ───────────────────────────────────────────────────────

def page_health(config: ACMConfig):
    st.markdown("""
    <div class="admin-header">
        <h1>❤️ CONFIG HEALTH</h1>
        <p>Integrity checks · coverage gaps · validation report</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">Running Checks...</div>',
                unsafe_allow_html=True)

    issues = []

    # ── Check 1: Components with no tech assignments ──────────────────────
    assigned_comps = set(config.component_technology['component_name'])
    unassigned = [c for c in config.component_names if c not in assigned_comps]
    if unassigned:
        issues.append(('⚠ Components with no technology assignments',
                        unassigned, 'warn'))

    # ── Check 2: Components not in any class ─────────────────────────────
    in_class = set(config.class_component['component_name'])
    orphans = [c for c in config.component_names if c not in in_class]
    if orphans:
        issues.append(('⚠ Components not assigned to any class',
                        orphans, 'warn'))

    # ── Check 3: Classes with no components ──────────────────────────────
    has_comp = set(config.class_component['class_name'])
    empty_classes = [c for c in config.class_names if c not in has_comp]
    if empty_classes:
        issues.append(('ℹ Classes with no components defined',
                        empty_classes, 'info'))

    # ── Check 4: Unknown refs in junction tables ──────────────────────────
    unknown_comps_ct = set(config.component_technology['component_name']) \
                       - set(config.component_names)
    if unknown_comps_ct:
        issues.append(('🔴 component_technology references unknown components',
                        list(unknown_comps_ct), 'danger'))

    unknown_techs = set(config.component_technology['technology_code']) \
                    - set(config.technology_codes)
    if unknown_techs:
        issues.append(('🔴 component_technology references unknown tech codes',
                        list(unknown_techs), 'danger'))

    unknown_classes_cc = set(config.class_component['class_name']) \
                         - set(config.class_names)
    if unknown_classes_cc:
        issues.append(('🔴 class_component references unknown classes',
                        list(unknown_classes_cc), 'danger'))

    # ── Summary scorecard ─────────────────────────────────────────────────

    danger_n  = sum(1 for _, _, s in issues if s == 'danger')
    warn_n    = sum(1 for _, _, s in issues if s == 'warn')
    info_n    = sum(1 for _, _, s in issues if s == 'info')

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        overall = 'ok' if danger_n + warn_n == 0 else \
                  'danger' if danger_n > 0 else 'warn'
        label = '✓ Healthy' if overall == 'ok' else \
                '✗ Issues' if overall == 'danger' else '⚠ Warnings'
        st.markdown(f"""
        <div class="stat-card">
            <div class="label">Overall</div>
            <div class="value {overall}">{label}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="label">Critical</div>
            <div class="value {'danger' if danger_n else 'ok'}">{danger_n}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="label">Warnings</div>
            <div class="value {'warn' if warn_n else 'ok'}">{warn_n}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="label">Info</div>
            <div class="value">{info_n}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-label">Issue Detail</div>',
                unsafe_allow_html=True)

    if not issues:
        st.markdown('<div class="health-ok">✓ All checks passed.</div>',
                    unsafe_allow_html=True)
    else:
        for title, items, severity in issues:
            with st.expander(f"{title} ({len(items)})"):
                for item in sorted(items):
                    st.markdown(
                        f'<div class="health-issue">{item}</div>',
                        unsafe_allow_html=True
                    )

    # ── Coverage matrix ───────────────────────────────────────────────────

    st.markdown('<div class="section-label">Technology Coverage Matrix</div>',
                unsafe_allow_html=True)

    tech_codes = config.technology_codes
    comp_names = config.component_names

    matrix = pd.DataFrame(index=comp_names, columns=tech_codes)
    for comp in comp_names:
        techs = config.get_component_technologies(comp)
        for _, row in techs.iterrows():
            matrix.loc[comp, row['technology_code']] = \
                1 if row['application_type'] == 'Primary' else 0.5
    matrix = matrix.fillna(0).astype(float)

    fig = go.Figure(data=go.Heatmap(
        z=matrix.values,
        x=tech_codes,
        y=comp_names,
        colorscale=[[0, '#0c0e14'], [0.5, '#1e3a5f'], [1, '#2563eb']],
        showscale=True,
        colorbar=dict(
            tickvals=[0, 0.5, 1],
            ticktext=['None', 'Secondary', 'Primary'],
            tickfont=dict(color='#94a3b8', size=10),
            bgcolor='#0c0e14',
            bordercolor='#1e2330',
        ),
        hovertemplate='%{y} — %{x}<extra></extra>',
    ))
    fig.update_layout(
        plot_bgcolor='#0c0e14',
        paper_bgcolor='#0c0e14',
        font_color='#94a3b8',
        height=max(400, len(comp_names) * 22),
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(side='top', tickfont=dict(
            family='DM Mono', size=11, color='#60a5fa')),
        yaxis=dict(tickfont=dict(size=10)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not st.session_state.admin_auth:
        login_screen()
        return

    config = get_config()
    sidebar(config)

    page = st.session_state.admin_page
    if page == 'pending':
        page_pending(config)
    elif page == 'history':
        page_history(config)
    elif page == 'health':
        page_health(config)


if __name__ == '__main__':
    main()
