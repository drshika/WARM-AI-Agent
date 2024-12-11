# Standard library imports
import os
from typing import List, Dict, Any, Optional, Tuple, TypedDict, Literal

# Third-party imports
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from sqlalchemy import text

def extract_sql_query(response: str) -> Optional[str]:
    if isinstance(response, dict):
        return response.get('sql_query')
    return None

class LocationMapper:
    STATION_MAPPING = {
        'BELLEVILLE': 'FRM',
        'BIG BEND': 'BBC', 
        'BONDVILLE': 'BVL',
        'BROWNSTOWN': 'BRW',
        'CARBONDALE': 'SIU',
        'CHAMPAIGN': 'CMI',
        'DEKALB': 'DEK',
        'DIXON SPRINGS': 'DXS',
        'FAIRFIELD': 'FAI',
        'FREEPORT': 'FRE',
        'KILBOURNE': 'SFM',
        'MONMOUTH': 'MON',
        'OLNEY': 'OLN',
        'PEORIA': 'ICC',
        'PERRY': 'ORR',
        'REND LAKE': 'RND',
        'SNICARTE': 'SNI',
        'ST. CHARLES': 'STC',
        'SPRINGFIELD': 'LLC',
        'STELLE': 'STE'
    }

    @classmethod
    def get_station_code(cls, location: str) -> Optional[str]:
        return cls.STATION_MAPPING.get(location.upper())

    @classmethod
    def get_all_locations(cls) -> List[str]:
        return list(cls.STATION_MAPPING.keys())

class SQLResponse(TypedDict):
    explanation: str
    sql_query: str
    suggested_actions: List[str]

class QueryIntent(TypedDict):
    needs_location: bool
    location_terms: List[str]
    query_type: Literal["location_specific", "general", "comparison"]

class AgentState(TypedDict):
    question: str
    intent: Optional[QueryIntent]
    processed_question: Optional[str]
    sql_response: Optional[SQLResponse]
    results: Optional[List[Dict[str, Any]]]
    error: Optional[str]

class SQLAIAgent:
    def __init__(self, connection_string: str, openai_api_key: str):
        self.base_system_prompt = """You are an expert with Microsoft SQL Server. Your role is to help users retrieve information from a database.
        
        Important Rules:
        1. You can ONLY execute SELECT queries
        2. You cannot perform any INSERT, UPDATE, DELETE, DROP, or other data modification operations
        3. If a user requests any data modification, politely explain that you can only help with reading data
        4. Always explain the Microsoft SQL Server query you're using in simple terms
        5. When users mention Illinois locations, map them to their corresponding station codes:
           {location_mappings}
        6. For locations not in the list, I will provide the nearest available station.

        Current Database Schema:
        {schema}
        """

        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query intent classifier for a weather station database. 
            Analyze the query to determine if it needs location processing.
            
            The database contains weather stations across Illinois with specific station codes.
            
            Output should be valid JSON with this exact format:
            {{
                "needs_location": boolean,
                "location_terms": string[],
                "query_type": "location_specific" | "general" | "comparison"
            }}
            
            Examples:
            Input: "What's the temperature in Champaign?"
            Output: {{
                "needs_location": true,
                "location_terms": ["Champaign"],
                "query_type": "location_specific"
            }}
            
            Input: "Show me all stations with temperature above 75"
            Output: {{
                "needs_location": false,
                "location_terms": [],
                "query_type": "general"
            }}
            
            Input: "Compare rainfall between Peoria and Springfield"
            Output: {{
                "needs_location": true,
                "location_terms": ["Peoria", "Springfield"],
                "query_type": "comparison"
            }}"""),
            ("human", "{question}")
        ])

        self.connection_string = connection_string
        self.openai_api_key = openai_api_key
        self.conn = None
        self.cursor = None

        self.workflow = self._create_graph()

    def _classify_intent(self, state: AgentState) -> AgentState:
        try:
            # print("Debug: Classifying intent for question:", state["question"])
            intent = self.intent_chain.invoke(state["question"])
            # print("Debug: Intent result:", intent)
            return {"intent": intent, **state}
        except Exception as e:
            # print("Debug: Intent classification error:", str(e))
            return {"error": f"Intent classification failed: {str(e)}", **state}
    
    def _execute_sql(self, state: AgentState) -> AgentState:
        if not state.get("sql_response"):
            return {"error": "No SQL query to execute", **state}
        
        try:
            results = self.execute_sql(state["sql_response"]["sql_query"])
            return {"results": results, **state}
        except Exception as e:
            return {"error": f"SQL execution failed: {str(e)}", **state}
    
    def _process_locations_helper(self, state: Dict[str, Any]) -> str:
        question = state["question"]
        intent = state["intent"]
        
        for location in intent["location_terms"]:
            station_code = LocationMapper.get_station_code(location)
            if station_code:
                question = question.lower().replace(
                    location.lower(),
                    f"{location} (Station: {station_code})"
                )
        
        return question
    
    def _process_locations(self, state: AgentState) -> AgentState:
        # print("Debug: Processing locations. State:", state)
        
        if not state.get("intent"):
            return {**state, "error": "No intent found in state"}
        
        if not state["intent"].get("needs_location", False):
            return {**state, "processed_question": state["question"]}
        
        try:
            processed = self._process_locations_helper(state)
            return {**state, "processed_question": processed}
        except Exception as e:
            # print(f"Debug: Location processing error: {str(e)}")
            return {**state, "error": f"Location processing failed: {str(e)}"}

    def _generate_sql(self, state: AgentState) -> AgentState:
        # print("Debug: Generating SQL. State:", state)
        
        if state.get("error"):
            return state
        
        try:
            question = state.get("processed_question", state["question"])
            sql_response = self.query_chain.invoke(question)
            return {**state, "sql_response": sql_response}
        except Exception as e:
            # print(f"Debug: SQL generation error: {str(e)}")
            return {**state, "error": f"SQL generation failed: {str(e)}"}

    def _should_execute_sql(self, state: AgentState) -> Literal["execute", "error", "end"]:
        # print("Debug: Checking execution state:", state)
        
        if state.get("error"):
            return "error"
        if state.get("sql_response"):
            return "execute"
        return "end"
    
    def _create_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("process_locations", self._process_locations)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("execute_sql", self._execute_sql)

        workflow.add_edge("classify_intent", "process_locations")
        workflow.add_edge("process_locations", "generate_sql")
        
        workflow.add_conditional_edges(
            "generate_sql",
            self._should_execute_sql,
            {
                "execute": "execute_sql",
                "error": END,
                "end": END
            }
        )
        
        workflow.add_edge("execute_sql", END)

        workflow.set_entry_point("classify_intent")

        return workflow.compile()

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
            
            self.db = SQLDatabase.from_uri(sqlalchemy_url)
            
            llm = ChatOpenAI(temperature=0, api_key=self.openai_api_key, model="gpt-4o-mini")
            
            location_mappings = "\n".join(
                f"- {location}: {code}" 
                for location, code in LocationMapper.STATION_MAPPING.items()
            )

            self.query_prompt = ChatPromptTemplate.from_messages([
                ("system", self.base_system_prompt + """
                You must respond in the following JSON format:
                {
                    "explanation": "A plain English explanation of what the query does",
                    "sql_query": "The SQL query to execute",
                    "suggested_actions": ["Optional list of follow-up actions or warnings"]
                }
                
                Example Response:
                {
                    "explanation": "This query finds the average temperature at the Champaign station for the past week",
                    "sql_query": "SELECT AVG(temperature) FROM weather_data WHERE station_code = 'CMI' AND date >= DATEADD(day, -7, GETDATE())",
                    "suggested_actions": ["Consider comparing with historical averages", "Check for missing data points"]
                }
                """),
                ("human", "{question}")
            ])

            self.query_parser = JsonOutputParser(pydantic_object=SQLResponse)
            self.intent_parser = JsonOutputParser(pydantic_object=QueryIntent)
            
            # print("Debug: Creating intent chain...")
            self.intent_chain = (
                self.intent_prompt 
                | llm 
                | self.intent_parser
            )
            # print("Debug: Intent chain created successfully")
            test_result = self.intent_chain.invoke("test question")
            # print("Debug: Test intent chain result:", test_result)
            
            location_chain = (
                self.query_prompt 
                | llm 
                | self.query_parser
            )

            direct_chain = (
                self.query_prompt 
                | llm 
                | self.query_parser
            )

            def branch_chain(inputs: dict):
                question = inputs["question"]
                intent_result = self.intent_chain.invoke(question)
                
                if intent_result["needs_location"]:
                    processed_question = self._process_locations({
                        "question": question, 
                        "intent": intent_result
                    })
                    return location_chain.invoke(processed_question)
                else:
                    return direct_chain.invoke(question)

            self.chain = branch_chain

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
        try:
            with self.db._engine.connect() as connection:
                result = connection.execute(text(query))
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            print(f"Error executing SQL query: {str(e)}")
            return None

    def preprocess_query(self, question: str) -> Tuple[str, Optional[str]]:
        processed_question = question
        matched_station = None
        
        for location in LocationMapper.get_all_locations():
            if location.lower() in question.lower():
                station_code = LocationMapper.get_station_code(location)
                processed_question = question.lower().replace(
                    location.lower(), 
                    f"{location} (Station: {station_code})"
                )
                matched_station = station_code
                break
                
        return processed_question, matched_station
    
    def _verify_initialization(self):
        required_attributes = [
            'intent_prompt',
            'intent_chain',
            'intent_parser',
            'query_prompt',
            'query_parser',
            'db',
            'workflow'
        ]
        
        missing = []
        for attr in required_attributes:
            if not hasattr(self, attr):
                missing.append(attr)
            elif getattr(self, attr) is None:
                missing.append(f"{attr} (None)")
        
        if missing:
            raise RuntimeError(f"Missing or None attributes: {', '.join(missing)}")
    
    def query(self, question: str) -> Dict[str, Any]:
        try:
            self._verify_initialization()

            initial_state = AgentState(
                question=question,
                intent=None,
                processed_question=None,
                sql_response=None,
                results=None,
                error=None
            )
            
            # print("Debug: Initial state:", initial_state)
            final_state = self.workflow.invoke(initial_state)
            # print("Debug: Final state:", final_state)
            
            if final_state.get("error"):
                print(f"Error in workflow: {final_state['error']}")
                agent_response = self.agent_executor.invoke({"input": question})
                return {
                    "explanation": "Fallback to agent executor",
                    "sql_query": extract_sql_query(agent_response),
                    "results": agent_response,
                    "suggested_actions": ["Workflow failed, used fallback agent"]
                }
            
            return {
                "explanation": final_state.get("sql_response", {}).get("explanation"),
                "sql_query": final_state.get("sql_response", {}).get("sql_query"),
                "results": final_state.get("results"),
                "suggested_actions": final_state.get("sql_response", {}).get("suggested_actions", [])
            }
            
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            return {
                "error": str(e),
                "results": None,
                "sql_query": None,
                "suggested_actions": ["Error occurred, please try again"]
            }
        
    def disconnect(self):
        if hasattr(self, 'db') and self.db:
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

        print("\nProcessing natural language query...")
        results = agent.query(user_query)

        if results:
            print("\nProposed response:")
            print(results)
            
            # Extract SQL query if present
            sql_query = extract_sql_query(results)
            if sql_query:
                verify = input("\nWould you like to execute this SQL query? (y/n): ")
                if verify.lower() in ['y', 'yes']:
                    print("\nExecuting query...")
                    results = agent.execute_sql(sql_query)
                    if results:
                        print("\nQuery Results:")
                        for row in results:
                            print(row)

            # Allow user to verify and continue
            verify = input("\nWould you like to ask another question? (y/n): ")
            if verify.lower() not in ['y', 'yes']:
                break

if __name__ == "__main__":
    main()
