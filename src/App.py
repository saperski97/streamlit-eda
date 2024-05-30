import pandas as pd
import streamlit as st
from ydata_profiling import ProfileReport
from streamlit_ydata_profiling import st_profile_report
from pygwalker.api.streamlit import StreamlitRenderer
from streamlit_ace import st_ace
import duckdb

st.set_page_config(layout="wide")


@st.cache_resource
def get_profile_report(tbl):
    return ProfileReport(tbl, orange_mode=True, explorative=True)


@st.cache_resource
def get_streamlit_renderer(tbl):
    return StreamlitRenderer(tbl, dark="light")


global tbl
tbl = None
tab = st.tabs(["Visual Exploration", "SQL Workbench", "Data Profiling"])
duckdb.query("install spatial")
duckdb.query("load spatial")

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
            duckdb.query(f"create or replace table '{file.name}' as select * from tbl")

    with st.container(border=True):
        select_table = st.selectbox("Select Table", [file.name for file in files])
        if files:
            tbl = duckdb.query(f"from '{select_table}'").df()

    with st.expander("About"):
        st.markdown(
            """
            This application is a powerful tool for anyone who needs to perform
            exploratory data analysis and manipulate data using SQL.\n
            __Upload File__: The application allows users to upload files in specified format.
            The uploaded data is then loaded into a pandas DataFrame for further processing.\n
            __Select Table__: Users can select a table from the uploaded files for further operations.\n
            __Visual Exploration__: Application provides a visual exploration interface using the pygwalker library.
            This allows users to interactively explore their data.\n
            __SQL Workbench__: The application provides an SQL workbench where users can write and execute
            SQL queries on the selected table. The results of the queries are displayed in a DataFrame.\n
            __Data Profiling__: The application generates a data profiling report using the ydata_profiling library.
            This report provides comprehensive insights into the selected data.\n
            """
        )

if files:
    with tab[0]:
        pyg_app = get_streamlit_renderer(tbl)
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
                        duckdb.query(content).to_df(), use_container_width=True
                    )
                except Exception as exception:
                    st.error(exception)
                except TypeError as error:
                    st.error(error)
            else:
                st.info("Execute non empty query")

    with tab[2]:
        pr = get_profile_report(tbl)
        st_profile_report(pr)
else:
    st.info("Upload a file")
