"""ACM Configuration Manager - Query and manage normalized config data."""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional

class ACMConfig:
    """Manager for Asset Condition Monitoring configuration data."""
    
    def __init__(self, config_dir='normalized_config'):
        """Load all configuration tables."""
        self.config_dir = Path(config_dir)
        
        self.components = pd.read_csv(self.config_dir / 'components.csv')
        self.technologies = pd.read_csv(self.config_dir / 'technologies.csv')
        self.classes = pd.read_csv(self.config_dir / 'classes.csv')
        self.component_technology = pd.read_csv(self.config_dir / 'component_technology.csv')
        self.class_component = pd.read_csv(self.config_dir / 'class_component.csv')
        
        print(f"✓ Loaded ACM configuration from {config_dir}")
    
    # ===== Component Queries =====
    
    def get_component_technologies(self, component_name: str) -> pd.DataFrame:
        """Get all technologies applicable to a component."""
        comp_id = self.components[
            self.components['component_name'] == component_name
        ]['component_id'].values[0]
        
        return self.component_technology[
            self.component_technology['component_id'] == comp_id
        ][['technology_code', 'application_type']]
    
    def get_component_classes(self, component_name: str) -> List[str]:
        """Get all asset classes that include this component."""
        comp_id = self.components[
            self.components['component_name'] == component_name
        ]['component_id'].values[0]
        
        class_ids = self.class_component[
            self.class_component['component_id'] == comp_id
        ]['class_id'].values
        
        return self.classes[
            self.classes['class_id'].isin(class_ids)
        ]['class_name'].tolist()
    
    # ===== Technology Queries =====
    
    def get_technology_components(self, tech_code: str, 
                                  application_type: Optional[str] = None) -> pd.DataFrame:
        """Get all components monitored by a technology."""
        tech_id = self.technologies[
            self.technologies['technology_code'] == tech_code
        ]['technology_id'].values[0]
        
        result = self.component_technology[
            self.component_technology['technology_id'] == tech_id
        ]
        
        if application_type:
            result = result[result['application_type'] == application_type]
        
        # Join with component names
        return result.merge(
            self.components[['component_id', 'component_name']],
            on='component_id'
        )[['component_name', 'application_type']]
    
    # ===== Class Queries =====
    
    def get_class_components(self, class_name: str) -> List[str]:
        """Get all components in an asset class."""
        class_id = self.classes[
            self.classes['class_name'] == class_name
        ]['class_id'].values[0]
        
        comp_ids = self.class_component[
            self.class_component['class_id'] == class_id
        ]['component_id'].values
        
        return self.components[
            self.components['component_id'].isin(comp_ids)
        ]['component_name'].tolist()
    
    def get_class_technologies(self, class_name: str) -> pd.DataFrame:
        """Get all technologies applicable to an asset class."""
        components = self.get_class_components(class_name)
        
        comp_ids = self.components[
            self.components['component_name'].isin(components)
        ]['component_id'].values
        
        techs = self.component_technology[
            self.component_technology['component_id'].isin(comp_ids)
        ].merge(
            self.components[['component_id', 'component_name']],
            on='component_id'
        )[['component_name', 'technology_code', 'application_type']]
        
        return techs.sort_values(['component_name', 'technology_code'])
    
    # ===== Add/Update Operations =====
    
    def add_component(self, component_name: str):
        """Add a new component."""
        if component_name in self.components['component_name'].values:
            print(f"Component '{component_name}' already exists")
            return
        
        new_id = self.components['component_id'].max() + 1
        new_row = pd.DataFrame({
            'component_id': [new_id],
            'component_name': [component_name]
        })
        self.components = pd.concat([self.components, new_row], ignore_index=True)
        self.save_components()
        print(f"✓ Added component: {component_name}")
    
    def add_technology(self, tech_code: str):
        """Add a new technology."""
        if tech_code in self.technologies['technology_code'].values:
            print(f"Technology '{tech_code}' already exists")
            return
        
        new_id = self.technologies['technology_id'].max() + 1
        new_row = pd.DataFrame({
            'technology_id': [new_id],
            'technology_code': [tech_code]
        })
        self.technologies = pd.concat([self.technologies, new_row], ignore_index=True)
        self.save_technologies()
        print(f"✓ Added technology: {tech_code}")
    
    def assign_technology_to_component(self, component_name: str, tech_code: str, 
                                      application_type: str = 'Primary'):
        """Assign a technology to a component."""
        comp_id = self.components[
            self.components['component_name'] == component_name
        ]['component_id'].values[0]
        
        tech_id = self.technologies[
            self.technologies['technology_code'] == tech_code
        ]['technology_id'].values[0]
        
        # Check if already exists
        exists = ((self.component_technology['component_id'] == comp_id) & 
                 (self.component_technology['technology_id'] == tech_id)).any()
        
        if exists:
            print(f"Assignment already exists: {component_name} - {tech_code}")
            return
        
        new_row = pd.DataFrame({
            'component_id': [comp_id],
            'technology_id': [tech_id],
            'technology_code': [tech_code],
            'application_type': [application_type]
        })
        self.component_technology = pd.concat([self.component_technology, new_row], ignore_index=True)
        self.save_component_technology()
        print(f"✓ Assigned {tech_code} ({application_type}) to {component_name}")
    
    def assign_component_to_class(self, class_name: str, component_name: str):
        """Assign a component to an asset class."""
        class_id = self.classes[
            self.classes['class_name'] == class_name
        ]['class_id'].values[0]
        
        comp_id = self.components[
            self.components['component_name'] == component_name
        ]['component_id'].values[0]
        
        # Check if already exists
        exists = ((self.class_component['class_id'] == class_id) & 
                 (self.class_component['component_id'] == comp_id)).any()
        
        if exists:
            print(f"Assignment already exists: {class_name} - {component_name}")
            return
        
        new_row = pd.DataFrame({
            'class_id': [class_id],
            'component_id': [comp_id]
        })
        self.class_component = pd.concat([self.class_component, new_row], ignore_index=True)
        self.save_class_component()
        print(f"✓ Assigned {component_name} to {class_name}")
    
    # ===== Save Operations =====
    
    def save_all(self):
        """Save all configuration files."""
        self.save_components()
        self.save_technologies()
        self.save_classes()
        self.save_component_technology()
        self.save_class_component()
        print("✓ Saved all configuration files")
    
    def save_components(self):
        self.components.to_csv(self.config_dir / 'components.csv', index=False)
    
    def save_technologies(self):
        self.technologies.to_csv(self.config_dir / 'technologies.csv', index=False)
    
    def save_classes(self):
        self.classes.to_csv(self.config_dir / 'classes.csv', index=False)
    
    def save_component_technology(self):
        self.component_technology.to_csv(self.config_dir / 'component_technology.csv', index=False)
    
    def save_class_component(self):
        self.class_component.to_csv(self.config_dir / 'class_component.csv', index=False)
    
    # ===== Export to Cross-tabs (for backwards compatibility) =====
    
    def export_comp_xref_tech(self, output_file='comp_xref_tech_export.csv'):
        """Export to original comp_xref_tech format."""
        # Pivot component_technology to cross-tab format
        pivot = self.component_technology.pivot_table(
            index='component_id',
            columns='technology_code',
            values='application_type',
            aggfunc='first'
        )
        
        # Map application type to S/P
        pivot = pivot.applymap(lambda x: 'S' if x == 'Secondary' else 'P' if x == 'Primary' else '')
        
        # Add component names
        pivot = pivot.merge(
            self.components[['component_id', 'component_name']],
            left_index=True,
            right_on='component_id'
        )
        
        # Reorder columns
        cols = ['component_name'] + [c for c in pivot.columns if c not in ['component_id', 'component_name']]
        result = pivot[cols]
        result = result.set_index('component_name').reset_index()
        
        result.to_csv(output_file, index=False)
        print(f"✓ Exported to {output_file}")
        return result
    
    def export_class_xref_comp(self, output_file='class_xref_comp_export.csv'):
        """Export to original class_xref_comp format."""
        # Get all unique components
        all_components = self.components['component_name'].tolist()
        
        # Create rows for each class
        rows = []
        for _, class_row in self.classes.iterrows():
            class_id = class_row['class_id']
            class_name = class_row['class_name']
            
            # Get components in this class
            comp_ids_in_class = self.class_component[
                self.class_component['class_id'] == class_id
            ]['component_id'].values
            
            components_in_class = self.components[
                self.components['component_id'].isin(comp_ids_in_class)
            ]['component_name'].tolist()
            
            # Build row
            row_dict = {'class_name': class_name}
            for comp in all_components:
                row_dict[comp] = 'X' if comp in components_in_class else ''
            
            rows.append(row_dict)
        
        result = pd.DataFrame(rows)
        result.to_csv(output_file, index=False)
        print(f"✓ Exported to {output_file}")
        return result
    
    # ===== Summary & Validation =====
    
    def summary(self):
        """Print configuration summary."""
        print("\n" + "="*60)
        print("ACM CONFIGURATION SUMMARY")
        print("="*60)
        print(f"Components: {len(self.components)}")
        print(f"Technologies: {len(self.technologies)}")
        print(f"Asset Classes: {len(self.classes)}")
        print(f"Component-Technology Assignments: {len(self.component_technology)}")
        print(f"Class-Component Assignments: {len(self.class_component)}")
        print("="*60)
        
        print("\nTechnologies:", ', '.join(self.technologies['technology_code'].tolist()))
        print("\nSample Components:", ', '.join(self.components['component_name'].head(10).tolist()))
        print("\nAsset Classes:", ', '.join(self.classes['class_name'].tolist()))
    
    def validate(self):
        """Run validation checks on configuration."""
        issues = []
        
        # Check for components with no technology assignments
        assigned_comps = self.component_technology['component_id'].unique()
        unassigned_comps = self.components[
            ~self.components['component_id'].isin(assigned_comps)
        ]['component_name'].tolist()
        
        if unassigned_comps:
            issues.append(f"Components with no technologies: {unassigned_comps}")
        
        # Check for components not in any class
        assigned_to_class = self.class_component['component_id'].unique()
        orphan_comps = self.components[
            ~self.components['component_id'].isin(assigned_to_class)
        ]['component_name'].tolist()
        
        if orphan_comps:
            issues.append(f"Components not in any class: {orphan_comps}")
        
        if issues:
            print("\n⚠ VALIDATION ISSUES:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✓ Configuration is valid!")
        
        return len(issues) == 0