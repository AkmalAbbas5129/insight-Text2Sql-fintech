from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.output_parsers import CommaSeparatedListOutputParser
from langchain_core.output_parsers import JsonOutputParser
import sqlite3
import pandas as pd


class Table(BaseModel):
    """Table in SQL database."""
    name: str = Field(description="Name of table in SQL database.")


class SqlQuery(BaseModel):
    """SQL Generated by LLM"""
    sql: str = Field(description="Sql query in string format")


def get_related_tables_from_db(db, llm, query_in_text):
    table_names = "\n".join(db.get_usable_table_names())
    system = """Return the names of ALL the SQL tables that MIGHT be relevant to the user question. \
    The tables are:

    {table_names}

    user question:

    {query}

    Remember to include ALL POTENTIALLY RELEVANT tables, even if you're not sure that they're needed.

    {format_instructions}
    """
    output_parser = CommaSeparatedListOutputParser()

    prompt = PromptTemplate(
        template=system,
        input_variables=["table_names"],
        partial_variables={"format_instructions": output_parser.get_format_instructions()},
    )

    table_chain = prompt | llm | output_parser
    table_names = table_chain.invoke({"table_names": table_names, "query": query_in_text})

    return table_names


def get_tables_ddl(database_uri, table_list):
    database_uri = database_uri.replace("sqlite:///", "")

    # Connect to the database
    connection = sqlite3.connect(database_uri)
    cursor = connection.cursor()

    # List to store DDL queries
    ddl_queries = []

    # Query to get the DDL queries for all tables
    all_tables_query = "SELECT name, sql FROM sqlite_master WHERE type='table';"
    cursor.execute(all_tables_query)
    results = cursor.fetchall()

    for result in results:
        table_name, ddl_query = result
        ddl_queries.append(ddl_query)

    # Close the connection
    connection.close()

    # Join the DDL queries into a single string
    ddl_string = "\n\n".join(ddl_queries)

    return ddl_string
    # database_uri = database_uri.replace("sqlite:///", "")
    # # Connect to the database
    # connection = sqlite3.connect(database_uri)
    # cursor = connection.cursor()
    #
    # # List to store DDL queries
    # ddl_queries = []
    #
    # # Loop through specified tables and get the DDL queries
    # for table_name in table_list:
    #     # Query to get the DDL query for a specific table
    #     table_query = f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';"
    #     cursor.execute(table_query)
    #     result = cursor.fetchone()
    #
    #     if result:
    #         ddl_query = result[0]
    #         ddl_queries.append(ddl_query)
    #
    # # Close the connection
    # connection.close()
    #
    # # Join the DDL queries into a single string
    # ddl_string = "\n\n".join(ddl_queries)
    #
    # return ddl_string


def generate_sql_wrt_question(db_uri, table_names, llm, user_query):
    # DEFAULT_PROMPT = """You are a SQLite expert. Given an input question, first create a syntactically correct SQLite
    # query to run, then look at the results of the query and return the answer to the input question. Unless the user
    # specifies in the question a specific number of examples to obtain, query for at most 5 results using the LIMIT
    # clause as per SQLite. You can order the results to return the most informative data in the database. Never query
    # for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each
    # column name in double quotes (") to denote them as delimited identifiers. Pay attention to use only the column
    # names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention
    # to which column is in which table. Pay attention to use date('now') function to get the current date,
    # if the question involves "today". DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
    # database.
    #
    # Use the following format:
    #
    # Only use the following tables:
    # {table_info}
    #
    # Write an initial draft of the query. Then double check the SQLite query for common mistakes, including:
    # - Using NOT IN with NULL values
    # - Using UNION when UNION ALL should have been used
    # - Using BETWEEN for exclusive ranges
    # - Data type mismatch in predicates
    # - Properly quoting identifiers
    # - Using the correct number of arguments for functions
    # - Casting to the correct data type
    # - Using the proper columns for joins
    #
    # Use format:
    #
    # First draft: <<FIRST_DRAFT_QUERY>>
    # Final answer: {format_instructions}
    #
    # ================================ Human Message =================================
    #
    # Question: {input}
    # """

    DEFAULT_PROMPT = """You are a SQLite expert. Given an input question, first create a syntactically correct SQLite 
    query to run, then look at the results of the query and return the answer to the input question. Unless the user 
    specifies in the question a specific number of examples to obtain, query for at most 10 results using the LIMIT
    clause as per SQLite. You can order the results to return the most informative data in the database. Never query 
    for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each 
    column name in double quotes (") to denote them as delimited identifiers. Pay attention to use only the column 
    names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention 
    to which column is in which table. Pay attention to use date('now') function to get the current date, 
    if the question involves "today". DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the 
    database.

    Use the following format:

    Only use the following tables:
    {table_info}

    Write an initial draft of the query. Then double check the SQLite query for common mistakes, including:
    - Using NOT IN with NULL values
    - Using UNION when UNION ALL should have been used
    - Using BETWEEN for exclusive ranges
    - Data type mismatch in predicates
    - Properly quoting identifiers
    - Using the correct number of arguments for functions
    - Casting to the correct data type
    - Using the proper columns for joins

    Use format:
    
    {format_instructions}

    ================================ Human Message =================================

    Question: {input}
    """

    try:
        context_ddl = get_tables_ddl(db_uri, table_names)
        print(f"\n\nDDL: {context_ddl}\n\n")

        parser = PydanticOutputParser(pydantic_object=SqlQuery)

        PROMPT = PromptTemplate(
            input_variables=["input", "table_info"], template=DEFAULT_PROMPT,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )

        print(f"\n\n DDL : {context_ddl}\n\n")
        query_chain = PROMPT | llm | parser
        sql_query = query_chain.invoke({
            "input": user_query,
            "table_info": context_ddl
        })

        print(f"SQL Query: {sql_query.sql} : {type(sql_query.sql)}")
        return sql_query.sql
    except Exception as ex:
        print(f"Exception in generating query: {ex}")
        return None


class InsightsModel(BaseModel):
    """SQL Generated by LLM"""
    insight_content: str = Field(description="Insights from the dataframe according to question")
    follow_up_questions: list = Field(description="Generate more follow up questions according to the question which "
                                                  "can help further in analysis")


def generate_dataframe_from_sql(sql_query, db_uri, user_question, llm):
    template_string = """
    I want you to act as a Data Analyst who can generate insights from dataframe. 
    I will give you a question and a dataframe which contains the data in answer to the
    question.
    You will answer the question according to the dataframe and will write easy to understand 
    insights from it. After generating insights you will suggest 5 follow up questions which can
    be asked according to question.
    You will start directly from the answer.
    You will not output or assume anything from your own, Just output the answer. 

    Question: 
    {analysis_question}

    Dataframe: 
    {dataframe}

    Insights:
    {format_instructions}
    """

    try:
        df = pd.read_sql(sql_query, db_uri)
        parser = PydanticOutputParser(pydantic_object=InsightsModel)

        PROMPT = PromptTemplate(
            input_variables=["input", "table_info"],
            template=template_string,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )

        chain_analysis = PROMPT | llm | parser

        analysis_insights = chain_analysis.invoke({
            "analysis_question": user_question,
            "dataframe": df
        })

        return df, sql_query, analysis_insights

    except Exception as ex:
        InsightsModel.insight_content = str(ex)
        InsightsModel.follow_up_questions = ""
        return pd.DataFrame(), sql_query, InsightsModel
    # print(analysis_insights)
    # print(analysis_insights.visualization_suggestion)


def generate_visualization_code(dataframe, llm, user_question):
    print(f"Dataframe for Visuals: {dataframe}")
    template_string = """
    You have the dataframe and i want you to write a code which will generate best visualization for the dataframe using
    matplotlib according to query. You will just output the code and nothing else.
    Always include dataframe values in the code as it is.

    Dataframe: 
    {dataframe}

    Query:
    {query}

    code:
    import matplotlib.pyplot as plt
    <dataframe>
    <plotting logic> 
    """
    PROMPT = PromptTemplate(input_variables=["dataframe", "query"], template=template_string)

    visualization_chain = PROMPT | llm

    visualization_code = visualization_chain.invoke({
        "dataframe": dataframe,
        "query": user_question
    })

    # print(visualization_code.content)
    return visualization_code.content
