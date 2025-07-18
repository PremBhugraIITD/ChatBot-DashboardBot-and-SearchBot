import streamlit as st
import mysql.connector
import pandas as pd
import openai
from dotenv import load_dotenv
import os
import json
import re
from typing import Dict, List, Any, Optional
import traceback

# Load environment variables
load_dotenv()

class DatabaseAnalyzer:
    """Handles database connections and form schema analysis"""
    
    def __init__(self):
        self.connection = None
        self.connect_to_database()
    
    def connect_to_database(self):
        """Establish connection to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv('DB_HOST'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME')
            )
            return True
        except Exception as e:
            st.error(f"Database connection failed: {str(e)}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection and return detailed status"""
        result = {
            'connected': False,
            'message': '',
            'db_info': {},
            'error': None
        }
        
        try:
            # Test environment variables
            env_vars = {
                'DB_HOST': os.getenv('DB_HOST'),
                'DB_USER': os.getenv('DB_USER'),
                'DB_PASSWORD': os.getenv('DB_PASSWORD'),
                'DB_NAME': os.getenv('DB_NAME')
            }
            
            missing_vars = [key for key, value in env_vars.items() if not value]
            if missing_vars:
                result['error'] = f"Missing environment variables: {', '.join(missing_vars)}"
                result['message'] = "❌ Environment variables not configured"
                return result
            
            # Test connection
            test_connection = mysql.connector.connect(
                host=env_vars['DB_HOST'],
                user=env_vars['DB_USER'],
                password=env_vars['DB_PASSWORD'],
                database=env_vars['DB_NAME']
            )
            
            # Get database info
            cursor = test_connection.cursor(dictionary=True)
            
            # Test database version
            cursor.execute("SELECT VERSION() as version")
            version_info = cursor.fetchone()
            
            # Test form_objects table existence
            cursor.execute("SHOW TABLES LIKE 'form_objects'")
            form_obj_exists = cursor.fetchone() is not None
            
            # Count forms if table exists
            form_count = 0
            if form_obj_exists:
                cursor.execute("SELECT COUNT(*) as count FROM form_objects WHERE STATUS = 1")
                form_count = cursor.fetchone()['count']
            
            cursor.close()
            test_connection.close()
            
            result['connected'] = True
            result['message'] = "✅ Database connection successful"
            result['db_info'] = {
                'host': env_vars['DB_HOST'],
                'database': env_vars['DB_NAME'],
                'version': version_info['version'],
                'form_obj_table_exists': form_obj_exists,
                'active_forms_count': form_count
            }
            
        except mysql.connector.Error as e:
            result['error'] = str(e)
            result['message'] = f"❌ Database connection failed: {str(e)}"
        except Exception as e:
            result['error'] = str(e)
            result['message'] = f"❌ Unexpected error: {str(e)}"
            
        return result
    
    def get_form_info(self, form_name: str) -> Optional[Dict]:
        """Get form information from form_objects table"""
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT OBJECT_NAME, SECONDARY_TABLE 
            FROM form_objects 
            WHERE OBJECT_NAME = %s AND STATUS = 1
            """
            cursor.execute(query, (form_name,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            st.error(f"Error fetching form info: {str(e)}")
            return None
    
    def list_available_forms(self, limit: int = 200) -> List[Dict]:
        """Get list of available forms from database"""
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT OBJECT_NAME, SECONDARY_TABLE
            FROM form_objects 
            WHERE STATUS = 1 
            ORDER BY OBJECT_NAME 
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            forms = cursor.fetchall()
            cursor.close()
            return forms
        except Exception as e:
            st.error(f"Error fetching forms list: {str(e)}")
            return []
    
    def analyze_form_schema(self, secondary_table: str) -> Dict[str, Any]:
        """Analyze the form's data structure from secondary table"""
        if not self.connection:
            return {}
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Get all unique field names
            query = f"SELECT DISTINCT FIELD_NAME FROM `{secondary_table}`"
            cursor.execute(query)
            field_names = [row['FIELD_NAME'] for row in cursor.fetchall()]
            
            # Calculate property count from distinct field names
            property_count = len(field_names)
            
            # Analyze each field
            field_analysis = {}
            for field_name in field_names:
                analysis = self.analyze_field(secondary_table, field_name)
                field_analysis[field_name] = analysis
            
            cursor.close()
            return {
                'fields': field_analysis,
                'total_fields': property_count,
                'table_name': secondary_table
            }
        except Exception as e:
            st.error(f"Error analyzing form schema: {str(e)}")
            return {}
    
    def analyze_field(self, table_name: str, field_name: str) -> Dict[str, Any]:
        """Analyze individual field characteristics"""
        cursor = self.connection.cursor(dictionary=True)
        
        # Get sample values and basic stats
        query = f"""
        SELECT FIELD_VALUE, COUNT(*) as frequency 
        FROM `{table_name}` 
        WHERE FIELD_NAME = %s AND FIELD_VALUE IS NOT NULL 
        GROUP BY FIELD_VALUE 
        ORDER BY frequency DESC 
        LIMIT 20
        """
        cursor.execute(query, (field_name,))
        value_distribution = cursor.fetchall()
        
        # Get total count
        query = f"SELECT COUNT(*) as total FROM `{table_name}` WHERE FIELD_NAME = %s"
        cursor.execute(query, (field_name,))
        total_count = cursor.fetchone()['total']
        
        # Infer data type
        sample_values = [row['FIELD_VALUE'] for row in value_distribution if row['FIELD_VALUE']]
        data_type = self.infer_data_type(sample_values)
        
        cursor.close()
        
        return {
            'data_type': data_type,
            'total_entries': total_count,
            'unique_values': len(value_distribution),
            'sample_values': sample_values[:10],
            'value_distribution': value_distribution[:10]
        }
    
    def infer_data_type(self, sample_values: List[str]) -> str:
        """Infer the data type of field values"""
        if not sample_values:
            return 'text'
        
        # Check for numeric
        numeric_count = 0
        date_count = 0
        email_count = 0
        
        for value in sample_values[:10]:  # Check first 10 samples
            if value:
                # Check numeric
                try:
                    float(value)
                    numeric_count += 1
                    continue
                except ValueError:
                    pass
                
                # Check date patterns
                if re.match(r'\d{4}-\d{2}-\d{2}', value) or re.match(r'\d{2}/\d{2}/\d{4}', value):
                    date_count += 1
                    continue
                
                # Check email
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                    email_count += 1
                    continue
        
        total_samples = len([v for v in sample_values[:10] if v])
        if total_samples == 0:
            return 'text'
        
        # Determine type based on majority
        if numeric_count / total_samples > 0.7:
            return 'numeric'
        elif date_count / total_samples > 0.7:
            return 'date'
        elif email_count / total_samples > 0.7:
            return 'email'
        else:
            return 'text'

class DashboardGenerator:
    """Handles OpenAI integration and code generation"""
    
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
    
    def generate_dashboard_code(self, user_prompt: str, form_schema: Dict[str, Any], form_info: Dict) -> str:
        """Generate Streamlit dashboard code using OpenAI"""
        
        # Create comprehensive prompt
        system_prompt = self.create_system_prompt(form_schema, form_info)
        user_message = f"User Requirements: {user_prompt}"
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            generated_code = response.choices[0].message.content
            
            # Clean up the code (remove markdown formatting if present)
            if "```python" in generated_code:
                generated_code = generated_code.split("```python")[1].split("```")[0]
            elif "```" in generated_code:
                generated_code = generated_code.split("```")[1].split("```")[0]
            
            return generated_code.strip()
            
        except Exception as e:
            st.error(f"Error generating code: {str(e)}")
            return ""
    
    def create_system_prompt(self, form_schema: Dict[str, Any], form_info: Dict) -> str:
        """Create comprehensive system prompt for OpenAI"""
        
        fields_description = []
        for field_name, analysis in form_schema.get('fields', {}).items():
            desc = f"""
Field: {field_name}
- Data Type: {analysis['data_type']}
- Total Entries: {analysis['total_entries']}
- Unique Values: {analysis['unique_values']}
- Sample Values: {analysis['sample_values'][:5]}
"""
            fields_description.append(desc)
        
        return f"""
You are an expert Streamlit developer. Generate a complete, functional Streamlit dashboard based on the user's requirements and the provided form data structure.

FORM INFORMATION:
- Form Name: {form_info.get('OBJECT_NAME', 'Unknown')}
- Data Table: {form_schema.get('table_name', 'Unknown')}
- Total Fields: {form_schema.get('total_fields', 0)}

AVAILABLE FIELDS AND DATA:
{''.join(fields_description)}

DATABASE CONNECTION DETAILS:
The dashboard should connect to MySQL using these environment variables:
- DB_HOST, DB_USER, DB_PASSWORD, DB_NAME (loaded from .env)
- Data is stored in the table: {form_schema.get('table_name', 'table_name')}
- Data structure: FIELD_NAME (varchar), FIELD_VALUE (longtext)

REQUIREMENTS:
1. Generate COMPLETE, EXECUTABLE Streamlit code
2. Include proper database connection using mysql.connector
3. Query data from the secondary table using the FIELD_NAME/FIELD_VALUE structure
4. Transform the key-value data structure into a proper DataFrame for analysis
5. Include appropriate visualizations based on data types:
   - Numeric fields: histograms, box plots, trend analysis
   - Text fields: word clouds, category counts
   - Date fields: time series analysis
   - Email fields: domain analysis
6. Add interactive filters and controls
7. Include error handling and loading states
8. Make the dashboard responsive and well-designed
9. Add metrics and KPIs where appropriate
10. Include data download functionality

TECHNICAL REQUIREMENTS:
- Use st.cache_data for database queries
- Include proper error handling
- Add loading indicators
- Make the UI intuitive and professional
- Use appropriate Streamlit components (charts, metrics, tables, etc.)

The code should be production-ready and handle edge cases gracefully.
"""

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
    st.title("🚀 Streamlit Dashboard Generator")
    st.markdown("""
    Generate custom dashboards from your Unleashx form data using AI.
    Simply describe what you want to see, select your form, and get a complete dashboard!
    """)
    
    # Initialize components
    db_analyzer = DatabaseAnalyzer()
    dashboard_generator = DashboardGenerator()
    
    # Sidebar for inputs
    st.sidebar.header("Dashboard Configuration")
    
    # Database connection test
    st.sidebar.subheader("🔌 Database Connection")
    test_connection_button = st.sidebar.button("🔍 Test Database Connection")
    
    if test_connection_button:
        with st.spinner("Testing database connection..."):
            connection_status = db_analyzer.test_connection()
        
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
            available_forms = db_analyzer.list_available_forms()
        
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
        "Dashboard Description",
        placeholder="Describe what kind of dashboard you want...\nExample: 'Create an analytics dashboard showing user demographics, trends over time, and key metrics with interactive filters'",
        height=150
    )
    
    # Generate button
    generate_button = st.sidebar.button("🎯 Generate Dashboard", type="primary")
    
    # Main content area
    if generate_button and form_name and user_prompt:
        with st.spinner("Analyzing form structure..."):
            # Get form info
            form_info = db_analyzer.get_form_info(form_name)
            
            if not form_info:
                st.error(f"❌ Form '{form_name}' not found in database")
                return
            
            st.success(f"✅ Found form: {form_info['OBJECT_NAME']}")
            
            # Analyze form schema
            form_schema = db_analyzer.analyze_form_schema(form_info['SECONDARY_TABLE'])
            
            if not form_schema.get('fields'):
                st.error("❌ No data found in form table")
                return
        
        # Display form analysis
        st.subheader("📊 Form Analysis")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Fields", form_schema['total_fields'])
        with col2:
            st.metric("Data Table", form_info['SECONDARY_TABLE'])
        with col3:
            st.metric("Property Count", form_schema['total_fields'])
        
        # Field details
        with st.expander("📋 Field Details"):
            for field_name, analysis in form_schema['fields'].items():
                st.write(f"**{field_name}** ({analysis['data_type']})")
                st.write(f"- Entries: {analysis['total_entries']}, Unique: {analysis['unique_values']}")
                if analysis['sample_values']:
                    st.write(f"- Samples: {', '.join(map(str, analysis['sample_values'][:3]))}")
                st.write("---")
        
        # Generate dashboard code
        with st.spinner("🤖 Generating dashboard code with AI..."):
            generated_code = dashboard_generator.generate_dashboard_code(
                user_prompt, form_schema, form_info
            )
        
        if generated_code:
            st.success("✅ Dashboard code generated successfully!")
            
            # Display generated code
            st.subheader("📝 Generated Dashboard Code")
            st.code(generated_code, language="python")
            
            # Download button
            st.download_button(
                label="💾 Download Dashboard Code",
                data=generated_code,
                file_name=f"dashboard_{form_name.lower().replace(' ', '_')}.py",
                mime="text/plain"
            )
            
            # Instructions
            st.subheader("🚀 How to Run Your Dashboard")
            st.markdown("""
            1. **Save the code** to a `.py` file (use the download button above)
            2. **Install dependencies**: `pip install streamlit mysql-connector-python pandas plotly`
            3. **Set up your `.env` file** with database credentials
            4. **Run the dashboard**: `streamlit run your_dashboard.py`
            """)
            
        else:
            st.error("❌ Failed to generate dashboard code")
    
    elif generate_button:
        st.warning("⚠️ Please provide both form name and dashboard description")
    
    else:
        # Welcome message
        st.markdown("""
        ### 👋 Welcome to the Dashboard Generator!
        
        This tool helps you create custom Streamlit dashboards from your Unleashx form data.
        
        **How it works:**
        1. **Enter your form name** - The exact name from your database
        2. **Describe your dashboard** - What insights do you want to see?
        3. **Generate** - AI creates a complete dashboard tailored to your data
        
        **Example prompts:**
        - "Create a sales analytics dashboard with charts and metrics"
        - "Build a user survey analysis with demographic breakdowns"
        - "Generate a customer feedback dashboard with sentiment analysis"
        """)

if __name__ == "__main__":
    main()
