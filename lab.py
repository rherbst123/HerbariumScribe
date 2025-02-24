import pandas as pd
import streamlit as st

data_df = pd.DataFrame(
    {
        "widgets": ["st.selectbox", "st.number_input", "st.text_area", "st.button"],
    }
)

st.data_editor(
    data_df,
    column_config={
        "widgets": st.column_config.TextColumn(
            "Widgets",
            help="Streamlit **widget** commands 🎈",
            default="st.",
            max_chars=50,
            validate=r"^st\.[a-z_]+$",
        )
    },
    hide_index=True,
)