from typing import Dict
import json

import pandas as pd
from google.cloud import bigquery
import streamlit as st

BIGQUERY_DATASET_ID = "ikea_yellow"

class Refinement:
    """
    Represents the refinement of a particular context.
    """
    def display_refinement(self):
        """
        Display the refinement to the user.
        """
        pass

    def use_as_local_context(self) -> str:
        """
        Use the refinement for successive refinements.
        """
        return "There is no previous context to this conversation"

    def completely_intermediate(self) -> str:
        """
        Whether the refinement type is solely an intermediate step
        """
        return False

class ErrorRefinement(Refinement):
    def __init__(self, error_message: str):
        self.error_message = error_message

    def display_refinement(self):
        st.write(self.error_message)

    def use_as_local_context(self):
        return "Received the following error:\n" + self.error_message

class DatabaseRefinement(Refinement):
    def __init__(self):
        client = bigquery.Client()
        context = {}
        
        # Get list of tables
        tables = client.list_tables(BIGQUERY_DATASET_ID)
        table_info = []
        
        for table in tables:
            # Get detailed table info
            table_details = client.get_table(f"{BIGQUERY_DATASET_ID}.{table.table_id}")
            table_info.append({
                "table_id": table.table_id,
                "description": table_details.description,
                "schema": [field.name for field in table_details.schema],
                "row_count": table_details.num_rows
            })
        
        context["dataset_id"] = BIGQUERY_DATASET_ID
        context["tables"] = table_info
        self.raw_data = context

    def completely_intermediate(self) -> str:
        return True

    def display_refinement(self):
        st.write(self.raw_data)
        
    def use_as_local_context(self):
        context_str = f"You have access to the following database structure:\n\nDataset: {self.raw_data['dataset_id']}\n"
        context_str += "Tables:\n"
        for table in self.raw_data["tables"]:
            context_str += f"\n- {table['table_id']}:\n"
            context_str += f"  Description: {table['description']}\n"
            context_str += f"  Columns: {', '.join(table['schema'])}\n"
            context_str += f"  Row count: {table['row_count']}\n"
        return context_str

class TableRefinement(Refinement):
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def display_refinement(self):
        st.table(self.df)

    def use_as_local_context(self) -> str:
        context_str = f"This table was generated during context refinement:\n\n"
        context_str += self.df.to_string()
        return context_str
    
    def get_table(self) -> pd.DataFrame:
        return self.df

class GraphRefinement(Refinement):
    def __init__(self, data: Dict):
        self.raw_data = data

    def display_refinement(self):
        st.bar_chart(self.raw_data["table"], x=self.raw_data["xaxis"], y=self.raw_data["yaxis"])

    def use_as_local_context(self) -> str:
        return "A bar chart was generated from the previous table. Complete the answer to the user's question."