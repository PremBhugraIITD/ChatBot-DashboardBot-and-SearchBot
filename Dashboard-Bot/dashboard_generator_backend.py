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
load_dotenv(override=True)

class DatabaseAnalyzer:
    """Handles database connections and form schema analysis"""
    
    def __init__(self):
        self.connection = None
        self.connect_to_database()
    
    def connect_to_database(self):
        """Establish connection to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST'),
                user=os.getenv('MYSQL_USER'),
                password=os.getenv('MYSQL_PASSWORD'),
                database=os.getenv('MYSQL_DATABASE')
            )
            return True
        except Exception as e:
            print(f"Database connection failed: {str(e)}")
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
                'MYSQL_HOST': os.getenv('MYSQL_HOST'),
                'MYSQL_USER': os.getenv('MYSQL_USER'),
                'MYSQL_PASSWORD': os.getenv('MYSQL_PASSWORD'),
                'MYSQL_DATABASE': os.getenv('MYSQL_DATABASE')
            }
            
            missing_vars = [key for key, value in env_vars.items() if not value]
            if missing_vars:
                result['error'] = f"Missing environment variables: {', '.join(missing_vars)}"
                result['message'] = "❌ Environment variables not configured"
                return result
            
            # Test connection
            test_connection = mysql.connector.connect(
                host=env_vars['MYSQL_HOST'],
                user=env_vars['MYSQL_USER'],
                password=env_vars['MYSQL_PASSWORD'],
                database=env_vars['MYSQL_DATABASE']
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
                'host': env_vars['MYSQL_HOST'],
                'database': env_vars['MYSQL_DATABASE'],
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
    
    def get_form_info(self, form_name: str, workspace_id: int = None) -> Optional[Dict]:
        """Get form information from form_objects table filtered by workspace_id"""
        if not self.connection:
            return None
        
        try:
            # Check if connection is alive, reconnect if necessary
            if not self.connection.is_connected():
                self.connect_to_database()
            
            cursor = self.connection.cursor(dictionary=True)
            
            # Consume any unread results
            try:
                while cursor.nextset():
                    pass
            except:
                pass
            
            # Build query with workspace_id filter for security
            if workspace_id is not None:
                query = """
                SELECT ID, OBJECT_NAME, SECONDARY_TABLE 
                FROM form_objects 
                WHERE OBJECT_NAME = %s AND STATUS = 1 AND WORKSPACE_ID = %s
                """
                cursor.execute(query, (form_name, workspace_id))
            else:
                # Fallback for cases where workspace_id is not provided (should be rare)
                query = """
                SELECT ID, OBJECT_NAME, SECONDARY_TABLE 
                FROM form_objects 
                WHERE OBJECT_NAME = %s AND STATUS = 1
                """
                cursor.execute(query, (form_name,))
            
            result = cursor.fetchone()
            
            # Ensure all results are consumed
            while cursor.nextset():
                pass
                
            cursor.close()
            return result
        except Exception as e:
            print(f"Error fetching form info: {str(e)}")
            # Try to reconnect
            try:
                self.connect_to_database()
            except:
                pass
            return None
    
    def list_available_forms(self, limit: int = 200, workspace_id: int = None) -> List[Dict]:
        """Get list of available forms from database filtered by workspace_id"""
        if not self.connection:
            return []
        
        try:
            # Check if connection is alive, reconnect if necessary
            if not self.connection.is_connected():
                self.connect_to_database()
            
            cursor = self.connection.cursor(dictionary=True)
            
            # Consume any unread results
            try:
                while cursor.nextset():
                    pass
            except:
                pass
            
            # Build query with workspace_id filter for security
            if workspace_id is not None:
                query = """
                SELECT ID, OBJECT_NAME, SECONDARY_TABLE
                FROM form_objects 
                WHERE STATUS = 1 AND WORKSPACE_ID = %s
                ORDER BY OBJECT_NAME 
                LIMIT %s
                """
                cursor.execute(query, (workspace_id, limit))
            else:
                # Fallback for cases where workspace_id is not provided (should be rare)
                query = """
                SELECT ID, OBJECT_NAME, SECONDARY_TABLE
                FROM form_objects 
                WHERE STATUS = 1 
                ORDER BY OBJECT_NAME 
                LIMIT %s
                """
                cursor.execute(query, (limit,))
            
            forms = cursor.fetchall()
            
            # Ensure all results are consumed
            while cursor.nextset():
                pass
                
            cursor.close()
            return forms
        except Exception as e:
            print(f"Error fetching forms list: {str(e)}")
            # Try to reconnect
            try:
                self.connect_to_database()
            except:
                pass
            return []
    
    def analyze_form_schema(self, secondary_table: str) -> Dict[str, Any]:
        """Analyze the form's data structure from secondary table"""
        if not self.connection:
            return {}
        
        try:
            # Check if connection is alive, reconnect if necessary
            if not self.connection.is_connected():
                self.connect_to_database()
            
            cursor = self.connection.cursor(dictionary=True)
            
            # Consume any unread results
            try:
                while cursor.nextset():
                    pass
            except:
                pass
            
            # Get all unique field names
            query = f"SELECT DISTINCT FIELD_NAME FROM `{secondary_table}`"
            cursor.execute(query)
            field_names = [row['FIELD_NAME'] for row in cursor.fetchall()]
            
            # Ensure all results are consumed
            while cursor.nextset():
                pass
            
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
            print(f"Error analyzing form schema: {str(e)}")
            # Try to reconnect
            try:
                self.connect_to_database()
            except:
                pass
            return {}
    
    def analyze_field(self, table_name: str, field_name: str) -> Dict[str, Any]:
        """Analyze individual field characteristics"""
        if not self.connection:
            return {
                'total_entries': 0,
                'unique_values': 0,
                'sample_values': [],
                'data_type': 'text'
            }
        
        try:
            # Check if connection is alive, reconnect if necessary
            if not self.connection.is_connected():
                self.connect_to_database()
            
            cursor = self.connection.cursor(dictionary=True)
            
            # Consume any unread results
            try:
                while cursor.nextset():
                    pass
            except:
                pass
            
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
            
            # Ensure all results are consumed
            while cursor.nextset():
                pass
            
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
        except Exception as e:
            print(f"Error analyzing field {field_name}: {str(e)}")
            # Try to reconnect
            try:
                self.connect_to_database()
            except:
                pass
            return {
                'total_entries': 0,
                'unique_values': 0,
                'sample_values': [],
                'data_type': 'text'
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

class ComponentGenerator:
    """Handles OpenAI integration and component generation"""
    
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')

    def select_best_form(self, user_prompt: str, available_forms: List[Dict]) -> str:
        """
        Use LLM to intelligently select the best form based on user prompt and available forms
        
        Args:
            user_prompt: User's description of what they want to analyze
            available_forms: List of available forms from database
        
        Returns:
            The name of the most appropriate form
        """
        if not available_forms:
            raise ValueError("No forms available for selection")
        
        # If only one form available, return it
        if len(available_forms) == 1:
            return available_forms[0]['OBJECT_NAME']
        
        # Create forms description for LLM
        forms_description = []
        for form in available_forms:
            forms_description.append(f"- {form['OBJECT_NAME']} (table: {form['SECONDARY_TABLE']})")
        
        system_prompt = f"""You are an expert data analyst. Based on the user's requirements, select the most appropriate form/dataset from the available options.

AVAILABLE FORMS:
{chr(10).join(forms_description)}

INSTRUCTIONS:
1. Analyze the user's prompt to understand what type of data they need
2. Match keywords and context from the prompt to the most relevant form name
3. Consider domain-specific terms (e.g., "vehicle" matches "vehicle_registration", "survey" matches "user_survey")
4. Return ONLY the exact form name as it appears in the list above
5. Do not include any explanation or additional text
6. If NO form is appropriate for the user's request, return exactly: "NO_VALID_FORM"

USER PROMPT: {user_prompt}

Select the most appropriate form name or return "NO_VALID_FORM":"""

        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt}
                ],
                max_tokens=200,  # Should be enough for just a form name
                temperature=0.1
            )
            
            selected_form = response.choices[0].message.content.strip()
            
            # Check if LLM explicitly said no valid form
            if selected_form == "NO_VALID_FORM":
                raise ValueError("LLM determined no appropriate form exists for this request")
            
            # Validate that the selected form exists in our list
            form_names = [form['OBJECT_NAME'] for form in available_forms]
            table_names = [form['SECONDARY_TABLE'] for form in available_forms]
            
            # Check if LLM returned a form name (OBJECT_NAME)
            if selected_form in form_names:
                return selected_form
            
            # Check if LLM returned a table name (SECONDARY_TABLE) instead
            if selected_form in table_names:
                # Find the corresponding form name for this table
                for form in available_forms:
                    if form['SECONDARY_TABLE'] == selected_form:
                        print(f"🔄 LLM returned table name '{selected_form}', mapped to form name '{form['OBJECT_NAME']}'")
                        return form['OBJECT_NAME']
            
            # Try to find the closest match by partial string matching
            for form in available_forms:
                form_name = form['OBJECT_NAME']
                table_name = form['SECONDARY_TABLE']
                # Check partial matches for both form names and table names
                if (selected_form.lower() in form_name.lower() or form_name.lower() in selected_form.lower() or
                    selected_form.lower() in table_name.lower() or table_name.lower() in selected_form.lower()):
                    print(f"🔄 LLM returned '{selected_form}', partial matched to form name '{form_name}'")
                    return form_name
            
            # If no match found, raise exception
            print(f"⚠️ LLM selected '{selected_form}' but it doesn't match available forms or tables.")
            raise ValueError(f"LLM selected invalid form: '{selected_form}'. Available forms: {form_names}, Available tables: {table_names}")
                
        except Exception as e:
            print(f"Error in form selection: {str(e)}")
            # Raise exception instead of fallback
            raise ValueError(f"Failed to select form via LLM: {str(e)}")

    def generate_components(self, user_prompt: str, form_schema: Dict[str, Any], form_info: Dict, max_components: int = 4) -> List[Dict[str, Any]]:
        """Generate component definitions using OpenAI"""
        
        # Create comprehensive prompt for component generation
        system_prompt = self.create_component_system_prompt(form_schema, form_info, max_components)
        user_message = f"User Requirements: {user_prompt}"
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1000,  # Increased from 200 to allow for complete responses
                temperature=0.3
            )
            
            generated_content = response.choices[0].message.content
            
            # Parse the JSON response
            if "```json" in generated_content:
                json_content = generated_content.split("```json")[1].split("```")[0]
            elif "```" in generated_content:
                json_content = generated_content.split("```")[1].split("```")[0]
            else:
                json_content = generated_content
            
            try:
                components = json.loads(json_content.strip())
                return components if isinstance(components, list) else [components]
            except json.JSONDecodeError:
                print(f"Failed to parse JSON: {json_content}")
                return []
            
        except Exception as e:
            print(f"Error generating components: {str(e)}")
            return []
    
    def create_component_system_prompt(self, form_schema: Dict[str, Any], form_info: Dict, max_components: int = 4) -> str:
        """Create comprehensive system prompt for component generation"""
        
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
You are an expert data visualization and analysis assistant. Based on the user's requirements and the provided form data structure, generate a JSON array of component definitions that can be rendered in a Streamlit application.

FORM INFORMATION:
- Form Name: {form_info.get('OBJECT_NAME', 'Unknown')}
- Data Table: {form_schema.get('table_name', 'Unknown')}
- Total Fields: {form_schema.get('total_fields', 0)}

AVAILABLE FIELDS AND DATA:
{''.join(fields_description)}

DATABASE STRUCTURE:
- Data is stored with FIELD_NAME (varchar) and FIELD_VALUE (longtext) columns
- Each form submission creates multiple rows (one per field)

RESPONSE FORMAT:
Return a JSON array where each component has this structure:
{{
    "type": "chart|table|metric|text",
    "title": "Component Title",
    "description": "Brief description",
    "data_processing": {{
        "target_fields": ["field1", "field2"],
        "operation": "count|avg|sum|group_by|pivot",
        "filters": {{}},
        "aggregation": "if needed"
    }},
    "visualization": {{
        "chart_type": "pie|bar|line|histogram|scatter",
        "x_axis": "field_name",
        "y_axis": "field_name", 
        "color_by": "field_name"
    }}
}}

SUPPORTED COMPONENT TYPES:
1. "chart" - Pie charts, bar charts, line charts, histograms
2. "table" - Data tables with filtering and sorting
3. "metric" - Key performance indicators and statistics
4. "text" - Summary text and insights

REQUIREMENTS:
- Only use fields that exist in the provided form schema
- Choose appropriate visualization types based on data types
- Include proper aggregations for meaningful insights
- Generate exactly {max_components} component{'s' if max_components != 1 else ''} (no more, no less)
- Ensure components are useful and relevant to the user's prompt

Example response:
[
    {{
        "type": "chart",
        "title": "Fuel Type Distribution",
        "description": "Shows the distribution of fuel types among users",
        "data_processing": {{
            "target_fields": ["fuel"],
            "operation": "count",
            "filters": {{}},
            "aggregation": "group_by"
        }},
        "visualization": {{
            "chart_type": "pie",
            "x_axis": "fuel",
            "y_axis": "count"
        }}
    }}
]
"""

class DashboardBackend:
    """Main backend class that orchestrates database analysis and component generation"""
    
    def __init__(self):
        self.db_analyzer = DatabaseAnalyzer()
        self.component_generator = ComponentGenerator()
        self.component_renderer = ComponentRenderer(self.db_analyzer)
    
    def test_database_connection(self) -> Dict[str, Any]:
        """Test database connection"""
        return self.db_analyzer.test_connection()
    
    def get_available_forms(self, limit: int = 200, workspace_id: int = None) -> List[Dict]:
        """Get list of available forms filtered by workspace_id"""
        return self.db_analyzer.list_available_forms(limit, workspace_id)

    def process_component_request(self, user_prompt: str, form_name: Optional[str] = None, workspace_id: int = None, max_components: int = 4) -> Dict[str, Any]:
        """
        Main function that processes a component generation request
        
        Args:
            user_prompt: User's description of desired components
            form_name: Optional name of the form to analyze. If not provided, LLM will select the best form
            workspace_id: User's workspace ID for security filtering
            max_components: Maximum number of components to generate (default: 4)
        
        Returns:
            Dictionary containing form_info, form_schema, components, and status
        """
        result = {
            'success': False,
            'form_info': None,
            'form_schema': None,
            'components': [],
            'rendered_components': [],
            'error_message': '',
            'selected_form': None  # Track which form was selected
        }
        
        try:
            # If form_name not provided, use LLM to select the best form
            if not form_name:
                available_forms = self.get_available_forms(workspace_id=workspace_id)
                if not available_forms:
                    result['error_message'] = "No forms available in database"
                    return result
                
                try:
                    # Use LLM to select the most appropriate form
                    selected_form = self.component_generator.select_best_form(user_prompt, available_forms)
                    result['selected_form'] = selected_form
                    print(f"🤖 LLM selected form: {selected_form}")
                except ValueError as e:
                    # LLM failed to find a valid form
                    result['error_message'] = "No Valid Form Found"
                    return result
            else:
                selected_form = form_name
                result['selected_form'] = selected_form
            
            # Get form info with workspace_id filter for security
            form_info = self.db_analyzer.get_form_info(selected_form, workspace_id)
            
            if not form_info:
                result['error_message'] = f"Form '{selected_form}' not found in database"
                return result
            
            result['form_info'] = form_info
            
            # Analyze form schema
            form_schema = self.db_analyzer.analyze_form_schema(form_info['SECONDARY_TABLE'])
            
            if not form_schema.get('fields'):
                result['error_message'] = "No data found in form table"
                return result
            
            result['form_schema'] = form_schema
            
            # Generate components
            components = self.component_generator.generate_components(
                user_prompt, form_schema, form_info, max_components
            )
            
            if not components:
                result['error_message'] = "Failed to generate components"
                return result
            
            result['components'] = components
            
            # Render components with data
            rendered_components = []
            for component in components:
                rendered_result = self.component_renderer.render_component(component, form_info)
                rendered_components.append(rendered_result)
            
            result['rendered_components'] = rendered_components
            result['success'] = True
            
        except Exception as e:
            result['error_message'] = f"Unexpected error: {str(e)}"
            
        return result

class ComponentRenderer:
    """Handles component rendering and data processing"""
    
    def __init__(self, db_analyzer: DatabaseAnalyzer):
        self.db_analyzer = db_analyzer
    
    def render_component(self, component: Dict[str, Any], form_info: Dict) -> Dict[str, Any]:
        """Render a single component with data and generate HTML"""
        result = {
            'success': False,
            'component': component,
            'data': None,
            'processed_data': None,
            'html': '',
            'error_message': ''
        }
        
        try:
            # Fetch raw data from database
            raw_data = self._fetch_form_data(form_info['SECONDARY_TABLE'])
            if raw_data.empty:
                result['error_message'] = "No data available"
                return result
            
            result['data'] = raw_data
            
            # Process data according to component requirements
            processed_data = self._process_component_data(raw_data, component)
            if processed_data is None:
                result['error_message'] = "Failed to process data"
                return result
            
            result['processed_data'] = processed_data
            
            # Generate HTML for the component
            html_content = self._generate_component_html(component, processed_data)
            result['html'] = html_content
            result['success'] = True
            
        except Exception as e:
            result['error_message'] = f"Error rendering component: {str(e)}"
            
        return result
    
    def _generate_component_html(self, component: Dict[str, Any], processed_data: pd.DataFrame) -> str:
        """Generate HTML content for a component"""
        component_type = component.get('type', 'table')
        
        if component_type == 'chart':
            return self._generate_chart_html(component, processed_data)
        elif component_type == 'table':
            return self._generate_table_html(component, processed_data)
        elif component_type == 'metric':
            return self._generate_metric_html(component, processed_data)
        elif component_type == 'text':
            return self._generate_text_html(component, processed_data)
        else:
            return f"<div><p>⚠️ Unknown component type: {component_type}</p></div>"
    
    def _generate_chart_html(self, component: Dict[str, Any], data: pd.DataFrame) -> str:
        """Generate HTML with Chart.js for chart components"""
        import uuid
        
        if data.empty or len(data.columns) < 2:
            return "<div><p>⚠️ Insufficient data for chart</p></div>"
        
        chart_id = f"chart_{uuid.uuid4().hex[:8]}"
        visualization = component.get('visualization', {})
        chart_type = visualization.get('chart_type', 'bar')
        title = component.get('title', 'Chart')
        
        # Prepare data for JavaScript
        labels = data.iloc[:, 0].astype(str).tolist()
        values = data.iloc[:, 1].tolist()
        
        # Convert to JSON-safe format
        labels_json = json.dumps(labels)
        values_json = json.dumps(values)
        
        # Generate colors
        colors = [
            'rgba(255, 99, 132, 0.8)',
            'rgba(54, 162, 235, 0.8)', 
            'rgba(255, 205, 86, 0.8)',
            'rgba(75, 192, 192, 0.8)',
            'rgba(153, 102, 255, 0.8)',
            'rgba(255, 159, 64, 0.8)'
        ] * (len(labels) // 6 + 1)
        
        colors_json = json.dumps(colors[:len(labels)])
        
        # Chart.js configuration based on chart type
        if chart_type == 'pie':
            chart_config = f"""
                type: 'pie',
                data: {{
                    labels: {labels_json},
                    datasets: [{{
                        data: {values_json},
                        backgroundColor: {colors_json}
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{
                            display: true,
                            text: '{title}'
                        }},
                        legend: {{
                            position: 'bottom'
                        }}
                    }}
                }}
            """
        elif chart_type == 'bar':
            chart_config = f"""
                type: 'bar',
                data: {{
                    labels: {labels_json},
                    datasets: [{{
                        label: '{data.columns[1]}',
                        data: {values_json},
                        backgroundColor: 'rgba(54, 162, 235, 0.8)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{
                            display: true,
                            text: '{title}'
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            """
        elif chart_type == 'line':
            chart_config = f"""
                type: 'line',
                data: {{
                    labels: {labels_json},
                    datasets: [{{
                        label: '{data.columns[1]}',
                        data: {values_json},
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{
                            display: true,
                            text: '{title}'
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            """
        else:
            # Default to bar chart
            chart_config = f"""
                type: 'bar',
                data: {{
                    labels: {labels_json},
                    datasets: [{{
                        label: '{data.columns[1]}',
                        data: {values_json},
                        backgroundColor: 'rgba(54, 162, 235, 0.8)'
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{
                            display: true,
                            text: '{title}'
                        }}
                    }}
                }}
            """
        
        return f"""
        <div style="width: 100%; height: 400px; margin: 20px 0;">
            <canvas id="{chart_id}"></canvas>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            (function() {{
                const ctx = document.getElementById('{chart_id}').getContext('2d');
                new Chart(ctx, {{
                    {chart_config}
                }});
            }})();
        </script>
        """
    
    def _generate_table_html(self, component: Dict[str, Any], data: pd.DataFrame) -> str:
        """Generate HTML table with sorting and filtering"""
        import uuid
        
        if data.empty:
            return "<div><p>⚠️ No data available for table</p></div>"
        
        table_id = f"table_{uuid.uuid4().hex[:8]}"
        title = component.get('title', 'Data Table')
        
        # Convert DataFrame to HTML table
        table_html = data.to_html(index=False, escape=False, classes='data-table')
        
        return f"""
        <div style="margin: 20px 0;">
            <h3>{title}</h3>
            <div style="overflow-x: auto; max-height: 400px;">
                <style>
                    .data-table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 10px 0;
                    }}
                    .data-table th, .data-table td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    .data-table th {{
                        background-color: #f2f2f2;
                        font-weight: bold;
                        cursor: pointer;
                    }}
                    .data-table th:hover {{
                        background-color: #e0e0e0;
                    }}
                    .data-table tr:nth-child(even) {{
                        background-color: #f9f9f9;
                    }}
                    .data-table tr:hover {{
                        background-color: #f5f5f5;
                    }}
                </style>
                {table_html}
            </div>
            <p style="color: #666; font-size: 0.9em;">
                Showing {len(data)} rows × {len(data.columns)} columns
            </p>
        </div>
        """
    
    def _generate_metric_html(self, component: Dict[str, Any], data: pd.DataFrame) -> str:
        """Generate HTML for metric cards"""
        if data.empty:
            return "<div><p>⚠️ No data available for metrics</p></div>"
        
        title = component.get('title', 'Metrics')
        metrics_html = []
        
        if len(data.columns) >= 2:
            # Multiple metrics from data
            for _, row in data.iterrows():
                metric_label = str(row.iloc[0])
                metric_value = str(row.iloc[1])
                metrics_html.append(f"""
                    <div class="metric-card">
                        <div class="metric-label">{metric_label}</div>
                        <div class="metric-value">{metric_value}</div>
                    </div>
                """)
        else:
            # Single metric
            value = data.iloc[0, 0] if not data.empty else 0
            metrics_html.append(f"""
                <div class="metric-card">
                    <div class="metric-label">{title}</div>
                    <div class="metric-value">{value}</div>
                </div>
            """)
        
        return f"""
        <div style="margin: 20px 0;">
            <h3>{title}</h3>
            <style>
                .metrics-container {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                }}
                .metric-card {{
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 20px;
                    min-width: 150px;
                    text-align: center;
                }}
                .metric-label {{
                    font-size: 0.9em;
                    color: #6c757d;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #212529;
                }}
            </style>
            <div class="metrics-container">
                {''.join(metrics_html)}
            </div>
        </div>
        """
    
    def _generate_text_html(self, component: Dict[str, Any], data: pd.DataFrame) -> str:
        """Generate HTML for text summaries"""
        title = component.get('title', 'Summary')
        description = component.get('description', '')
        
        if data.empty:
            return f"""
            <div style="margin: 20px 0;">
                <h3>{title}</h3>
                <p>{description}</p>
                <p>⚠️ No data available for analysis</p>
            </div>
            """
        
        # Generate summary statistics
        summary_items = [
            f"<strong>Total Records:</strong> {len(data)}",
            f"<strong>Fields:</strong> {', '.join(data.columns)}"
        ]
        
        # Add statistics for numeric columns
        numeric_cols = data.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            for col in numeric_cols:
                mean_val = data[col].mean()
                summary_items.append(f"<strong>{col} Average:</strong> {mean_val:.2f}")
        
        return f"""
        <div style="margin: 20px 0;">
            <h3>{title}</h3>
            {f'<p>{description}</p>' if description else ''}
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff;">
                {'<br>'.join(summary_items)}
            </div>
        </div>
        """
    
    def _fetch_form_data(self, table_name: str) -> pd.DataFrame:
        """Fetch raw data from form table"""
        if not self.db_analyzer.connection:
            return pd.DataFrame()
        
        try:
            # Check if connection is alive, reconnect if necessary
            if not self.db_analyzer.connection.is_connected():
                self.db_analyzer.connect_to_database()
            
            cursor = self.db_analyzer.connection.cursor(dictionary=True)
            
            # Consume any unread results
            try:
                while cursor.nextset():
                    pass
            except:
                pass
            
            query = f"SELECT FIELD_NAME, FIELD_VALUE FROM `{table_name}`"
            cursor.execute(query)
            data = cursor.fetchall()
            
            # Ensure all results are consumed
            while cursor.nextset():
                pass
                
            cursor.close()
            
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error fetching form data: {str(e)}")
            # Try to reconnect
            try:
                self.db_analyzer.connect_to_database()
            except:
                pass
            return pd.DataFrame()
    
    def _process_component_data(self, raw_data: pd.DataFrame, component: Dict[str, Any]) -> pd.DataFrame:
        """Process raw data according to component requirements"""
        try:
            data_processing = component.get('data_processing', {})
            target_fields = data_processing.get('target_fields', [])
            operation = data_processing.get('operation', 'count')
            
            # Filter data for target fields
            if target_fields:
                filtered_data = raw_data[raw_data['FIELD_NAME'].isin(target_fields)]
            else:
                filtered_data = raw_data
            
            if filtered_data.empty:
                return pd.DataFrame()
            
            # Perform operation
            if operation == 'count':
                # Count occurrences of field values
                if len(target_fields) == 1:
                    field_data = filtered_data[filtered_data['FIELD_NAME'] == target_fields[0]]
                    result = field_data['FIELD_VALUE'].value_counts().reset_index()
                    result.columns = [target_fields[0], 'count']
                    return result
                else:
                    # Multiple fields - pivot and count
                    return self._pivot_and_count(filtered_data, target_fields)
            
            elif operation == 'group_by':
                # Group by field values
                if len(target_fields) >= 1:
                    field_data = filtered_data[filtered_data['FIELD_NAME'] == target_fields[0]]
                    result = field_data['FIELD_VALUE'].value_counts().reset_index()
                    result.columns = [target_fields[0], 'count']
                    return result
            
            elif operation == 'pivot':
                # Pivot the data
                return self._pivot_data(filtered_data)
            
            else:
                # Default: return filtered data
                return filtered_data
                
        except Exception as e:
            print(f"Error processing component data: {str(e)}")
            return None
    
    def _pivot_and_count(self, data: pd.DataFrame, target_fields: List[str]) -> pd.DataFrame:
        """Pivot data and count occurrences"""
        try:
            # Add record IDs
            unique_fields = data['FIELD_NAME'].unique()
            fields_per_record = len(unique_fields)
            
            if fields_per_record == 0:
                return pd.DataFrame()
            
            data = data.reset_index()
            data['record_id'] = data.index // fields_per_record
            
            # Pivot
            pivoted = data.pivot(index='record_id', columns='FIELD_NAME', values='FIELD_VALUE')
            
            # Count combinations
            if len(target_fields) >= 2:
                subset = pivoted[target_fields].dropna()
                result = subset.value_counts().reset_index()
                result.columns = target_fields + ['count']
                return result
            else:
                return pivoted.reset_index()
                
        except Exception as e:
            print(f"Error in pivot and count: {str(e)}")
            return pd.DataFrame()
    
    def _pivot_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Pivot data from key-value to columns"""
        try:
            unique_fields = data['FIELD_NAME'].unique()
            fields_per_record = len(unique_fields)
            
            if fields_per_record == 0:
                return pd.DataFrame()
            
            data = data.reset_index()
            data['record_id'] = data.index // fields_per_record
            
            pivoted = data.pivot(index='record_id', columns='FIELD_NAME', values='FIELD_VALUE')
            return pivoted.reset_index(drop=True)
            
        except Exception as e:
            print(f"Error in pivot: {str(e)}")
            return pd.DataFrame()
