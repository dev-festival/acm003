"""
ACM Configuration Dashboard
Visualize asset class configurations, components, and technology assignments
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add current directory for imports
sys.path.append(str(Path(__file__).parent))
from acm_config import ACMConfig

# Page configuration
st.set_page_config(
    page_title="ACM Configuration Dashboard",
    page_icon="⚙️",
    layout="wide"
)

# Styling
st.markdown("""
    <style>
    /* Make table text bigger */
    .stDataFrame {
        font-size: 16px;
    }
    
    /* Style dataframe cells */
    div[data-testid="stDataFrame"] table {
        font-size: 16px;
    }
    
    div[data-testid="stDataFrame"] th {
        font-size: 18px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize configuration
@st.cache_resource
def load_config():
    """Load the ACM configuration (cached)"""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    config_dir = Path('data/st_tbl/normalized_config')
    
    if not config_dir.exists():
        st.error(f"⚠️ Configuration directory not found at: {config_dir}")
        st.error("Please run `convert_config.py` first to generate the normalized configuration.")
        st.stop()
    
    return ACMConfig(str(config_dir))

try:
    config = load_config()
except Exception as e:
    st.error(f"⚠️ Error loading configuration: {str(e)}")
    st.error(f"Current working directory: {Path.cwd()}")
    st.error(f"Script directory: {Path(__file__).parent}")
    st.stop()

# Header
st.title("⚙️ Asset Condition Monitoring Configuration")
st.markdown("---")

# Asset Class selector in main content (no sidebar)
asset_classes = sorted(config.classes['class_name'].tolist())

# Custom CSS for grey background selector
st.markdown("""
    <style>
    div[data-baseweb="select"] > div {
        background-color: #f0f2f6;
    }
    </style>
""", unsafe_allow_html=True)

# Create columns for inline layout
col1, col2 = st.columns([1, 4])

with col1:
    st.markdown("### 📊 Asset Class:")

with col2:
    selected_class = st.selectbox(
        "Asset Class",
        options=asset_classes,
        index=0,
        label_visibility="collapsed"
    )

st.markdown("---")

# Main content
if selected_class:
    
    components_in_class = config.get_class_components(selected_class)
    
    st.subheader(f"Components ({len(components_in_class)})")
    
    if components_in_class:
        # Display as badge grid
        cols = st.columns(5)
        for idx, component in enumerate(sorted(components_in_class)):
            with cols[idx % 5]:
                st.markdown(f"🔧 **{component}**")
    else:
        st.info("No components assigned to this asset class.")
    
    st.markdown("---")
    
    # Get technology assignments
    tech_assignments = config.get_class_technologies(selected_class)
    
    st.subheader(f"Technology Assignments")
    
    st.subheader(f"Technology Assignments")

    if not tech_assignments.empty:
        
        st.markdown("**Primary (P)** and **Secondary (S)** technology applications:")
        
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
                return 'background-color: #90EE90; color: black; font-weight: bold; font-size: 16px;'
            elif val == 'S':
                return 'background-color: #FFD700; color: black; font-weight: bold; font-size: 16px;'
            else:
                return 'font-size: 16px;'
        
        styled_df = pivot_df.style.applymap(
            style_ps_values,
            subset=[col for col in pivot_df.columns if col != 'Component']
        ).set_properties(**{
            'font-size': '16px',
            'text-align': 'center'
        }, subset=[col for col in pivot_df.columns if col != 'Component'])
        
        # Display styled dataframe
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        
        # Component detail dropdown
        st.subheader("Component Detail View")
        
        selected_component = st.selectbox(
            "Select a component for detailed view",
            options=sorted(components_in_class)
        )
        
        if selected_component:
            component_techs = config.get_component_technologies(selected_component)
            
            detail_df = component_techs.copy()
            detail_df.columns = ['Technology', 'Application Type']
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown(f"### {selected_component}")
                st.metric("Technologies", len(detail_df))
                
                primary_count = (detail_df['Application Type'] == 'Primary').sum()
                secondary_count = (detail_df['Application Type'] == 'Secondary').sum()
                
                st.metric("Primary", primary_count)
                st.metric("Secondary", secondary_count)
            
            with col2:
                st.markdown("### Technology Details")
                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    hide_index=True
                )
        
        st.markdown("---")
        
        # Download tables
        st.subheader("📥 Download Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Technology Assignment Matrix**")
            st.dataframe(pivot_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("**Detailed Technology List**")
            detail_export = tech_assignments.copy()
            detail_export.columns = ['Component', 'Technology', 'Application Type']
            st.dataframe(detail_export, use_container_width=True, hide_index=True)
    
    else:
        st.info("No technology assignments for this class.")

# Footer
st.markdown("---")
st.caption("ACM Configuration Dashboard | Honda Manufacturing of Alabama")