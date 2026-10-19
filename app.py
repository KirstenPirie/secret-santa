import random

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Secret Santa", page_icon="🎅", layout="centered")


def draw_names(names):
    """Return a dict giver -> receiver where nobody gets themselves."""
    while True:
        receivers = names[:]
        random.shuffle(receivers)
        if all(g != r for g, r in zip(names, receivers)):
            return dict(zip(names, receivers))


st.title("🎅 Secret Santa")
st.write(
    "Add everyone taking part below. Click the **+** row at the bottom of the "
    "table to add more people."
)

edited = st.data_editor(
    pd.DataFrame({"Name": ["", "", ""]}),
    num_rows="dynamic",
    width="stretch",
    key="editor",
)

if st.button("🎲 Draw names", type="primary"):
    names = [n.strip() for n in edited["Name"].fillna("").astype(str) if n.strip()]

    if len(names) < 2:
        st.error("Please enter at least 2 names.")
    elif len({n.lower() for n in names}) != len(names):
        st.error("Names must be unique. Add a surname or initial to tell people apart.")
    else:
        st.session_state.assignments = draw_names(names)

if st.session_state.get("assignments"):
    st.divider()
    st.subheader("Who is buying for whom")
    result_df = pd.DataFrame(
        {
            "Giver": list(st.session_state.assignments.keys()),
            "Buys a gift for": list(st.session_state.assignments.values()),
        }
    )
    st.table(result_df.set_index("Giver"))
