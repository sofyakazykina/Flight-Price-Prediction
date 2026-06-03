import streamlit as st
import pandas as pd
import random

st.title("Flight Analysis Dashboard")
st.header("Example 1")
st.subheader("Data Overview")

df = pd.read_csv('Clean_Dataset.csv')

st.write("### Raw Data")
st.write(df.head(10))

st.write("### Airline Counts")
st.bar_chart(df['airline'].value_counts())

if st.button("Show Balloons"):
    st.balloons()
    st.snow()

if st.button("Random Flight"):
    random_flight = df.sample(1)
    st.write("Here is a random flight:")
    st.dataframe(random_flight)

if st.button("Say mew", type="primary"):
    st.write("mew")
else:
    st.write("hi")