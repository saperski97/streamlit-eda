import pandas as pd
import streamlit as st
from ydata_profiling import ProfileReport
from streamlit_ydata_profiling import st_profile_report
from pygwalker.api.streamlit import StreamlitRenderer
from streamlit_ace import st_ace
import duckdb
import requests
import re


@st.cache_resource
def get_profile_report(tbl):
    return ProfileReport(tbl, orange_mode=True, minimal=True, explorative=True)


@st.cache_resource
def get_streamlit_renderer(tbl):
    return StreamlitRenderer(tbl, appearance="light")


def get_db_connection():
    if "conn" not in st.session_state:
        conn = duckdb.connect()
        conn.install_extension("spatial")
        conn.load_extension("spatial")
        st.session_state["conn"] = conn
    return st.session_state["conn"]


about = """
            This application is a powerful tool for anyone who needs to perform
            exploratory data analysis and manipulate data using SQL.\n
            __Upload File__: The application allows users to upload files in specified format.
            The uploaded data is then loaded into a pandas DataFrame for further processing.\n
            __Get File from URL__: Users may load data into application by providing URL address.\n
            __Select Table__: Users can select a table from the uploaded files for further operations.\n
            __Visual Exploration__: Application provides a visual exploration interface using the pygwalker library.
            This allows users to interactively explore their data.\n
            __SQL Workbench__: The application provides an SQL workbench where users can write and execute
            SQL queries on the selected table. The results of the queries are displayed in a DataFrame.\n
            __Data Profiling__: The application generates a data profiling report using the ydata_profiling library.
            This report provides comprehensive insights into the selected data.\n
            """


st.set_page_config(page_title="EDA workbench", page_icon=":bar_chart:", layout="wide")


conn = get_db_connection()
cur = conn.cursor()

with st.sidebar:
    with st.container(border=True):
        files = st.file_uploader(
            "Upload File",
            type={"csv", "txt", "xlsx", "parquet"},
            accept_multiple_files=True,
        )

        for file in files:
            if file.type == "application/octet-stream":
                tbl = pd.read_parquet(file)
            elif file.type == "text/csv":
                tbl = pd.read_csv(file)
            elif (
                file.type
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ):
                tbl = pd.read_excel(file)
            conn.sql(f"create table if not exists '{file.name}' as select * from tbl")

    with st.container(border=True):
        url = st.text_input("Get File from URL")
        if st.button("Download file"):
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    if "content-disposition" in response.headers.keys():
                        file_name = re.findall(
                            'filename="(.+)"', response.headers["content-disposition"]
                        )[0]
                    else:
                        file_name = re.findall(
                            "(\\w+)(\\.\\w+)+(?!.*(\\w+)(\\.\\w+)+)", url
                        )[0][0]
                    conn.sql(
                        f"create table if not exists '{file_name}' as select * from '{url}'"
                    )
                else:
                    st.toast(f"Invalid URL {url}.")
            except duckdb.CatalogException:
                st.toast("Data not in correct format.")
            except Exception as exception:
                st.toast(exception)

    with st.container(border=True):
        cur.execute("show all tables")
        recs = cur.fetchall()
        table_lst = [rec[2] for rec in recs]

    with st.expander("About"):
        st.markdown(about)

if table_lst:
    select_table = st.selectbox("Select Table", table_lst)
    df = conn.sql(f"from '{select_table}'").df()
    tab = st.tabs(["Visual Exploration", "SQL Workbench", "Data Profiling"])

    with tab[0]:
        pyg_app = get_streamlit_renderer(df)
        pyg_app.explorer(default_tab="data")

    with tab[1]:
        with st.container(border=True):
            st.markdown(
                "Query editor",
                help="Application uses DuckDB as query engine: https://duckdb.org/docs/",
            )
            content = st_ace(
                language="sql",
                value=f"select * from '{select_table}' limit 10;",
                placeholder=f"select * from '{select_table}' limit 10;",
            )

        with st.container(border=True):
            st.markdown("Query result")
            if content:
                try:
                    st.dataframe(
                        cur.execute(content).fetch_df(), use_container_width=True
                    )
                except Exception as exception:
                    st.error(exception)
                except TypeError as error:
                    st.error(error)
            else:
                st.info("Execute non empty query")

    with tab[2]:
        pr = get_profile_report(df)
        st_profile_report(pr)
else:
    st.markdown(about)
