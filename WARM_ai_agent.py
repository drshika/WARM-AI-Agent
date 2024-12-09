from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from sqlalchemy import text
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate

def extract_sql_query(response: str) -> str:
    """Extract SQL query from the agent's response"""
    # Look for SQL between triple backticks
    import re
    sql_match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    return None
class SQLAIAgent:
    def __init__(self, connection_string: str, openai_api_key: str):
        """Initialize the SQL AI Agent with database connection and OpenAI credentials"""
        self.system_prompt = """You are an expert with Microsoft SQL Server. Your role is to help users retrieve information from a database.
        
        Important Rules:
        1. You can ONLY execute SELECT queries
        2. You cannot perform any INSERT, UPDATE, DELETE, DROP, or other data modification operations
        3. If a user requests any data modification, politely explain that you can only help with reading data
        4. Always explain the Microsoft SQL Server query you're using in simple terms
        
        Current Database Schema:
        {schema}
        """
        self.connection_string = connection_string
        self.openai_api_key = openai_api_key
        self.conn = None
        self.cursor = None
        
    def connect(self):
        try:
            connection_params = {
                "driver": "ODBC Driver 18 for SQL Server",
                "TrustServerCertificate": "yes",
                "timeout": "60",
                "connection_timeout": "60"
            }
            
            params = "&".join(f"{key}={value}" for key, value in connection_params.items())
            sqlalchemy_url = f"mssql+pyodbc:///?odbc_connect={self.connection_string}&{params}"
            
            # Initialize database
            self.db = SQLDatabase.from_uri(sqlalchemy_url)
            
            # Initialize LLM 
            llm = ChatOpenAI(temperature=0, api_key=self.openai_api_key, model="gpt-4o-mini")
            
            # Create custom prompt
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt.format(schema=self.db.get_table_info())),
                ("human", "{question}")
            ])

            # Create the LCEL chain
            self.chain = (
                {"question": RunnablePassthrough()} 
                | self.prompt 
                | llm 
                | StrOutputParser()
            )

            # Create toolkit and agent per documentation
            toolkit = SQLDatabaseToolkit(db=self.db, llm=llm)
            self.agent_executor = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                verbose=True,
                agent_type="tool-calling"
            )

            print("Successfully connected to the database")
            
        except Exception as e:
            print(f"Error connecting to database: {str(e)}")
            raise

    def execute_sql(self, query: str) -> List[Dict[str, Any]]:
        """Execute a raw SQL query and return results"""
        try:
            # Execute the query using SQLAlchemy
            with self.db._engine.connect() as connection:
                result = connection.execute(text(query))
                # Convert results to list of dictionaries
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            print(f"Error executing SQL query: {str(e)}")
            return None

    def query(self, question: str) -> Dict[str, Any]:
        """Execute a natural language query using the SQL agent"""
        try:
            # First attempt with simple LCEL chain
            response = self.chain.invoke(question)
            
            # If the response doesn't contain SQL or seems incomplete,
            # fall back to the more complex agent
            if "SELECT" not in response.upper():
                response = self.agent_executor.invoke({"input": question})
                
            return response
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            return None
        
    def disconnect(self):
        """Close database connection"""
        if hasattr(self, 'db') and self.db:
            # Access the engine through _engine attribute
            if hasattr(self.db, '_engine'):
                self.db._engine.dispose()

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

    while True:
        # Get user input
        user_query = input("\nEnter your question (or 'quit' to exit): ")
        
        # Check for exit condition
        if user_query.lower() in ['quit', 'exit', 'q']:
            break
        
        # Check for user running query
        if user_query.lower() in ['run', 'run query', 'execute', 'execute query']:
            response = agent.query(user_query)
            

        print("\nProcessing natural language query...")
        results = agent.query(user_query)

        if results:
            print("\nProposed response:")
            print(results)
            
            # Allow user to verify and continue
            verify = input("\nWould you like to ask another question? (y/n): ")
            if verify.lower() not in ['y', 'yes']:
                break

if __name__ == "__main__":
    main()
