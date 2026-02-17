"""
ACM Coverage Dashboard
Visualize coverage metrics by department, class, and asset
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add the directory containing acm_config.py to Python path
sys.path.insert(0, 'data/st_tbl')

# Page configuration
st.set_page_config(
    page_title="ACM Coverage Dashboard",
    page_icon="📊",
    layout="wide"
)

# Load coverage report
@st.cache_data
def load_coverage_data():
    """Load the coverage report"""
    return pd.read_pickle('data/coverage_report.pkl')

try:
    coverage_data = load_coverage_data()
except FileNotFoundError:
    st.error("⚠️ Coverage report not found at 'output/coverage_report.csv'")
    st.info("Please run your QMD analysis first to generate the coverage report.")
    st.stop()

from acm_config import ACMConfig

@st.cache_resource
def load_acm_config():
    """Load the ACM configuration"""
    return ACMConfig('data/st_tbl/normalized_config')

config = load_acm_config()

# Get technology codes from judge columns
tech_codes = [col.replace('_judge', '').upper() 
              for col in coverage_data.columns if col.endswith('_judge')]

# Header
st.title("📊 ACM Coverage Dashboard")
st.markdown("---")

# ====================
# SECTION 1: Department Selector & Overview with Filters
# ====================

st.header("Department Coverage Overview")

# Sidebar for filtering departments from top chart
with st.sidebar:
    st.header("Chart Filters")
    
    all_departments = sorted(coverage_data['ASSET_DEPT'].unique())
    
    st.markdown("### Departments to Display")
    st.caption("Uncheck departments to hide from the overview chart")
    
    # Multi-select for departments to include in top chart
    departments_to_show = st.multiselect(
        "Select departments to display",
        options=all_departments,
        default=all_departments,
        label_visibility="collapsed"
    )
    
    # Quick select/deselect all buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Select All"):
            st.session_state.departments_to_show = all_departments
            st.rerun()
    with col2:
        if st.button("Deselect All"):
            st.session_state.departments_to_show = []
            st.rerun()

# Department selector for detail views
selected_dept = st.selectbox(
    "Select Department for Detail View",
    options=all_departments
)

st.markdown("---")

# Calculate department-level metrics for FILTERED departments
dept_metrics = []

for dept in departments_to_show:
    dept_data_temp = coverage_data[coverage_data['ASSET_DEPT'] == dept]
    
    # Classify each asset
    def classify_asset(row):
        judgments = [row[f'{tech.lower()}_judge'] for tech in tech_codes]
        if 'R' in judgments:
            return 'RED'
        if 'G' in judgments:
            return 'GREEN'
        if 'Y' in judgments:
            return 'YELLOW'
        return 'N'
    
    dept_data_temp['overall_status'] = dept_data_temp.apply(classify_asset, axis=1)
    
    # Count status distribution
    total_red = (dept_data_temp['overall_status'] == 'RED').sum()
    total_green = (dept_data_temp['overall_status'] == 'GREEN').sum()
    total_yellow = (dept_data_temp['overall_status'] == 'YELLOW').sum()
    total_na = (dept_data_temp['overall_status'] == 'N').sum()
    
    dept_metrics.append({
        'Department': dept,
        'RED': total_red,
        'GREEN': total_green,
        'YELLOW': total_yellow,
        'N': total_na,
    })

dept_metrics_df = pd.DataFrame(dept_metrics)

# Add sorting options with color-based ordering
col1, col2 = st.columns([3, 1])

with col1:
    sort_by = st.radio(
        "Sort departments by:",
        options=['RED (Critical Gap)', 'GREEN (Covered)', 'YELLOW (Over-monitored)', 'N (Not Applicable)'],
        horizontal=True
    )

with col2:
    sort_order = st.radio(
        "Order:",
        options=['Max → Min', 'Min → Max'],
        horizontal=True
    )

# Map display name to column
sort_map = {
    'RED (Critical Gap)': 'RED',
    'GREEN (Covered)': 'GREEN',
    'YELLOW (Over-monitored)': 'YELLOW',
    'N (Not Applicable)': 'N'
}

# Sort based on selection
ascending = (sort_order == 'Min → Max')
dept_metrics_df = dept_metrics_df.sort_values(sort_map[sort_by], ascending=ascending)

# Create stacked bar chart for filtered departments
if not dept_metrics_df.empty:
    fig_dept = go.Figure()

    fig_dept.add_trace(go.Bar(
        name='RED (Critical Gap)',
        x=dept_metrics_df['Department'],
        y=dept_metrics_df['RED'],
        marker_color='#FF6B6B'
    ))

    fig_dept.add_trace(go.Bar(
        name='GREEN (Covered)',
        x=dept_metrics_df['Department'],
        y=dept_metrics_df['GREEN'],
        marker_color='#90EE90'
    ))

    fig_dept.add_trace(go.Bar(
        name='YELLOW (Over-monitored)',
        x=dept_metrics_df['Department'],
        y=dept_metrics_df['YELLOW'],
        marker_color='#FFA500'
    ))

    fig_dept.add_trace(go.Bar(
        name='N (Not Applicable)',
        x=dept_metrics_df['Department'],
        y=dept_metrics_df['N'],
        marker_color='#808080'
    ))

    fig_dept.update_layout(
        barmode='stack',
        title=f'Coverage Status by Department ({len(departments_to_show)} departments shown)',
        xaxis_title='Department',
        yaxis_title='Count',
        height=400,
        showlegend=True
    )

    st.plotly_chart(fig_dept, use_container_width=True)
else:
    st.warning("⚠️ No departments selected. Please select at least one department from the sidebar.")

st.markdown("---")

# ====================
# SECTION 2: Selected Department Pie Chart
# ====================

# Department selector
selected_dept = st.selectbox(
    "Select Department",
    options=sorted(coverage_data['ASSET_DEPT'].unique())
)

st.subheader(f"Department: {selected_dept}")

dept_data = coverage_data[coverage_data['ASSET_DEPT'] == selected_dept]
st.markdown(f"**{len(dept_data):,} assets** in this department")

# Classify each asset into ONE category based on overall status
def classify_asset(row):
    """Classify asset based on all its technology judgments"""
    judgments = [row[f'{tech.lower()}_judge'] for tech in tech_codes]
    
    # If ANY red → Critical Gap
    if 'R' in judgments:
        return 'RED'
    
    # If ANY green (and no red) → Covered
    if 'G' in judgments:
        return 'GREEN'
    
    # If ANY yellow (and no red/green) → Partially Montiored
    if 'Y' in judgments:
        return 'YELLOW'
    
    # If ALL N → Not Applicable
    return 'N'

dept_data['overall_status'] = dept_data.apply(classify_asset, axis=1)

# Count assets in each category
dept_red = (dept_data['overall_status'] == 'RED').sum()
dept_green = (dept_data['overall_status'] == 'GREEN').sum()
dept_yellow = (dept_data['overall_status'] == 'YELLOW').sum()
dept_na = (dept_data['overall_status'] == 'N').sum()

# Create pie chart for selected department
labels = []
values = []
colors = []

if dept_red > 0:
    labels.append(f"RED (Critical Gap): {dept_red}")
    values.append(dept_red)
    colors.append('#FF6B6B')

if dept_green > 0:
    labels.append(f"GREEN (Covered): {dept_green}")
    values.append(dept_green)
    colors.append('#90EE90')

if dept_yellow > 0:
    labels.append(f"YELLOW (Partial Monitoring): {dept_yellow}")
    values.append(dept_yellow)
    colors.append('#FFA500')

if dept_na > 0:
    labels.append(f"N (Not Applicable): {dept_na}")
    values.append(dept_na)
    colors.append('#808080')

fig_dept_pie = go.Figure(data=[go.Pie(
    labels=labels,
    values=values,
    marker=dict(colors=colors),
    hole=0.4,
    textinfo='label+percent',
    textposition='outside'
)])

fig_dept_pie.update_layout(
    title=f'{selected_dept} - Overall Coverage Status',
    height=500,
    showlegend=False
)

st.plotly_chart(fig_dept_pie, use_container_width=True)

st.markdown("---")

# ====================
# SECTION 3: Asset Class 4-Block Breakdown
# ====================

st.header("Asset Class Breakdown")

# Calculate asset class metrics for the selected department
class_status_metrics = []

for asset_class in dept_data['ASSET_CLASS'].dropna().unique():
    class_data = dept_data[dept_data['ASSET_CLASS'] == asset_class]
    
    # Count assets in each status for this class
    red_count = (class_data['overall_status'] == 'RED').sum()
    green_count = (class_data['overall_status'] == 'GREEN').sum()
    yellow_count = (class_data['overall_status'] == 'YELLOW').sum()
    na_count = (class_data['overall_status'] == 'N').sum()
    
    class_status_metrics.append({
        'Asset_Class': asset_class,
        'RED': red_count,
        'GREEN': green_count,
        'YELLOW': yellow_count,
        'N': na_count,
        'Total': len(class_data)
    })

class_metrics_df = pd.DataFrame(class_status_metrics)

# Create 2x2 grid for 4-block view
col1, col2 = st.columns(2)

with col1:
    # Critical Gap (RED) - Top 10 asset classes
    st.markdown("### Critical Gap")
    
    top_red = class_metrics_df.nlargest(10, 'RED')
    
    if not top_red.empty and top_red['RED'].sum() > 0:
        fig_red = go.Figure(data=[go.Bar(
            x=top_red['Asset_Class'],
            y=top_red['RED'],
            marker_color='#FF6B6B',
            marker_line_color='darkred',
            marker_line_width=2,
            text=top_red['RED'],
            textposition='outside'
        )])
        
        fig_red.update_layout(
            height=350,
            showlegend=False,
            xaxis_title='Asset Class',
            yaxis_title='Assets',
            margin=dict(t=20, b=100, l=40, r=20),
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig_red, use_container_width=True)
    else:
        st.success("No critical gaps! ✓")

with col2:
    # Covered (GREEN) - Top 10 asset classes
    st.markdown("### Covered")
    
    top_green = class_metrics_df.nlargest(10, 'GREEN')
    
    if not top_green.empty and top_green['GREEN'].sum() > 0:
        fig_green = go.Figure(data=[go.Bar(
            x=top_green['Asset_Class'],
            y=top_green['GREEN'],
            marker_color='#90EE90',
            marker_line_color='darkgreen',
            marker_line_width=2,
            text=top_green['GREEN'],
            textposition='outside'
        )])
        
        fig_green.update_layout(
            height=350,
            showlegend=False,
            xaxis_title='Asset Class',
            yaxis_title='Assets',
            margin=dict(t=20, b=100, l=40, r=20),
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig_green, use_container_width=True)
    else:
        st.info("No coverage")

col3, col4 = st.columns(2)

with col3:
    # Over-Monitored (YELLOW) - Top 10 asset classes
    st.markdown("### Partially Monitored")
    
    top_yellow = class_metrics_df.nlargest(10, 'YELLOW')
    
    if not top_yellow.empty and top_yellow['YELLOW'].sum() > 0:
        fig_yellow = go.Figure(data=[go.Bar(
            x=top_yellow['Asset_Class'],
            y=top_yellow['YELLOW'],
            marker_color='#FFA500',
            marker_line_color='darkorange',
            marker_line_width=2,
            text=top_yellow['YELLOW'],
            textposition='outside'
        )])
        
        fig_yellow.update_layout(
            height=350,
            showlegend=False,
            xaxis_title='Asset Class',
            yaxis_title='Assets',
            margin=dict(t=20, b=100, l=40, r=20),
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig_yellow, use_container_width=True)
    else:
        st.info("None")

with col4:
    # Not Applicable (N) - Top 10 asset classes
    st.markdown("### Not Applicable")
    
    top_na = class_metrics_df.nlargest(10, 'N')
    
    if not top_na.empty and top_na['N'].sum() > 0:
        fig_na = go.Figure(data=[go.Bar(
            x=top_na['Asset_Class'],
            y=top_na['N'],
            marker_color='#808080',
            marker_line_color='#404040',
            marker_line_width=2,
            text=top_na['N'],
            textposition='outside'
        )])
        
        fig_na.update_layout(
            height=350,
            showlegend=False,
            xaxis_title='Asset Class',
            yaxis_title='Assets',
            margin=dict(t=20, b=100, l=40, r=20),
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig_na, use_container_width=True)
    else:
        st.info("None")

st.markdown("---")


# ====================
# SECTION 4: Asset Detail Table by Class
# ====================

st.header("Asset Detail View")

# Get list of asset classes in selected department
asset_classes_in_dept = sorted(dept_data['ASSET_CLASS'].dropna().unique())

# Asset class selector
selected_class = st.selectbox(
    "Select Asset Class for Detail View",
    options=asset_classes_in_dept
)

if selected_class:
     
    with st.expander("📋 Technology Requirements Reference (from Configuration)", expanded=True):
        st.markdown(f"**Expected monitoring for {selected_class} based on configuration**")
        
        # Get technology assignments for this class from config
        tech_assignments = config.get_class_technologies(selected_class)
        
        if not tech_assignments.empty:
            # Create matrix view
            pivot_df = tech_assignments.pivot_table(
                index='component_name',
                columns='technology_code',
                values='application_type',
                aggfunc='first'
            ).fillna('')
            
            # Map to P/S
            pivot_df = pivot_df.applymap(lambda x: 'P' if x == 'Primary' else 'S' if x == 'Secondary' else '')
            pivot_df = pivot_df.reset_index()
            pivot_df.columns.name = None
            pivot_df = pivot_df.rename(columns={'component_name': 'Component'})
            
            # Style the dataframe with colors
            def style_ps_values(val):
                if val == 'P':
                    return 'background-color: #90EE90; color: black; font-weight: bold; font-size: 14px;'
                elif val == 'S':
                    return 'background-color: #FFD700; color: black; font-weight: bold; font-size: 14px;'
                else:
                    return 'font-size: 14px;'
            
            styled_df = pivot_df.style.applymap(
                style_ps_values,
                subset=[col for col in pivot_df.columns if col != 'Component']
            ).set_properties(**{
                'font-size': '14px',
                'text-align': 'center'
            }, subset=[col for col in pivot_df.columns if col != 'Component'])
            
            # Display styled dataframe
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True
            )
            
            st.caption("P = Primary (NEEDS monitoring) | S = Secondary (CAN USE for monitoring)")
        else:
            st.info("No technology requirements configured for this asset class.")
    
    st.markdown("---")

    class_assets = dept_data[dept_data['ASSET_CLASS'] == selected_class].copy()
    
    st.subheader(f"Assets in {selected_class}")
    st.markdown(f"**{len(class_assets)} assets**")
    
    # Build display table with colored status boxes
    display_cols = ['ASSETNUM', 'ASSET_DESC'] + [f'{tech.lower()}_judge' for tech in tech_codes]
    
    asset_display = class_assets[display_cols].copy()
    
    # Rename judge columns to just tech codes
    rename_dict = {f'{tech.lower()}_judge': tech for tech in tech_codes}
    asset_display = asset_display.rename(columns=rename_dict)
    
    # Style the dataframe
    def color_judgment(val):
        if val == 'G':
            return 'background-color: #90EE90; color: black; font-weight: bold;'
        elif val == 'R':
            return 'background-color: #FF6B6B; color: white; font-weight: bold;'
        elif val == 'Y':
            return 'background-color: #FFA500; color: black; font-weight: bold;'
        else:  # N
            return 'background-color: #808080; color: white;'
    
    styled_asset_display = asset_display.style.applymap(
        color_judgment,
        subset=tech_codes
    ).set_properties(**{
        'text-align': 'center',
        'font-size': '14px'
    }, subset=tech_codes)
    
    st.dataframe(
        styled_asset_display,
        use_container_width=True,
        hide_index=True,
        height=600
    )

# Footer
st.markdown("---")
st.caption("ACM Coverage Dashboard | Honda Manufacturing of Alabama")