"""
ACM Coverage Analysis Dashboard
Streamlit app for exploring asset condition monitoring coverage
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page config
st.set_page_config(
    page_title="ACM Coverage Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
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
    }
    </style>
""", unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    """Load coverage report from pickle file"""
    try:
        df = pd.read_pickle('data/coverage_report.pkl')
        return df
    except FileNotFoundError:
        st.error("❌ Coverage report not found! Please run the Quarto analysis first.")
        st.stop()

# Load technology definitions
@st.cache_data
def load_tech_definitions():
    """Load technology definitions"""
    try:
        return pd.read_csv('data/st_tbl/techs_def.csv')
    except FileNotFoundError:
        # Fallback to hardcoded list if file not found
        return pd.DataFrame({
            'tech_code': ['GM', 'IR', 'UL', 'VI', 'LU', 'MC', 'ZD', 'CW'],
            'domain': ['General Metering', 'Thermography', 'Ultrasound', 
                      'Vibration', 'Lubrication', 'Motor Current Testing',
                      'Robotics Monitoring', 'Chain Monitoring']
        })

# Main app
def main():
    # Load data
    df = load_data()
    tech_defs = load_tech_definitions()
    tech_codes = tech_defs['tech_code'].tolist()
    
    # Header
    st.title("🔧 Asset Condition Monitoring Coverage Analysis")
    st.markdown("---")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Executive Summary", 
        "🔍 Gap Analysis", 
        "🎯 Asset Deep Dive",
        "🏢 Departmental View"
    ])
    
    # ==================== TAB 1: Executive Summary ====================
    with tab1:
        st.header("Executive Summary")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_assets = len(df)
        compliant_assets = (df['MASTER_JUDGE'] == 1).sum()
        gap_assets = (df['MASTER_JUDGE'] == 0).sum()
        compliance_rate = (compliant_assets / total_assets * 100) if total_assets > 0 else 0
        
        with col1:
            st.metric("Total Assets", f"{total_assets:,}")
        with col2:
            st.metric("Full Compliance", f"{compliant_assets:,}", 
                     delta=f"{compliance_rate:.1f}%", delta_color="normal")
        with col3:
            st.metric("Critical Gaps", f"{gap_assets:,}", 
                     delta=f"{(gap_assets/total_assets*100):.1f}%", delta_color="inverse")
        with col4:
            st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
        
        st.markdown("---")
        
        # Gap overview by technology
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Critical Gaps by Technology")
            gap_data = []
            for tech in tech_codes:
                judge_col = f'{tech}_JUDGE'
                if judge_col in df.columns:
                    gap_count = (df[judge_col] == 0).sum()
                    gap_data.append({'Technology': tech, 'Critical Gaps': gap_count})
            
            gap_df = pd.DataFrame(gap_data)
            gap_df = gap_df[gap_df['Critical Gaps'] > 0].sort_values('Critical Gaps', ascending=True)
            
            if len(gap_df) > 0:
                fig = px.bar(gap_df, x='Critical Gaps', y='Technology', 
                            orientation='h',
                            color='Critical Gaps',
                            color_continuous_scale='Reds')
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No critical gaps found!")
        
        with col2:
            st.subheader("Compliance by Department")
            dept_compliance = df.groupby('ASSET_DEPT')['MASTER_JUDGE'].agg(['sum', 'count'])
            dept_compliance['compliance_rate'] = (dept_compliance['sum'] / dept_compliance['count'] * 100)
            dept_compliance = dept_compliance.sort_values('compliance_rate', ascending=True).reset_index()
            
            fig = px.bar(dept_compliance, x='compliance_rate', y='ASSET_DEPT',
                        orientation='h',
                        color='compliance_rate',
                        color_continuous_scale='RdYlGn',
                        labels={'compliance_rate': 'Compliance Rate (%)', 'ASSET_DEPT': 'Department'})
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Department heatmap
        st.subheader("Department × Technology Coverage Heatmap")
        
        # Build heatmap data
        heatmap_data = []
        for dept in sorted(df['ASSET_DEPT'].dropna().astype(str).unique()):
            dept_df = df[df['ASSET_DEPT'] == dept]
            row = {'Department': dept}
            for tech in tech_codes:
                judge_col = f'{tech}_JUDGE'
                if judge_col in dept_df.columns:
                    compliance = (dept_df[judge_col] == 1).sum() / len(dept_df) * 100
                    row[tech] = compliance
            heatmap_data.append(row)
        
        heatmap_df = pd.DataFrame(heatmap_data).set_index('Department')
        
        fig = px.imshow(heatmap_df, 
                       labels=dict(x="Technology", y="Department", color="Compliance %"),
                       color_continuous_scale='RdYlGn',
                       aspect="auto")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # ==================== TAB 2: Gap Analysis ====================
    with tab2:
        st.header("Gap Analysis")
        
        # Sidebar filters
        with st.sidebar:
            st.subheader("Filters")
            
            # Department filter
            all_depts = ['All'] + sorted(df['ASSET_DEPT'].dropna().astype(str).unique().tolist())
            selected_dept = st.selectbox("Department", all_depts)
            
            # Technology filter
            all_techs = ['All'] + tech_codes
            selected_tech = st.selectbox("Technology", all_techs)
            
            # Gap filter
            gap_filter = st.radio("Show", ["All Assets", "Only Critical Gaps", "Only Compliant"])
            
            # Primary/Secondary toggle
            need_level = st.radio("Need Level", ["Primary Only", "Primary + Secondary"])
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_dept != 'All':
            filtered_df = filtered_df[filtered_df['ASSET_DEPT'] == selected_dept]
        
        if gap_filter == "Only Critical Gaps":
            filtered_df = filtered_df[filtered_df['MASTER_JUDGE'] == 0]
        elif gap_filter == "Only Compliant":
            filtered_df = filtered_df[filtered_df['MASTER_JUDGE'] == 1]
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filtered Assets", f"{len(filtered_df):,}")
        with col2:
            compliant = (filtered_df['MASTER_JUDGE'] == 1).sum()
            st.metric("Compliant", f"{compliant:,}")
        with col3:
            gaps = (filtered_df['MASTER_JUDGE'] == 0).sum()
            st.metric("Critical Gaps", f"{gaps:,}")
        
        st.markdown("---")
        
        # Technology-specific analysis
        if selected_tech != 'All':
            st.subheader(f"{selected_tech} Coverage Analysis")
            
            needs_col = f'NEEDS_{selected_tech}'
            has_col = f'HAS_{selected_tech}'
            judge_col = f'{selected_tech}_JUDGE'
            
            if all(col in filtered_df.columns for col in [needs_col, has_col, judge_col]):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Needs vs Has breakdown
                    breakdown = filtered_df.groupby([needs_col, has_col]).size().reset_index(name='count')
                    fig = px.sunburst(breakdown, path=[needs_col, has_col], values='count',
                                     title=f"{selected_tech}: Needs vs Has Breakdown")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Coverage pie
                    coverage_dist = filtered_df[judge_col].value_counts().reset_index()
                    coverage_dist.columns = ['Status', 'Count']
                    coverage_dist['Status'] = coverage_dist['Status'].map({1: 'Compliant', 0: 'Critical Gap'})
                    
                    fig = px.pie(coverage_dist, values='Count', names='Status',
                                color='Status',
                                color_discrete_map={'Compliant': '#2e7d32', 'Critical Gap': '#c62828'},
                                title=f"{selected_tech}: Coverage Status")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            # Multi-technology comparison
            st.subheader("Technology Comparison")
            
            tech_summary = []
            for tech in tech_codes:
                needs_col = f'NEEDS_{tech}'
                has_col = f'HAS_{tech}'
                judge_col = f'{tech}_JUDGE'
                
                if all(col in filtered_df.columns for col in [needs_col, has_col, judge_col]):
                    primary_need = (filtered_df[needs_col] == 'P').sum()
                    secondary_need = (filtered_df[needs_col] == 'S').sum()
                    has_coverage = (filtered_df[has_col] == 'Y').sum()
                    critical_gaps = (filtered_df[judge_col] == 0).sum()
                    
                    tech_summary.append({
                        'Technology': tech,
                        'Primary Needs': primary_need,
                        'Secondary Needs': secondary_need,
                        'Has Coverage': has_coverage,
                        'Critical Gaps': critical_gaps
                    })
            
            summary_df = pd.DataFrame(tech_summary)
            
            # Stacked bar chart
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Primary Needs', x=summary_df['Technology'], 
                                y=summary_df['Primary Needs'], marker_color='#1976d2'))
            fig.add_trace(go.Bar(name='Has Coverage', x=summary_df['Technology'], 
                                y=summary_df['Has Coverage'], marker_color='#2e7d32'))
            fig.add_trace(go.Bar(name='Critical Gaps', x=summary_df['Technology'], 
                                y=summary_df['Critical Gaps'], marker_color='#c62828'))
            
            fig.update_layout(barmode='group', title='Technology Coverage Summary', height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Asset table
        st.subheader("Asset Details")
        
        # Select columns to display
        display_cols = ['ASSETNUM', 'ASSET_DESC', 'ASSET_CLASS', 'ASSET_DEPT', 'MASTER_JUDGE']
        if selected_tech != 'All':
            display_cols.extend([f'NEEDS_{selected_tech}', f'HAS_{selected_tech}', f'{selected_tech}_JUDGE'])
        
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_cols].sort_values('MASTER_JUDGE'),
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name=f"acm_coverage_filtered_{selected_dept}_{selected_tech}.csv",
            mime="text/csv"
        )
    
    # ==================== TAB 3: Asset Deep Dive ====================
    with tab3:
        st.header("Asset Deep Dive")
        
        # Asset search
        col1, col2 = st.columns([2, 1])
        with col1:
            search_asset = st.text_input("Search by Asset Number", "")
        with col2:
            search_class = st.selectbox("Or filter by Asset Class", 
                                       ['All'] + sorted(df['ASSET_CLASS'].dropna().astype(str).unique().tolist()))
        
        # Filter assets
        if search_asset:
            asset_df = df[df['ASSETNUM'].str.contains(search_asset, case=False, na=False)]
        elif search_class != 'All':
            asset_df = df[df['ASSET_CLASS'] == search_class]
        else:
            asset_df = df.head(50)  # Show first 50 by default
        
        if len(asset_df) == 0:
            st.warning("No assets found matching your criteria.")
        else:
            st.info(f"Showing {len(asset_df)} asset(s)")
            
            # Asset selector
            selected_asset = st.selectbox("Select Asset", asset_df['ASSETNUM'].tolist())
            
            if selected_asset:
                asset_row = df[df['ASSETNUM'] == selected_asset].iloc[0]
                
                # Asset card
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Asset Number", asset_row['ASSETNUM'])
                with col2:
                    st.metric("Class", asset_row['ASSET_CLASS'])
                with col3:
                    st.metric("Department", asset_row['ASSET_DEPT'])
                with col4:
                    judge_status = "✅ Compliant" if asset_row['MASTER_JUDGE'] == 1 else "❌ Critical Gap"
                    st.metric("Status", judge_status)
                
                st.markdown(f"**Description:** {asset_row['ASSET_DESC']}")
                st.markdown("---")
                
                # Technology matrix
                st.subheader("Technology Coverage Matrix")
                
                matrix_data = []
                for tech in tech_codes:
                    needs_col = f'NEEDS_{tech}'
                    has_col = f'HAS_{tech}'
                    judge_col = f'{tech}_JUDGE'
                    
                    if all(col in asset_row.index for col in [needs_col, has_col, judge_col]):
                        needs = asset_row[needs_col]
                        has = asset_row[has_col]
                        judge = asset_row[judge_col]
                        
                        status = "✅ OK" if judge == 1 else "❌ GAP"
                        
                        matrix_data.append({
                            'Technology': tech,
                            'Needs': needs,
                            'Has': has,
                            'Status': status
                        })
                
                matrix_df = pd.DataFrame(matrix_data)
                
                # Color code the dataframe
                def color_status(val):
                    if val == '✅ OK':
                        return 'background-color: #c8e6c9'
                    elif val == '❌ GAP':
                        return 'background-color: #ffcdd2'
                    return ''
                
                styled_df = matrix_df.style.applymap(color_status, subset=['Status'])
                st.dataframe(styled_df, use_container_width=True)
    
    # ==================== TAB 4: Departmental View ====================
    with tab4:
        st.header("Departmental View")
        
        # Department selector
        selected_dept_view = st.selectbox("Select Department", 
                                         sorted(df['ASSET_DEPT'].dropna().astype(str).unique().tolist()))
        
        dept_df = df[df['ASSET_DEPT'] == selected_dept_view]
        
        # Department scorecard
        st.subheader(f"{selected_dept_view} Scorecard")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Assets", f"{len(dept_df):,}")
        with col2:
            compliant = (dept_df['MASTER_JUDGE'] == 1).sum()
            st.metric("Compliant Assets", f"{compliant:,}")
        with col3:
            gaps = (dept_df['MASTER_JUDGE'] == 0).sum()
            st.metric("Critical Gaps", f"{gaps:,}")
        with col4:
            rate = (compliant / len(dept_df) * 100) if len(dept_df) > 0 else 0
            st.metric("Compliance Rate", f"{rate:.1f}%")
        
        st.markdown("---")
        
        # Technology breakdown with compliance overlay
        st.subheader("Technology Needs vs Compliance Rate")

        # Calculate needs and compliance by technology
        tech_analysis = []
        for tech in tech_codes:
            needs_col = f'NEEDS_{tech}'
            judge_col = f'{tech}_JUDGE'
            
            if needs_col in dept_df.columns and judge_col in dept_df.columns:
                # Count primary needs
                primary_needs = (dept_df[needs_col] == 'P').sum()
                # Calculate compliance rate for this technology
                compliant = (dept_df[judge_col] == 1).sum()
                total = len(dept_df)
                compliance_rate = (compliant / total * 100) if total > 0 else 0
                
                # Get domain name from tech_defs
                domain = tech_defs[tech_defs['tech_code'] == tech]['domain'].values[0] if len(tech_defs[tech_defs['tech_code'] == tech]) > 0 else tech
                
                tech_analysis.append({
                    'Technology': tech,
                    'Domain': domain,
                    'Primary Needs': primary_needs,
                    'Compliance Rate': compliance_rate
                })

        tech_df = pd.DataFrame(tech_analysis)

        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add bar chart (needs)
        fig.add_trace(
            go.Bar(name='Primary Needs', x=tech_df['Domain'], y=tech_df['Primary Needs'],
                marker_color='#1976d2'),
            secondary_y=False,
        )

        # Add line chart (compliance rate)
        fig.add_trace(
            go.Scatter(name='Compliance Rate', x=tech_df['Domain'], y=tech_df['Compliance Rate'],
                    mode='lines+markers', marker=dict(size=10), line=dict(color='#c62828', width=3)),
            secondary_y=True,
        )

        # Set axis titles
        fig.update_xaxes(title_text="Technology", tickangle=-45)
        fig.update_yaxes(title_text="Number of Assets with Primary Needs", secondary_y=False)
        fig.update_yaxes(title_text="Compliance Rate (%)", secondary_y=True)

        fig.update_layout(height=500, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
        
        # Prioritized gap list
        st.subheader("Prioritized Gap List (Primary Needs Not Met)")
        
        gap_list = []
        for _, row in dept_df[dept_df['MASTER_JUDGE'] == 0].iterrows():
            asset_gaps = []
            for tech in tech_codes:
                needs_col = f'NEEDS_{tech}'
                has_col = f'HAS_{tech}'
                if needs_col in row.index and has_col in row.index:
                    if row[needs_col] == 'P' and row[has_col] == 'N':
                        asset_gaps.append(tech)
            
            if asset_gaps:
                gap_list.append({
                    'ASSETNUM': row['ASSETNUM'],
                    'ASSET_DESC': row['ASSET_DESC'],
                    'ASSET_CLASS': row['ASSET_CLASS'],
                    'Missing Technologies': ', '.join(asset_gaps),
                    'Gap Count': len(asset_gaps)
                })
        
        if gap_list:
            gap_df = pd.DataFrame(gap_list).sort_values('Gap Count', ascending=False)
            st.dataframe(gap_df, use_container_width=True, height=400)
            
            # Download button
            csv = gap_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Gap List (CSV)",
                data=csv,
                file_name=f"acm_gaps_{selected_dept_view}.csv",
                mime="text/csv"
            )
        else:
            st.success("✅ No critical gaps in this department!")

if __name__ == "__main__":
    main()
