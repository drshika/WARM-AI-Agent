# WARM SQL AI Agent

A Python-based AI agent that interfaces with a Microsoft SQL Server database (WARM database from Prarie Research Institue) and enables natural language querying using OpenAI's GPT-3.5 model. The agent translates natural language questions into SQL queries and provides formatted, analytical responses.

## Features

- Dual-approach query processing system:
  - Fast LCEL (LangChain Expression Language) chain for simple queries
  - Comprehensive SQL agent for complex queries
- Natural language to SQL query conversion using GPT-4o-mini
- Interactive query verification before execution
- Automatic database schema detection and integration
- Secure database connection handling with Kerberos authentication
- Built-in safety constraints:
  - Read-only operations (SELECT queries only)
  - No data modification capabilities
  - Query verification prompts
- Comprehensive error handling and logging
- Custom prompt templates for accurate SQL generation

## Prerequisites

- Python 3.x
- ODBC Driver 18 for SQL Server
- OpenAI API key
- Access to WARM database
- Kerberos authentication configured

## Installation

1. Clone the repository
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with the following variables:
```
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_SERVER=your_server_name
DB_NAME=your_database_name
DB_TRUSTED_CONNECTION=yes
DB_TRUST_SERVER_CERT=yes
OPENAI_API_KEY=your_openai_api_key
```

## Usage

1. Ensure your Kerberos ticket is valid

```bash
kinit   {netid}@AD.UILLINOIS.EDU
```

2. Run the agent:
```bash
python WARM_ai_agent.py
```

3. Enter your questions in natural language when prompted. Type 'quit' to exit.

EXAMPLE:

```python
> python3 WARM_ai_agent.py
Starting WARM AI Agent...
Initializing agent with connection string...
Connecting to database...
Successfully connected to the database

Enter your question (or 'quit' to exit): how many days in 2010 was it 10c

Processing natural language query...

Proposed response:
To find out how many days in 2010 had an air temperature of 10°C, we can query the `WarmICNData` table, specifically looking for records where the `nAirTemp` is equal to 10. We will also need to filter the results to only include the year 2010 and group the results by date to count the unique days.

Here’s the SQL query that accomplishes this:

```sql
SELECT COUNT(DISTINCT CAST(nDateTime AS DATE)) AS DaysAt10C
FROM WarmICNData
WHERE nAirTemp = 10 AND YEAR(nDateTime) = 2010;
```

### Explanation:
- `SELECT COUNT(DISTINCT CAST(nDateTime AS DATE))`: This part counts the unique days (dates) where the temperature was exactly 10°C.
- `FROM WarmICNData`: This specifies the table we are querying.
- `WHERE nAirTemp = 10`: This filters the records to only include those where the air temperature is 10°C.
- `AND YEAR(nDateTime) = 2010`: This further filters the records to only include those from the year 2010.

You can run this query to get the number of days in 2010 when the temperature was 10°C.

Would you like to execute this SQL query? (y/n): y

Executing query...

Query Results:
{'DaysAt10C': 3}

Would you like to ask another question? (y/n): n
```

## Key Components

### SQLAIAgent Class
- Manages database connections and AI interactions
- Implements both simple and complex query processing chains
- Uses LangChain Expression Language (LCEL) for efficient query processing
- Falls back to more complex agent for complicated queries
- Provides SQL query verification before execution

### Main Functions
- `query()`: Processes natural language queries using AI
- `execute_sql()`: Safely executes verified SQL queries
- `extract_sql_query()`: Extracts SQL queries from AI responses
- `connect()`: Establishes database connection with proper configuration

## Security Features

- Environment variable-based configuration
- Kerberos authentication support
- Trusted connections by default
- Parameterized query execution
- Certificate validation options

## Error Handling

The agent includes comprehensive error handling for:
- Database connection issues
- Query execution errors
- API communication problems
- Schema detection failures
- Data type conversion errors

## AI Implementation

The agent uses a dual-approach system for query processing:
1. Simple LCEL chain for straightforward queries
2. Complex SQL agent for more sophisticated requests

The system uses:
- OpenAI's GPT-4-mini model for query understanding
- LangChain's SQL Database Toolkit
- Custom prompt templates for accurate SQL generation
- Interactive query verification system

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

For issues and enhancement requests, please use the GitHub Issues tracker.