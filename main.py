import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.schema.output_parser import StrOutputParser
import sqlite3
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from sqlalchemy import create_engine, inspect
import streamlit as st
# from dotenv import load_dotenv
# load_dotenv()
import os

class SQL_LLM:
    def __init__(self):
        try:
            API_KEY=os.environ["API_KEY"]
            if 'history' not in st.session_state: #Used to pass into the LLM to remind previous conversations.
                st.session_state.history = []
            #instantiating the Gemini LLM
            self.llm = ChatGoogleGenerativeAI( 
                model="gemini-1.5-flash",
                temperature=0,
                google_api_key='AIzaSyCO0kTVUbzq8PdXHhk3OfCYsjdnMyVT02k',
                # max_retries=2,
            )
            #Streamlit
            st.set_page_config(page_title="I can Retrieve Any SQL query")
            st.header(".App To Retrieve SQL Data")
            self.schema = self.extract_schema('sqlite:///car_ds.db')
        except Exception as e:
            st.error("Error in initializing the app")
            return


    def read_sql_query(self,sql,db):
        """
        Function to connect to the database and to run the provided SQL command from the LLM.
        Input: SQL command from LLM and database connection link 
        """
        try:
            conn=sqlite3.connect(db) #COnnecting to SQLite database
            cur=conn.cursor()
            # print(sql)
            cur.execute(sql) #Executing the LLM SQL command
            rows=cur.fetchall()
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Data Base Error {e}")
            rows = []
        except Exception as e:
            st.error(f"Error executing SQL {e}")
            rows = []
        finally:
            conn.close()
            return rows
    

    def extract_schema(self, db_url):
        """
        Function used to get the schema of the database, so that the schema will be passed to the LLM to get a detailed idea about the databse.
        Input: Database URL"""
        try:
            engine = create_engine(db_url)
            inspector = inspect(engine)
            schema_info = []
            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                schema_info.append(f"Table: {table_name}")
                for column in columns:
                    schema_info.append(f"  - {column['name']} ({column['type']})")
            return "\n".join(schema_info)
        except Exception as e:
            st.error(f"Error extracting schema {e}")
    
    def get_sql_command(self, question, schema, history):
        """
        The function responsible for providing the SQL command based on the user's question. 
        Input: Schema of the database, history of the previous conversations."""
        try:
            #Template that pass to the LLM to provide answers as per the user request. 
            template = """
            You are SQLite expert. 
            you need to write SQL queries based on the given user question: {question} and the history of user questions {history}. 
            If the history  contains many questions, then consider based on the final one.
            The database consists of second hand cars. 
            This is the schema of the table which contains table name, column names and data type of each column. schema: {schema}
            Here is an example of the data in the database:
                "index": 1,
                "name": "Maruti Wagon R LXI Minor",
                "year": 2007,
                "selling_price": 135000 (In rupees),
                "km_driven": 50000,
                "fuel": "Petrol",
                "seller_type": "Individual",
                "transmission": "Manual",
                "owner": "First Owner"
            Price is provided in Indian Rupees
            Do not use ``` , \n in begining or end of the SQL query.
            """
            prompt_template_one = ChatPromptTemplate.from_template(template) #Chat prompt template creation with the defined template
            sql_command = prompt_template_one | self.llm #cahin: first it pass through the prompt_template_one and then the prompt_template_one with added details will be passed to LLM
            response = sql_command.invoke({'question':question,'schema':schema, 'history':history}) #executing the chain with the provided inputs. 
            # print(response)
            return response.content
        except Exception as e:
            st.error(f"Error in generating SQL command {e}")
            return ''

    def get_user_answer(self, question, sql_command, sql_answer):
        """
        This function will help to rewrite the answer provided by database to a user friendly manner. 
        Because after geting the SQL query from LLM teh database will give an answer and it will not be user firendly. """
        
        #template to rewrite the answer as per the user question.
        prompt_two = """
        You have given a user question to get details from a SQL database, sql command and the result from database. 
        You need to give a human friendly answer to the user. 
        The user question: {question},
        SQL command: {sql}
        Output from database: {sql_answer}
        
        """
        prompt_template_two = ChatPromptTemplate.from_template(prompt_two)
        chain = prompt_template_two | self.llm #chain
        response = chain.invoke({'question':question, 'sql':sql_command, 'sql_answer':sql_answer}) #invoking of chain with the required parameters. 
        return response.content #extracting the answer only
    
    def chat(self, prompt):
        """
        A single function to do all the tasks. All the functions are defined here in a step by step manner
        Input: The user question (directly from the chatbox)"""
        try:
            st.session_state.history.append(prompt) #chat history
            sql_command = self.get_sql_command(prompt, self.schema, st.session_state.history) #calling the function to get SQL command from LLM
            sql_command = sql_command.replace('ite','').replace('sql', '').replace('```', '') #Here the LLM used is a free version of Gemini and it has some limitations to remove the marks defined here
            
            st.write(sql_command) #To show the provided SQL command by the LLM (Not required for the user, but to make sure to the developer that the correct SQL query)           
            sql_answer = self.read_sql_query(sql_command, 'car_ds.db') #To get answer from Database

            final = self.get_user_answer(prompt, sql_command, sql_answer) #Change the answer as per the user question
            print(st.session_state.history)
            return final
        except Exception as e:
            st.error(f"Error occured {e}")
    

sql = SQL_LLM() #initializing the class
try:
    #streamlit app
    if prompt := st.chat_input("Ask a SQL question"): 
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from the chat method
        final = sql.chat(prompt)
        
        # Display LLM  response in chat message container
        with st.chat_message("ai"):
            st.markdown(final)
except Exception as e:
    st.error(f"Error in processing user input")