import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from dashboard_generator_backend import DashboardBackend

def display_component(rendered_component: dict):
    """Display a rendered component in Streamlit using HTML"""
    if not rendered_component['success']:
        st.error(f"❌ {rendered_component['error_message']}")
        return
    
    component = rendered_component['component']
    processed_data = rendered_component['processed_data']
    html_content = rendered_component.get('html', '')
    
    if processed_data is None or processed_data.empty:
        st.warning(f"⚠️ No data available for {component.get('title', 'component')}")
        return
    
    # Display the HTML component using Streamlit's components
    if html_content:
        # Determine height based on component type
        component_type = component.get('type', 'table')
        if component_type == 'chart':
            height = 450
        elif component_type == 'table':
            height = 500
        elif component_type == 'metric':
            height = 200
        else:
            height = 300
        
        # Render the HTML component
        components.html(html_content, height=height, scrolling=True)
    else:
        # Fallback to legacy display if HTML is not available
        st.subheader(component.get('title', 'Component'))
        if component.get('description'):
            st.write(component['description'])
        
        st.warning("HTML content not generated, showing raw data:")
        st.dataframe(processed_data)

def main():
    """Main Streamlit application"""
    print("Starting Streamlit Dashboard Generator...")
    # Page config
    st.set_page_config(
        page_title="Dashboard Generator",
        page_icon="🚀",
        layout="wide"
    )
    
    # Title and description
    st.title("🚀 Component Generator")
    st.markdown("""
    Generate custom data visualization components from your form data using AI.
    Simply describe what you want to see, select your form, and get interactive components!
    """)
    
    # Initialize backend
    backend = DashboardBackend()
    
    # Sidebar for inputs
    st.sidebar.header("Component Configuration")
    
    # Database connection test
    st.sidebar.subheader("🔌 Database Connection")
    test_connection_button = st.sidebar.button("🔍 Test Database Connection")
    
    if test_connection_button:
        with st.spinner("Testing database connection..."):
            connection_status = backend.test_database_connection()
        
        if connection_status['connected']:
            st.sidebar.success(connection_status['message'])
            with st.sidebar.expander("📊 Database Info"):
                st.write(f"**Host:** {connection_status['db_info']['host']}")
                st.write(f"**Database:** {connection_status['db_info']['database']}")
                st.write(f"**Version:** {connection_status['db_info']['version']}")
                st.write(f"**Form Table Exists:** {'✅' if connection_status['db_info']['form_obj_table_exists'] else '❌'}")
                st.write(f"**Active Forms:** {connection_status['db_info']['active_forms_count']}")
        else:
            st.sidebar.error(connection_status['message'])
            if connection_status['error']:
                st.sidebar.code(connection_status['error'], language="text")
    
    st.sidebar.markdown("---")
    
    # Form name input
    form_name = st.sidebar.text_input(
        "Form Name (OBJECT_NAME)",
        placeholder="Enter the exact form name from your database",
        help="This should match the OBJECT_NAME in your form_objects table"
    )
    
    # Browse available forms
    browse_forms_button = st.sidebar.button("📋 Browse Available Forms")
    if browse_forms_button:
        with st.spinner("Loading available forms..."):
            available_forms = backend.get_available_forms()
        
        if available_forms:
            st.sidebar.success(f"Found {len(available_forms)} active forms:")
            with st.sidebar.expander("📝 Available Forms"):
                for form in available_forms:
                    st.write(f"**{form['OBJECT_NAME']}**")
                    st.write(f"  - Table: {form['SECONDARY_TABLE']}")
                    st.write("---")
        else:
            st.sidebar.warning("No forms found in database")
    
    # User prompt
    user_prompt = st.sidebar.text_area(
        "Component Description",
        placeholder="Describe what components you want to see...\nExample: 'Show me a pie chart of fuel types and a table with user statistics'",
        height=150
    )
    
    # Generate button
    generate_button = st.sidebar.button("🎯 Generate Components", type="primary")
    
    # Main content area
    if generate_button and form_name and user_prompt:
        with st.spinner("Analyzing form structure and generating components..."):
            # Process the component request through backend
            result = backend.process_component_request(form_name, user_prompt)
        
        if not result['success']:
            st.error(f"❌ {result['error_message']}")
            return
        
        # Extract results
        form_info = result['form_info']
        form_schema = result['form_schema']
        components = result['components']
        rendered_components = result['rendered_components']
        
        st.success(f"✅ Found form: {form_info['OBJECT_NAME']}")
        
        # Display form analysis
        st.subheader("📊 Form Analysis")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Fields", form_schema['total_fields'])
        with col2:
            st.metric("Data Table", form_info['SECONDARY_TABLE'])
        with col3:
            st.metric("Generated Components", len(components))
        
        # Field details
        with st.expander("📋 Field Details"):
            for field_name, analysis in form_schema['fields'].items():
                st.write(f"**{field_name}** ({analysis['data_type']})")
                st.write(f"- Entries: {analysis['total_entries']}, Unique: {analysis['unique_values']}")
                if analysis['sample_values']:
                    st.write(f"- Samples: {', '.join(map(str, analysis['sample_values'][:3]))}")
                st.write("---")
        
        # Display components
        st.subheader("📈 Generated Components")
        
        if rendered_components:
            for i, rendered_component in enumerate(rendered_components):
                with st.container():
                    display_component(rendered_component)
                    
                    if i < len(rendered_components) - 1:  # Add separator except for last component
                        st.markdown("---")
        else:
            st.warning("No components were generated")
    
    elif generate_button:
        st.warning("⚠️ Please provide both form name and component description")
    
    else:
        # Welcome message
        st.markdown("""
        ### 👋 Welcome to the Component Generator!
        
        This tool helps you create custom data visualization components from your form data.
        
        **How it works:**
        1. **Enter your form name** - The exact name from your database
        2. **Describe your components** - What visualizations do you want to see?
        3. **Generate** - AI creates interactive components displayed right here!
        
        **Example prompts:**
        - "Show me a pie chart of account types"
        - "Create a table of user demographics and a bar chart of age distribution"
        - "Display key metrics and a histogram of income levels"
        - "Generate a line chart showing trends over time"
        """)

if __name__ == "__main__":
    main()
