import time
import statsmodels.api as sm
import pandas as pd
import streamlit as st
from google.cloud import bigquery
from vertexai.generative_models import FunctionDeclaration, GenerativeModel, Part, Tool

BIGQUERY_DATASET_ID = "ingka-ushub-whartonfy25-test.ikea_yellow"

list_datasets_func = FunctionDeclaration(
    name="list_datasets",
    description="Get a list of datasets that will help answer the user's question",
    parameters={
        "type": "object",
        "properties": {},
    },
)

list_tables_func = FunctionDeclaration(
    name="list_tables",
    description="List tables in a dataset that will help answer the user's question",
    parameters={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "string",
                "description": "Dataset ID to fetch tables from.",
            }
        },
        "required": [
            "dataset_id",
        ],
    },
)

get_table_func = FunctionDeclaration(
    name="get_table",
    description="Get information about a table, including the description, schema, and number of rows that will help answer the user's question. Always use the fully qualified dataset and table names.",
    parameters={
        "type": "object",
        "properties": {
            "table_id": {
                "type": "string",
                "description": "Fully qualified ID of the table to get information about",
            }
        },
        "required": [
            "table_id",
        ],
    },
)

sql_query_func = FunctionDeclaration(
    name="sql_query",
    description="Get information from data in BigQuery using SQL queries",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL query on a single line that will help give quantitative answers to the user's question when run on a BigQuery dataset and table. In the SQL query, always use the fully qualified dataset and table names.",
            }
        },
        "required": [
            "query",
        ],
    },
)

sql_query_tool = Tool(
    function_declarations=[
        list_datasets_func,
        list_tables_func,
        get_table_func,
        sql_query_func,
    ],
)

model = GenerativeModel(
    "gemini-1.5-pro",
    generation_config={"temperature": 0},
    tools=[sql_query_tool],
)

st.set_page_config(
    page_title="SQL Talk with BigQuery",
    page_icon="vertex-ai.png",
    layout="wide",
)

col1, col2 = st.columns([8, 1])
with col1:
    st.title("SQL Talk with BigQuery")
with col2:
    st.image("vertex-ai.png")

st.subheader("Powered by Function Calling in Gemini")

st.markdown(
    "[Source Code](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/function-calling/sql-talk-app/)   •   [Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling)   •   [Codelab](https://codelabs.developers.google.com/codelabs/gemini-function-calling)   •   [Sample Notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb)"
)

with st.expander("Sample prompts", expanded=True):
    st.write(
        """
        - What kind of information is in this database?
        - What percentage of orders are returned?
        - How is inventory distributed across our regional distribution centers?
        - Do customers typically place more than one order?
        - Which product categories have the highest profit margins?
    """
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"].replace("$", r"\$"))  # noqa: W605
        try:
            with st.expander("Function calls, parameters, and responses"):
                st.markdown(message["backend_details"])
        except KeyError:
            pass

TARGET_TABLE = "country_goals_tbl"
client = bigquery.Client()

def run_regression(df, dependent_var, independent_vars):

    df = df.dropna(subset=[dependent_var] + independent_vars)

    df[dependent_var] = df[dependent_var].astype(float)
    df[independent_vars] = df[independent_vars].astype(float)

    if df.empty:
        st.error("Error: No valid numeric data found for regression after conversion!")
        return "No valid data to run regression."

    X = df[independent_vars]
    X = sm.add_constant(X)  # Adds intercept
    y = df[dependent_var]

    model = sm.OLS(y, X).fit()
    return model.summary()

def find_table_and_run_regression():
    datasets = list(client.list_datasets())
    dataset_ids = [dataset.dataset_id for dataset in datasets]

    if BIGQUERY_DATASET_ID.split(".")[-1] not in dataset_ids:
        st.error(f"Dataset {BIGQUERY_DATASET_ID} not found!")
        return

    tables = list(client.list_tables(BIGQUERY_DATASET_ID))
    table_ids = [table.table_id for table in tables]

    if TARGET_TABLE not in table_ids:
        st.error(f"Table '{TARGET_TABLE}' not found in dataset '{BIGQUERY_DATASET_ID}'!")
        return

    table_ref = f"{BIGQUERY_DATASET_ID}.{TARGET_TABLE}"
    table = client.get_table(table_ref)
    column_names = [field.name for field in table.schema]

    query = f"SELECT * FROM `{table_ref}`"
    df = client.query(query).to_dataframe()

    dependent_var = "cre_net_sales_ty"
    independent_vars = ["online_store_visits_ty", "gross_transactions_ty"]

    if not all(col in df.columns for col in [dependent_var] + independent_vars):
        st.error(f"One or more required columns are missing: {dependent_var}, {independent_vars}")
        return

    result = run_regression(df, dependent_var, independent_vars)
    st.text(result)

def fetch_bigquery_data(query):
    """Executes a BigQuery query and returns a Pandas DataFrame."""
    query_job = client.query(query)
    return query_job.to_dataframe()

queries = {
    "Created Net Sales": """
        SELECT 
            "Total" AS sales_channel,
            ROUND(SUM(cre_net_sales_ty),1) AS created_net_sales,
            ROUND(SUM(cre_net_sales_ly),1) AS created_net_sales_ly,
            ROUND((SUM(cre_net_sales_ty) / SUM(cre_net_sales_ly)) * 100,1) AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE date BETWEEN '2024-01-01' AND '2024-12-31'
        UNION ALL
        SELECT 
            sales_channel,
            ROUND(SUM(cre_net_sales_ty),1) AS created_net_sales,
            ROUND(SUM(cre_net_sales_ly),1) AS created_net_sales_ly,
            ROUND((SUM(cre_net_sales_ty) / SUM(cre_net_sales_ly)) * 100,1) AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE date BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY sales_channel;
    """,

    "Created Net Transactions": """
        SELECT 
            "Total" AS sales_channel,
            ROUND(SUM(cre_net_transactions_ty),1) AS created_net_transactions,
            ROUND(SUM(cre_net_transactions_ly),1) AS created_net_transactions_ly,
            ROUND((SUM(cre_net_transactions_ty) / SUM(cre_net_transactions_ly)) * 100,1) AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE date BETWEEN '2024-01-01' AND '2024-12-31'
        UNION ALL
        SELECT 
            sales_channel,
            ROUND(SUM(cre_net_transactions_ty),1) AS created_net_transactions,
            ROUND(SUM(cre_net_transactions_ly),1) AS created_net_transactions_ly,
            ROUND((SUM(cre_net_transactions_ty) / SUM(cre_net_transactions_ly)) * 100,1) AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE date BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY sales_channel;
    """,

    "Average Order Value": """
        SELECT 
            "Total" AS sales_channel,
            ROUND(SUM(cre_net_sales_ty) / SUM(cre_net_transactions_ty),2) AS avg_order_value,
            ROUND((SUM(cre_net_sales_ty) / SUM(cre_net_transactions_ty)) / 
                  (SUM(cre_net_sales_ly) / SUM(cre_net_transactions_ly)) * 100,1) AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE date BETWEEN '2024-01-01' AND '2024-12-31'
        UNION ALL
        SELECT 
            sales_channel,
            ROUND(SUM(cre_net_sales_ty) / SUM(cre_net_transactions_ty),2) AS avg_order_value,
            ROUND((SUM(cre_net_sales_ty) / SUM(cre_net_transactions_ty)) / 
                  (SUM(cre_net_sales_ly) / SUM(cre_net_transactions_ly)) * 100,1) AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE date BETWEEN '2024-01-01' AND '2024-12-31'
        GROUP BY sales_channel;
    """,

    "Store Visitation": """
        SELECT 
            SUM(online_store_visits_ty) AS store_visitation,
            (SUM(online_store_visits_ty) / SUM(online_store_visits_ly)) * 100 AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE sales_channel = 'Store'
        AND date BETWEEN '2024-01-01' AND '2024-12-31';
    """,

    "National Online Sessions": """
        SELECT 
            SUM(online_store_visits_ty) AS national_online_sessions,
            (SUM(online_store_visits_ty) / SUM(online_store_visits_ly)) * 100 AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE sales_channel = 'Online'
        AND date BETWEEN '2024-01-01' AND '2024-12-31';
    """,

    "Store Conversion": """
        SELECT 
            (SUM(cre_net_transactions_ty) / SUM(online_store_visits_ty)) * 100 AS store_conversion,
            ((SUM(cre_net_transactions_ty) / SUM(online_store_visits_ty)) / 
            (SUM(cre_net_transactions_ly) / SUM(online_store_visits_ly))) * 100 AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE sales_channel = 'Store'
        AND date BETWEEN '2024-01-01' AND '2024-12-31';
    """,

    "Online Conversion": """
        SELECT 
            (SUM(cre_net_transactions_ty) / SUM(online_store_visits_ty)) * 100 AS online_conversion,
            ((SUM(cre_net_transactions_ty) / SUM(online_store_visits_ty)) / 
            (SUM(cre_net_transactions_ly) / SUM(online_store_visits_ly))) * 100 AS yoy_index
        FROM `ingka-ushub-whartonfy25-test.ikea_yellow.country_goals_tbl`
        WHERE sales_channel = 'Online'
        AND date BETWEEN '2024-01-01' AND '2024-12-31';
    """
}

st.title("HFO Sales Tree (2024)")

st.subheader("Sales Performance")
sales_df = fetch_bigquery_data(queries["Created Net Sales"])
transactions_df = fetch_bigquery_data(queries["Created Net Transactions"])
st.dataframe(sales_df)
st.dataframe(transactions_df)

st.subheader("Performance Breakdown")
col1, col2 = st.columns(2)

with col1:
    avg_order_value_df = fetch_bigquery_data(queries["Average Order Value"])
    st.dataframe(avg_order_value_df)

    store_visitation_df = fetch_bigquery_data(queries["Store Visitation"])
    st.dataframe(store_visitation_df)

    store_conversion_df = fetch_bigquery_data(queries["Store Conversion"])
    st.dataframe(store_conversion_df)

with col2:
    online_sessions_df = fetch_bigquery_data(queries["National Online Sessions"])
    st.dataframe(online_sessions_df)

    online_conversion_df = fetch_bigquery_data(queries["Online Conversion"])
    st.dataframe(online_conversion_df)

if prompt := st.chat_input("Ask me about information in the database..."):

    if "run regression" in prompt.lower():
        find_table_and_run_regression()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        chat = model.start_chat()
        client = bigquery.Client()

        prompt += """
            Please give a concise, high-level summary followed by detail in
            plain language about where the information in your response is
            coming from in the database. Only use information that you learn
            from BigQuery, do not make up information.
            """

        try:
            response = chat.send_message(prompt)
            response = response.candidates[0].content.parts[0]

            print(response)

            api_requests_and_responses = []
            backend_details = ""

            function_calling_in_process = True
            while function_calling_in_process:
                try:
                    params = {}
                    for key, value in response.function_call.args.items():
                        params[key] = value

                    print(response.function_call.name)
                    print(params)

                    if response.function_call.name == "list_datasets":
                        api_response = client.list_datasets()
                        api_response = BIGQUERY_DATASET_ID
                        api_requests_and_responses.append(
                            [response.function_call.name, params, api_response]
                        )

                    if response.function_call.name == "list_tables":
                        api_response = client.list_tables(params["dataset_id"])
                        api_response = str([table.table_id for table in api_response])
                        api_requests_and_responses.append(
                            [response.function_call.name, params, api_response]
                        )

                    if response.function_call.name == "get_table":
                        api_response = client.get_table(params["table_id"])
                        api_response = api_response.to_api_repr()
                        api_requests_and_responses.append(
                            [
                                response.function_call.name,
                                params,
                                [
                                    str(api_response.get("description", "")),
                                    str(
                                        [
                                            column["name"]
                                            for column in api_response["schema"][
                                                "fields"
                                            ]
                                        ]
                                    ),
                                ],
                            ]
                        )
                        api_response = str(api_response)

                    if response.function_call.name == "sql_query":
                        job_config = bigquery.QueryJobConfig(
                            maximum_bytes_billed=100000000
                        )  # Data limit per query job
                        try:
                            cleaned_query = (
                                params["query"]
                                .replace("\\n", " ")
                                .replace("\n", "")
                                .replace("\\", "")
                            )
                            query_job = client.query(
                                cleaned_query, job_config=job_config
                            )
                            api_response = query_job.result()
                            api_response = str([dict(row) for row in api_response])
                            api_response = api_response.replace("\\", "").replace(
                                "\n", ""
                            )
                            api_requests_and_responses.append(
                                [response.function_call.name, params, api_response]
                            )
                        except Exception as e:
                            error_message = f"""
                            We're having trouble running this SQL query. This
                            could be due to an invalid query or the structure of
                            the data. Try rephrasing your question to help the
                            model generate a valid query. Details:

                            {str(e)}"""
                            st.error(error_message)
                            api_response = error_message
                            api_requests_and_responses.append(
                                [response.function_call.name, params, api_response]
                            )
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "content": error_message,
                                }
                            )

                    print(api_response)

                    response = chat.send_message(
                        Part.from_function_response(
                            name=response.function_call.name,
                            response={
                                "content": api_response,
                            },
                        ),
                    )
                    response = response.candidates[0].content.parts[0]

                    backend_details += "- Function call:\n"
                    backend_details += (
                        "   - Function name: ```"
                        + str(api_requests_and_responses[-1][0])
                        + "```"
                    )
                    backend_details += "\n\n"
                    backend_details += (
                        "   - Function parameters: ```"
                        + str(api_requests_and_responses[-1][1])
                        + "```"
                    )
                    backend_details += "\n\n"
                    backend_details += (
                        "   - API response: ```"
                        + str(api_requests_and_responses[-1][2])
                        + "```"
                    )
                    backend_details += "\n\n"
                    with message_placeholder.container():
                        st.markdown(backend_details)

                except AttributeError:
                    function_calling_in_process = False

            time.sleep(3)

            full_response = response.text
            with message_placeholder.container():
                st.markdown(full_response.replace("$", r"\$"))  # noqa: W605
                with st.expander("Function calls, parameters, and responses:"):
                    st.markdown(backend_details)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": full_response,
                    "backend_details": backend_details,
                }
            )
        except Exception as e:
            print(e)
            error_message = f"""
                Something went wrong! We encountered an unexpected error while
                trying to process your request. Please try rephrasing your
                question. Details:

                {str(e)}"""
            st.error(error_message)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                }
            )
