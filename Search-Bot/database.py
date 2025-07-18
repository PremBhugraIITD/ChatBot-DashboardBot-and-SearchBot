import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Database:
    def __init__(self):
        self.host = os.getenv('MYSQL_HOST')
        self.user = os.getenv('MYSQL_USER')
        self.password = os.getenv('MYSQL_PASSWORD')
        self.database = os.getenv('MYSQL_DATABASE')
    
    def get_connection(self):
        """Establish database connection"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            return connection
        except mysql.connector.Error as e:
            print(f"Error connecting to database: {e}")
            return None
    
    def get_all_pages_with_content(self, workspace_id):
        """
        Get all active pages with their content elements for a specific workspace
        
        SECURITY CRITICAL: workspace_id is mandatory to prevent cross-account data access
        
        Args:
            workspace_id: Workspace ID to filter pages by (MANDATORY for security)
        Returns a list of dictionaries with page info and content
        """
        # Security validation: workspace_id must be provided
        if workspace_id is None:
            raise ValueError("SECURITY ERROR: workspace_id is mandatory - cannot access data without account isolation")
        
        connection = self.get_connection()
        if not connection:
            return []
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # SQL query to get pages and their content elements
            # Using INNER JOIN to only include pages that have content elements
            query = """
            SELECT 
                p.ID as page_id,
                p.TITLE as page_title,
                e.ELEMENT_TYPE as element_type,
                e.CONTENT as content
            FROM page_schema p
            INNER JOIN element_schema e ON p.ID = e.PAGE_ID
            WHERE p.STATUS = 1 
            AND p.WORKSPACE_ID = %s
            AND e.STATUS = 1
            AND e.ELEMENT_TYPE IN ('TEXT', 'HEADER1', 'HEADER2', 'HEADER3', 'NUMBERED_LIST', 'BULLET_LIST', 'TODO_LIST')
            AND e.CONTENT IS NOT NULL AND e.CONTENT != ''
            ORDER BY p.ID, e.ELEMENT_INDEX
            """
            
            cursor.execute(query, (workspace_id,))
            results = cursor.fetchall()
            
            # Group results by page
            pages_data = {}
            for row in results:
                page_id = row['page_id']
                if page_id not in pages_data:
                    pages_data[page_id] = {
                        'page_id': page_id,
                        'page_title': row['page_title'],
                        'content_elements': []
                    }
                
                # Add content element (no need to check for NULL since we use INNER JOIN)
                pages_data[page_id]['content_elements'].append({
                    'element_type': row['element_type'],
                    'content': row['content']
                })
            
            return list(pages_data.values())
            
        except mysql.connector.Error as e:
            print(f"Error executing query: {e}")
            return []
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def update_openai_usage(self, company_id, workspace_id, model, prompt_tokens, completion_tokens, total_tokens):
        """
        Update OpenAI usage tracking in the openai_usage table
        
        This method implements upsert behavior: one row per workspace that gets updated on each request.
        - If a record exists for the workspace_id and model, it updates the existing record
        - If no record exists, it creates a new record
        - Increments request_count and adds to token totals on each call
        
        Args:
            company_id: Company ID from user data
            workspace_id: Workspace ID from user data
            model: OpenAI model used (e.g., 'gpt-4o-mini')
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            total_tokens: Total tokens used (prompt + completion)
        """
        # Security validation: workspace_id and company_id must be provided
        if workspace_id is None or company_id is None:
            raise ValueError("SECURITY ERROR: workspace_id and company_id are mandatory for usage tracking")
        
        connection = self.get_connection()
        if not connection:
            print("Failed to connect to database for usage tracking")
            return False
        
        try:
            cursor = connection.cursor()
            
            # First, try to find existing record for this workspace and model
            check_query = """
            SELECT ID, REQUEST_COUNT, TOTAL_TOKENS_USED, PROMPT_TOKENS, COMPLETION_TOKENS 
            FROM openai_usage 
            WHERE WORKSPACE_ID = %s AND MODEL = %s AND REQUEST_TYPE = 'text'
            """
            
            cursor.execute(check_query, (workspace_id, model))
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Update existing record - increment request_count and add to token totals
                update_query = """
                UPDATE openai_usage 
                SET TOTAL_TOKENS_USED = TOTAL_TOKENS_USED + %s,
                    PROMPT_TOKENS = PROMPT_TOKENS + %s,
                    COMPLETION_TOKENS = COMPLETION_TOKENS + %s,
                    REQUEST_COUNT = REQUEST_COUNT + 1,
                    UPDATED_AT = CURRENT_TIMESTAMP
                WHERE ID = %s
                """
                
                cursor.execute(update_query, (total_tokens, prompt_tokens, completion_tokens, existing_record[0]))
                print(f"✅ Updated existing usage record for workspace {workspace_id}: +{total_tokens} tokens, request_count incremented")
                
            else:
                # Insert new record - first request for this workspace
                insert_query = """
                INSERT INTO openai_usage 
                (COMPANY_ID, WORKSPACE_ID, MODEL, TOTAL_TOKENS_USED, PROMPT_TOKENS, COMPLETION_TOKENS, 
                 REQUEST_TYPE, REQUEST_COUNT, CREDENTIAL_USED) 
                VALUES (%s, %s, %s, %s, %s, %s, 'text', 1, 'internal')
                """
                
                cursor.execute(insert_query, (company_id, workspace_id, model, total_tokens, prompt_tokens, completion_tokens))
                print(f"✅ Created new usage record for workspace {workspace_id}: {total_tokens} tokens, request_count=1")
            
            connection.commit()
            return True
            
        except mysql.connector.Error as e:
            print(f"❌ Error updating OpenAI usage: {e}")
            connection.rollback()
            return False
        except Exception as e:
            print(f"❌ Unexpected error updating OpenAI usage: {e}")
            connection.rollback()
            return False
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    def get_usage_stats(self, workspace_id):
        """
        Get OpenAI usage statistics for a workspace
        
        Args:
            workspace_id: Workspace ID to get stats for
            
        Returns:
            dict: Usage statistics or None if not found
        """
        if workspace_id is None:
            raise ValueError("SECURITY ERROR: workspace_id is mandatory")
        
        connection = self.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            query = """
            SELECT COMPANY_ID, WORKSPACE_ID, MODEL, TOTAL_TOKENS_USED, PROMPT_TOKENS, 
                   COMPLETION_TOKENS, REQUEST_TYPE, REQUEST_COUNT, CREDENTIAL_USED,
                   CREATED_AT, UPDATED_AT
            FROM openai_usage 
            WHERE WORKSPACE_ID = %s
            ORDER BY CREATED_AT DESC
            """
            
            cursor.execute(query, (workspace_id,))
            results = cursor.fetchall()
            
            return results
            
        except mysql.connector.Error as e:
            print(f"Error getting usage stats: {e}")
            return None
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
