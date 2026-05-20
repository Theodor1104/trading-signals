import streamlit as st

st.title("Test")
st.write("Hvis du kan se dette, virker Streamlit!")

if st.button("Klik her"):
    st.success("Det virker!")
