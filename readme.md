# WARM SQL AI Agent

A Python-based AI agent that interfaces with a Microsoft SQL Server database (WARM database from Prarie Research Institue) and enables natural language querying using OpenAI's GPT-3.5 model. The agent translates natural language questions into SQL queries and provides formatted, analytical responses.

## Features

- Natural language to SQL query conversion using GPT-3.5
- Automatic database schema detection and analysis
- Statistical analysis of numeric query results
- Secure database connection handling with Kerberos authentication
- Formatted result output with data summaries
- Comprehensive error handling and logging

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
2. Edit natural language queries in `main()` function
3. Run the agent:
```bash
python WARM_ai_agent.py
```

EXAMPLE:

```python
> python3 WARM_ai_agent.py 
Starting WARM AI Agent...
Initializing agent with connection string...
Connecting to database...
Successfully connected to the database
Processing natural language query...
[{'nAirTemp': Decimal('19.8000')}, {'nAirTemp': Decimal('19.0200')}, {'nAirTemp': Decimal('19.2200')}, {'nAirTemp': Decimal('18.4800')}, {'nAirTemp': Decimal('18.8200')}, {'nAirTemp': Decimal('18.3600')}, {'nAirTemp': Decimal('18.4000')}, {'nAirTemp': Decimal('18.1200')}, {'nAirTemp': Decimal('18.6900')}, {'nAirTemp': Decimal('17.7000')}, {'nAirTemp': Decimal('18.3500')}, {'nAirTemp': Decimal('18.3700')}, {'nAirTemp': Decimal('18.4400')}, {'nAirTemp': Decimal('20.8300')}, {'nAirTemp': Decimal('20.7500')}, {'nAirTemp': Decimal('21.5500')}, {'nAirTemp': Decimal('23.7400')}, {'nAirTemp': Decimal('24.5000')}, {'nAirTemp': Decimal('26.2900')}, {'nAirTemp': Decimal('26.0000')}, {'nAirTemp': Decimal('27.1000')}, {'nAirTemp': Decimal('27.1500')}, {'nAirTemp': Decimal('27.8400')}, {'nAirTemp': Decimal('28.4300')}, {'nAirTemp': Decimal('29.6800')}, {'nAirTemp': Decimal('28.6000')}, {'nAirTemp': Decimal('29.4700')}, {'nAirTemp': Decimal('30.0000')}, {'nAirTemp': Decimal('29.3200')}, {'nAirTemp': Decimal('29.8700')}, {'nAirTemp': Decimal('30.2400')}, {'nAirTemp': Decimal('29.6900')}, {'nAirTemp': Decimal('30.0900')}, {'nAirTemp': Decimal('30.5500')}, {'nAirTemp': Decimal('30.0700')}, {'nAirTemp': Decimal('30.1800')}, {'nAirTemp': Decimal('30.5400')}, {'nAirTemp': Decimal('29.9700')}, {'nAirTemp': Decimal('29.8500')}, {'nAirTemp': Decimal('30.2200')}, {'nAirTemp': Decimal('29.9000')}, {'nAirTemp': Decimal('29.5800')}, {'nAirTemp': Decimal('29.2600')}, {'nAirTemp': Decimal('29.2800')}, {'nAirTemp': Decimal('28.8600')}, {'nAirTemp': Decimal('27.5800')}, {'nAirTemp': Decimal('27.8200')}, {'nAirTemp': Decimal('27.4700')}, {'nAirTemp': Decimal('24.4800')}, {'nAirTemp': Decimal('25.7300')}, {'nAirTemp': Decimal('25.6600')}, {'nAirTemp': Decimal('23.2900')}, {'nAirTemp': Decimal('23.5000')}, {'nAirTemp': Decimal('23.5600')}, {'nAirTemp': Decimal('22.1100')}, {'nAirTemp': Decimal('22.6000')}, {'nAirTemp': Decimal('22.4800')}, {'nAirTemp': Decimal('20.6800')}, {'nAirTemp': Decimal('21.8600')}, {'nAirTemp': Decimal('21.9400')}]
Query results:
Based on 60 measurements, the average was 25.03, ranging from 17.70 to 30.55
Disconnecting from database...
Done.
```

## Key Components

### SQLAIAgent Class
- Manages database connections and AI interactions
- Handles schema detection and query generation
- Provides statistical analysis of results

### Main Functions
- `generate_sql_query()`: Converts natural language to SQL using GPT-3.5
- `execute_query()`: Safely executes SQL queries with error handling
- `process_natural_language_query()`: Processes queries and provides analytical results
- `get_table_schema()`: Automatically detects and formats database schema

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

## Statistical Analysis

For numeric results, the agent automatically calculates:
- Average values
- Minimum and maximum ranges
- Result count and summaries

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

For issues and enhancement requests, please use the GitHub Issues tracker.