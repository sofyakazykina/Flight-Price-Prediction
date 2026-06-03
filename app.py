import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.title("✈️ Flight Analysis Dashboard")

df = pd.read_csv('Clean_Dataset.csv')
df["num_stops"] = df["stops"].map({"zero": 0, "one": 1, "two_or_more": 2})

# --- Data Overview ---
st.header("Data Overview")
st.write("### Raw Data")
st.write(df.head(10))

st.write("### Airline Counts")
st.bar_chart(df['airline'].value_counts())

if st.button("Random Flight"):
    random_flight = df.sample(1)
    st.write("Here is a random flight:")
    st.dataframe(random_flight)

# --- Flight Route Map ---
st.header("✈️ Flight Route Map")

city_coords = {
    "Delhi":     {"lat": 28.6139, "lon": 77.2090},
    "Mumbai":    {"lat": 19.0760, "lon": 72.8777},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946},
    "Kolkata":   {"lat": 22.5726, "lon": 88.3639},
    "Chennai":   {"lat": 13.0827, "lon": 80.2707},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
}

cities = list(city_coords.keys())
col1, col2 = st.columns(2)
with col1:
    source = st.selectbox("From", cities, index=0)
with col2:
    dest = st.selectbox("To", cities, index=1)

if source == dest:
    st.warning("Please select different cities!")
else:
    src = city_coords[source]
    dst = city_coords[dest]

    # Фильтруем — только прямые рейсы
    route_flights = df[
        (df["source_city"] == source) &
        (df["destination_city"] == dest) &
        (df["num_stops"] == 0)
    ]

    # Карта
    fig = go.Figure()

    for city, coords in city_coords.items():
        fig.add_trace(go.Scattergeo(
            lon=[coords["lon"]],
            lat=[coords["lat"]],
            mode="markers+text",
            marker=dict(size=10, color="steelblue"),
            text=city,
            textposition="top center",
            showlegend=False
        ))

    fig.add_trace(go.Scattergeo(
        lon=[src["lon"], dst["lon"]],
        lat=[src["lat"], dst["lat"]],
        mode="lines+markers",
        line=dict(width=3, color="tomato"),
        marker=dict(size=12, color="tomato"),
        name=f"{source} → {dest}",
    ))

    fig.update_layout(
        geo=dict(
            scope="asia",
            showland=True,
            landcolor="rgb(240, 240, 240)",
            showocean=True,
            oceancolor="rgb(210, 230, 255)",
            showcountries=True,
            countrycolor="white",
            center=dict(lat=20, lon=80),
            projection_scale=4,
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Статистика
    if len(route_flights) > 0:
        st.write(f"**{len(route_flights)} direct flights** from {source} to {dest}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg price", f"₹{route_flights['price'].mean():,.0f}")
        col2.metric("Avg duration", f"{route_flights['duration'].mean():.1f}h")
        col3.metric("Airlines", route_flights['airline'].nunique())
        st.dataframe(
            route_flights[["airline", "class", "price", "duration"]].head(10)
        )
    else:
        st.info("No direct flights found for this route.")