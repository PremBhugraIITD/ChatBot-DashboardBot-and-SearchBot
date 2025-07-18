import os
from openai import OpenAI
from dotenv import load_dotenv
from database import Database
from mongo_manager import MongoDBManager
import json

load_dotenv(override=True)

class SearchBot:
    def __init__(self, mongodb_manager=None):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=api_key)
        self.db = Database()
        self.mongodb_manager = mongodb_manager or MongoDBManager()
        self.model = "gpt-4o-mini"
        self.max_tokens = 350  # Increased to ensure AI has enough space for PAGES_USED section
    
    def extract_referenced_pages_from_response(self, ai_response, available_pages):
        """
        Extract which pages were actually referenced by the AI from its response
        
        Args:
            ai_response: The AI's response text
            available_pages: List of page dictionaries with page_id and page_title
        
        Returns:
            List of page info dictionaries for only the pages that were actually referenced
        """
        referenced_pages_info = []
        referenced_page_ids = set()  # Track page IDs to avoid duplicates
        
        try:
            # Look for the PAGES_USED section in the response
            if "PAGES_USED:" in ai_response:
                # Extract the part after PAGES_USED:
                pages_section = ai_response.split("PAGES_USED:")[1].strip()
                
                # Extract just the first line in case there's additional content after
                pages_line = pages_section.split('\n')[0].strip()
                
                if pages_line and pages_line.lower() != "none":
                    # Split by comma and clean up page names
                    mentioned_page_titles = [title.strip() for title in pages_line.split(',')]
                    
                    # Find ALL matching pages from available pages
                    for mentioned_title in mentioned_page_titles:
                        if mentioned_title:  # Skip empty strings
                            for page in available_pages:
                                if (page['page_title'].lower() == mentioned_title.lower() and 
                                    page['page_id'] not in referenced_page_ids):
                                    referenced_pages_info.append({
                                        "page_id": page['page_id'], 
                                        "page_title": page['page_title']
                                    })
                                    referenced_page_ids.add(page['page_id'])
            
            # Enhanced fallback: if no PAGES_USED section found or it's empty, try intelligent page detection
            if not referenced_pages_info:
                # Strategy 1: Look for explicit page mentions in the response
                for page in available_pages:
                    page_title_lower = page['page_title'].lower()
                    ai_response_lower = ai_response.lower()
                    
                    # Check if the page title is mentioned in the response
                    if (page_title_lower in ai_response_lower and 
                        page['page_id'] not in referenced_page_ids):
                        referenced_pages_info.append({
                            "page_id": page['page_id'], 
                            "page_title": page['page_title']
                        })
                        referenced_page_ids.add(page['page_id'])
            
        except Exception as e:
            # If parsing fails, return empty list rather than all pages
            print(f"Error parsing referenced pages: {e}")
            return []
        
        return referenced_pages_info

    def format_page_content(self, page_data):
        """
        Format page content for AI processing
        """
        formatted_content = f"Page Title: {page_data['page_title']}\n"
        formatted_content += "Content:\n"
        
        for element in page_data['content_elements']:
            element_type = element['element_type']
            content = element['content']
            
            if element_type == 'HEADER1':
                formatted_content += f"# {content}\n"
            elif element_type == 'HEADER2':
                formatted_content += f"## {content}\n"
            elif element_type == 'HEADER3':
                formatted_content += f"### {content}\n"
            elif element_type == 'TEXT':
                formatted_content += f"{content}\n"
            elif element_type in ['NUMBERED_LIST', 'BULLET_LIST', 'TODO_LIST']:
                formatted_content += f"List ({element_type}): {content}\n"
        
        formatted_content += "\n---\n\n"
        return formatted_content
    
    def format_conversation_history(self, chat_history):
        """
        Format recent conversation history for AI context
        
        Args:
            chat_history: List of chat messages from MongoDB
        Returns:
            Formatted conversation string
        """
        if not chat_history:
            return ""
        
        conversation = "Recent Conversation History:\n"
        for message in chat_history[-10:]:  # Last 10 messages for context
            sender = "User" if message.get('sender_type') == 'user' else "Assistant"
            content = message.get('message_content', '')
            conversation += f"{sender}: {content}\n"
        
        conversation += "\n---\n\n"
        return conversation
    
    def extract_referenced_pages(self, llm_response, all_pages_info):
        """
        Extract the pages that the LLM actually referenced from its response
        
        Args:
            llm_response: The full response from the LLM
            all_pages_info: List of all page info dicts with page_id and page_title
        
        Returns:
            tuple: (clean_answer, filtered_pages_info)
        """
        try:
            # Split the response to extract the PAGES_USED section
            if "PAGES_USED:" in llm_response:
                parts = llm_response.split("PAGES_USED:")
                clean_answer = parts[0].strip()
                pages_section = parts[1].strip() if len(parts) > 1 else ""
                
                # Extract page names from the PAGES_USED section
                if pages_section:
                    # Split by comma and clean up page names
                    referenced_page_names = [name.strip() for name in pages_section.split(",") if name.strip()]
                    
                    # Filter the pages_info to only include referenced pages
                    filtered_pages_info = []
                    for page_info in all_pages_info:
                        if page_info['page_title'] in referenced_page_names:
                            filtered_pages_info.append(page_info)
                    
                    return clean_answer, filtered_pages_info
                else:
                    # No pages specified in PAGES_USED section
                    return clean_answer, []
            else:
                # No PAGES_USED section found, return original response with empty pages
                return llm_response, []
        
        except Exception as e:
            # If parsing fails, return original response with empty pages
            return llm_response, []
    
    def search_and_answer(self, user_query, workspace_id, company_id=None):
        """
        Main search function that retrieves pages and uses AI to answer
        
        SECURITY CRITICAL: workspace_id is mandatory to prevent cross-account data access
        
        Args:
            user_query: The user's search query
            workspace_id: The workspace ID to filter pages by (MANDATORY for security)
            company_id: The company ID for usage tracking (optional, for tracking only)
        
        Returns:
            dict: Contains 'answer', 'referenced_pages_info', and 'usage_info' keys
        """
        # Security validation: workspace_id must be provided
        if workspace_id is None:
            raise ValueError("SECURITY ERROR: workspace_id is mandatory - cannot search without account isolation")
        
        try:
            # Get all pages with their content for the specific workspace
            pages_data = self.db.get_all_pages_with_content(workspace_id)
            
            if not pages_data:
                return {
                    "answer": f"No pages found in workspace {workspace_id}.",
                    "referenced_pages_info": []
                }
            
            # Extract page names and IDs for the response
            page_ids = [page['page_id'] for page in pages_data]
            
            # Create ALL available pages info for reference (used for extraction later)
            all_pages_info = [
                {"page_id": page['page_id'], "page_title": page['page_title']}
                for page in pages_data
            ]
            
            # Get recent conversation history for context (last 10 messages)
            chat_history = self.mongodb_manager.get_chat_history(workspace_id, limit=10)
            
            # Format all page content for AI
            knowledge_base = ""
            for page in pages_data:
                knowledge_base += self.format_page_content(page)
            
            # Format conversation history for context
            conversation_context = self.format_conversation_history(chat_history)
            
            # Prepare the prompt for OpenAI with conversation context and specific instructions for page attribution
            system_prompt = """You are a helpful search assistant that answers questions based on a knowledge base of user-created pages and maintains conversation context.

The knowledge base contains pages with various content elements like headers, text, and lists. Your job is to:
1. Search through the provided content to find relevant information
2. Use the conversation history to understand context and follow-up questions
3. Provide accurate answers based only on the information in the knowledge base
4. Reference previous parts of the conversation when relevant
5. If the information is not available in the knowledge base, clearly state that
6. IMPORTANT: When referencing information, mention which specific page(s) you used by their EXACT page title
7. Be concise but comprehensive in your responses

MANDATORY REQUIREMENT: You MUST end every response with "PAGES_USED:" followed by a comma-separated list of the exact page titles you referenced. This is REQUIRED for the system to function properly. Examples:

If you use one page:
PAGES_USED: Contact Information

If you use multiple pages:
PAGES_USED: Contact Information, Project Details, Meeting Notes

If you don't use any specific pages:
PAGES_USED: None

CRITICAL: The "PAGES_USED:" line is MANDATORY and must be the last line of your response.

{conversation_context}Knowledge Base:
{knowledge_base}

Remember: Always end with the PAGES_USED line - this is essential for the system to work correctly."""

            user_prompt = f"Current Question: {user_query}\n\nPlease search through the knowledge base and provide a helpful answer. CRITICAL: You MUST end your response with 'PAGES_USED:' followed by the exact page titles you used. This is mandatory for the system to function."
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt.format(
                            conversation_context=conversation_context,
                            knowledge_base=knowledge_base
                        )
                    },
                    {
                        "role": "user", 
                        "content": user_prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.1  # Lower temperature for more consistent instruction following
            )
            
            # Get the AI response
            ai_response = response.choices[0].message.content
            
            # Extract token usage information
            usage_info = None
            if hasattr(response, 'usage') and response.usage:
                usage_info = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
                
                # Track usage in database if company_id is provided
                if company_id:
                    try:
                        self.db.update_openai_usage(
                            company_id=company_id,
                            workspace_id=workspace_id,
                            model=self.model,
                            prompt_tokens=usage_info['prompt_tokens'],
                            completion_tokens=usage_info['completion_tokens'],
                            total_tokens=usage_info['total_tokens']
                        )
                    except Exception as e:
                        # Log error but don't fail the search operation
                        print(f"Warning: Failed to track OpenAI usage: {e}")
            
            # Extract only the pages that were actually referenced by the AI
            referenced_pages_info = self.extract_referenced_pages_from_response(ai_response, all_pages_info)
            
            result = {
                "answer": ai_response,
                "referenced_pages_info": referenced_pages_info
            }
            
            # Include usage info if available
            if usage_info:
                result["usage_info"] = usage_info
            
            return result
            
        except Exception as e:
            return {
                "answer": f"Error processing your query: {str(e)}",
                "referenced_pages_info": [],
                "usage_info": None
            }
    
    def get_knowledge_base_summary(self, workspace_id):
        """
        Get a summary of available pages in the knowledge base for a specific workspace
        
        SECURITY CRITICAL: workspace_id is mandatory to prevent cross-account data access
        
        Args:
            workspace_id: The workspace ID to filter pages by (MANDATORY for security)
        """
        # Security validation: workspace_id must be provided
        if workspace_id is None:
            raise ValueError("SECURITY ERROR: workspace_id is mandatory - cannot access summary without account isolation")
        
        try:
            pages_data = self.db.get_all_pages_with_content(workspace_id)
            
            if not pages_data:
                return f"No pages found in workspace {workspace_id}."
            
            summary = f"Knowledge Base Summary for Workspace {workspace_id} ({len(pages_data)} pages):\n\n"
            
            for page in pages_data:
                content_count = len(page['content_elements'])
                summary += f"• {page['page_title']} (ID: {page['page_id']}) - {content_count} content elements\n"
            
            return summary
            
        except Exception as e:
            return f"Error getting knowledge base summary: {str(e)}"
