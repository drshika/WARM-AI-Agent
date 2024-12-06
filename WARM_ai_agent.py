import pyodbc
import openai
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

class SQLAIAgent:
    def __init__(self, connection_string: str, openai_api_key: str):
        """Initialize the SQL AI Agent with database connection and OpenAI credentials"""
        self.connection_string = connection_string
        openai.api_key = openai_api_key
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish connection to the MS SQL database"""
        try:
            self.conn = pyodbc.connect(self.connection_string)
            self.cursor = self.conn.cursor()
            print("Successfully connected to the database")
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def get_table_schema(self) -> str:
        """Get the schema information for relevant tables"""
        try:
            # Query to get column information for tables
            schema_query = """
            SELECT 
                t.name AS TableName,
                c.name AS ColumnName,
                ty.name AS DataType
            FROM sys.tables t
            INNER JOIN sys.columns c ON t.object_id = c.object_id
            INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
            ORDER BY t.name, c.column_id;
            """
            self.cursor.execute(schema_query)
            schema_info = []
            for row in self.cursor.fetchall():
                schema_info.append(f"Table: {row[0]}, Column: {row[1]}, Type: {row[2]}")
            return "\n".join(schema_info)
        except Exception as e:
            print(f"Error getting schema: {str(e)}")
            return None
            
    def generate_sql_query(self, user_prompt: str) -> str:
        """Generate SQL query using OpenAI"""
        try:
            # Get schema information first
            schema_info = self.get_table_schema()
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": """You are a SQL expert for Microsoft SQL Server. Generate only the SQL query without any explanation.
                        Use SQL Server specific functions like GETDATE() instead of MySQL functions.
                        Here is the database schema:
                        """ + schema_info
                    },
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating SQL query: {str(e)}")
            return None
            
    def execute_query(self, query: str) -> List[Dict[Any, Any]]:
        """Execute SQL query and return results"""
        try:
            self.cursor.execute(query)
            columns = [column[0] for column in self.cursor.description]
            results = []
            
            for row in self.cursor.fetchall():
                results.append(dict(zip(columns, row)))
                
            return results
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            return None
            
    def process_natural_language_query(self, user_prompt: str) -> List[Dict[Any, Any]]:
        """Process natural language query and return results"""
        # Generate SQL query from natural language
        sql_query = self.generate_sql_query(user_prompt)
        
        if sql_query:
            results = self.execute_query(sql_query)
            print(results)
            if results:
                # If we have multiple results
                if len(results) > 1:
                    # Extract numeric values for statistics
                    numeric_values = []
                    for row in results:
                        for value in row.values():
                            # Try to convert to float if possible
                            try:
                                numeric_values.append(float(str(value).strip()))
                            except (ValueError, TypeError):
                                continue
                    
                    if numeric_values:
                        avg = sum(numeric_values) / len(numeric_values)
                        max_val = max(numeric_values)
                        min_val = min(numeric_values)
                        formatted_result = (
                            f"Based on {len(results)} measurements, "
                            f"the average was {avg:.2f}, "
                            f"ranging from {min_val:.2f} to {max_val:.2f}"
                        )
                    else:
                        # If no numeric values found, just join the results
                        values = [f"{k.strip()}: {str(v).strip()}" for row in results for k, v in row.items()]
                        formatted_result = f"Found {len(results)} results: " + ", ".join(values)
                else:
                    # Single result handling (unchanged)
                    formatted_result = "Based on the data, "
                    values = [f"{k.strip()}: {str(v).strip()}" for k, v in results[0].items()]
                    formatted_result += ", ".join(values)
                
                return formatted_result.replace('\n', ' ').replace('\r', '')
        return "No results found for your query."

def main():
    print("Starting WARM AI Agent...")

    # Load environment variables
    load_dotenv()
    
    # Build connection string from environment variables
    connection_str = (
        f"Driver={os.getenv('DB_DRIVER')};"
        f"Server={os.getenv('DB_SERVER')};"
        f"Database={os.getenv('DB_NAME')};"
        f"Trusted_Connection={os.getenv('DB_TRUSTED_CONNECTION')};"
        f"TrustServerCertificate={os.getenv('DB_TRUST_SERVER_CERT')};"
    )

    print("Initializing agent with connection string...")
    agent = SQLAIAgent(connection_str, os.getenv('OPENAI_API_KEY'))
    print("Connecting to database...")
    agent.connect()

    print("Processing natural language query...")
    # Example natural language query
    results = agent.process_natural_language_query("What was the air on july 16th in 2010?")

    if results:
        print("Query results:")
        print(results)
    else:
        print("No results returned from query")

    print("Disconnecting from database...")
    agent.disconnect()
    print("Done.")

if __name__ == "__main__":
    main()
