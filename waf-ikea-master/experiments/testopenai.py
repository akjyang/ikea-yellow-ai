from openai import OpenAI
import os

key = "insert_key_here"

client = OpenAI(api_key=key)

def generate_sql_from_text(user_query: str):
    prompt = f"""
    You are an SQL expert working with Google BigQuery.
    Convert the following user question into a valid BigQuery SQL query.

    Database Schema:
    - Table: organization_table (Row, Index, Organization Id, Name, Website, Country, Description, Founded, Industry, Number of employees)
    - Table: people_info (Row, Index, User Id, First Name, Last Name, Sex, Email, Phone, Date of birth, Job Title)

    User Question: "{user_query}"

    SQL Query:
    """

    response = client.chat.completions.create(model="gpt-4-turbo",
    messages=[{"role": "system", "content": "You are an SQL expert."},
              {"role": "user", "content": prompt}],
    temperature=0.2)

    return response.choices[0].message.content

for i in range(5):
    user_query = input("Enter your question: ")
    sql_query = generate_sql_from_text(user_query)
    print(sql_query)
