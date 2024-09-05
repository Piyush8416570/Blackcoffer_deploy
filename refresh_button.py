# refresh_button.py
import streamlit as st

def reset_session_state():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Reinitialize any default values you want to keep
    st.session_state.use_default_template = False
    st.session_state.uploaded_template = None
    st.session_state.company_name = "We Buy Houses Anywhere LLC"
    st.session_state.your_name = "Justin Pickell"
    st.session_state.executed = False
    
    # If you have any other session state variables, reset them here
    # For example:
    # st.session_state.other_variable = default_value