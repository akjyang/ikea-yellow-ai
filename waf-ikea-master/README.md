# Ikea Data Analysis Tool

## General Architecture
The tool works by providing the model with a prompt as well as an api of
function calls. Initially, as background context, the model is provided the
database schema along with the prompt. The model can then refine that
context by generating a sql query to fetch a table of data from BigQuery.
If satifised, the model will output a response. Otherwise, the model can
continue to refine the context of its information through additional
steps (further SQL queries/graph generation).

The whole history of this reasoning is stored for every interaction.

The UI is created using Streamlit in order to get something up and running
asap.

## Extending the Function API
I am currently working on adding documentation to be able to add new
functions. This will improve upon the richness of the api available to the
llm, and will thus lead to higher quality results.

## Setup Instructions
Run the scripts in the gcloud shell.
