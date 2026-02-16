#!/usr/bin/env python3
"""Convert cross-tab config files to normalized relational structure."""

import pandas as pd
import os

def convert_crosstabs_to_normalized(comp_tech_file, class_comp_file, output_dir='normalized_config'):
    """Convert cross-tab files to normalized tables."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Read cross-tab files
    comp_tech_df = pd.read_csv(comp_tech_file)
    class_comp_df = pd.read_csv(class_comp_file)
    
    # 1. Components table
    components_list = comp_tech_df.iloc[:, 0].unique()
    components_df = pd.DataFrame({
        'component_id': range(1, len(components_list) + 1),
        'component_name': components_list
    })
    comp_name_to_id = dict(zip(components_df['component_name'], components_df['component_id']))
    
    # 2. Technologies table
    tech_codes = comp_tech_df.columns[1:].tolist()
    technologies_df = pd.DataFrame({
        'technology_id': range(1, len(tech_codes) + 1),
        'technology_code': tech_codes
    })
    tech_code_to_id = dict(zip(technologies_df['technology_code'], technologies_df['technology_id']))
    
    # 3. Classes table
    class_names = class_comp_df.iloc[:, 0].unique()
    classes_df = pd.DataFrame({
        'class_id': range(1, len(class_names) + 1),
        'class_name': class_names
    })
    class_name_to_id = dict(zip(classes_df['class_name'], classes_df['class_id']))
    
    # 4. Component-Technology junction
    comp_tech_records = []
    for idx, row in comp_tech_df.iterrows():
        component_name = row.iloc[0]
        component_id = comp_name_to_id[component_name]
        
        for tech_code in tech_codes:
            value = row[tech_code]
            
            # Only record if there's a value (S or P), skip dashes and empty
            if pd.notna(value):
                value_str = str(value).strip()
                # Only process if it's 'S' or 'P', skip dashes and empty strings
                if value_str.upper() in ['S', 'P']:
                    application_type = 'Secondary' if value_str.upper() == 'S' else 'Primary'
                    
                    comp_tech_records.append({
                        'component_id': component_id,
                        'technology_id': tech_code_to_id[tech_code],
                        'technology_code': tech_code,
                        'application_type': application_type
                    })
    
    component_technology_df = pd.DataFrame(comp_tech_records)
    
    # 5. Class-Component junction
    class_comp_records = []
    component_columns = class_comp_df.columns[1:].tolist()
    
    for idx, row in class_comp_df.iterrows():
        class_name = row.iloc[0]
        class_id = class_name_to_id[class_name]
        
        for comp_name in component_columns:
            value = row[comp_name]
            if pd.notna(value) and str(value).strip().upper() == 'X':
                if comp_name in comp_name_to_id:
                    class_comp_records.append({
                        'class_id': class_id,
                        'component_id': comp_name_to_id[comp_name]
                    })
    
    class_component_df = pd.DataFrame(class_comp_records)
    
    # Save all files
    components_df.to_csv(f'{output_dir}/components.csv', index=False)
    technologies_df.to_csv(f'{output_dir}/technologies.csv', index=False)
    classes_df.to_csv(f'{output_dir}/classes.csv', index=False)
    component_technology_df.to_csv(f'{output_dir}/component_technology.csv', index=False)
    class_component_df.to_csv(f'{output_dir}/class_component.csv', index=False)
    
    print(f"✓ Converted to normalized format in {output_dir}/")
    print(f"  - {len(components_df)} components")
    print(f"  - {len(technologies_df)} technologies")
    print(f"  - {len(classes_df)} classes")
    print(f"  - {len(component_technology_df)} component-technology relationships")
    print(f"  - {len(class_component_df)} class-component relationships")
    
    return {
        'components': components_df,
        'technologies': technologies_df,
        'classes': classes_df,
        'component_technology': component_technology_df,
        'class_component': class_component_df
    }

if __name__ == '__main__':
    convert_crosstabs_to_normalized(
        'comp_xref_tech.csv',
        'class_xref_comp.csv',
        'normalized_config'
    )