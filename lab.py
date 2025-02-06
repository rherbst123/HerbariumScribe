import streamlit as st
import pandas as pd
import re

text = "test"

text = "test"
st.markdown(f"<span style='color: red'>{text}</span>", unsafe_allow_html=True)
df = pd.DataFrame(
    [
        {"command": f"{text}", "rating": 4, "is_widget": True},
        {"command": "st.balloons", "rating": 5, "is_widget": False},
        {"command": "st.time_input", "rating": 3, "is_widget": True},
    ]
)

edited_df = st.data_editor(df)