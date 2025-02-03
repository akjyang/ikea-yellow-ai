import refinement as rf
from google.cloud import bigquery

MAX_BYTES_BILLED = 100000000000000

class ContextFrame:
    """
    ContextFrame is a class that represents a frame in the context of an ongoing context refinement chat session
    """
    def __init__(self):
        self.refinements = [self.execute_database_refinement()]
        self.terminated = False
        self.available_refinements = []
        self.update_available_refinements()
        self.response = "I retrieved the following from big query."
    
    def get_response(self):
        return self.response
        
    def set_response(self, response):
        self.response = response

    def extract_history(self):
        return self.refinements

    def get_local_context(self):
        local_context = self.refinements[-1].use_as_local_context()
        full_prompt = f"""
        This is some context that has been refined over iterations:
        {local_context}

        Answer the above prompt given the context.
        """
        return full_prompt

    def continue_refining(self):
        return not self.terminated

    def update_available_refinements(self):
        if (type(self.refinements[-1]) == rf.DatabaseRefinement):
            self.available_refinements = ["sql_query"]
        if (type(self.refinements[-1]) == rf.ErrorRefinement) or (type(self.refinements[-1]) == rf.GraphRefinement):
            self.available_refinements = []
        if (type(self.refinements[-1]) == rf.TableRefinement):
            self.available_refinements = ["barchart_generation"]

    def get_available_refinements(self):
        return self.available_refinements

    def execute_refinement(self, func_name, params):
        """
        Execute a refinement function based on the function name and parameters
        """
        curr_refinement = self.execute_error_refinement("A valid function call was not generated")
        if func_name == "sql_query":
            curr_refinement = self.execute_sql_refinement(params)
        elif func_name == "barchart_generation":
            curr_refinement = self.execute_barchart_refinement(params)
        self.refinements.append(curr_refinement)
        self.update_available_refinements() 
        return curr_refinement

    def execute_error_refinement(self, e_msg) -> rf.Refinement:
        self.terminated = True
        return rf.ErrorRefinement(e_msg)

    def execute_database_refinement(self) -> rf.Refinement:
        return rf.DatabaseRefinement()

    def execute_sql_refinement(self, params) -> rf.Refinement:
        client = bigquery.Client()
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=MAX_BYTES_BILLED
        )
        try:
            cleaned_query = (
                params["query"]
                .replace("\\n", " ")
                .replace("\n", "")
                .replace("\\", "")
            )
            df = client.query_and_wait(
                cleaned_query, job_config=job_config
            ).to_dataframe()
            return rf.TableRefinement(df)
        except Exception as e:
            return self.execute_error_refinement(str(e))

    def execute_barchart_refinement(self, params) -> rf.Refinement:
        # Use the previous table in the context to generate a graph
        if type(self.refinements[-1]) != rf.TableRefinement:
            raise Exception("Can only generate graph provided a table context")
        data = {
            "table": self.refinements[-1].get_table(),
            "xaxis": params["xaxis"],
            "yaxis": params["yaxis"]
        }
        return rf.GraphRefinement(data)