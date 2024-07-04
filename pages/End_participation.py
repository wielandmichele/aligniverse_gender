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

def insert_email(email):
    insert_query = """
    INSERT INTO df_emails (
        email
    ) VALUES (%s)
    """
    with pool.connect() as db_conn:
        db_conn.execute(insert_query, (
            email
        )
)

st.title("Thank you!")
st.write("Thank you for being part of our study and helping us improve the alignment of Large Language Models.")
st.balloons()

#st.write("If you would like to take part in the prize draw for three Airbnb vouchers worth 50 euros each, please leave us your email address. We collect the email address individually for data protection reasons.")

#email = st.text_input("Email",max_chars=50)
#if st.button("Submit Email"):
    #insert_email(email)                                                                                                                                                                             

st.divider()
st.write("If you'd like to spend more time rating, editing, and creating answers, please restart the survey. This is required for data protection purposes.")
st.link_button("Restart survey", "https://aligniverse.streamlit.app/")

# Close the SSH tunnel
tunnel.stop()
ssh.close()
