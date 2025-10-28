from airflow import DAG
from airflow.models import Variable
from airflow.decorators import task
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

from datetime import datetime
import requests

def return_snowflake_conn():
    hook = SnowflakeHook(snowflake_conn_id='snowflake_conn')
    return hook.get_conn()

@task
def create_tables():
    conn = return_snowflake_conn()
    try:
        cur = conn.cursor()
        try:
            #Table creation for the user session channel
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.user_session_channel(
                    userId int not Null,
                    sessionID varchar(32) primary key,
                        channel varchar(32) default 'direct'
                )
            """)

            #Table creation for the user session_timestamp
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.session_timestamp(
                    sessionId varchar(32) primary key,
                    ts timestamp
                )
            """)
        finally:
            cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

@task
def load_data():
    conn = return_snowflake_conn()
    try:
        cur = conn.cursor()
        try:
            
            cur.execute("""
                CREATE OR REPLACE STAGE raw.blob_stage
                url = 's3://s3-geospatial/readonly/'
                file_format = (type = csv, skip_header = 1, field_optionally_enclosed_by = '"');
            """)

            # Load data into table session channel
            cur.execute("""
                COPY INTO raw.user_session_channel
                FROM @raw.blob_stage/user_session_channel.csv;
            """)

            # Load data into table session timestamp
            cur.execute("""
                COPY INTO raw.session_timestamp
                FROM @raw.blob_stage/session_timestamp.csv;
            """)
        finally:
            cur.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

with DAG(
    dag_id='snowflake_Load_session',
    start_date=datetime(2025, 10, 28),
    schedule_interval='30 3 * * *',
    catchup=False,
    tags=['Snowflake', 'load', 'ETL'],
) as dag:

    #Dag Task
    create_tables_task = create_tables()
    load_data_task = load_data()

    # Task Order
    create_tables_task >> load_data_task