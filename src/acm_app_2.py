"""
ACM Coverage Analysis Dashboard v2
Streamlit app for exploring asset condition monitoring coverage gaps
Focus: Department Scorecard and Technology Navigator
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page config
st.set_page_config(
    page_title="ACM Coverage Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# Load data functions
@st.cache_data
def load_coverage_data():
    """Load coverage report from pickle file"""
    try:
        df = pd.read_pickle('data/coverage_report.pkl')
        
        # Patch: Consolidate all FA* departments into 'FA'
        df['ASSET_DEPT'] = df['ASSET_DEPT'].apply(
            lambda x: 'FA' if str(x).startswith('FA') else x
        )
        
        return df
    except FileNotFoundError:
        st.error("❌ Coverage report not found at 'data/coverage_report.pkl'")
        st.info("Please run the Quarto analysis first to generate the coverage report.")
        st.stop()

@st.cache_data
def load_tech_definitions():
    """Load technology definitions"""
    try:
        techs = pd.read_csv('data/st_tbl/techs_def.csv')
        return techs
    except FileNotFoundError:
        st.warning("⚠️ Technology definitions not found. Using fallback list.")
        # Fallback based on your data
        return pd.DataFrame({
            'tech_code': ['GM', 'IR', 'UL', 'VI', 'LU', 'MC', 'ZD', 'CW'],
            'domain': ['General Metering', 'Thermography', 'Ultrasound', 
                      'Vibration', 'Lubrication', 'Motor Current Testing',
                      'Zone Dosimetry', 'Chain Monitoring']
        })



# Main app
# Main app
def main():
    # Load data
    df = load_coverage_data()
    tech_defs = load_tech_definitions()
    tech_codes = tech_defs['tech_code'].tolist()
    
    # Header
    st.title("🔧 ACM Coverage Dashboard")
    st.markdown("**Asset Condition Monitoring Coverage Analysis**")
    st.markdown("---")
    
    # Sidebar navigation
    st.sidebar.title("📊 Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["🏢 Department Scorecard", "🎯 Technology Navigator"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    
    # Route to appropriate page
    if page == "🏢 Department Scorecard":
        department_scorecard(df, tech_defs, tech_codes)
    else:
        technology_navigator(df, tech_defs, tech_codes)
    
    # Sidebar info
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Dataset Info")
    st.sidebar.metric("Total Assets", f"{len(df):,}")
    st.sidebar.metric("Departments", f"{df['ASSET_DEPT'].nunique()}")
    st.sidebar.metric("Technologies", f"{len(tech_codes)}")
    st.sidebar.metric("Overall Compliance", f"{(df['MASTER_JUDGE'].sum() / len(df) * 100):.1f}%")

# ==================== PAGE 1: Department Scorecard ====================
def department_scorecard(df, tech_defs, tech_codes):
    st.header("Department Scorecard")
    st.markdown("*View coverage compliance by department, filterable by technology*")
    
    # Sidebar filters for Department view
    st.sidebar.markdown("### 🏢 Department Filters")
    
    # Department multi-select filter
    all_departments = sorted(df['ASSET_DEPT'].unique())
    selected_departments = st.sidebar.multiselect(
        "Select Departments to Display",
        all_departments,
        default=all_departments,
        key='dept_filter'
    )
    
    # Technology filter
    tech_filter_options = ['All Technologies'] + [
        f"{code} - {tech_defs[tech_defs['tech_code']==code]['domain'].values[0]}" 
        if code in tech_defs['tech_code'].values else code
        for code in tech_codes
    ]
    selected_tech_filter = st.sidebar.selectbox(
        "Filter by Technology",
        tech_filter_options,
        key='dept_tech_filter'
    )
    
    # Add checkbox to include "Not Required" assets
    include_not_required = st.sidebar.checkbox(
        "Include 'Not Required' assets",
        value=False,
        key='dept_include_not_req',
        help="Show assets that don't need this technology (JUDGE = 2)"
    )
    
    # Check if departments selected
    if not selected_departments:
        st.warning("⚠️ Please select at least one department from the sidebar.")
        return
    
    # Filter dataframe by selected departments
    filtered_df = df[df['ASSET_DEPT'].isin(selected_departments)]
    
    # Extract tech code if specific technology selected
    if selected_tech_filter == 'All Technologies':
        filter_tech = None
        judge_col = 'MASTER_JUDGE'
        st.info("📊 Showing **overall compliance** (all technologies must be compliant)")
        # For MASTER_JUDGE, we don't filter out "Not Required" since it's aggregate
        include_not_required = True
    else:
        filter_tech = selected_tech_filter.split(' - ')[0]
        judge_col = f'{filter_tech}_JUDGE'
        tech_name = tech_defs[tech_defs['tech_code']==filter_tech]['domain'].values[0]
        st.info(f"📊 Showing compliance for **{filter_tech} - {tech_name}**")
        
        # Filter out "Not Required" (JUDGE = 2) if checkbox is unchecked
        if not include_not_required:
            filtered_df = filtered_df[filtered_df[judge_col] != 2]
    
    # Calculate department metrics
    dept_summary = []
    
    for dept in selected_departments:
        dept_df = filtered_df[filtered_df['ASSET_DEPT'] == dept]
        
        if len(dept_df) == 0:
            # Department has no assets after filtering
            continue
            
        total = len(dept_df)
        compliant = (dept_df[judge_col] == 1).sum()
        gaps = (dept_df[judge_col] == 0).sum()
        not_required = (dept_df[judge_col] == 2).sum() if include_not_required else 0
        compliance_rate = (compliant / total * 100) if total > 0 else 0
        
        dept_summary.append({
            'Department': dept,
            'Total Assets': total,
            'Compliant': compliant,
            'Critical Gaps': gaps,
            'Not Required': not_required,
            'Compliance %': compliance_rate
        })
    
    if not dept_summary:
        st.warning("⚠️ No assets found after applying filters.")
        return
    
    summary_df = pd.DataFrame(dept_summary).sort_values('Compliance %')
    
    # Display summary table
    st.subheader("Department Summary")
    display_cols = ['Department', 'Total Assets', 'Compliant', 'Critical Gaps']
    if include_not_required:
        display_cols.append('Not Required')
    display_cols.append('Compliance %')
    
    st.dataframe(
        summary_df[display_cols].style.background_gradient(subset=['Compliance %'], cmap='RdYlGn', vmin=0, vmax=100),
        use_container_width=True,
        height=300
    )
    
    st.markdown("---")
    
    # Create horizontal stacked bar chart
    st.subheader("Compliance Distribution by Department")
    
    # Prepare data for stacked bar
    chart_data = summary_df.copy()
    chart_data = chart_data.sort_values('Compliance %', ascending=True)
    
    fig = go.Figure()
    
    # Add compliant bar (green)
    fig.add_trace(go.Bar(
        name='Compliant',
        y=chart_data['Department'],
        x=chart_data['Compliant'],
        orientation='h',
        marker=dict(color='#2e7d32'),
        text=chart_data['Compliant'],
        textposition='inside',
        hovertemplate='<b>%{y}</b><br>Compliant: %{x}<br>Rate: %{customdata:.1f}%<extra></extra>',
        customdata=chart_data['Compliance %']
    ))
    
    # Add critical gaps bar (red)
    fig.add_trace(go.Bar(
        name='Critical Gaps',
        y=chart_data['Department'],
        x=chart_data['Critical Gaps'],
        orientation='h',
        marker=dict(color='#c62828'),
        text=chart_data['Critical Gaps'],
        textposition='inside',
        hovertemplate='<b>%{y}</b><br>Critical Gaps: %{x}<extra></extra>'
    ))
    
    # Add not required bar (gray) if included
    if include_not_required:
        fig.add_trace(go.Bar(
            name='Not Required',
            y=chart_data['Department'],
            x=chart_data['Not Required'],
            orientation='h',
            marker=dict(color='#9e9e9e'),
            text=chart_data['Not Required'],
            textposition='inside',
            hovertemplate='<b>%{y}</b><br>Not Required: %{x}<extra></extra>'
        ))
    
    fig.update_layout(
        barmode='stack',
        height=max(400, len(selected_departments) * 40),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        xaxis_title="Number of Assets",
        yaxis_title="Department",
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Download option
    st.markdown("---")
    csv = summary_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Department Summary (CSV)",
        data=csv,
        file_name=f"dept_scorecard_{filter_tech if filter_tech else 'all_tech'}.csv",
        mime="text/csv"
    )

# ==================== PAGE 2: Technology Navigator ====================
def technology_navigator(df, tech_defs, tech_codes):
    st.header("Technology Navigator")
    st.markdown("*View coverage compliance by technology, filterable by department*")
    
    # Sidebar filters for Technology view
    st.sidebar.markdown("### 🎯 Technology Filters")
    
    # Department filter
    dept_filter_options = ['All Departments'] + sorted(df['ASSET_DEPT'].unique().tolist())
    selected_dept_filter = st.sidebar.selectbox(
        "Filter by Department",
        dept_filter_options,
        key='tech_dept_filter'
    )
    
    # Add checkbox to include "Not Required" assets
    include_not_required = st.sidebar.checkbox(
        "Include 'Not Required' assets",
        value=False,
        key='tech_include_not_req',
        help="Show assets that don't need each technology (JUDGE = 2)"
    )
    
    # Filter dataframe by department if selected
    if selected_dept_filter == 'All Departments':
        filtered_df = df
        st.info("📊 Showing coverage across **all departments**")
    else:
        filtered_df = df[df['ASSET_DEPT'] == selected_dept_filter]
        st.info(f"📊 Showing coverage for **{selected_dept_filter}** department")
    
    # Calculate technology metrics
    tech_summary = []
    
    for tech in tech_codes:
        judge_col = f'{tech}_JUDGE'
        needs_col = f'NEEDS_{tech}'
        has_col = f'HAS_{tech}'
        
        # Filter out "Not Required" if checkbox is unchecked
        tech_df = filtered_df.copy()
        if not include_not_required:
            tech_df = tech_df[tech_df[judge_col] != 2]
        
        total = len(tech_df)
        compliant = (tech_df[judge_col] == 1).sum()
        gaps = (tech_df[judge_col] == 0).sum()
        not_required = (tech_df[judge_col] == 2).sum() if include_not_required else 0
        compliance_rate = (compliant / total * 100) if total > 0 else 0
        
        # Additional breakdown (from original filtered_df, not tech_df)
        primary_need = (filtered_df[needs_col] == 'P').sum()
        secondary_need = (filtered_df[needs_col] == 'S').sum()
        has_coverage = (filtered_df[has_col] == 'Y').sum()
        
        tech_name = tech_defs[tech_defs['tech_code']==tech]['domain'].values[0] if tech in tech_defs['tech_code'].values else tech
        
        tech_summary.append({
            'Technology': f"{tech}",
            'Full Name': tech_name,
            'Total Assets': total,
            'Compliant': compliant,
            'Critical Gaps': gaps,
            'Not Required': not_required,
            'Compliance %': compliance_rate,
            'Primary Needs': primary_need,
            'Secondary Needs': secondary_need,
            'Has Coverage': has_coverage
        })
    
    summary_df = pd.DataFrame(tech_summary).sort_values('Compliance %')
    
    # Display summary table
    st.subheader("Technology Summary")
    display_cols = ['Technology', 'Full Name', 'Total Assets', 'Compliant', 'Critical Gaps']
    if include_not_required:
        display_cols.append('Not Required')
    display_cols.append('Compliance %')
    
    st.dataframe(
        summary_df[display_cols].style.background_gradient(subset=['Compliance %'], cmap='RdYlGn', vmin=0, vmax=100),
        use_container_width=True,
        height=300
    )
    
    # Expandable details
    with st.expander("📋 Show Detailed Breakdown (Needs vs Has)"):
        detail_cols = ['Technology', 'Full Name', 'Primary Needs', 'Secondary Needs', 'Has Coverage', 'Critical Gaps']
        st.dataframe(summary_df[detail_cols], use_container_width=True)
    
    st.markdown("---")
    
    # Create horizontal stacked bar chart
    st.subheader("Compliance Distribution by Technology")
    
    # Prepare data for stacked bar
    chart_data = summary_df.copy()
    chart_data = chart_data.sort_values('Compliance %', ascending=True)
    
    fig = go.Figure()
    
    # Add compliant bar (green)
    fig.add_trace(go.Bar(
        name='Compliant',
        y=chart_data['Technology'],
        x=chart_data['Compliant'],
        orientation='h',
        marker=dict(color='#2e7d32'),
        text=chart_data['Compliant'],
        textposition='inside',
        hovertemplate='<b>%{y}</b><br>Compliant: %{x}<br>Rate: %{customdata:.1f}%<extra></extra>',
        customdata=chart_data['Compliance %']
    ))
    
    # Add critical gaps bar (red)
    fig.add_trace(go.Bar(
        name='Critical Gaps',
        y=chart_data['Technology'],
        x=chart_data['Critical Gaps'],
        orientation='h',
        marker=dict(color='#c62828'),
        text=chart_data['Critical Gaps'],
        textposition='inside',
        hovertemplate='<b>%{y}</b><br>Critical Gaps: %{x}<extra></extra>'
    ))
    
    # Add not required bar (gray) if included
    if include_not_required:
        fig.add_trace(go.Bar(
            name='Not Required',
            y=chart_data['Technology'],
            x=chart_data['Not Required'],
            orientation='h',
            marker=dict(color='#9e9e9e'),
            text=chart_data['Not Required'],
            textposition='inside',
            hovertemplate='<b>%{y}</b><br>Not Required: %{x}<extra></extra>'
        ))
    
    fig.update_layout(
        barmode='stack',
        height=max(400, len(tech_codes) * 50),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        xaxis_title="Number of Assets",
        yaxis_title="Technology",
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Download option
    st.markdown("---")
    csv = summary_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Technology Summary (CSV)",
        data=csv,
        file_name=f"tech_navigator_{selected_dept_filter.replace(' ', '_') if selected_dept_filter != 'All Departments' else 'all_depts'}.csv",
        mime="text/csv")

if __name__ == "__main__":
    main()

