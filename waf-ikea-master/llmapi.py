from vertexai.generative_models import FunctionDeclaration, Tool

def get_llm_api():
    sql_query_func = FunctionDeclaration(
        name="sql_query",
        description="Get information from data in BigQuery using SQL queries",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query that will help give quantitative answers to the user's question. Always use fully qualified dataset and table names.",
                }
            },
            "required": ["query"],
        },
    )

    barchart_generation_func = FunctionDeclaration(
        name="barchart_generation",
        description="Generate a bar chart from the header names of the provided table context",
        parameters={
            "type": "object",
            "properties": {
                "xaxis": {
                    "type": "string",
                    "description": "Label of the x-axis from the table provided in the context.",
                },
                "yaxis": {
                    "type": "string",
                    "description": "Label of the y-axis from the table provided in the context. Must be numeric.",
                }
            },
            "required": ["xaxis", "yaxis"],
        },
    )

    return Tool(
        function_declarations=[sql_query_func, barchart_generation_func],
    )
