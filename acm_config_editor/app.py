"""
ACM Configuration Editor
========================
Team-facing Streamlit app for reliability engineers to browse and manage
the ACM monitoring configuration.

Layout: Entity-oriented — browse Components or Classes, act from there.

Run:
    streamlit run acm_config_editor/app.py
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd

# Allow import of acm_config from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from acm_config import ACMConfig

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ACM Config Editor",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* App background */
.stApp { background-color: #0f1117; color: #e0e0e0; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #161b27;
    border-right: 1px solid #2a2f3e;
}

/* Header bar */
.acm-header {
    background: linear-gradient(135deg, #1a2235 0%, #0f1117 100%);
    border: 1px solid #2a3a5c;
    border-left: 4px solid #3b82f6;
    border-radius: 4px;
    padding: 16px 24px;
    margin-bottom: 24px;
}
.acm-header h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.3rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0;
    letter-spacing: 0.05em;
}
.acm-header p {
    color: #64748b;
    font-size: 0.8rem;
    margin: 4px 0 0 0;
    font-family: 'IBM Plex Mono', monospace;
}

/* Section headers */
.section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    color: #3b82f6;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    border-bottom: 1px solid #2a2f3e;
    padding-bottom: 8px;
    margin: 24px 0 16px 0;
}

/* Cards */
.info-card {
    background: #161b27;
    border: 1px solid #2a2f3e;
    border-radius: 6px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.info-card .label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 4px;
}
.info-card .value {
    font-size: 1.4rem;
    font-weight: 600;
    color: #e2e8f0;
}

/* Tech badges */
.badge-primary {
    display: inline-block;
    background: #1e3a5f;
    color: #60a5fa;
    border: 1px solid #2a4a7f;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 3px;
    margin: 2px;
}
.badge-secondary {
    display: inline-block;
    background: #1a2a1a;
    color: #86efac;
    border: 1px solid #2a4a2a;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 3px;
    margin: 2px;
}
.badge-na {
    display: inline-block;
    background: #1a1a1a;
    color: #475569;
    border: 1px solid #2a2a2a;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 3px;
    margin: 2px;
}

/* Request warning box */
.request-box {
    background: #1a1500;
    border: 1px solid #854d0e;
    border-left: 4px solid #f59e0b;
    border-radius: 4px;
    padding: 14px 18px;
    margin: 12px 0;
}
.request-box .req-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: #f59e0b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 4px;
}
.request-box p { color: #d4a847; font-size: 0.85rem; margin: 0; }

/* Success box */
.success-box {
    background: #0a1f0a;
    border: 1px solid #166534;
    border-left: 4px solid #22c55e;
    border-radius: 4px;
    padding: 14px 18px;
    margin: 12px 0;
}

/* Logged-in user chip */
.user-chip {
    background: #1e2a40;
    border: 1px solid #2a3a5c;
    border-radius: 20px;
    padding: 4px 12px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #93c5fd;
    display: inline-block;
}

/* Dataframe overrides */
.stDataFrame { border: 1px solid #2a2f3e; border-radius: 6px; }

/* Form submit buttons */
.stButton > button {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}

/* Divider */
hr { border-color: #2a2f3e; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────

def init_state():
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'config' not in st.session_state:
        st.session_state.config = None
    if 'page' not in st.session_state:
        st.session_state.page = 'components'

init_state()


# ── Config loader ─────────────────────────────────────────────────────────────

@st.cache_resource
def get_config() -> ACMConfig:
    return ACMConfig()

def reload_config():
    """Force reload from disk after a write."""
    st.cache_resource.clear()


# ── Login screen ──────────────────────────────────────────────────────────────

def login_screen():
    st.markdown("""
    <div style="max-width:420px; margin: 80px auto 0 auto;">
        <div class="acm-header">
            <h1>⚙ ACM CONFIG EDITOR</h1>
            <p>Asset Condition Monitoring · Configuration Management</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="section-header">Identify Yourself</div>',
                    unsafe_allow_html=True)
        name = st.text_input("Your name", placeholder="e.g. Jane Smith",
                             label_visibility="collapsed")
        if st.button("Enter →", use_container_width=True, type="primary"):
            if name.strip():
                st.session_state.user = name.strip()
                st.rerun()
            else:
                st.error("Please enter your name to continue.")

        st.markdown("""
        <p style="color:#475569; font-size:0.75rem; text-align:center; margin-top:16px;">
        Your name is recorded on every change you submit.<br>
        Removals require admin approval before taking effect.
        </p>
        """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def sidebar(config: ACMConfig):
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 8px 0 16px 0;">
            <div style="font-family:'IBM Plex Mono',monospace; font-size:0.9rem;
                        font-weight:600; color:#e2e8f0; margin-bottom:4px;">
                ⚙ ACM EDITOR
            </div>
            <div class="user-chip">👤 {st.session_state.user}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Navigate</div>',
                    unsafe_allow_html=True)

        if st.button("🔩 Components", use_container_width=True,
                     type="primary" if st.session_state.page == 'components' else "secondary"):
            st.session_state.page = 'components'
            st.rerun()

        if st.button("🏭 Asset Classes", use_container_width=True,
                     type="primary" if st.session_state.page == 'classes' else "secondary"):
            st.session_state.page = 'classes'
            st.rerun()

        st.markdown('<div class="section-header">Config Stats</div>',
                    unsafe_allow_html=True)

        pending = len(config.get_pending_requests())

        st.markdown(f"""
        <div class="info-card">
            <div class="label">Components</div>
            <div class="value">{len(config.components)}</div>
        </div>
        <div class="info-card">
            <div class="label">Asset Classes</div>
            <div class="value">{len(config.classes)}</div>
        </div>
        <div class="info-card">
            <div class="label">Tech Assignments</div>
            <div class="value">{len(config.component_technology)}</div>
        </div>
        """, unsafe_allow_html=True)

        if pending > 0:
            st.markdown(f"""
            <div class="request-box">
                <div class="req-label">Pending Requests</div>
                <p>{pending} awaiting admin review</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def tech_badges(config: ACMConfig, component_name: str) -> str:
    """Return HTML badges for all tech assignments on a component."""
    techs = config.get_component_technologies(component_name)
    if techs.empty:
        return '<span class="badge-na">— none —</span>'
    html = ''
    for _, row in techs.iterrows():
        css = 'badge-primary' if row['application_type'] == 'Primary' else 'badge-secondary'
        html += f'<span class="{css}">{row["technology_code"]} · {row["application_type"][0]}</span> '
    return html


def class_badge_count(config: ACMConfig, component_name: str) -> str:
    classes = config.get_component_classes(component_name)
    return f"{len(classes)} class{'es' if len(classes) != 1 else ''}"


# ── Components page ───────────────────────────────────────────────────────────

def page_components(config: ACMConfig):
    user = st.session_state.user

    st.markdown("""
    <div class="acm-header">
        <h1>🔩 COMPONENTS</h1>
        <p>Browse monitorable component types · assign technologies · manage class membership</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Component browser ──────────────────────────────────────────────────

    st.markdown('<div class="section-header">Browse Components</div>',
                unsafe_allow_html=True)

    search = st.text_input("Filter components", placeholder="Type to search...",
                           label_visibility="collapsed")

    names = config.component_names
    if search:
        names = [n for n in names if search.lower() in n.lower()]

    if not names:
        st.info("No components match your search.")
    else:
        selected = st.selectbox("Select a component to work with",
                                names, label_visibility="collapsed")

        if selected:
            techs = config.get_component_technologies(selected)
            classes = config.get_component_classes(selected)

            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown(f"""
                <div class="info-card">
                    <div class="label">Selected Component</div>
                    <div style="font-size:1.1rem; font-weight:600;
                                color:#e2e8f0; margin-bottom:10px;">
                        {selected}
                    </div>
                    <div class="label" style="margin-bottom:6px;">
                        Technology Assignments
                    </div>
                    {tech_badges(config, selected)}
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="info-card">
                    <div class="label">Assigned to Classes</div>
                    <div class="value">{len(classes)}</div>
                    <div style="color:#64748b; font-size:0.8rem; margin-top:4px;">
                        {', '.join(classes[:4])}{'...' if len(classes) > 4 else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # ── Actions on selected component ──────────────────────────────

            st.markdown('<div class="section-header">Actions</div>',
                        unsafe_allow_html=True)

            action_tabs = st.tabs([
                "➕ Assign Technology",
                "🔄 Update P↔S",
                "🏭 Assign to Class",
                "⚠️ Request Removal"
            ])

            # Tab 1: Assign technology
            with action_tabs[0]:
                st.markdown("**Assign a new technology to this component**")
                assigned_codes = techs['technology_code'].tolist() if not techs.empty else []
                available_techs = [t for t in config.technology_codes
                                   if t not in assigned_codes]

                if not available_techs:
                    st.info("All technologies are already assigned to this component.")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        new_tech = st.selectbox("Technology", available_techs,
                                                key="assign_tech_code")
                    with col2:
                        new_app_type = st.selectbox("Application Type",
                                                    ["Primary", "Secondary"],
                                                    key="assign_tech_type")

                    if st.button("Assign Technology", key="btn_assign_tech",
                                 type="primary"):
                        config.assign_technology_to_component(
                            selected, new_tech, new_app_type, requested_by=user
                        )
                        st.success(f"✓ Assigned {new_tech} ({new_app_type}) to {selected}")
                        reload_config()
                        st.rerun()

            # Tab 2: Update P↔S (goes as request)
            with action_tabs[1]:
                st.markdown("""
                <div class="request-box">
                    <div class="req-label">⏳ Submitted as Request</div>
                    <p>P↔S changes affect compliance calculations and require admin approval.</p>
                </div>
                """, unsafe_allow_html=True)

                if techs.empty:
                    st.info("No technology assignments to update.")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        update_tech = st.selectbox(
                            "Technology to update",
                            techs['technology_code'].tolist(),
                            key="update_tech_code"
                        )
                    with col2:
                        current_type = techs[
                            techs['technology_code'] == update_tech
                        ]['application_type'].values[0] if update_tech else ''
                        new_type = "Secondary" if current_type == "Primary" else "Primary"
                        st.markdown(f"""
                        <div style="padding-top:28px; color:#94a3b8; font-size:0.85rem;">
                            Current: <strong style="color:#e2e8f0">{current_type}</strong>
                            → Requesting: <strong style="color:#60a5fa">{new_type}</strong>
                        </div>
                        """, unsafe_allow_html=True)

                    notes = st.text_area("Reason for change", key="update_notes",
                                        placeholder="Explain why this assignment type should change...")

                    if st.button("Submit Update Request", key="btn_update_type",
                                 type="primary"):
                        if not notes.strip():
                            st.error("Please provide a reason for the change.")
                        else:
                            config.request_update_application_type(
                                selected, update_tech, new_type,
                                notes=notes, requested_by=user
                            )
                            st.success(
                                f"✓ Request submitted: {selected} — {update_tech} "
                                f"{current_type} → {new_type}"
                            )
                            reload_config()
                            st.rerun()

            # Tab 3: Assign to class
            with action_tabs[2]:
                st.markdown("**Add this component to an asset class**")
                already_in = set(config.get_component_classes(selected))
                available_classes = [c for c in config.class_names
                                     if c not in already_in]

                if not available_classes:
                    st.info("This component is already assigned to all classes.")
                else:
                    assign_class = st.selectbox("Asset Class", available_classes,
                                                key="assign_to_class")
                    if st.button("Assign to Class", key="btn_assign_class",
                                 type="primary"):
                        config.assign_component_to_class(
                            assign_class, selected, requested_by=user
                        )
                        st.success(f"✓ Assigned {selected} to {assign_class}")
                        reload_config()
                        st.rerun()

            # Tab 4: Request removal
            with action_tabs[3]:
                st.markdown("""
                <div class="request-box">
                    <div class="req-label">⚠ Removal Request</div>
                    <p>Removing a component removes all its technology and class assignments.
                    This requires admin approval.</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="info-card">
                    <div class="label">Impact if approved</div>
                    <div style="color:#fca5a5; font-size:0.85rem; margin-top:4px;">
                        • Removes {len(techs)} technology assignment(s)<br>
                        • Removes from {len(classes)} asset class(es)<br>
                        • Affects all assets in those classes at next pipeline run
                    </div>
                </div>
                """, unsafe_allow_html=True)

                removal_notes = st.text_area(
                    "Reason for removal request", key="removal_notes",
                    placeholder="Why should this component be removed? "
                                "Is it replaced by another component?"
                )

                if st.button("Submit Removal Request", key="btn_remove_comp",
                             type="primary"):
                    if not removal_notes.strip():
                        st.error("Please provide a reason.")
                    else:
                        log_id = config.request_remove_component(
                            selected, notes=removal_notes, requested_by=user
                        )
                        st.success(
                            f"✓ Removal request submitted (log #{log_id}). "
                            f"Admin will review."
                        )
                        reload_config()
                        st.rerun()

    st.markdown("---")

    # ── Add new component ──────────────────────────────────────────────────

    st.markdown('<div class="section-header">Add New Component</div>',
                unsafe_allow_html=True)

    with st.expander("➕ Add a new component type"):
        new_comp_name = st.text_input(
            "Component name",
            placeholder="e.g. Servo Motors - Encoder",
            key="new_comp_name"
        )

        st.markdown("**Initial technology assignments** *(optional — can add later)*")

        tech_assignments = {}
        cols = st.columns(4)
        for i, tech in enumerate(config.technology_codes):
            with cols[i % 4]:
                assignment = st.selectbox(
                    tech, ["—", "Primary", "Secondary"],
                    key=f"new_comp_tech_{tech}"
                )
                if assignment != "—":
                    tech_assignments[tech] = assignment

        if st.button("Add Component", key="btn_add_comp", type="primary"):
            if not new_comp_name.strip():
                st.error("Component name is required.")
            elif new_comp_name.strip() in config.component_names:
                st.error(f"'{new_comp_name.strip()}' already exists.")
            else:
                name = new_comp_name.strip()
                config.add_component(name, requested_by=user)
                for tech, app_type in tech_assignments.items():
                    config.assign_technology_to_component(
                        name, tech, app_type, requested_by=user
                    )
                st.success(
                    f"✓ Added '{name}' with "
                    f"{len(tech_assignments)} technology assignment(s)."
                )
                reload_config()
                st.rerun()


# ── Classes page ──────────────────────────────────────────────────────────────

def page_classes(config: ACMConfig):
    user = st.session_state.user

    st.markdown("""
    <div class="acm-header">
        <h1>🏭 ASSET CLASSES</h1>
        <p>Browse asset classes · manage component assignments · request removals</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Class browser ──────────────────────────────────────────────────────

    st.markdown('<div class="section-header">Browse Asset Classes</div>',
                unsafe_allow_html=True)

    search = st.text_input("Filter classes", placeholder="Type to search...",
                           label_visibility="collapsed", key="class_search")

    names = config.class_names
    if search:
        names = [n for n in names if search.lower() in n.lower()]

    if not names:
        st.info("No classes match your search.")
    else:
        selected_class = st.selectbox("Select a class to work with",
                                      names, label_visibility="collapsed",
                                      key="selected_class")

        if selected_class:
            components = config.get_class_components(selected_class)
            techs_df = config.get_class_technologies(selected_class)

            col1, col2 = st.columns([2, 3])
            with col1:
                st.markdown(f"""
                <div class="info-card">
                    <div class="label">Asset Class</div>
                    <div style="font-size:1.1rem; font-weight:600;
                                color:#e2e8f0; margin-bottom:8px;">
                        {selected_class}
                    </div>
                    <div class="label">Assigned Components</div>
                    <div class="value">{len(components)}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if techs_df.empty:
                    st.markdown("""
                    <div class="info-card">
                        <div class="label">Required Technologies</div>
                        <div style="color:#475569; font-size:0.85rem; margin-top:6px;">
                            No technology requirements defined yet.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    badges = ''
                    for _, row in techs_df.iterrows():
                        css = ('badge-primary' if row['application_type'] == 'Primary'
                               else 'badge-secondary')
                        badges += (f'<span class="{css}">'
                                   f'{row["technology_code"]} · '
                                   f'{row["application_type"][0]}</span> ')
                    st.markdown(f"""
                    <div class="info-card">
                        <div class="label">Required Technologies (derived)</div>
                        <div style="margin-top:8px;">{badges}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ── Component list with per-row removal requests ────────────────

            st.markdown('<div class="section-header">Component Assignments</div>',
                        unsafe_allow_html=True)

            if not components:
                st.info("No components assigned to this class yet.")
            else:
                for comp in components:
                    col1, col2, col3 = st.columns([3, 3, 1])
                    with col1:
                        st.markdown(f"""
                        <div style="padding: 8px 0; color:#e2e8f0;
                                    font-size:0.9rem;">{comp}</div>
                        """, unsafe_allow_html=True)
                    with col2:
                        st.markdown(
                            f'<div style="padding:8px 0">'
                            f'{tech_badges(config, comp)}</div>',
                            unsafe_allow_html=True
                        )
                    with col3:
                        if st.button("⚠ Remove", key=f"rm_cc_{selected_class}_{comp}"):
                            st.session_state[f"confirm_rm_{selected_class}_{comp}"] = True

                    # Inline confirmation form
                    confirm_key = f"confirm_rm_{selected_class}_{comp}"
                    if st.session_state.get(confirm_key):
                        with st.container():
                            st.markdown(f"""
                            <div class="request-box">
                                <div class="req-label">Submit Removal Request</div>
                                <p>Request removal of <strong>{comp}</strong>
                                from <strong>{selected_class}</strong></p>
                            </div>
                            """, unsafe_allow_html=True)
                            rm_notes = st.text_area(
                                "Reason", key=f"rm_notes_{selected_class}_{comp}",
                                placeholder="Why should this component be removed from this class?"
                            )
                            rcol1, rcol2 = st.columns(2)
                            with rcol1:
                                if st.button("Submit Request",
                                             key=f"submit_rm_{selected_class}_{comp}",
                                             type="primary"):
                                    if not rm_notes.strip():
                                        st.error("Reason required.")
                                    else:
                                        log_id = config.request_remove_component_from_class(
                                            selected_class, comp,
                                            notes=rm_notes, requested_by=user
                                        )
                                        st.success(f"✓ Request submitted (log #{log_id})")
                                        st.session_state[confirm_key] = False
                                        reload_config()
                                        st.rerun()
                            with rcol2:
                                if st.button("Cancel",
                                             key=f"cancel_rm_{selected_class}_{comp}"):
                                    st.session_state[confirm_key] = False
                                    st.rerun()

            # ── Add component to this class ────────────────────────────────

            st.markdown('<div class="section-header">Add Component to This Class</div>',
                        unsafe_allow_html=True)

            already_in = set(components)
            available = [c for c in config.component_names if c not in already_in]

            if not available:
                st.info("All components are already assigned to this class.")
            else:
                col1, col2 = st.columns([3, 1])
                with col1:
                    add_comp = st.selectbox("Component to add", available,
                                            key=f"add_comp_to_{selected_class}")
                with col2:
                    st.markdown('<div style="padding-top:28px"></div>',
                                unsafe_allow_html=True)
                    if st.button("Assign →", key=f"btn_add_comp_class",
                                 type="primary"):
                        config.assign_component_to_class(
                            selected_class, add_comp, requested_by=user
                        )
                        st.success(f"✓ Assigned '{add_comp}' to {selected_class}")
                        reload_config()
                        st.rerun()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not st.session_state.user:
        login_screen()
        return

    config = get_config()
    sidebar(config)

    if st.session_state.page == 'components':
        page_components(config)
    elif st.session_state.page == 'classes':
        page_classes(config)


if __name__ == '__main__':
    main()
