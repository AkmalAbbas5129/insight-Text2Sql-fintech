import streamlit as st
from langchain_openai import AzureChatOpenAI
# from langchain_community.utilities import SQLDatabase
from langchain_community.utilities.sql_database import SQLDatabase
from custom_vanna_utils import *

llm = AzureChatOpenAI(
    model_name="gpt-35-turbo-16k",
    deployment_name=st.secrets["deployment_name"],
    openai_api_key=st.secrets["openai_api_key"],
    azure_endpoint=st.secrets["azure_endpoint"],
    openai_api_type="azure",
    openai_api_version="2023-03-15-preview",
    temperature="0"
)
# db_uri = "sqlite:///employee_data_updated.db"
# db_uri = "sqlite:///sales_db.db"
# db_uri = "sqlite:///sql_schema/hr_database.db"
db_uri = "sqlite:///fintech_database.db"
db = SQLDatabase.from_uri(db_uri)


def get_insights(user_query):
    table_names = get_related_tables_from_db(db, llm, user_query)
    print(f"Table Names to be used: {table_names}" and {type(table_names)})
    generated_sql_query = generate_sql_wrt_question(db_uri, table_names, llm, user_query)
    print(generated_sql_query)
    if generated_sql_query:
        dataframe, sql_query, insights = generate_dataframe_from_sql(generated_sql_query, db_uri, user_query, llm)
        # print(f"Dataframe: {dataframe}")
        # print(f"SQL Query: {sql_query}")
        # print(f"Insights: {insights}")
        return dataframe, sql_query, insights
    else:
        return "Question is not related to database"

logo_url = "https://i.brecorder.com/primary/2022/04/626b6c9fc04c7.jpg"  # Replace with the actual URL of your logo

col1, col2, col3 = st.columns([2, 2, 2])
# Display the logo using st.image
with col2:
    st.image(logo_url, width=200)

st.title("Insights Bot")
st.set_option('deprecation.showPyplotGlobalUse', False)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Set the maximum history length
max_history_length = 2

if not st.session_state.messages:
    # welcome_message = """Welcome to our database insights tool. Feel free to start with your own questions about the
    # data, or if you need some inspiration, you can ask for following insights.
    #
    # 1. What is the average salary for employees in the Engineering department compared to the Marketing department?
    # 2. What percentage of employees are enrolled in the company's health insurance plan?
    # 3. Are there specific departments or job roles experiencing higher turnover rates?
    # 4. What is the overall promotion rate within the company?
    # 5. Are there any trends or patterns in salary distribution based on job roles or experience levels within each department?
    # """

    welcome_message = """Welcome to our database insights tool. Feel free to start with your own questions about the
    data. Currently the

    Customers: This stores information about users like their names, email addresses, phone numbers, and where they
    live. It helps the platform keep track of who its users are and how to reach them.

    Transactions: Every time someone does something with money on the platform, like buying something or transferring
    money, those actions are recorded here. It helps users keep track of what they've done with their money.

    Merchants: This is a list of businesses that are partnered with the platform. It includes their names and where
    they are located. It helps users find businesses they can interact with on the platform.

    MerchantTransactions:
    When users buy something from one of the partnered businesses, those transactions are recorded here.
    It helps users keep track of what they've bought from each business.

    Regions:
    This helps the platform understand where its users are located.
    It includes different areas like cities or states. It helps the platform provide localized services to users.

    CustomerRegions: This connects users to the regions they are in. It helps the platform understand the
    geographical distribution of its users and provide services tailored to different regions."""

    st.session_state.messages.append({"role": "assistant", "content": welcome_message, "visualization": "",
                                       "follow_ups": "", "dataframe": pd.DataFrame()})

# If the number of messages exceeds the maximum history length, remove the oldest messages
if len(st.session_state.messages) > max_history_length:
    st.session_state.messages = st.session_state.messages[-max_history_length:]
    st.empty()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] != "user" and message["visualization"]:
            if not message["dataframe"].empty:
                st.dataframe(message["dataframe"])
            try:
                st.pyplot(exec(message["visualization"]))
            except Exception as ex:
                print("No suitable graph")

            # st.write(message["follow_ups"])
            st.subheader("You can also ask following questions to further fuel your in insights!")
            for question in message["follow_ups"]:
                st.write(question)

if prompt := st.chat_input("Ask me about insights"):
    st.session_state.messages.append(
        {"role": "user", "content": prompt, "visualization": "", "follow_ups": "", "dataframe": pd.DataFrame()})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        data_frame, sql_query, insight_cls = get_insights(prompt)
        insight_answer = insight_cls.insight_content
        followup_questions = insight_cls.follow_up_questions
        print(f"Data in UI: {data_frame}")
        full_response = f"Insight Answer:\n {insight_answer}"
        st.markdown(full_response)
        st.write(sql_query)
        st.dataframe(data_frame)
        if not data_frame.empty:
            code_plotlib = generate_visualization_code(data_frame, llm, prompt)
            try:
                print(code_plotlib)
                st.pyplot(exec(code_plotlib))
                # st.plotly_chart(exec(visualization_code))
            except Exception as ex:

                print(f"No suitable graph: {ex}")
        else:
            code_plotlib = ""

        st.subheader("You can also ask following questions to further fuel your in insights!")
        for question in followup_questions:
            st.write(question)

    st.session_state.messages.append(
        {"role": "assistant", "content": full_response, "visualization": code_plotlib,
         "follow_ups": followup_questions, "dataframe": data_frame})
