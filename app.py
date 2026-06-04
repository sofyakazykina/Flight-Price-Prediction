import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px  # добавлено для цветов (опционально)
import matplotlib.pyplot as plt
import seaborn as sns

st.title("Flight Analysis Dashboard")

df = pd.read_csv('Clean_Dataset.csv')
df["num_stops"] = df["stops"].map({"zero": 0, "one": 1, "two_or_more": 2})
df["price_per_hour"] = df["price"] / df["duration"]

# --- Data Overview ---
st.header("Data Overview")
st.write("### Raw Data")
st.write(df.head(10))

st.write("### Airline Counts")
st.bar_chart(df['airline'].value_counts())

# --- Pie Chart: Airline Distribution ---
st.subheader("Airline Share (Pie Chart)")
airline_counts = df['airline'].value_counts()
fig_pie = go.Figure(data=[go.Pie(
    labels=airline_counts.index,
    values=airline_counts.values,
    hole=0.3,
    marker=dict(colors=px.colors.qualitative.Pastel)  # красивая цветовая палитра
)])
fig_pie.update_layout(title="Proportion of flights by airline", height=500)
st.plotly_chart(fig_pie, use_container_width=True)
st.markdown("The pie chart shows the share of flights operated by each airline. IndiGo and Air India are the most frequent.")

if st.button("Random Flight"):
    random_flight = df.sample(1)
    st.write("Here is a random flight:")
    st.dataframe(random_flight)

# --- Flight Route Map ---
st.header("Flight Route Map")

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

ticket_class = st.radio("Class", ["Both", "Economy", "Business"], horizontal=True)

if source == dest:
    st.warning("Please select different cities!")
else:
    src = city_coords[source]
    dst = city_coords[dest]

    route_flights = df[
        (df["source_city"] == source) &
        (df["destination_city"] == dest) &
        (df["num_stops"] == 0)
    ]

    if ticket_class != "Both":
        route_flights = route_flights[route_flights["class"] == ticket_class]

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

# --- Price Distribution ---
st.header("Price Distribution")

fig, ax = plt.subplots(figsize=(10, 5))
sns.histplot(df['price'], bins=60, kde=True, color='steelblue', ax=ax)
ax.axvline(df['price'].median(), color='tomato', linestyle='--',
           linewidth=1.5, label=f"Median: {df['price'].median():,.0f}")
ax.axvline(df['price'].mean(), color='orange', linestyle='--',
           linewidth=1.5, label=f"Mean: {df['price'].mean():,.0f}")
ax.set_title('Distribution of flight ticket prices', fontsize=14)
ax.set_xlabel('Price (INR)')
ax.set_ylabel('Count')
ax.legend()
st.pyplot(fig)

st.markdown("Most tickets cost under 20 000 INR. The distribution has a long right tail caused by expensive Business class tickets.")

# --- Price by Class ---
st.header("Price by Class")

fig, ax = plt.subplots(figsize=(6, 5))
class_stats = df.groupby('class')['price'].agg(['mean', 'median']).round(0)
bars = ax.bar(class_stats.index, class_stats['mean'],
              color=['steelblue', 'tomato'], edgecolor='white', width=0.5)
for bar, val in zip(bars, class_stats['mean']):
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 500,
            f'{val:,.0f} INR', ha='center', va='bottom', fontsize=11)
ax.set_title('Average ticket price by class', fontsize=14)
ax.set_xlabel('Class')
ax.set_ylabel('Mean price (INR)')
st.pyplot(fig)

st.markdown("Business class is on average ~6x more expensive than Economy.")

# --- Price by Airline ---
st.header("Price by Airline")

fig, ax = plt.subplots(figsize=(12, 5))
sns.boxplot(data=df, x='airline', y='price', ax=ax)
ax.set_title('Price distribution by airline')
ax.set_xlabel('Airline')
ax.set_ylabel('Price (INR)')
ax.tick_params(axis='x', rotation=15)
st.pyplot(fig)

st.markdown("Vistara and Air India have the highest median prices. Budget airlines like IndiGo and SpiceJet are significantly cheaper.")

# --- Price vs Days Left ---
st.header("Price vs Days Before Departure")

fig, ax = plt.subplots(figsize=(10, 5))
for cls in df["class"].unique():
    subset = df[df["class"] == cls].groupby("days_left")["price"].median()
    ax.plot(subset.index, subset.values, label=cls)
ax.set_title("Median price vs days left before departure")
ax.set_xlabel("Days left")
ax.set_ylabel("Median price (INR)")
ax.legend()
st.pyplot(fig)

st.markdown("Prices rise as departure approaches. The effect is stronger for Business class.")