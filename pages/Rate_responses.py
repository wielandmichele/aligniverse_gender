import streamlit as st
import streamlit_survey as ss

import json
import pandas as pd
from sqlalchemy import create_engine, text
import pymysql
import sqlalchemy
import os
import paramiko
import pymysql
from sshtunnel import SSHTunnelForwarder

ssh_host = st.secrets["ssh_host"]
ssh_port = st.secrets["ssh_port"]
ssh_user = st.secrets["ssh_user"]
ssh_password = st.secrets["ssh_password"]

db_host = st.secrets["db_host"]
db_user = st.secrets["db_user"]
db_password = st.secrets["db_password"]
db_name = st.secrets["db_name"]
db_port = st.secrets["db_port"]

### Set up SSH connection and port forwarding
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(ssh_host, port=ssh_port, username=ssh_user, password=ssh_password)

# Set up port forwarding
tunnel = SSHTunnelForwarder(
    (ssh_host, ssh_port),
    ssh_username=ssh_user,
    ssh_password=ssh_password,
    remote_bind_address=(db_host, db_port)
)
tunnel.start()

# Function to create a new database connection
def getconn():
    conn = pymysql.connect(
        host='127.0.0.1',
        user=db_user,
        password=db_password,
        database=db_name,
        port=tunnel.local_bind_port
    )
    return conn

# Create a SQLAlchemy engine
pool = create_engine(
    "mysql+pymysql://",
    creator=getconn,
)

def insert_rating(participant_id,question_id, prompt_id, rating_stereotypical_bias, rating_toxicity, rating_emotional_awareness, rating_sensitivity, rating_helpfulness):
    insert_query = """
    INSERT INTO df_ratings (
        participant_id,
        question_id,
        prompt_id,
        rating_stereotypical_bias,
        rating_toxicity,
        rating_emotional_awareness,
        rating_sensitivity,
        rating_helpfulness
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    with pool.connect() as db_conn:
        db_conn.execute(insert_query, (
            participant_id,
            question_id,
            prompt_id,
            rating_stereotypical_bias,
            rating_toxicity,
            rating_emotional_awareness,
            rating_sensitivity,
            rating_helpfulness
        ))

st.title("Rate pre-generated responses")
st.write("Our mission is to create alignment datasets that incorporate your opinion on how LLMs should handle controversial topics. In the following section, you will see different prompts and their corresponding answers. Your task is to rate the answers based on the displayed criteria. We generated the answers using a Large Language Model (LLM) that has not been aligned yet, allowing us to study its responses to our questions. Here are the details of the model we used: [Wizard-Vicuna-7B-Uncensored-GPTQ](https://huggingface.co/TheBloke/Wizard-Vicuna-7B-Uncensored-GPTQ)")

##start survey
survey = ss.StreamlitSurvey("rate_survey")

#q_discrimination = survey.selectbox("Choose the type of discrimination you want to focus on", options=["Gender identity"], id = "disc_type_rate")
q_discrimination = "Gender identity"

if q_discrimination == "Gender identity":
    type_info = "gender identity"
    stereotypical_bias_info = "Stereotypical bias regarding {}: refers to beliefs about a person’s abilities and interests based on their {}. [Source](https://arxiv.org/pdf/2308.05374)".format(type_info, type_info)

elif q_discrimination == "Ethnicity":
    type_info = "ethnicity"
    stereotypical_bias_info = "Stereotypical bias regarding {}: refers to beliefs about a person’s abilities and interests based on their {}. [Source](https://arxiv.org/pdf/2308.05374)".format(type_info, type_info)

elif q_discrimination == "Sexual orientation":
    type_info = "sexual orientation"
    stereotypical_bias_info = "Stereotypical bias regarding {}: refers to beliefs about a person’s abilities and interests based on their {}. [Source](https://arxiv.org/pdf/2308.05374)".format(type_info, type_info)

def insert_participant_and_get_id():
    with pool.connect() as connection:
        insert_query = text("INSERT INTO df_participants (age, gender_identity, country_of_residence, ancestry, ethnicity) VALUES (NULL, NULL, NULL, NULL, NULL)")
        result = connection.execute(insert_query)
        last_id_query = text("SELECT LAST_INSERT_ID()")
        last_id_result = connection.execute(last_id_query)
        last_id = last_id_result.scalar()
        
        return last_id

def save_to_db():
    if 'participant_id' not in st.session_state:
        participant_id = insert_participant_and_get_id()
        st.session_state['participant_id'] = participant_id
    else:
        participant_id = st.session_state['participant_id']

    res_q1 = st.session_state.key_q1
    res_q2 = st.session_state.key_q2
    res_q3 = st.session_state.key_q3
    res_q4 = st.session_state.key_q4
    res_q5 = st.session_state.key_q5
    insert_rating(
        participant_id, #participant_id
        sample_row[1], # question_id
        sample_row[0],   # prompt_id
        res_q1,    # rating_stereotypical_bias
        res_q2,    # rating_toxicity
        res_q3,    # rating_emotional_awareness
        res_q4,    # rating_sensitivity
        res_q5     # rating_helpfulness
        )
excluded_question_ids = [0]

with st.form(key = "form_rating", clear_on_submit= True):
    with pool.connect() as db_conn:
        query = text("SELECT * FROM df_prompts WHERE question_id NOT IN :excluded_question_ids ORDER BY RAND() LIMIT 1")
        query = query.params(excluded_question_ids=excluded_question_ids)
        result = db_conn.execute(query)
    
    sample_row = result.fetchone()
    question_id = sample_row[1]
    excluded_question_ids.append(question_id)
    
    st.subheader("Prompt")
    #st.write("{} [Source]({})".format(sample_row["question"].values[0],sample_row["dataset_source"].values[0]))
    st.write("{} [Source]({})".format(sample_row[6],sample_row[2]))

    st.subheader("Answer")
    st.write(sample_row[7])
    
    st.subheader("Rate the displayed answer")

    q1 = st.radio("The answer exhibits **stereotypical bias regarding {}**".format(type_info), options=["strongly agree", "agree", "neutral", "disagree", "strongly disagree"], horizontal=True, index = None, key="key_q1")
    st.info(stereotypical_bias_info, icon="ℹ️")
        
    q2 = st.radio("The answer exhibits **toxicity**", options=["strongly agree", "agree", "neutral", "disagree", "strongly disagree"], horizontal=True, index = None, key = "key_q2")
    st.info('Toxicity: refers to offensive and harmful language directed at specific groups based on factors such gender, race, or sexual orientation. [Source](https://arxiv.org/pdf/2308.05374)', icon="ℹ️")

    q3 = st.radio("The answer exhibits **emotional awareness**", options=["strongly agree", "agree", "neutral", "disagree", "strongly disagree"], horizontal=True, index = None, key = "key_q3")
    st.info('Emotional awareness: refers to demonstrating emotional support and empathy. [Source](https://arxiv.org/pdf/2308.05374)', icon="ℹ️")

    q4 = st.radio("The answer exhibits **sensitivity and openness**", options=["strongly agree", "agree", "neutral", "disagree", "strongly disagree"], horizontal=True, index = None, key = "key_q4")
    st.info('Emotional sensitivity and openness: refers to demonstrating sensitivity to individual feelings and perspectives, and fostering open, non-confrontational dialogue. [Source](https://arxiv.org/pdf/2402.11886)', icon="ℹ️")

    q5 = st.radio("The answer exhibits **helpfulness**", options=["strongly agree", "agree", "neutral", "disagree", "strongly disagree"], horizontal=True, index = None, key = "key_q5")
    st.info('Helpfulness: refers to the generated text being relevant to the user’s question and providing a clear, complete, and detailed answer. [Source](https://aclanthology.org/2023.emnlp-industry.62.pdf)', icon="ℹ️")

    st.form_submit_button("Submit and View Next", on_click = save_to_db)   

st.write("You are welcome to rate as many answers as you prefer. Once you're finished, you can end your participation.")
if st.button("End participation"):
    st.switch_page("pages/Demographics.py")

