import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import folium
from streamlit_folium import st_folium
from scipy.stats import mannwhitneyu

st.set_page_config(page_title="Flight Analysis", layout="wide")

st.title("Flight Analysis Dashboard")
st.markdown("Analysis of air ticket price structure for domestic flights in India")
st.markdown("---")

st.info(
    "This dashboard explores factors affecting ticket prices: airline, travel class, "
    "number of stops, flight duration, and days before departure. "
    "Use the sidebar to navigate between sections."
)

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose section",
    ["Overview", "Route Map", "Price Analysis"]
)

@st.cache_data
def load_data():
    df = pd.read_csv('Clean_Dataset.csv')
    df["num_stops"] = df["stops"].map({"zero": 0, "one": 1, "two_or_more": 2})
    df["price_per_hour"] = df["price"] / df["duration"]
    return df

df = load_data()

# ==================== OVERVIEW ====================
if page == "Overview":
    st.header("Overview")

    st.subheader("Dataset Description")
    st.markdown("""
    The dataset contains information about domestic flights in India.  
    - **Airline** – airline name  
    - **Source / Destination** – departure and arrival cities  
    - **Departure/Arrival time** – time of day (Early_Morning, Morning, Afternoon, Evening, Night)  
    - **Stops** – number of stops (zero, one, two_or_more)  
    - **Class** – Economy or Business  
    - **Duration** – flight duration in hours  
    - **Days left** – days between booking and departure  
    - **Price** – ticket price in INR  
    """)

    st.subheader("Data Cleanliness")
    missing = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()
    st.write(f"Missing values: {missing}")
    st.write(f"Duplicate rows: {duplicates}")
    if missing == 0 and duplicates == 0:
        st.success("The dataset is clean (no missing values or duplicates).")
    else:
        st.warning("Data needs cleaning.")

    st.subheader("Descriptive Statistics")
    num_cols = ["price", "duration", "days_left", "num_stops"]
    stats = df[num_cols].agg(["mean", "median", "std"]).round(2)
    st.dataframe(stats)

    st.subheader("Basic Data Distribution")

    # 1. Гистограмма цены
    fig1, ax1 = plt.subplots(figsize=(10,5))
    sns.histplot(df["price"], bins=60, kde=True, color="steelblue", ax=ax1)
    ax1.axvline(df["price"].median(), color="tomato", linestyle="--", label=f"Median: {df['price'].median():,.0f}")
    ax1.axvline(df["price"].mean(), color="orange", linestyle="--", label=f"Mean: {df['price'].mean():,.0f}")
    ax1.set_title("Ticket Price Distribution")
    ax1.set_xlabel("Price (INR)")
    ax1.legend()
    st.pyplot(fig1)

    # 2. Scatter plot длительность vs цена
    fig2, ax2 = plt.subplots(figsize=(10,5))
    sns.scatterplot(data=df, x="duration", y="price", alpha=0.3, hue="class", ax=ax2)
    ax2.set_title("Flight Duration vs Price")
    ax2.set_xlabel("Duration (hours)")
    ax2.set_ylabel("Price (INR)")
    st.pyplot(fig2)

    # 3. Столбчатая диаграмма средней цены по авиакомпаниям
    fig3, ax3 = plt.subplots(figsize=(10,5))
    airline_avg = df.groupby("airline")["price"].mean().sort_values()
    airline_avg.plot(kind="bar", color="steelblue", ax=ax3)
    ax3.set_title("Average Price by Airline")
    ax3.set_ylabel("Price (INR)")
    ax3.tick_params(axis='x', rotation=45)
    st.pyplot(fig3)

    st.markdown("Most tickets cost under 20 000 INR. Business class flights create a long right tail in the distribution.")

# ==================== ROUTE MAP ====================
elif page == "Route Map":
    st.header("Route Map")

    city_coords = {
        "Delhi":     [28.6139, 77.2090],
        "Mumbai":    [19.0760, 72.8777],
        "Bangalore": [12.9716, 77.5946],
        "Kolkata":   [22.5726, 88.3639],
        "Chennai":   [13.0827, 80.2707],
        "Hyderabad": [17.3850, 78.4867],
    }
    cities = list(city_coords.keys())

    col1, col2 = st.columns(2)
    with col1:
        source = st.selectbox("From", cities, index=0)
    with col2:
        dest = st.selectbox("To", cities, index=1)

    ticket_class = st.radio("Ticket class", ["Both", "Economy", "Business"], horizontal=True)

    if source == dest:
        st.warning("Please select different cities!")
        st.stop()

    src = city_coords[source]
    dst = city_coords[dest]

    route_flights = df[
        (df["source_city"] == source) &
        (df["destination_city"] == dest) &
        (df["num_stops"] == 0)
    ]
    if ticket_class != "Both":
        route_flights = route_flights[route_flights["class"] == ticket_class]

    # --- Создание карты Folium ---
    center_lat = (src[0] + dst[0]) / 2
    center_lon = (src[1] + dst[1]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=5)

    # Скрыть attribution (надпись Leaflet/OSM)
    st.markdown("""
    <style>
    .leaflet-control-attribution {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    for city, coords in city_coords.items():
        folium.Marker(
            location=coords,
            popup=city,
            tooltip=city,
            icon=folium.Icon(color="blue", icon="cloud", prefix="fa")
        ).add_to(m)

    folium.PolyLine(
        locations=[src, dst],
        color="red",
        weight=3,
        opacity=0.8,
        tooltip=f"{source} → {dest}"
    ).add_to(m)

    st_data = st_folium(m, width=725)

    # Статистика
    if len(route_flights) > 0:
        st.success(f"**{len(route_flights)} direct flights** from {source} to {dest} (class: {ticket_class})")
        col1, col2, col3 = st.columns(3)
        col1.metric("Average price", f"₹{route_flights['price'].mean():,.0f}")
        col2.metric("Average duration", f"{route_flights['duration'].mean():.1f} h")
        col3.metric("Number of airlines", route_flights['airline'].nunique())
        with st.expander("Show flights"):
            st.dataframe(route_flights[["airline", "class", "price", "duration"]].head(10))
    else:
        st.info(f"No direct flights found for {source} → {dest} with class {ticket_class}.")

# ==================== PRICE ANALYSIS ====================
else:  # Price Analysis
    st.header("Price Analysis")

    # Кнопка 1: процент рейсов с пересадками
    if st.button("🔄 Show percentage of flights with stops"):
        stops_pct = df["num_stops"].value_counts(normalize=True) * 100
        stops_pct = stops_pct.rename({0: "Zero stops", 1: "One stop", 2: "Two or more stops"})
        fig_stops, ax_stops = plt.subplots()
        stops_pct.plot(kind="pie", autopct="%1.1f%%", ax=ax_stops)
        ax_stops.set_title("Flights by number of stops")
        ax_stops.set_ylabel("")
        st.pyplot(fig_stops)
        st.write("**Detailed percentages:**")
        st.dataframe(stops_pct.reset_index().rename(columns={"index": "Stops", 0: "Percent"}))

    # Кнопка 2: распределение по времени вылета
    if st.button("⏰ Show departure time distribution"):
        dep_counts = df["departure_time"].value_counts()
        fig_dep, ax_dep = plt.subplots()
        dep_counts.plot(kind="bar", color="steelblue", ax=ax_dep)
        ax_dep.set_title("Number of flights by departure time")
        ax_dep.set_xlabel("Departure time")
        ax_dep.set_ylabel("Count")
        st.pyplot(fig_dep)

    # 1. Boxplot цены по авиакомпаниям и классам
    st.subheader("Price Distribution by Airline and Class")
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(data=df, x="airline", y="price", hue="class", ax=ax)
    ax.set_title("Ticket Price by Airline and Class")
    ax.set_xlabel("Airline")
    ax.set_ylabel("Price (INR)")
    ax.tick_params(axis='x', rotation=45)
    st.pyplot(fig)

    # 2. График медианной цены от дней до вылета (по классам)
    st.subheader("Median Price vs Days Before Departure")
    fig, ax = plt.subplots(figsize=(10,5))
    for cls in df["class"].unique():
        subset = df[df["class"] == cls].groupby("days_left")["price"].median()
        ax.plot(subset.index, subset.values, label=cls)
    ax.set_title("Median Price vs Days Left Before Departure")
    ax.set_xlabel("Days left")
    ax.set_ylabel("Median price (INR)")
    ax.legend()
    st.pyplot(fig)
    st.markdown("Prices rise as departure approaches. The effect is stronger for Business class.")

    # 3. Тепловая карта корреляции
    st.subheader("Correlation Heatmap")
    corr = df[["price", "duration", "days_left", "num_stops"]].corr()
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", ax=ax)
    ax.set_title("Correlation Between Numerical Features")
    st.pyplot(fig)

    # 4. Проверка гипотез
    st.subheader("Hypothesis Testing")

    # Гипотеза 1: Бизнес-класс дороже эконома
    st.write("**Hypothesis 1:** Business class tickets are more expensive than Economy.")
    economy_prices = df[df["class"] == "Economy"]["price"]
    business_prices = df[df["class"] == "Business"]["price"]
    stat, p1 = mannwhitneyu(economy_prices, business_prices, alternative='less')
    st.write(f"Mann-Whitney U test p-value: {p1:.5f}")
    if p1 < 0.05:
        st.success("Reject H₀: Business class tickets are significantly more expensive.")
    else:
        st.warning("Cannot reject H₀.")

    # Гипотеза 2: Раннее бронирование (days_left > 30) дешевле
    st.write("**Hypothesis 2:** Tickets booked more than 30 days in advance are cheaper.")
    df["early_booking"] = (df["days_left"] > 30).astype(int)
    early = df[df["early_booking"] == 1]["price"]
    late = df[df["early_booking"] == 0]["price"]
    stat, p2 = mannwhitneyu(early, late, alternative='less')
    st.write(f"Mann-Whitney U test p-value: {p2:.5f}")
    if p2 < 0.05:
        st.success("Reject H₀: Early booking is associated with lower prices.")
    else:
        st.warning("Cannot reject H₀.")

    st.feedback("stars")