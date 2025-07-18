from mcp.server.fastmcp import FastMCP
from typing import List
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Set current directory for consistent file operations
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Global map to count how many times each table has been sampled
SAMPLED_TABLES = {}

def get_workspace_id():
    """Read workspace_id from middle.json file"""
    try:
        import json
        middle_json_path = os.path.join(CURRENT_DIR, "middle.json")
        
        if not os.path.exists(middle_json_path):
            print("⚠️ middle.json not found, cannot determine workspace_id")
            return None
            
        with open(middle_json_path, "r") as f:
            middle_data = json.load(f)
            
        workspace_id = middle_data.get("workspace_id")
        if workspace_id is not None:
            return int(workspace_id)
        else:
            print("⚠️ workspace_id not found in middle.json")
            return None
            
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"❌ Error reading workspace_id from middle.json: {e}")
        return None

def extract_column_names_from_query(query: str) -> List[str]:
    """
    Extract column names from SQL SELECT query, looking for aliases first
    
    Args:
        query: SQL SELECT query
        
    Returns:
        List of column names extracted from the query
    """
    try:
        import re
        
        # Convert to uppercase for easier parsing
        query_upper = query.upper()
        
        # Find the SELECT clause (between SELECT and FROM)
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query_upper, re.DOTALL)
        if not select_match:
            return []
        
        select_clause = select_match.group(1).strip()
        
        # Split by comma to get individual column expressions
        columns = [col.strip() for col in select_clause.split(',')]
        
        column_names = []
        for col in columns:
            # Look for alias pattern: "expression AS alias" or "expression alias"
            as_match = re.search(r'\s+AS\s+(\w+)$', col)
            if as_match:
                column_names.append(as_match.group(1).lower().capitalize())
            else:
                # Look for implicit alias (space without AS)
                space_match = re.search(r'\s+(\w+)$', col)
                if space_match and not re.search(r'\s+(FROM|WHERE|GROUP|ORDER|HAVING|LIMIT)$', col):
                    column_names.append(space_match.group(1).lower().capitalize())
                else:
                    # No alias found, try to extract meaningful name from expression
                    # Remove functions and get the core field name
                    clean_col = re.sub(r'.*\((.*?)\).*', r'\1', col)  # Remove function calls
                    clean_col = re.sub(r'.*\.', '', clean_col)  # Remove table prefixes
                    clean_col = clean_col.strip()
                    
                    if clean_col and clean_col != '*':
                        column_names.append(clean_col.lower().capitalize())
                    else:
                        column_names.append(f"Column {len(column_names) + 1}")
        
        return column_names
        
    except Exception as e:
        print(f"⚠️ Error parsing column names from query: {str(e)}")
        return []


mcp = FastMCP("Dashboard")

@mcp.tool()
def search_exact_form_name(form_name: str) -> List:
    """
    Search for an exact form name in the database
    
    Args:
        form_name: Exact name of the form to search for
        
    Returns:
        List of form records matching the exact name
    """
    try:
        workspace_id = get_workspace_id()
        if not workspace_id:
            print("❌ Workspace ID not available")
            return []
        
        # Check form search limit (5 calls total)
        form_search_key = "FORM_SEARCH_COUNT"
        current_count = SAMPLED_TABLES.get(form_search_key, 0)
        
        if current_count >= 5:
            print(f"⚠️ Form search limit reached ({current_count} calls). Returning 'No relevant form found'")
            # Write error to middle.json
            import json
            error_data = {
                "form_id": None,
                "component_html": "",
                "error": "No relevant form found",
                "component_type": ""
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(error_data, f, indent=2)
            return [{"ERROR": "No relevant form found"}]
        
        # Increment form search counter
        SAMPLED_TABLES[form_search_key] = current_count + 1
        print(f"🔍 Searching for exact form: '{form_name}' in workspace {workspace_id} (search attempt {SAMPLED_TABLES[form_search_key]}/5)")
        
        # Connect to database
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT ID, OBJECT_NAME, SECONDARY_TABLE 
        FROM form_objects 
        WHERE STATUS = 1 AND WORKSPACE_ID = %s AND OBJECT_NAME = %s
        """
        cursor.execute(query, (workspace_id, form_name))
        results = cursor.fetchall()
        
        print(f"✅ Found {len(results)} exact matches for form '{form_name}'")
        
        cursor.close()
        connection.close()
        
        return results
        
    except Exception as e:
        print(f"❌ Error searching exact form name: {str(e)}")
        return []

@mcp.tool()
def search_matching_form_names(pattern: str) -> List:
    """
    Search for forms with names matching a pattern
    
    Args:
        pattern: Pattern to search for in form names (will be wrapped with %)
        
    Returns:
        List of form records with names matching the pattern (limited to 20)
    """
    try:
        workspace_id = get_workspace_id()
        if not workspace_id:
            print("❌ Workspace ID not available")
            return []
        
        # Check form search limit (5 calls total)
        form_search_key = "FORM_SEARCH_COUNT"
        current_count = SAMPLED_TABLES.get(form_search_key, 0)
        
        if current_count >= 5:
            print(f"⚠️ Form search limit reached ({current_count} calls). Returning 'No relevant form found'")
            # Write error to middle.json
            import json
            error_data = {
                "form_id": None,
                "component_html": "",
                "error": "No relevant form found",
                "component_type": ""
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(error_data, f, indent=2)
            return [{"ERROR": "No relevant form found"}]
        
        # Increment form search counter
        SAMPLED_TABLES[form_search_key] = current_count + 1
        print(f"🔍 Searching for forms matching pattern: '{pattern}' in workspace {workspace_id} (search attempt {SAMPLED_TABLES[form_search_key]}/5)")
        
        # Connect to database
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = connection.cursor(dictionary=True)
        query = """
        SELECT ID, OBJECT_NAME, SECONDARY_TABLE 
        FROM form_objects 
        WHERE STATUS = 1 AND WORKSPACE_ID = %s AND OBJECT_NAME LIKE %s
        LIMIT 20
        """
        # Add % wildcards around the pattern
        search_pattern = f"%{pattern}%"
        cursor.execute(query, (workspace_id, search_pattern))
        results = cursor.fetchall()
        
        print(f"✅ Found {len(results)} forms matching pattern '{pattern}'")
        
        cursor.close()
        connection.close()
        
        return results
        
    except Exception as e:
        print(f"❌ Error searching matching form names: {str(e)}")
        return []

@mcp.tool()
def get_table_sample_data(table_name: str) -> List:
    """
    Get sample data from a secondary table to understand its structure
    Returns one representative sample for each unique field name
    
    Args:
        table_name: Name of the secondary table to analyze
        
    Returns:
        List of dictionaries with FIELD_NAME and FIELD_VALUE for each field type
    """
    try:
        # Check if this table has already been sampled (count > 0)
        if table_name in SAMPLED_TABLES and SAMPLED_TABLES[table_name] >= 1:
            call_count = SAMPLED_TABLES[table_name]
            print(f"⚠️ Table '{table_name}' has already been sampled {call_count} time(s). Returning cached message to prevent repeated calls.")
            return [{"FIELD_NAME": "ALREADY_SAMPLED", "FIELD_VALUE": f"You already called this tool once, so never call this tool again."}]
        
        print(f"🔍 Getting sample data from table: '{table_name}' (first time)")
        
        # Increment the counter for this table (or initialize to 1 if first time)
        if table_name in SAMPLED_TABLES:
            SAMPLED_TABLES[table_name] += 1
        else:
            SAMPLED_TABLES[table_name] = 1
        
        # Connect to database
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = connection.cursor(dictionary=True)
        
        # Get one sample for each unique field name
        query = f"""
        SELECT t1.FIELD_NAME, t1.FIELD_VALUE , t1.SUBMITTED_ID
        FROM `{table_name}` t1
        INNER JOIN (
            SELECT FIELD_NAME, MIN(ID) as first_id 
            FROM `{table_name}` 
            GROUP BY FIELD_NAME
        ) t2 ON t1.FIELD_NAME = t2.FIELD_NAME AND t1.ID = t2.first_id
        ORDER BY t1.FIELD_NAME
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        print(f"✅ Retrieved {len(results)} field samples from table '{table_name}' (call count: {SAMPLED_TABLES[table_name]})")
        # results.append({"MESSAGE":"You already called this tool once, so never call this tool again."})
        cursor.close()
        connection.close()
        
        return results
        
    except Exception as e:
        print(f"❌ Error getting sample data from table '{table_name}': {str(e)}")
        return []


@mcp.tool()
def execute_sql_query(query: str) -> List:
    """
    Execute SQL query and return results as a list of rows
    Only SELECT queries are allowed for security.
    
    Args:
        query: SQL SELECT query to execute
        
    Returns:
        List of rows, where each row is a list of column values
    """
    try:
        # Log the query being executed for monitoring
        print(f"🔍 Executing SQL query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        # Validate that only SELECT queries are allowed
        query_stripped = query.strip().upper()
        if not query_stripped.startswith('SELECT'):
            print(f"❌ Security violation: Only SELECT queries are allowed. Got: {query[:50]}...")
            return []
        
        # Additional security check - reject dangerous keywords
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in query_stripped:
                print(f"❌ Security violation: Query contains forbidden keyword '{keyword}'")
                return []
        
        # Connect to database
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Return all rows and columns, handling NULL/empty values
        processed_results = []
        for row in results:
            processed_row = []
            for value in row:
                if value is not None and value != '':
                    # Keep numeric values as numbers, convert others to strings
                    if isinstance(value, (int, float)):
                        processed_row.append(value)
                    else:
                        processed_row.append(str(value))
                else:
                    # Replace NULL/empty with a placeholder
                    processed_row.append('Unknown/Empty')
            processed_results.append(processed_row)
        
        print(f"✅ Query executed successfully, returned {len(processed_results)} rows (with NULL/empty handling)")
        
        cursor.close()
        connection.close()
        
        return processed_results
        
    except Exception as e:
        print(f"❌ SQL query execution failed: {str(e)}")
        return []

@mcp.tool()
def generate_pie_chart_component(combined_query: str, form_id: int) -> str:
    """
    Generate HTML code for a pie chart using Chart.js with a single SQL query
    
    Args:
        combined_query: SQL SELECT query that returns exactly 2 columns (label, value)
                       Example: "SELECT category, COUNT(*) FROM table GROUP BY category ORDER BY COUNT(*) DESC"
        form_id: Unique identifier of the form being used
        
    Note: Only SELECT queries are allowed for security reasons.
    
    Returns:
        str: HTML code with canvas and Chart.js script for pie chart
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = None
    
    try:
        # Execute single query to get both labels and data with perfect alignment
        results = execute_sql_query(combined_query)
        
        # Validate data
        if not results:
            error = "<p>❌ Error: No data returned from SQL query</p>"
            # Write to middle.json
            middle_data = {
                "form_id": form_id,
                "component_html": component_html,
                "error": error,
                "component_type": "pie_chart",
                "sql_used": sql_used
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Extract labels and data from the two-column results
        labels = []
        data = []
        for row in results:
            # Handle label (first column)
            label = row[0] if row[0] is not None and row[0] != '' else 'Unknown/Empty'
            labels.append(str(label))
            
            # Handle data (second column)  
            value = row[1] if row[1] is not None else 0
            data.append(value)
        
        # Determine if we need show/hide functionality (more than 10 sections)
        total_sections = len(labels)
        show_limit = 5  # Change this value to adjust how many sections are shown initially
        needs_toggle = total_sections > show_limit
        
        # Prepare data for both views
        if needs_toggle:
            limited_labels = labels[:show_limit]
            limited_data = data[:show_limit]
            additional_count = total_sections - show_limit
        else:
            limited_labels = labels
            limited_data = data
            additional_count = 0
        
        print("Pie Chart Tool Invoked")
        
        # Modern color palette - beautiful and consistent colors
        modern_colors = [
            '#7F55F6', '#3BAFCF', '#61B0FF', '#EF8FD5', '#F1C147',
            '#DD454B', '#6EC85A', '#83758F', '#6366F1', '#EC4899',
            '#84CC16', '#6B7280', '#DC2626', '#7C3AED', '#059669'
        ]
        
        # Generate HTML with toggle functionality if needed
        if needs_toggle:
            component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="pieChart" height="550" width="550"></canvas>
<br><br>
<button id="toggleBtn" onclick="toggleSections()" style="padding: 12px 20px; background: linear-gradient(135deg, #3B82F6, #8B5CF6); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease; box-shadow: 0 3px 10px rgba(59, 130, 246, 0.3);">
    Show All ({additional_count} more)
</button>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const fullLabels = {labels};
const fullData = {data};
const limitedLabels = {limited_labels};
const limitedData = {limited_data};
const pieColors = {modern_colors};

let showingAll = false;
let pieChart;

function initChart() {{
    const ctx = document.getElementById('pieChart').getContext('2d');
    pieChart = new Chart(ctx, {{
        type: 'pie',
        data: {{
            labels: limitedLabels,
            datasets: [{{
                data: limitedData,
                backgroundColor: pieColors.slice(0, limitedLabels.length),
                borderColor: '#ffffff',
                borderWidth: 2,
                hoverBorderWidth: 3,
                hoverOffset: 6
            }}]
        }},
        options: {{
            responsive: true,
            animation: {{
                animateRotate: true,
                duration: 800
            }},
            plugins: {{
                legend: {{
                    position: 'bottom',
                    labels: {{
                        padding: 15,
                        usePointStyle: true,
                        font: {{
                            size: 12
                        }}
                    }}
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    cornerRadius: 6,
                    padding: 10
                }}
            }}
        }}
    }});
}}

function toggleSections() {{
    const btn = document.getElementById('toggleBtn');
    
    if (showingAll) {{
        pieChart.data.labels = limitedLabels;
        pieChart.data.datasets[0].data = limitedData;
        pieChart.data.datasets[0].backgroundColor = pieColors.slice(0, limitedLabels.length);
        btn.innerHTML = 'Show All ({additional_count} more)';
        showingAll = false;
    }} else {{
        pieChart.data.labels = fullLabels;
        pieChart.data.datasets[0].data = fullData;
        pieChart.data.datasets[0].backgroundColor = pieColors.slice(0, fullLabels.length);
        btn.innerHTML = 'Show Less';
        showingAll = true;
    }}
    
    pieChart.update('active');
}}

initChart();
</script>"""
        else:
            # Standard pie chart without toggle for <= 5 sections
            component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="pieChart" height="550" width="550"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const ctx = document.getElementById('pieChart').getContext('2d');
const pieColors = {modern_colors};
new Chart(ctx, {{
    type: 'pie',
    data: {{
        labels: {labels},
        datasets: [{{
            data: {data},
            backgroundColor: pieColors.slice(0, {len(labels)}),
            borderColor: '#ffffff',
            borderWidth: 2,
            hoverBorderWidth: 3,
            hoverOffset: 6
        }}]
    }},
    options: {{
        responsive: true,
        animation: {{
            animateRotate: true,
            duration: 800
        }},
        plugins: {{
            legend: {{
                position: 'bottom',
                labels: {{
                    padding: 15,
                    usePointStyle: true,
                    font: {{
                        size: 12
                    }}
                }}
            }},
            tooltip: {{
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                cornerRadius: 6,
                padding: 10
            }}
        }}
    }}
}});
</script>"""
        
        # Write successful result to middle.json
        sql_used = combined_query  # Store the successful SQL query
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "pie_chart",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
            
        return component_html
        
    except Exception as e:
        error = str(e)
        # Write error to middle.json
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "pie_chart",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
        return error

@mcp.tool()
def generate_bar_graph_component(combined_query: str, x_name: str, y_name: str, form_id: int) -> str:
    """
    Generate HTML code for a bar chart using Chart.js with a single SQL query
    
    Args:
        combined_query: SQL SELECT query that returns exactly 2 columns (label, value)
                       Example: "SELECT category, COUNT(*) FROM table GROUP BY category ORDER BY COUNT(*) DESC"
        x_name: Title for X-axis
        y_name: Title for Y-axis
        form_id: Unique identifier of the form being used
        
    Note: Only SELECT queries are allowed for security reasons.
    
    Returns:
        str: HTML code with canvas and Chart.js script for bar chart
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = None
    
    try:
        # Execute single query to get both labels and data with perfect alignment
        results = execute_sql_query(combined_query)
        
        # Validate data
        if not results:
            error = "<p>❌ Error: No data returned from SQL query</p>"
            # Write to middle.json
            middle_data = {
                "form_id": form_id,
                "component_html": component_html,
                "error": error,
                "component_type": "bar_graph",
                "sql_used": sql_used,
                "x_name": x_name,
                "y_name": y_name
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Extract labels and data from the two-column results
        labels = []
        data = []
        for row in results:
            # Handle label (first column)
            label = row[0] if row[0] is not None and row[0] != '' else 'Unknown/Empty'
            labels.append(str(label))
            
            # Handle data (second column)  
            value = row[1] if row[1] is not None else 0
            data.append(value)
        
        # Determine if we need show/hide functionality (more than 5 bars)
        total_bars = len(labels)
        show_limit = 5  # Change this value to adjust how many bars are shown initially
        needs_toggle = total_bars > show_limit
        
        # Prepare data for both views
        if needs_toggle:
            limited_labels = labels[:show_limit]
            limited_data = data[:show_limit]
            additional_count = total_bars - show_limit
        else:
            limited_labels = labels
            limited_data = data
            additional_count = 0
        
        print("Bar Graph Tool Invoked")
        
        # Generate HTML for bar chart with better styling
        if needs_toggle:
            component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="barChart" height="400" width="800"></canvas>
<br><br>
<button id="toggleBtn" onclick="toggleBars()" style="padding: 12px 20px; background: linear-gradient(135deg, #3B82F6, #8B5CF6); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease; box-shadow: 0 3px 10px rgba(59, 130, 246, 0.3);">
    Show All ({additional_count} more)
</button>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const fullLabels = {labels};
const fullData = {data};
const limitedLabels = {limited_labels};
const limitedData = {limited_data};

let showingAll = false;
let barChart;

function initChart() {{
    const ctx = document.getElementById('barChart').getContext('2d');
    barChart = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: limitedLabels,
            datasets: [{{
                label: '{y_name}',
                data: limitedData,
                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 2,
                borderRadius: 6,
                borderSkipped: false,
                hoverBackgroundColor: 'rgba(59, 130, 246, 0.9)',
                hoverBorderColor: 'rgba(59, 130, 246, 1)',
                hoverBorderWidth: 3
            }}]
        }},
        options: {{
            responsive: true,
            animation: {{
                duration: 1000,
                easing: 'easeOutQuart'
            }},
            scales: {{
                x: {{
                    title: {{
                        display: true,
                        text: '{x_name}',
                        font: {{
                            size: 14,
                            weight: 'bold'
                        }},
                        color: '#374151'
                    }},
                    grid: {{
                        display: false
                    }},
                    ticks: {{
                        color: '#6B7280',
                        font: {{
                            size: 12
                        }}
                    }}
                }},
                y: {{
                    title: {{
                        display: true,
                        text: '{y_name}',
                        font: {{
                            size: 14,
                            weight: 'bold'
                        }},
                        color: '#374151'
                    }},
                    beginAtZero: true,
                    grid: {{
                        color: 'rgba(107, 114, 128, 0.2)',
                        lineWidth: 1
                    }},
                    ticks: {{
                        color: '#6B7280',
                        font: {{
                            size: 12
                        }}
                    }}
                }}
            }},
            plugins: {{
                legend: {{
                    display: true,
                    position: 'top',
                    labels: {{
                        padding: 20,
                        font: {{
                            size: 13,
                            weight: '500'
                        }},
                        color: '#374151'
                    }}
                }},
                tooltip: {{
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    cornerRadius: 8,
                    padding: 12,
                    font: {{
                        size: 13
                    }}
                }}
            }}
        }}
    }});
}}

function toggleBars() {{
    const btn = document.getElementById('toggleBtn');
    
    if (showingAll) {{
        barChart.data.labels = limitedLabels;
        barChart.data.datasets[0].data = limitedData;
        btn.innerHTML = 'Show All ({additional_count} more)';
        showingAll = false;
    }} else {{
        barChart.data.labels = fullLabels;
        barChart.data.datasets[0].data = fullData;
        btn.innerHTML = 'Show Less';
        showingAll = true;
    }}
    
    barChart.update('active');
}}

initChart();
</script>"""
        else:
            # Standard bar chart without toggle for <= 5 bars
            component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="barChart" height="400" width="800"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const ctx = document.getElementById('barChart').getContext('2d');
new Chart(ctx, {{
    type: 'bar',
    data: {{
        labels: {labels},
        datasets: [{{
            label: '{y_name}',
            data: {data},
            backgroundColor: 'rgba(59, 130, 246, 0.8)',
            borderColor: 'rgba(59, 130, 246, 1)',
            borderWidth: 2,
            borderRadius: 6,
            borderSkipped: false,
            hoverBackgroundColor: 'rgba(59, 130, 246, 0.9)',
            hoverBorderColor: 'rgba(59, 130, 246, 1)',
            hoverBorderWidth: 3
        }}]
    }},
    options: {{
        responsive: true,
        animation: {{
            duration: 1000,
            easing: 'easeOutQuart'
        }},
        scales: {{
            x: {{
                title: {{
                    display: true,
                    text: '{x_name}',
                    font: {{
                        size: 14,
                        weight: 'bold'
                    }},
                    color: '#374151'
                }},
                grid: {{
                    display: false
                }},
                ticks: {{
                    color: '#6B7280',
                    font: {{
                        size: 12
                    }}
                }}
            }},
            y: {{
                title: {{
                    display: true,
                    text: '{y_name}',
                    font: {{
                        size: 14,
                        weight: 'bold'
                    }},
                    color: '#374151'
                }},
                beginAtZero: true,
                grid: {{
                    color: 'rgba(107, 114, 128, 0.2)',
                    lineWidth: 1
                }},
                ticks: {{
                    color: '#6B7280',
                    font: {{
                        size: 12
                    }}
                }}
            }}
        }},
        plugins: {{
            legend: {{
                display: true,
                position: 'top',
                labels: {{
                    padding: 20,
                    font: {{
                        size: 13,
                        weight: '500'
                    }},
                    color: '#374151'
                }}
            }},
            tooltip: {{
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                cornerRadius: 8,
                padding: 12,
                font: {{
                    size: 13
                }}
            }}
        }}
    }}
}});
</script>"""
        
        # Write successful result to middle.json
        sql_used = combined_query  # Store the successful SQL query
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "bar_graph",
            "sql_used": sql_used,
            "x_name": x_name,
            "y_name": y_name
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
            
        return component_html
        
    except Exception as e:
        error = str(e)
        # Write error to middle.json
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "bar_graph",
            "sql_used": sql_used,
            "x_name": x_name,
            "y_name": y_name
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
        return error

@mcp.tool()
def generate_line_chart_component(combined_query: str, x_name: str, y_name: str, form_id: int) -> str:
    """
    Generate HTML code for a line chart using Chart.js with a single SQL query
    
    Args:
        combined_query: SQL SELECT query that returns exactly 2 columns (label, value)
                       Example: "SELECT date, COUNT(*) FROM table GROUP BY date ORDER BY date"
        x_name: Title for X-axis
        y_name: Title for Y-axis
        form_id: Unique identifier of the form being used
        
    Note: Only SELECT queries are allowed for security reasons.
    
    Returns:
        str: HTML code with canvas and Chart.js script for line chart
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = None
    
    try:
        # Execute single query to get both labels and data with perfect alignment
        results = execute_sql_query(combined_query)
        
        # Validate data
        if not results:
            error = "<p>❌ Error: No data returned from SQL query</p>"
            # Write to middle.json
            middle_data = {
                "form_id": form_id,
                "component_html": component_html,
                "error": error,
                "component_type": "line_chart",
                "sql_used": sql_used,
                "x_name": x_name,
                "y_name": y_name
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Extract labels and data from the two-column results
        labels = []
        data = []
        for row in results:
            # Handle label (first column)
            label = row[0] if row[0] is not None and row[0] != '' else 'Unknown/Empty'
            labels.append(str(label))
            
            # Handle data (second column)  
            value = row[1] if row[1] is not None else 0
            data.append(value)
        
        print("Line Chart Tool Invoked")
        
        # Determine if we need show/hide functionality
        show_limit = 5  # Change this value to adjust how many points are shown initially
        needs_toggle = len(labels) > show_limit
        
        # Generate HTML for line chart with better styling
        if needs_toggle:
            # Create limited data for initial display
            labels_limited = labels[:show_limit]
            data_limited = data[:show_limit]
            additional_count = len(labels) - show_limit
            
            component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="lineChart" height="400" width="800"></canvas>
<br><br>
<button id="toggleLineButton" onclick="toggleLineChart()" style="padding: 12px 20px; background: linear-gradient(135deg, #3B82F6, #8B5CF6); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease; box-shadow: 0 3px 10px rgba(59, 130, 246, 0.3);">Show All ({additional_count} more)</button>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  let lineChart;
  let showingAll = false;
  
  const allLabels = {labels};
  const allData = {data};
  const limitedLabels = {labels_limited};
  const limitedData = {data_limited};
  
  function initLineChart(labels, data) {{
    const ctx = document.getElementById('lineChart').getContext('2d');
    
    if (lineChart) {{
      lineChart.destroy();
    }}
    
    lineChart = new Chart(ctx, {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [{{
          label: '{y_name}',
          data: data,
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderColor: 'rgba(16, 185, 129, 1)',
          borderWidth: 3,
          fill: true,
          tension: 0.1,
          pointBackgroundColor: 'rgba(16, 185, 129, 1)',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointHoverBackgroundColor: 'rgba(16, 185, 129, 1)',
          pointHoverBorderColor: '#ffffff',
          pointHoverBorderWidth: 3
        }}]
      }},
      options: {{
        responsive: true,
        animation: {{
          duration: 1200,
          easing: 'easeOutCubic'
        }},
        scales: {{
          x: {{
            title: {{
              display: true,
              text: '{x_name}',
              font: {{
                size: 14,
                weight: 'bold'
              }},
              color: '#374151'
            }},
            grid: {{
              color: 'rgba(107, 114, 128, 0.2)',
              lineWidth: 1
            }},
            ticks: {{
              color: '#6B7280',
              font: {{
                size: 12
              }}
            }}
          }},
          y: {{
            title: {{
              display: true,
              text: '{y_name}',
              font: {{
                size: 14,
                weight: 'bold'
              }},
              color: '#374151'
            }},
            beginAtZero: true,
            grid: {{
              color: 'rgba(107, 114, 128, 0.2)',
              lineWidth: 1
            }},
            ticks: {{
              color: '#6B7280',
              font: {{
                size: 12
              }}
            }}
          }}
        }},
        plugins: {{
          legend: {{
            display: true,
            position: 'top',
            labels: {{
              padding: 20,
              font: {{
                size: 13,
                weight: '500'
              }},
              color: '#374151'
            }}
          }},
          tooltip: {{
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            cornerRadius: 8,
            padding: 12,
            font: {{
              size: 13
            }}
          }}
        }},
        interaction: {{
          intersect: false,
          mode: 'index'
        }}
      }}
    }});
  }}
  
  function toggleLineChart() {{
    const button = document.getElementById('toggleLineButton');
    
    if (showingAll) {{
      initLineChart(limitedLabels, limitedData);
      button.textContent = 'Show All ({additional_count} more)';
      showingAll = false;
    }} else {{
      initLineChart(allLabels, allData);
      button.textContent = 'Show Less';
      showingAll = true;
    }}
  }}
  
  initLineChart(limitedLabels, limitedData);
</script>"""
        else:
            # For show_limit or fewer points, show all without toggle button
            component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="lineChart" height="400" width="800"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  new Chart(
    document.getElementById('lineChart').getContext('2d'),
    {{
      type: 'line',
      data: {{
        labels: {labels},
        datasets: [{{
          label: '{y_name}',
          data: {data},
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderColor: 'rgba(16, 185, 129, 1)',
          borderWidth: 3,
          fill: true,
          tension: 0.1,
          pointBackgroundColor: 'rgba(16, 185, 129, 1)',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointHoverBackgroundColor: 'rgba(16, 185, 129, 1)',
          pointHoverBorderColor: '#ffffff',
          pointHoverBorderWidth: 3
        }}]
      }},
      options: {{
        responsive: true,
        animation: {{
          duration: 1200,
          easing: 'easeOutCubic'
        }},
        scales: {{
          x: {{
            title: {{
              display: true,
              text: '{x_name}',
              font: {{
                size: 14,
                weight: 'bold'
              }},
              color: '#374151'
            }},
            grid: {{
              color: 'rgba(107, 114, 128, 0.2)',
              lineWidth: 1
            }},
            ticks: {{
              color: '#6B7280',
              font: {{
                size: 12
              }}
            }}
          }},
          y: {{
            title: {{
              display: true,
              text: '{y_name}',
              font: {{
                size: 14,
                weight: 'bold'
              }},
              color: '#374151'
            }},
            beginAtZero: true,
            grid: {{
              color: 'rgba(107, 114, 128, 0.2)',
              lineWidth: 1
            }},
            ticks: {{
              color: '#6B7280',
              font: {{
                size: 12
              }}
            }}
          }}
        }},
        plugins: {{
          legend: {{
            display: true,
            position: 'top',
            labels: {{
              padding: 20,
              font: {{
                size: 13,
                weight: '500'
              }},
              color: '#374151'
            }}
          }},
          tooltip: {{
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            cornerRadius: 8,
            padding: 12,
            font: {{
              size: 13
            }}
          }}
        }},
        interaction: {{
          intersect: false,
          mode: 'index'
        }}
      }}
    }}
  );
</script>"""
        
        # Write successful result to middle.json
        sql_used = combined_query  # Store the successful SQL query
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "line_chart",
            "sql_used": sql_used,
            "x_name": x_name,
            "y_name": y_name
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
            
        return component_html
        
    except Exception as e:
        error = str(e)
        # Write error to middle.json
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "line_chart",
            "sql_used": sql_used,
            "x_name": x_name,
            "y_name": y_name
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
        return error

@mcp.tool()
def generate_table_component(combined_query: str, form_id: int) -> str:
    """
    Generate HTML code for a data table using the results from a single SQL query
    
    Args:
        combined_query: SQL SELECT query that returns data for the table
        form_id: Unique identifier of the form being used
        
    Note: Only SELECT queries are allowed for security reasons.
    
    Returns:
        str: HTML code with a styled table displaying all query results
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = None
    
    try:
        # Execute single query to get all data
        results = execute_sql_query(combined_query)
        
        # Validate data
        if not results:
            error = "<p>❌ Error: No data returned from SQL query</p>"
            # Write to middle.json
            middle_data = {
                "form_id": form_id,
                "component_html": component_html,
                "error": error,
                "component_type": "table",
                "sql_used": sql_used
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Extract column names from the SQL query
        column_names = extract_column_names_from_query(combined_query)
        
        # Determine if we need show/hide functionality
        row_limit = 10  # Change this value to adjust how many rows are shown initially
        col_limit = 2   # Change this value to adjust how many columns are shown initially
        
        total_rows = len(results)
        total_cols = len(results[0]) if results else 0
        
        needs_row_toggle = total_rows > row_limit
        needs_col_toggle = total_cols > col_limit
        needs_toggle = needs_row_toggle or needs_col_toggle
        
        # Calculate additional counts for button text
        additional_rows = max(0, total_rows - row_limit) if needs_row_toggle else 0
        additional_cols = max(0, total_cols - col_limit) if needs_col_toggle else 0
        
        # Generate improved HTML table with center alignment and clear demarcation
        print("Table Generation Tool Invoked")
        
        table_html = f"""<div style="padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<div style="overflow-x: auto; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
<table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: white;">
<thead>
<tr style="background: linear-gradient(135deg, #3B82F6, #8B5CF6);">"""
        
        # Add headers with center alignment and clear borders
        num_columns = len(results[0]) if results else 0
        for i in range(num_columns):
            # Use extracted column name if available, otherwise fallback to generic
            column_name = column_names[i] if i < len(column_names) and column_names[i] else f"Column {i+1}"
            
            # Add CSS class for column hiding functionality
            col_class = ""
            if needs_col_toggle and i >= col_limit:
                col_class = ' class="col-hidden"'
                
            table_html += f'''<th{col_class} style="
                border-right: 2px solid rgba(255,255,255,0.3); 
                padding: 16px 20px; 
                text-align: center; 
                font-weight: 600; 
                color: white; 
                font-size: 14px; 
                text-transform: uppercase; 
                letter-spacing: 0.5px;
            ">{column_name}</th>'''
        
        table_html += "</tr></thead><tbody>"
        
        # Add data rows with center alignment and clear borders
        for row_index, row in enumerate(results):
            # Alternate row colors for better readability
            row_bg = "#f8fafc" if row_index % 2 == 0 else "white"
            
            # Add CSS class for row hiding functionality
            row_class = ""
            if needs_row_toggle and row_index >= row_limit:
                row_class = ' class="row-hidden"'
                
            table_html += f'''<tr{row_class} style="
                background-color: {row_bg}; 
                transition: background-color 0.2s ease;
                border-bottom: 1px solid #e2e8f0;
            " onmouseover="this.style.backgroundColor='#e0f2fe'" onmouseout="this.style.backgroundColor='{row_bg}'">'''
            
            for col_index, cell_value in enumerate(row):
                # Handle NULL/empty values
                display_value = str(cell_value) if cell_value is not None and cell_value != '' else 'N/A'
                
                # Add CSS class for column hiding functionality
                col_class = ""
                if needs_col_toggle and col_index >= col_limit:
                    col_class = ' class="col-hidden"'
                    
                table_html += f'''<td{col_class} style="
                    border-right: 1px solid #e2e8f0; 
                    padding: 14px 20px; 
                    text-align: center; 
                    font-weight: 500; 
                    color: #374151;
                    font-size: 13px;
                ">{display_value}</td>'''
            table_html += "</tr>"
        
        table_html += """</tbody></table></div>
<div style="margin-top: 15px; text-align: center;">
<span style="color: #6B7280; font-size: 12px; font-style: italic;">
""" + f"📊 Total Records: {len(results)}" + """
</span>
</div>
</div>"""
        
        # Generate final HTML with toggle functionality if needed
        if needs_toggle:
            # Create button text based on what's hidden
            button_text_parts = []
            if additional_rows > 0:
                button_text_parts.append(f"{additional_rows} more rows")
            if additional_cols > 0:
                button_text_parts.append(f"{additional_cols} more columns")
            button_text = "Show All (" + ", ".join(button_text_parts) + ")"
            
            component_html = f"""<div style="margin: 20px;">
    <style>
        .row-hidden {{ display: none; }}
        .col-hidden {{ display: none; }}
        .toggle-button {{
            margin: 15px 0 10px 0;
            padding: 10px 20px;
            background: linear-gradient(135deg, #3B82F6, #8B5CF6);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 3px 10px rgba(59, 130, 246, 0.3);
        }}
        .toggle-button:hover {{
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            transform: translateY(-1px);
        }}
    </style>
    {table_html}
    <button id="toggleTableButton" class="toggle-button" onclick="toggleTable()">
        {button_text}
    </button>
    
    <script>
        let showingAllTable = false;
        
        function toggleTable() {{
            const button = document.getElementById('toggleTableButton');
            const table = document.querySelector('table');
            const rowLimit = {row_limit};
            const colLimit = {col_limit};
            
            if (showingAllTable) {{
                const allRows = table.querySelectorAll('tbody tr');
                for (let i = rowLimit; i < allRows.length; i++) {{
                    allRows[i].style.display = 'none';
                    allRows[i].classList.add('row-hidden');
                }}
                
                const headers = table.querySelectorAll('th');
                for (let i = colLimit; i < headers.length; i++) {{
                    headers[i].style.display = 'none';
                    headers[i].classList.add('col-hidden');
                }}
                
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {{
                    const cells = row.querySelectorAll('td');
                    for (let i = colLimit; i < cells.length; i++) {{
                        cells[i].style.display = 'none';
                        cells[i].classList.add('col-hidden');
                    }}
                }});
                
                button.textContent = '{button_text}';
                showingAllTable = false;
            }} else {{
                const hiddenRows = table.querySelectorAll('.row-hidden');
                hiddenRows.forEach(row => {{
                    row.style.display = 'table-row';
                    row.classList.remove('row-hidden');
                }});
                
                const hiddenHeaders = table.querySelectorAll('th.col-hidden');
                hiddenHeaders.forEach(header => {{
                    header.style.display = 'table-cell';
                    header.classList.remove('col-hidden');
                }});
                
                const hiddenCells = table.querySelectorAll('td.col-hidden');
                hiddenCells.forEach(cell => {{
                    cell.style.display = 'table-cell';
                    cell.classList.remove('col-hidden');
                }});
                
                button.textContent = 'Show Less';
                showingAllTable = true;
            }}
        }}
    </script>
</div>"""
        else:
            # For tables within limits, show all without toggle button
            component_html = table_html
        
        # Write successful result to middle.json
        sql_used = combined_query  # Store the successful SQL query
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "table",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
            
        return component_html
        
    except Exception as e:
        error = str(e)
        # Write error to middle.json
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "table",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
        return error

@mcp.tool()
def generate_metric_component(combined_query: str, form_id: int) -> str:
    """
    Generate HTML code for metric cards displaying key performance indicators and statistics
    
    Args:
        combined_query: SQL SELECT query that returns either:
                       - Single metric: 1 column with a single value (e.g., "SELECT COUNT(*) FROM table")
                       - Multiple metrics: 2 columns (metric_name, metric_value) 
                         (e.g., "SELECT 'Total Users', COUNT(*) UNION SELECT 'Active Users', COUNT(*) WHERE status='active'")
        form_id: Unique identifier of the form being used
    Note: Only SELECT queries are allowed for security reasons.
    
    Returns:
        str: HTML code with styled metric cards
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = None
    
    try:
        # Execute SQL query to get metric data
        results = execute_sql_query(combined_query)
        
        # Validate data
        if not results:
            error = "<div><p>❌ Error: No data returned from SQL query</p></div>"
            # Write to middle.json
            middle_data = {
                "form_id": form_id,
                "component_html": component_html,
                "error": error,
                "component_type": "metric",
                "sql_used": sql_used
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        metrics_html = []
        
        # Check if we have multiple columns (metric name + value) or single column (just value)
        if len(results[0]) >= 2:
            # Multiple metrics with labels and values
            for row in results:
                # Handle metric label (first column)
                metric_label = row[0] if row[0] is not None and row[0] != '' else 'Unknown'
                # Handle metric value (second column) - preserve numeric types
                metric_value = row[1] if row[1] is not None else 0
                
                # Format numbers properly
                if isinstance(metric_value, (int, float)):
                    # Keep as number for calculations, format for display
                    if metric_value == int(metric_value):
                        formatted_value = f"{int(metric_value):,}"
                    else:
                        formatted_value = f"{metric_value:,.2f}"
                else:
                    # For string values, check if it's a numeric string
                    try:
                        numeric_val = float(str(metric_value))
                        if numeric_val == int(numeric_val):
                            formatted_value = f"{int(numeric_val):,}"
                        else:
                            formatted_value = f"{numeric_val:,.2f}"
                    except (ValueError, TypeError):
                        formatted_value = str(metric_value)
                if formatted_value == "Unknown/Empty":
                    formatted_value = "0"
                metrics_html.append(f"""
                <div class="metric-card">
                    <div class="metric-value">{formatted_value}</div>
                    <div class="metric-divider"></div>
                    <div class="metric-label">{str(metric_label)}</div>
                </div>
            """)
        else:
            # Single metric - use a default label
            value = results[0][0] if results[0][0] is not None else 0
            
            # Format numbers properly
            if isinstance(value, (int, float)):
                # Keep as number for calculations, format for display
                if value == int(value):
                    formatted_value = f"{int(value):,}"
                else:
                    formatted_value = f"{value:,.2f}"
            else:
                # For string values, check if it's a numeric string
                try:
                    numeric_val = float(str(value))
                    if numeric_val == int(numeric_val):
                        formatted_value = f"{int(numeric_val):,}"
                    else:
                        formatted_value = f"{numeric_val:,.2f}"
                except (ValueError, TypeError):
                    formatted_value = str(value)
            if formatted_value == "Unknown/Empty":
                formatted_value = "0"
            metrics_html.append(f"""
            <div class="metric-card">
                <div class="metric-value">{formatted_value}</div>
                <div class="metric-divider"></div>
                <div class="metric-label">Metric</div>
            </div>
        """)
        
        # Determine if we need show/hide functionality
        show_limit = 5  # Change this value to adjust how many metrics are shown initially
        total_metrics = len(metrics_html)
        needs_toggle = total_metrics > show_limit
        
        print("Metric Component Tool Invoked")
        
        # Generate HTML with toggle functionality if needed
        if needs_toggle:
            # Calculate additional count for button text
            additional_count = total_metrics - show_limit
            
            # Add CSS classes to metrics for show/hide functionality
            limited_metrics_html = []
            for i, metric_html in enumerate(metrics_html):
                if i < show_limit:
                    # Add visible class to first show_limit metrics
                    limited_metrics_html.append(metric_html.replace('class="metric-card"', 'class="metric-card metric-visible"'))
                else:
                    # Add hidden class to remaining metrics
                    limited_metrics_html.append(metric_html.replace('class="metric-card"', 'class="metric-card metric-hidden"'))
            
            component_html = f"""
    <div style="margin: 20px 0;">
        <style>
            .metrics-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                justify-content: flex-start;
            }}
            .metric-card {{
                background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
                border: 1px solid #cbd5e1;
                border-radius: 16px;
                padding: 35px;
                min-width: 280px;
                text-align: center;
                box-shadow: 0 8px 20px rgba(0,0,0,0.12);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            .metric-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 12px 30px rgba(0,0,0,0.15);
            }}
            .metric-hidden {{
                display: none;
            }}
            .metric-visible {{
                display: block;
            }}
            .metric-label {{
                font-size: 1.1em;
                color: #475569;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                font-weight: 500;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            .metric-value {{
                font-size: 3.2em;
                font-weight: 700;
                color: #1e293b;
                line-height: 1.2;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            .metric-divider {{
                width: 60px;
                height: 3px;
                background: linear-gradient(135deg, #3B82F6, #8B5CF6);
                margin: 0 auto 15px auto;
                border-radius: 2px;
            }}
            .toggle-button {{
                margin: 20px 0 10px 0;
                padding: 12px 20px;
                background: linear-gradient(135deg, #3B82F6, #8B5CF6);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s ease;
                box-shadow: 0 3px 10px rgba(59, 130, 246, 0.3);
            }}
            .toggle-button:hover {{
                background: linear-gradient(135deg, #2563eb, #7c3aed);
                transform: translateY(-1px);
            }}
            @media (max-width: 768px) {{
                .metric-card {{
                    min-width: 250px;
                    padding: 30px;
                }}
                .metric-value {{
                    font-size: 2.5em;
                }}
            }}
        </style>
        <div class="metrics-container">
            {''.join(limited_metrics_html)}
        </div>
        <button id="toggleMetricsButton" class="toggle-button" onclick="toggleMetrics()">
            Show All ({additional_count} more)
        </button>
        
        <script>
            let showingAllMetrics = false;
            
            function toggleMetrics() {{
                const button = document.getElementById('toggleMetricsButton');
                const allMetrics = document.querySelectorAll('.metric-card');
                const showLimit = {show_limit};
                
                if (showingAllMetrics) {{
                    for (let i = showLimit; i < allMetrics.length; i++) {{
                        allMetrics[i].style.display = 'none';
                        allMetrics[i].classList.remove('metric-visible');
                        allMetrics[i].classList.add('metric-hidden');
                    }}
                    button.textContent = 'Show All ({additional_count} more)';
                    showingAllMetrics = false;
                }} else {{
                    for (let i = showLimit; i < allMetrics.length; i++) {{
                        allMetrics[i].style.display = 'block';
                        allMetrics[i].classList.remove('metric-hidden');
                        allMetrics[i].classList.add('metric-visible');
                    }}
                    button.textContent = 'Show Less';
                    showingAllMetrics = true;
                }}
            }}
        </script>
    </div>
    """
        else:
            # For show_limit or fewer metrics, show all without toggle button
            component_html = f"""
    <div style="margin: 20px 0;">
        <style>
            .metrics-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                justify-content: flex-start;
            }}
            .metric-card {{
                background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
                border: 1px solid #cbd5e1;
                border-radius: 16px;
                padding: 35px;
                min-width: 280px;
                text-align: center;
                box-shadow: 0 8px 20px rgba(0,0,0,0.12);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            .metric-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 12px 30px rgba(0,0,0,0.15);
            }}
            .metric-label {{
                font-size: 1.1em;
                color: #475569;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                font-weight: 500;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            .metric-value {{
                font-size: 3.2em;
                font-weight: 700;
                color: #1e293b;
                line-height: 1.2;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            .metric-divider {{
                width: 60px;
                height: 3px;
                background: linear-gradient(135deg, #3B82F6, #8B5CF6);
                margin: 0 auto 15px auto;
                border-radius: 2px;
            }}
            @media (max-width: 768px) {{
                .metric-card {{
                    min-width: 250px;
                    padding: 30px;
                }}
                .metric-value {{
                    font-size: 2.5em;
                }}
            }}
        </style>
        <div class="metrics-container">
            {''.join(metrics_html)}
        </div>
    </div>
    """
        
        # Write successful result to middle.json
        sql_used = combined_query  # Store the successful SQL query
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "metric",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
            
        return component_html
        
    except Exception as e:
        error = str(e)
        # Write error to middle.json
        middle_data = {
            "form_id": form_id,
            "component_html": component_html,
            "error": error,
            "component_type": "metric",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f)
        return error

# Helper function to get middle.json path
def get_middle_json_path():
    """Get the absolute path to middle.json"""
    return os.path.join(CURRENT_DIR, "middle.json")

if __name__ == "__main__":
    # print(execute_sql_query("Select * from form_objects where workspace_id=98;"))
    print("Starting MCP Dashboard Server...")
    mcp.run(transport="stdio")
