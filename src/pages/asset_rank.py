"""
Asset Rank Page
Browse and filter ranked assets from Maximo asset_rank query.
Loads from cached pickle; refresh button re-runs the query.
"""

import streamlit as st
import pandas as pd
import pyodbc
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Asset Rank",
    page_icon="🏆",
    layout="wide"
)

# ── Paths & credentials ───────────────────────────────────────────────────────
PICKLE_PATH = Path('data/asset_rank.pkl')
SQL_PATH    = Path('query/asset_rank.sql')

load_dotenv(find_dotenv())
DSN      = os.getenv('MAXIMO_DSN')
USER     = os.getenv('MAXIMO_USER')
PASSWORD = os.getenv('MAXIMO_PASS')

# ── Rank color map ────────────────────────────────────────────────────────────
# S → A → B → C, highest to lowest criticality
RANK_COLORS = {
    'S': '#9B59B6',   # purple  – super critical
    'A': '#90EE90',   # green   – high criticality
    'B': '#F5F5DC',   # beige   – medium criticality
    'C': '#5B9BD5',   # blue    – standard criticality
}

def rank_cell_style(val):
    color = RANK_COLORS.get(str(val).strip().upper(), '#D3D3D3')
    return f'background-color: {color}; color: black; font-weight: bold; text-align: center;'

# ── Query runner ──────────────────────────────────────────────────────────────
def run_asset_rank_query() -> pd.DataFrame:
    """Connect to Maximo and execute asset_rank.sql."""
    if not SQL_PATH.exists():
        raise FileNotFoundError(f"SQL script not found: {SQL_PATH}")

    conn  = pyodbc.connect(f"DSN={DSN};UID={USER};PWD={PASSWORD}")
    query = SQL_PATH.read_text()
    df    = pd.read_sql(query, conn)
    conn.close()

    # Consistent dtypes (mirrors asset_rank.py)
    for col in ['ASSETNUM', 'ASSET_DESC', 'ASSET_CLASS', 'ASSET_DEPT', 'RANK']:
        if col in df.columns:
            df[col] = df[col].astype('category')

    return df

# ── Load data (cache-first) ───────────────────────────────────────────────────
def load_data() -> tuple[pd.DataFrame | None, str | None]:
    """Return (dataframe, last_refreshed_str) from pickle, or (None, None)."""
    if PICKLE_PATH.exists():
        df        = pd.read_pickle(PICKLE_PATH)
        ts        = datetime.fromtimestamp(PICKLE_PATH.stat().st_mtime)
        refreshed = ts.strftime('%Y-%m-%d  %H:%M')
        return df, refreshed
    return None, None

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏆 Asset Rank")
st.markdown("Ranked assets from Maximo — sorted by criticality tier.")
st.markdown("---")

# ── Sidebar: data source controls ────────────────────────────────────────────
with st.sidebar:
    st.header("Data Source")

    df, last_refreshed = load_data()

    if df is not None:
        st.success(f"✅ Cached data loaded")
        st.caption(f"Last refreshed: {last_refreshed}")
    else:
        st.warning("⚠️ No cached data found")
        st.caption(f"Expected: `{PICKLE_PATH}`")

    refresh_clicked = st.button(
        "🔄 Refresh from Maximo",
        help="Re-runs asset_rank.sql against Maximo and saves a new pickle",
        use_container_width=True
    )

    if refresh_clicked:
        with st.spinner("Running query against Maximo…"):
            try:
                df = run_asset_rank_query()
                PICKLE_PATH.parent.mkdir(parents=True, exist_ok=True)
                df.to_pickle(PICKLE_PATH)
                st.success("✅ Query complete — data refreshed")
                st.rerun()
            except FileNotFoundError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Query failed: {e}")

    # ── Filters (only show when data is loaded) ───────────────────────────────
    if df is not None:
        st.markdown("---")
        st.header("Filters")

        # DEPT filter
        all_depts = sorted(df['ASSET_DEPT'].astype(str).unique())
        selected_depts = st.multiselect(
            "Department",
            options=all_depts,
            default=all_depts,
        )

        # RANK filter — auto-detect available tiers
        all_ranks = sorted(df['RANK'].astype(str).unique())
        selected_ranks = st.multiselect(
            "Rank Tier",
            options=all_ranks,
            default=all_ranks,
        )

# ── Main content ──────────────────────────────────────────────────────────────
if df is None:
    st.info("No data available. Use **Refresh from Maximo** in the sidebar to run the query, or ensure `data/asset_rank.pkl` exists.")
    st.stop()

# Apply filters
mask = (
    df['ASSET_DEPT'].astype(str).isin(selected_depts) &
    df['RANK'].astype(str).isin(selected_ranks)
)
filtered = df[mask].copy()

# ── Summary metrics ───────────────────────────────────────────────────────────
total        = len(filtered)
rank_counts  = filtered['RANK'].astype(str).value_counts().sort_index()

metric_cols = st.columns(1 + len(rank_counts))
metric_cols[0].metric("Total Assets", f"{total:,}")
for i, (rank, count) in enumerate(rank_counts.items(), start=1):
    label = f"Rank {rank}"
    metric_cols[i].metric(label, f"{count:,}")

st.markdown("---")

# ── Rank distribution bar chart ───────────────────────────────────────────────
if not filtered.empty:
    import plotly.graph_objects as go

    # Distribution by department × rank (stacked bar)
    dept_rank = (
        filtered.groupby(['ASSET_DEPT', 'RANK'], observed=True)
        .size()
        .reset_index(name='Count')
    )

    fig = go.Figure()
    for rank_val in sorted(dept_rank['RANK'].astype(str).unique()):
        subset = dept_rank[dept_rank['RANK'].astype(str) == rank_val]
        bar_color = RANK_COLORS.get(rank_val.strip().upper(), '#D3D3D3')
        fig.add_trace(go.Bar(
            name=f"Rank {rank_val}",
            x=subset['ASSET_DEPT'].astype(str),
            y=subset['Count'],
            marker_color=bar_color,
            text=subset['Count'],
            textposition='auto'
        ))

    fig.update_layout(
        barmode='stack',
        title='Asset Count by Department and Rank',
        xaxis_title='Department',
        yaxis_title='Asset Count',
        height=400,
        legend_title='Rank',
        xaxis={'categoryorder': 'total descending'}
    )

    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Asset detail table ────────────────────────────────────────────────────────
st.subheader(f"Asset Detail  ({total:,} assets)")

# Column order: RANK first so the color stands out
display_cols = [c for c in ['RANK', 'ASSETNUM', 'ASSET_DEPT', 'ASSET_CLASS', 'ASSET_DESC']
                if c in filtered.columns]
display_df = filtered[display_cols].reset_index(drop=True)

# Sort by RANK ascending (A first / 1 first)
display_df = display_df.sort_values('RANK', ascending=True).reset_index(drop=True)

styled = display_df.style.applymap(
    rank_cell_style,
    subset=['RANK']
).set_properties(**{
    'font-size': '13px',
})

st.dataframe(
    styled,
    use_container_width=True,
    hide_index=True,
    height=600
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("ACM Coverage Dashboard | Honda Manufacturing of Alabama")
