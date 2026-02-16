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

# Tech Card Code
def create_tech_card(df, tech_code, tech_name):
    """Create a technology coverage card with metrics"""
    
    judge_col = f'{tech_code}_JUDGE'
    needs_col = f'NEEDS_{tech_code}'
    
    # Calculate metrics
    primary_needs = (df[needs_col] == 'P').sum()
    secondary_needs = (df[needs_col] == 'S').sum()
    
    # Judgment breakdown (using your string values)
    compliant = (df[judge_col] == 'Compliant').sum()
    partial = (df[judge_col] == 'Partial Coverage').sum()
    critical_gap = (df[judge_col] == 'Critical Gap').sum()
    not_applicable = (df[judge_col] == 'Not Applicable').sum()
    
    # Calculate percentages (based on assets that need this tech)
    assets_needing_tech = primary_needs + secondary_needs
    if assets_needing_tech > 0:
        pct_compliant = (compliant / assets_needing_tech) * 100
        pct_partial = (partial / assets_needing_tech) * 100
        pct_critical = (critical_gap / assets_needing_tech) * 100
    else:
        pct_compliant = pct_partial = pct_critical = 0
    
    # Create the card using columns
    with st.container():
        st.markdown(f"#### {tech_name}")
        st.caption(tech_code)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Primary Needs", f"{primary_needs:,}")
            st.metric("Secondary Appl.", f"{secondary_needs:,}")
        
        with col2:
            st.metric("Total Needs", f"{assets_needing_tech:,}")
            st.metric("Not Applicable", f"{not_applicable:,}")
        
        # Color-coded status sections
        
        st.markdown(f"""
                <div style="background-color: #e8f5e9; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                    <p style="margin: 0 0 8px 0;"><strong>🟢 Compliant:</strong> {pct_compliant:.1f}% ({compliant:,} assets)</p>
                    <div style="background-color: #e0e0e0; border-radius: 5px; overflow: hidden;">
                        <div style="background-color: #2e7d32; width: {pct_compliant}%; padding: 5px 0;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
                <div style="background-color: #fff3e0; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                    <p style="margin: 0 0 8px 0;"><strong>🟡 Partial Applied:</strong> {pct_partial:.1f}% ({partial:,} assets)</p>
                    <div style="background-color: #e0e0e0; border-radius: 5px; overflow: hidden;">
                        <div style="background-color: #ffa726; width: {pct_partial}%; padding: 5px 0;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="background-color: #ffebee; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                <p style="margin: 0 0 8px 0;"><strong>🔴 Critical Gap:</strong> {pct_critical:.1f}% ({critical_gap:,} assets)</p>
                <div style="background-color: #e0e0e0; border-radius: 5px; overflow: hidden;">
                    <div style="background-color: #c62828; width: {pct_critical}%; padding: 5px 0;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        

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

    # Department multi-select filter
    all_departments = sorted(df['ASSET_DEPT'].unique())
    selected_departments = st.multiselect(
        "Select Departments to Display",
        all_departments,
        default=None,
        key='dept_filter'
    )

    # Check if departments selected
    if not selected_departments:
        st.warning("⚠️ Please select at least one department from the sidebar.")
        return

    # Filter by selected departments only (for the chart)
    dept_filtered_df = df[df['ASSET_DEPT'].isin(selected_departments)]

    # Create asset class breakdown chart
    st.subheader("Asset Class Distribution by Compliance")

    # Calculate compliance by asset class
    class_compliance = []
    for asset_class in sorted(dept_filtered_df['ASSET_CLASS'].unique()):
        class_df = dept_filtered_df[dept_filtered_df['ASSET_CLASS'] == asset_class]
        
        if selected_tech_filter == 'All Technologies':
            judge_col = 'MASTER_JUDGE'
        else:
            filter_tech = selected_tech_filter.split(' - ')[0]
            judge_col = f'{filter_tech}_JUDGE'
        
        # Filter out "Not Applicable" if needed
        if not include_not_required:
            class_df = class_df[class_df[judge_col] != 'Not Applicable']
        
        total = len(class_df)
        if total > 0:
            compliant = (class_df[judge_col] == 'Compliant').sum()
            partial = (class_df[judge_col] == 'Partial Coverage').sum()
            critical = (class_df[judge_col] == 'Critical Gap').sum()
            not_app = (class_df[judge_col] == 'Not Applicable').sum()
            
            class_compliance.append({
                'Asset Class': asset_class,
                'Compliant': compliant,
                'Partial Coverage': partial,
                'Critical Gap': critical,
                'Not Applicable': not_app if include_not_required else 0,
                'Total': total
            })

    if class_compliance:
        compliance_df = pd.DataFrame(class_compliance).sort_values('Total', ascending=True)
        
        # Create stacked bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Compliant',
            x=compliance_df['Asset Class'],
            y=compliance_df['Compliant'],
            marker=dict(color='#2e7d32'),
            text=compliance_df['Compliant'],
            textposition='inside'
        ))
        
        fig.add_trace(go.Bar(
            name='Partial Coverage',
            x=compliance_df['Asset Class'],
            y=compliance_df['Partial Coverage'],
            marker=dict(color='#ffa726'),
            text=compliance_df['Partial Coverage'],
            textposition='inside'
        ))
        
        fig.add_trace(go.Bar(
            name='Critical Gap',
            x=compliance_df['Asset Class'],
            y=compliance_df['Critical Gap'],
            marker=dict(color='#c62828'),
            text=compliance_df['Critical Gap'],
            textposition='inside'
        ))
        
        if include_not_required:
            fig.add_trace(go.Bar(
                name='Not Applicable',
                x=compliance_df['Asset Class'],
                y=compliance_df['Not Applicable'],
                marker=dict(color='#9e9e9e'),
                text=compliance_df['Not Applicable'],
                textposition='inside'
            ))
        
        fig.update_layout(
            barmode='stack',
            height=500,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            yaxis_title="Number of Assets",
            xaxis_title="Asset Class",
            hovermode='closest'
        )
    
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Get asset classes available in selected departments
    available_classes = sorted(
        df[df['ASSET_DEPT'].isin(selected_departments)]['ASSET_CLASS'].unique()
    )

    # Asset Class Filter
    selected_classes = st.multiselect(
        "Select Asset Classes to Display",
        available_classes,
        default=available_classes,  # Defaults to all classes in selected departments
        key='class_filter'
    )

    # Filter dataframe by selected departments and asset classes
    filtered_df = df[
        df['ASSET_DEPT'].isin(selected_departments) & 
        df['ASSET_CLASS'].isin(selected_classes)
    ]
    
    # Extract tech code if specific technology selected
    if selected_tech_filter == 'All Technologies':
        filter_tech = None
        judge_col = 'MASTER_JUDGE'
        st.info("📊 text")
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
    
    # In your technology_navigator function, add this section:
    st.subheader("Technology Coverage Cards")

    # Create cards in rows of 2 or 3
    for i in range(0, len(tech_codes), 3):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(tech_codes):
                tech = tech_codes[i + j]
                tech_name = tech_defs[tech_defs['tech_code']==tech]['domain'].values[0]
                with col:
                    with st.container():
                        st.markdown("---")
                        create_tech_card(filtered_df, tech, tech_name)

    # Technology multi-select filter
    selected_techs = st.multiselect(
        "Select Technologies to Display",
        tech_codes,
        default=tech_codes,
        key='tech_filter'
    )

    # Filter dataframe by all three filters
    filtered_df = df[
        df['ASSET_DEPT'].isin(selected_departments) & 
        df['ASSET_CLASS'].isin(selected_classes)
    ]

    st.markdown("---")

    # Asset Details Table
    st.subheader("Asset Details")

    # Build the columns to display
    base_cols = ['ASSETNUM', 'ASSET_DESC', 'ASSET_CLASS']
    tech_cols_to_show = []

    # For each selected technology, check if asset needs it (P or S)
    for tech in selected_techs:
        needs_col = f'NEEDS_{tech}'
        has_col = f'HAS_{tech}'
        judge_col = f'{tech}_JUDGE'
        
        # Add columns for technologies where ANY asset in filtered set has P or S
        if ((filtered_df[needs_col] == 'P') | (filtered_df[needs_col] == 'S')).any():
            tech_cols_to_show.extend([needs_col, has_col, judge_col])

    # Add MASTER_JUDGE at the end
    display_cols = base_cols + tech_cols_to_show + ['MASTER_JUDGE']

    # Filter to only show rows that have at least one P or S need in selected technologies
    needs_cols_selected = [f'NEEDS_{tech}' for tech in selected_techs]
    has_need_mask = filtered_df[needs_cols_selected].isin(['P', 'S']).any(axis=1)
    table_df = filtered_df[has_need_mask][display_cols]

    st.dataframe(
        table_df,
        use_container_width=True,
        height=400
    )

    st.metric("Assets Shown", f"{len(table_df):,}")
    
    st.markdown("---")
    


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

