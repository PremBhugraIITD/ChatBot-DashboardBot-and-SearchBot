from mcp.server.fastmcp import FastMCP
from typing import List
import mysql.connector
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Set current directory for consistent file operations
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Global map to count how many times sample data has been requested
SAMPLE_DATA_REQUESTS = 0

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

def add_workspace_filter_to_query(original_query: str, workspace_id: int) -> str:
    """
    Automatically inject workspace filtering and ACTION_TYPE = 'calling' into SQL queries for security
    """
    try:
        import re
        query = original_query.strip()
        # Check if workspace filtering already exists
        if re.search(r'\bWORKSPACE_ID\s*=\s*\d+', query, re.IGNORECASE) and re.search(r"ACTION_TYPE\s*=\s*'calling'", query, re.IGNORECASE):
            print(f"✅ Query already contains workspace and action type filtering: {query[:100]}...")
            return query
        # Build the filter string
        filter_str = f"WORKSPACE_ID = {workspace_id} AND ACTION_TYPE = 'calling'"
        # Check if query has WHERE clause
        where_match = re.search(r'\bWHERE\b', query, re.IGNORECASE)
        if where_match:
            # Insert filters after existing WHERE clause
            where_pos = where_match.end()
            filtered_query = (
                query[:where_pos] +
                f" {filter_str} AND" +
                query[where_pos:]
            )
        else:
            # Add WHERE clause with filters
            insert_pos = len(query)
            for keyword in ['GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT']:
                match = re.search(rf'\b{keyword}\b', query, re.IGNORECASE)
                if match:
                    insert_pos = min(insert_pos, match.start())
            filtered_query = (
                query[:insert_pos].rstrip() +
                f" WHERE {filter_str} " +
                query[insert_pos:]
            )
        logger.info(f"🔒 Applied workspace and action type filtering (ID: {workspace_id}): {filtered_query[:100]}...")
        return filtered_query
    except Exception as e:
        print(f"❌ Error applying workspace/action_type filter: {str(e)}")
        return original_query

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


mcp = FastMCP("VoiceAnalytics")

@mcp.tool()
def get_agent_executions_sample_data() -> List:
    """
    Get sample data from agent_executions table to understand its structure
    Returns a representative sample of different column types and values
    
    Returns:
        List of dictionaries with sample records from agent_executions table
    """
    global SAMPLE_DATA_REQUESTS
    try:
        # Check if sample data has already been requested
        if SAMPLE_DATA_REQUESTS >= 1:
            print(f"⚠️ Agent executions table has already been sampled {SAMPLE_DATA_REQUESTS} time(s). Returning cached message to prevent repeated calls.")
            return [{"COLUMN_NAME": "ALREADY_SAMPLED", "SAMPLE_VALUE": f"This table (agent_executions) has already been analyzed {SAMPLE_DATA_REQUESTS} time(s). Please proceed with SQL query generation instead of requesting sample data again."}]
        
        print(f"🔍 Getting sample data from agent_executions table (first time)")
        
        # Increment the counter
        SAMPLE_DATA_REQUESTS += 1
        
        # Connect to database
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = connection.cursor(dictionary=True)
        
        # Get workspace_id from middle.json for filtering
        workspace_id = get_workspace_id()
        if workspace_id is None:
            print("⚠️ Cannot get sample data: workspace_id not found in middle.json")
            return [{"COLUMN_NAME": "ERROR", "SAMPLE_VALUE": "workspace_id not found in middle.json"}]
        
        # Get a sample of records to show table structure with proper filtering
        query = f"""
        SELECT ID, EXECUTION_ID, AGENT_ID, STATUS, TOTAL_DURATION, WORKFLOW_ID,
               CREATED_AT, CALLING_NUMBER, PROVIDER_NUMBER, IS_ESCALATED, 
               IS_HOT_DEAL, START_TIME, END_TIME, AGENT_TALK_RATIO, 
               INTERRUPTIONS_COUNT, SILENCE_DURATION_TOTAL, 
               SPEECH_CLARITY_ISSUES, LLM_FAILURE_FLAG, 
               ASR_ACCURACY, MANUAL_REVIEW_REQUIRED, COMPANY_ID,
               OVERALL_SENTIMENT, CUSTOMER_SENTIMENT_SCORE
        FROM agent_executions 
        WHERE WORKSPACE_ID = {workspace_id} AND ACTION_TYPE = 'calling'
        LIMIT 2
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print(f"✅ Retrieved {len(results)} sample records from agent_executions table (call count: {SAMPLE_DATA_REQUESTS})")
        
        cursor.close()
        connection.close()
        
        return results
        
    except Exception as e:
        print(f"❌ Error getting sample data from agent_executions table: {str(e)}")
        return []


@mcp.tool()
def execute_sql_query(query: str) -> List:
    """
    Execute SQL query against agent_executions table and return results as a list of rows
    Only SELECT queries are allowed for security.
    
    Args:
        query: SQL SELECT query to execute
        
    Returns:
        List of rows, where each row is a list of column values
    """
    try:
        # Log the original query being executed for monitoring
        print(f"🔍 Original SQL query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        # Validate that only SELECT queries are allowed
        query_stripped = query.strip().upper()
        if not query_stripped.startswith('SELECT'):
            print(f"❌ Security violation: Only SELECT queries are allowed. Got: {query[:50]}...")
            return []
        
        # Additional security check - reject dangerous keywords
        import re
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in dangerous_keywords:
            # Only match as a whole word, not as a substring
            if re.search(r'\b' + keyword + r'\b', query_stripped):
                print(f"❌ Security violation: Query contains forbidden keyword '{keyword}'")
                return []
        
        # Apply workspace and action type filtering for security consistency
        workspace_id = get_workspace_id()
        if workspace_id is None:
            print("❌ Unable to determine workspace_id for security filtering")
            return []
        
        # Add workspace and action type filters for security consistency with component generation
        filtered_query = add_workspace_filter_to_query(query, workspace_id)
        print(f"🔒 Filtered SQL query: {filtered_query[:100]}{'...' if len(filtered_query) > 100 else ''}")
        
        # Connect to database
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        
        cursor = connection.cursor()
        cursor.execute(filtered_query)
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
                    # Convert NULL/empty to 'Unknown/Empty'
                    processed_row.append('Unknown/Empty')
            processed_results.append(processed_row)
        
        print(f"✅ Query executed successfully, returned {len(processed_results)} rows")
        
        cursor.close()
        connection.close()
        
        return processed_results
        
    except Exception as e:
        print(f"❌ Error executing SQL query: {str(e)}")
        return []


@mcp.tool()
def generate_pie_chart_component(combined_query: str) -> str:
    """
    Generate HTML code for a pie chart using Chart.js for voice analytics
    
    Args:
        combined_query: SQL SELECT query that returns exactly 2 columns (label, value)
                       Example: "SELECT STATUS, COUNT(*) FROM agent_executions WHERE WORKSPACE_ID = 123 GROUP BY STATUS"
        
    Note: Only SELECT queries are allowed for security reasons.
    
    Returns:
        str: HTML code with canvas and Chart.js script for pie chart
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = combined_query
    
    try:
        # Get workspace_id and apply automatic filtering
        workspace_id = get_workspace_id()
        if workspace_id is None:
            error = "<p>❌ Error: Unable to determine workspace_id for security filtering</p>"
            middle_data = {
                "component_html": component_html,
                "error": error,
                "component_type": "pie_chart",
                "sql_used": sql_used
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Apply automatic workspace filtering to query
        filtered_query = add_workspace_filter_to_query(combined_query, workspace_id)
        sql_used = filtered_query  # Update sql_used to show the filtered query
        
        # Execute filtered query to get both labels and data
        results = execute_sql_query(filtered_query)
        
        # Validate data
        if not results:
            error = "<p>❌ Error: No data returned from SQL query</p>"
            # Write to middle.json
            middle_data = {
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
        
        print("Voice Analytics Pie Chart Tool Invoked")
        
        # Modern color palette - beautiful and consistent colors
        modern_colors = [
            '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#10B981',
            '#06B6D4', '#F97316', '#8B5A2B', '#6366F1', '#EC4899',
            '#84CC16', '#6B7280', '#DC2626', '#7C3AED', '#059669'
        ]
        
        # Generate HTML with toggle functionality if needed
        if needs_toggle:
            component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="voiceAnalyticsPieChart" height="550" width="550"></canvas>
<br><br>
<button id="voiceAnalyticsToggleBtn" onclick="toggleVoiceAnalyticsSections()" style="padding: 12px 20px; background: linear-gradient(135deg, #3B82F6, #8B5CF6); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease; box-shadow: 0 3px 10px rgba(59, 130, 246, 0.3);">
    Show All ({additional_count} more)
</button>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const voiceAnalyticsFullLabels = {labels};
const voiceAnalyticsFullData = {data};
const voiceAnalyticsLimitedLabels = {limited_labels};
const voiceAnalyticsLimitedData = {limited_data};
const pieColors = {modern_colors};

let voiceAnalyticsShowingAll = false;
let voiceAnalyticsPieChart;

function initVoiceAnalyticsChart() {{
    const ctx = document.getElementById('voiceAnalyticsPieChart').getContext('2d');
    voiceAnalyticsPieChart = new Chart(ctx, {{
        type: 'pie',
        data: {{
            labels: voiceAnalyticsLimitedLabels,
            datasets: [{{
                data: voiceAnalyticsLimitedData,
                backgroundColor: pieColors.slice(0, voiceAnalyticsLimitedLabels.length),
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

function toggleVoiceAnalyticsSections() {{
    const btn = document.getElementById('voiceAnalyticsToggleBtn');
    
    if (voiceAnalyticsShowingAll) {{
        voiceAnalyticsPieChart.data.labels = voiceAnalyticsLimitedLabels;
        voiceAnalyticsPieChart.data.datasets[0].data = voiceAnalyticsLimitedData;
        voiceAnalyticsPieChart.data.datasets[0].backgroundColor = pieColors.slice(0, voiceAnalyticsLimitedLabels.length);
        btn.innerHTML = 'Show All ({additional_count} more)';
        voiceAnalyticsShowingAll = false;
    }} else {{
        voiceAnalyticsPieChart.data.labels = voiceAnalyticsFullLabels;
        voiceAnalyticsPieChart.data.datasets[0].data = voiceAnalyticsFullData;
        voiceAnalyticsPieChart.data.datasets[0].backgroundColor = pieColors.slice(0, voiceAnalyticsFullLabels.length);
        btn.innerHTML = 'Show Less';
        voiceAnalyticsShowingAll = true;
    }}
    
    voiceAnalyticsPieChart.update('active');
}}

initVoiceAnalyticsChart();
</script>"""
        else:
            # Standard pie chart without toggle for <= 5 sections
            component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="voiceAnalyticsPieChart" height="550" width="550"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const voiceAnalyticsCtx = document.getElementById('voiceAnalyticsPieChart').getContext('2d');
const pieColors = {modern_colors};
const voiceAnalyticsPieChart = new Chart(voiceAnalyticsCtx, {{
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

        # Write to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "pie_chart",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return component_html
        
    except Exception as e:
        error = f"<p>❌ Error generating pie chart: {str(e)}</p>"
        print(f"❌ Error in generate_pie_chart_component: {str(e)}")
        
        # Write error to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "pie_chart",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return error


@mcp.tool()
def generate_bar_graph_component(combined_query: str, x_name: str, y_name: str) -> str:
    """
    Generate HTML code for a bar graph using Chart.js for voice analytics
    
    Args:
        combined_query: SQL SELECT query that returns exactly 2 columns (x_axis, y_axis)
                       Example: "SELECT AGENT_ID, AVG(TOTAL_DURATION) FROM agent_executions WHERE WORKSPACE_ID = 123 GROUP BY AGENT_ID"
        x_name: Label for X-axis (e.g., "Agent ID", "Call Status")
        y_name: Label for Y-axis (e.g., "Average Duration", "Call Count")
        
    Returns:
        str: HTML code with canvas and Chart.js script for bar graph
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = combined_query
    
    try:
        # Get workspace_id and apply automatic filtering
        workspace_id = get_workspace_id()
        if workspace_id is None:
            error = "<p>❌ Error: Unable to determine workspace_id for security filtering</p>"
            middle_data = {
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
        
        # Apply automatic workspace filtering to query
        filtered_query = add_workspace_filter_to_query(combined_query, workspace_id)
        sql_used = filtered_query  # Update sql_used to show the filtered query
        
        # Execute filtered query to get both x and y axis data
        results = execute_sql_query(filtered_query)
        
        # Validate data
        # if not results:
        #     error = "<p>❌ Error: No data returned from SQL query</p>"
        #     # Write to middle.json
        #     middle_data = {
        #         "component_html": component_html,
        #         "error": error,
        #         "component_type": "bar_graph",
        #         "sql_used": sql_used,
        #         "x_name": x_name,
        #         "y_name": y_name
        #     }
        #     with open(get_middle_json_path(), "w") as f:
        #         json.dump(middle_data, f)
        #     return error
        
        # Extract x-axis labels and y-axis data
        labels = []
        data = []
        for row in results:
            # Handle x-axis label (first column)
            label = row[0] if row[0] is not None and row[0] != '' else 'Unknown/Empty'
            labels.append(str(label))
            
            # Handle y-axis data (second column)
            value = row[1] if row[1] is not None else 0
            data.append(value)
        
        print("Voice Analytics Bar Graph Tool Invoked")
        
        # Generate HTML for bar chart with better styling
        component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="voiceAnalyticsBarChart" height="400" width="800"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const voiceAnalyticsBarCtx = document.getElementById('voiceAnalyticsBarChart').getContext('2d');
const voiceAnalyticsBarChart = new Chart(voiceAnalyticsBarCtx, {{
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

        # Write to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "bar_graph",
            "sql_used": sql_used,
            "x_name": x_name,
            "y_name": y_name
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return component_html
        
    except Exception as e:
        error = f"<p>❌ Error generating bar graph: {str(e)}</p>"
        print(f"❌ Error in generate_bar_graph_component: {str(e)}")
        
        # Write error to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "bar_graph",
            "sql_used": sql_used,
            "x_name": x_name,
            "y_name": y_name
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return error


@mcp.tool()
def generate_line_chart_component(combined_query: str, x_name: str, y_name: str) -> str:
    """
    Generate HTML code for a line chart using Chart.js for voice analytics
    
    Args:
        combined_query: SQL SELECT query that returns exactly 2 columns (x_axis, y_axis)
                       Example: "SELECT DATE(CREATED_AT), COUNT(*) FROM agent_executions WHERE WORKSPACE_ID = 123 GROUP BY DATE(CREATED_AT) ORDER BY DATE(CREATED_AT)"
        x_name: Label for X-axis (e.g., "Date", "Time Period")
        y_name: Label for Y-axis (e.g., "Call Count", "Average Duration")
        
    Returns:
        str: HTML code with canvas and Chart.js script for line chart
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = combined_query
    
    try:
        # Get workspace_id and apply automatic filtering
        workspace_id = get_workspace_id()
        if workspace_id is None:
            error = "<p>❌ Error: Unable to determine workspace_id for security filtering</p>"
            middle_data = {
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
        
        # Apply automatic workspace filtering to query
        filtered_query = add_workspace_filter_to_query(combined_query, workspace_id)
        sql_used = filtered_query  # Update sql_used to show the filtered query
        
        # Execute filtered query to get both x and y axis data
        results = execute_sql_query(filtered_query)
        
        # Validate data
        # if not results:
        #     error = "<p>❌ Error: No data returned from SQL query</p>"
        #     # Write to middle.json
        #     middle_data = {
        #         "component_html": component_html,
        #         "error": error,
        #         "component_type": "line_chart",
        #         "sql_used": sql_used,
        #         "x_name": x_name,
        #         "y_name": y_name
        #     }
        #     with open(get_middle_json_path(), "w") as f:
        #         json.dump(middle_data, f)
        #     return error
        
        # Extract x-axis labels and y-axis data
        labels = []
        data = []
        for row in results:
            # Handle x-axis label (first column)
            label = row[0] if row[0] is not None and row[0] != '' else 'Unknown/Empty'
            labels.append(str(label))
            
            # Handle y-axis data (second column)
            value = row[1] if row[1] is not None else 0
            data.append(value)
        
        print("Voice Analytics Line Chart Tool Invoked")
        
        # Generate HTML for line chart with better styling
        component_html = f"""<div style="text-align: center; padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<canvas id="voiceAnalyticsLineChart" height="400" width="800"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const voiceAnalyticsLineCtx = document.getElementById('voiceAnalyticsLineChart').getContext('2d');
const voiceAnalyticsLineChart = new Chart(voiceAnalyticsLineCtx, {{
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
}});
</script>"""

        # Write to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "line_chart",
            "sql_used": sql_used,
            "x_name": x_name,
            "y_name": y_name
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return component_html
        
    except Exception as e:
        error = f"<p>❌ Error generating line chart: {str(e)}</p>"
        print(f"❌ Error in generate_line_chart_component: {str(e)}")
        
        # Write error to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "line_chart",
            "sql_used": sql_used,
            "x_name": x_name,
            "y_name": y_name
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return error


@mcp.tool()
def generate_table_component(combined_query: str) -> str:
    """
    Generate HTML code for a data table for voice analytics
    
    Args:
        combined_query: SQL SELECT query that returns data for table display
                       Example: "SELECT AGENT_ID, STATUS, TOTAL_DURATION, OVERALL_SENTIMENT FROM agent_executions WHERE WORKSPACE_ID = 123 LIMIT 10"
        
    Returns:
        str: HTML code for data table
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = combined_query
    
    try:
        # Get workspace_id and apply automatic filtering
        workspace_id = get_workspace_id()
        if workspace_id is None:
            error = "<p>❌ Error: Unable to determine workspace_id for security filtering</p>"
            middle_data = {
                "component_html": component_html,
                "error": error,
                "component_type": "table",
                "sql_used": sql_used
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Apply automatic workspace filtering to query
        filtered_query = add_workspace_filter_to_query(combined_query, workspace_id)
        sql_used = filtered_query  # Update sql_used to show the filtered query
        
        # Execute filtered query to get table data
        results = execute_sql_query(filtered_query)
        
        # Validate data
        if not results:
            error = "<p>❌ Error: No data returned from SQL query</p>"
            # Write to middle.json
            middle_data = {
                "component_html": component_html,
                "error": error,
                "component_type": "table",
                "sql_used": sql_used
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Extract column names from the query
        column_names = extract_column_names_from_query(combined_query)
        if not column_names:
            column_names = [f"Column {i+1}" for i in range(len(results[0]) if results else 0)]
        
        print("Voice Analytics Table Tool Invoked")
        
        # Generate improved HTML table with center alignment and clear demarcation
        table_html = f"""<div style="padding: 25px; background-color: #f8fafc; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin: 20px;">
<div style="overflow-x: auto; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
<table style="width: 100%; border-collapse: collapse; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: white;">
<thead>
<tr style="background: linear-gradient(135deg, #3B82F6, #8B5CF6);">"""
        
        # Add headers with center alignment and clear borders
        for col_name in column_names:
            table_html += f'''<th style="
                border-right: 2px solid rgba(255,255,255,0.3); 
                padding: 16px 20px; 
                text-align: center; 
                font-weight: 600; 
                color: white; 
                font-size: 14px; 
                text-transform: uppercase; 
                letter-spacing: 0.5px;
            ">{col_name}</th>'''
        
        table_html += "</tr></thead><tbody>"
        
        # Add data rows with center alignment and clear borders
        for i, row in enumerate(results):
            row_bg = "#f8fafc" if i % 2 == 0 else "white"
            table_html += f'''<tr style="
                background-color: {row_bg}; 
                transition: background-color 0.2s ease;
                border-bottom: 1px solid #e2e8f0;
            " onmouseover="this.style.backgroundColor='#e0f2fe'" onmouseout="this.style.backgroundColor='{row_bg}'">'''
            
            for value in row:
                table_html += f'''<td style="
                    border-right: 1px solid #e2e8f0; 
                    padding: 14px 20px; 
                    text-align: center; 
                    font-weight: 500; 
                    color: #374151;
                    font-size: 13px;
                ">{value}</td>'''
            table_html += "</tr>"
        
        table_html += """</tbody></table></div>
<div style="margin-top: 15px; text-align: center;">
<span style="color: #6B7280; font-size: 12px; font-style: italic;">
""" + f"📊 Total Records: {len(results)}" + """
</span>
</div>
</div>"""
        
        component_html = table_html

        # Write to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "table",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return component_html
        
    except Exception as e:
        error = f"<p>❌ Error generating table: {str(e)}</p>"
        print(f"❌ Error in generate_table_component: {str(e)}")
        
        # Write error to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "table",
            "sql_used": sql_used
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return error


@mcp.tool()
def generate_metric_component(combined_query: str, unit: str, metric_label: str) -> str:
    """
    Generate HTML code for a metric card component for voice analytics KPIs
    
    Args:
        combined_query: SQL SELECT query that returns a single numeric value
                       Example: "SELECT AVG(TOTAL_DURATION) FROM agent_executions WHERE WORKSPACE_ID = 123 AND STATUS = 'completed'"
        unit: Unit of the metric (e.g., "min", "$", "%","Kg")
        metric_label: Custom label for the metric (e.g., "Average Call Duration", "Total Calls Today", "Success Rate")
        
    Returns:
        str: HTML code for metric card
    """
    import json
    
    # Initialize variables for middle.json
    component_html = None
    error = None
    sql_used = combined_query
    
    try:
        # Get workspace_id and apply automatic filtering
        workspace_id = get_workspace_id()
        if workspace_id is None:
            error = "<p>❌ Error: Unable to determine workspace_id for security filtering</p>"
            middle_data = {
                "component_html": component_html,
                "error": error,
                "component_type": "metric",
                "sql_used": sql_used,
                "metric_label": metric_label
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Apply automatic workspace filtering to query
        filtered_query = add_workspace_filter_to_query(combined_query, workspace_id)
        sql_used = filtered_query  # Update sql_used to show the filtered query
        
        # Execute filtered query to get metric value
        results = execute_sql_query(filtered_query)
        
        # Validate data
        if not results or not results[0]:
            error = "<p>❌ Error: No data returned from SQL query</p>"
            # Write to middle.json
            middle_data = {
                "component_html": component_html,
                "error": error,
                "component_type": "metric",
                "sql_used": sql_used,
                "metric_label": metric_label
            }
            with open(get_middle_json_path(), "w") as f:
                json.dump(middle_data, f)
            return error
        
        # Get the metric value (first column of first row)
        metric_value = results[0][0]
        
        # Format the metric value
        if isinstance(metric_value, float):
            formatted_value = f"{metric_value:.2f}"
        else:
            formatted_value = str(metric_value)

        if formatted_value == "Unknown/Empty":
            formatted_value = "0"
        
        # Use the provided metric_label parameter directly
        
        print("Voice Analytics Metric Tool Invoked")
        
        # Generate HTML for metric card with light background
        component_html = f"""<div style="text-align: center; margin: 20px;">
<div style="display: inline-block; padding: 35px; background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); border-radius: 16px; box-shadow: 0 8px 20px rgba(0,0,0,0.12); border: 1px solid #cbd5e1; min-width: 280px;">
<h2 style="margin: 0 0 15px 0; font-size: 3.2em; font-weight: 700; color: #1e293b; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">{formatted_value} {unit}</h2>
<div style="width: 60px; height: 3px; background: linear-gradient(135deg, #3B82F6, #8B5CF6); margin: 0 auto 15px auto; border-radius: 2px;"></div>
<p style="margin: 0; font-size: 1.1em; color: #475569; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 500; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">{metric_label}</p>
</div>
</div>"""

        # Write to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "metric",
            "sql_used": sql_used,
            "metric_label": metric_label
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return component_html
        
    except Exception as e:
        error = f"<p>❌ Error generating metric: {str(e)}</p>"
        print(f"❌ Error in generate_metric_component: {str(e)}")
        
        # Write error to middle.json
        middle_data = {
            "component_html": component_html,
            "error": error,
            "component_type": "metric",
            "sql_used": sql_used,
            "metric_label": metric_label
        }
        with open(get_middle_json_path(), "w") as f:
            json.dump(middle_data, f, indent=2)
        
        return error


def get_middle_json_path():
    """Get the path to middle.json file"""
    return os.path.join(CURRENT_DIR, "middle.json")


if __name__ == "__main__":
    mcp.run() 