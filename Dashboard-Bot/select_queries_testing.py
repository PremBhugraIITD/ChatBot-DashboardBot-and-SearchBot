#!/usr/bin/env python3
"""
Test script for running SELECT queries on MySQL database
Uses environment variables for database credentials
"""

import mysql.connector
import pandas as pd
from dotenv import load_dotenv
import os
from typing import Dict, Any, List, Optional

# Load environment variables
load_dotenv(override=True)

class DatabaseTester:
    """Class to test database SELECT queries"""
    
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
            print("✅ Database connection successful!")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    def test_connection(self):
        """Test database connection and show basic info"""
        if not self.connection:
            print("❌ No database connection")
            return
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Get database version
            cursor.execute("SELECT VERSION() as version")
            version_info = cursor.fetchone()
            print(f"📊 MySQL Version: {version_info['version']}")
            
            # Get current database name
            cursor.execute("SELECT DATABASE() as db_name")
            db_info = cursor.fetchone()
            print(f"🗄️  Current Database: {db_info['db_name']}")
            
            cursor.close()
            
        except Exception as e:
            print(f"❌ Error testing connection: {str(e)}")
    
    def show_tables(self):
        """Show all tables in the database"""
        if not self.connection:
            print("❌ No database connection")
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print("\n📋 Available Tables:")
            print("-" * 30)
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table[0]}")
            
            cursor.close()
            return [table[0] for table in tables]
            
        except Exception as e:
            print(f"❌ Error showing tables: {str(e)}")
            return []
    
    def describe_table(self, table_name: str):
        """Show table structure"""
        if not self.connection:
            print("❌ No database connection")
            return
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            
            print(f"\n📊 Table Structure: {table_name}")
            print("-" * 50)
            for col in columns:
                print(f"Column: {col['Field']} | Type: {col['Type']} | Null: {col['Null']} | Key: {col['Key']}")
            
            cursor.close()
            
        except Exception as e:
            print(f"❌ Error describing table {table_name}: {str(e)}")
    
    def run_select_query(self, query: str, limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """Run a SELECT query and return results as DataFrame"""
        if not self.connection:
            print("❌ No database connection")
            return None
        
        try:
            # Add LIMIT if specified and not already in query
            if limit and "LIMIT" not in query.upper():
                query = f"{query.rstrip(';')} LIMIT {limit}"
            
            print(f"\n🔍 Executing Query:")
            print(f"   {query}")
            print("-" * 50)
            
            # Execute query and get results
            df = pd.read_sql(query, self.connection)
            
            print(f"✅ Query executed successfully!")
            print(f"📊 Results: {len(df)} rows × {len(df.columns)} columns")
            
            # Display results
            if not df.empty:
                print("\n📋 Data Preview:")
                print(df.head(10).to_string(index=False))
                
                if len(df) > 10:
                    print(f"\n... ({len(df) - 10} more rows)")
            else:
                print("⚠️  No data returned")
            
            return df
            
        except Exception as e:
            print(f"❌ Error executing query: {str(e)}")
            return None
    
    def quick_explore_table(self, table_name: str, limit: int = 10):
        """Quick exploration of a table"""
        print(f"\n🔍 Quick Exploration: {table_name}")
        print("=" * 50)
        
        # Show table structure
        self.describe_table(table_name)
        
        # Show row count
        count_query = f"SELECT COUNT(*) as total_rows FROM `{table_name}`"
        count_df = self.run_select_query(count_query)
        
        # Show sample data
        sample_query = f"SELECT * FROM `{table_name}`"
        self.run_select_query(sample_query, limit=limit)
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("🔒 Database connection closed")

def main():
    """Main interactive testing function"""
    print("🚀 MySQL Database Query Tester")
    print("=" * 40)
    
    # Initialize database tester
    db_tester = DatabaseTester()
    
    if not db_tester.connection:
        print("❌ Cannot proceed without database connection")
        return
    
    # Test connection
    db_tester.test_connection()
    
    # Show available tables
    tables = db_tester.show_tables()
    
    if not tables:
        print("❌ No tables found in database")
        db_tester.close_connection()
        return
    
    try:
        while True:
            print("\n" + "=" * 50)
            print("OPTIONS:")
            print("1. 💻 Run custom SELECT query")
            print("2. ❌ Exit")
            print("=" * 50)
            
            choice = input("Enter your choice (1-2): ").strip()
            
            if choice == "1":
                print("\n💻 Enter your SELECT query:")
                print("(Type 'cancel' to go back)")
                query = input("Query: ").strip()
                
                if query.lower() != 'cancel' and query:
                    if not query.upper().startswith('SELECT'):
                        print("⚠️  Only SELECT queries are allowed")
                        continue
                    
                    limit = input("Enter row limit (press Enter for no limit): ").strip()
                    limit = int(limit) if limit.isdigit() else None
                    
                    result_df = db_tester.run_select_query(query, limit)
                    
                    if result_df is not None and not result_df.empty:
                        export = input("\n💾 Export results to CSV? (y/n): ").strip().lower()
                        if export == 'y':
                            filename = input("Enter filename (without .csv): ").strip()
                            if filename:
                                try:
                                    result_df.to_csv(f"{filename}.csv", index=False)
                                    print(f"✅ Results exported to {filename}.csv")
                                except Exception as e:
                                    print(f"❌ Export failed: {str(e)}")
            
            elif choice == "2":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please select 1-2.")
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    
    finally:
        db_tester.close_connection()

if __name__ == "__main__":
    main()
