import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Flight Analysis", layout="wide")

st.title("✈️ Flight Analysis Dashboard")
st.markdown("Analysis of air ticket price structure for domestic flights in India")
st.markdown("---")

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose section",
    ["Overview", "Route Map", "Price Explorer"]
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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total flights", f"{len(df):,}")
    col2.metric("Airlines", df["airline"].nunique())
    col3.metric("Routes", df["source_city"].nunique())
    col4.metric("Avg price", f"₹{df['price'].mean():,.0f}")

    st.markdown("---")

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

    st.subheader("Data Quality")
    missing = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()
    if missing == 0 and duplicates == 0:
        st.success("No missing values or duplicates — dataset is clean.")

    st.subheader("Descriptive Statistics")
    num_cols = ["price", "duration", "days_left", "num_stops"]
    stats = df[num_cols].agg(["mean", "median", "std"]).round(2)
    st.dataframe(stats, use_container_width=True)

    st.markdown("---")
    if st.button("🎲 Show random flight"):
        st.balloons()
        flight = df.sample(1).iloc[0]
        st.subheader(f"✈️ {flight['source_city']} → {flight['destination_city']}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Airline", flight["airline"])
        col2.metric("Price", f"₹{flight['price']:,.0f}")
        col3.metric("Class", flight["class"])

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

    fig_map = go.Figure()

    for city, coords in city_coords.items():
        fig_map.add_trace(go.Scattergeo(
            lon=[coords[1]], lat=[coords[0]],
            mode="markers+text",
            marker=dict(size=10, color="steelblue"),
            text=city, textposition="top center",
            showlegend=False
        ))

    fig_map.add_trace(go.Scattergeo(
        lon=[src[1], dst[1]], lat=[src[0], dst[0]],
        mode="lines+markers",
        line=dict(width=3, color="tomato"),
        marker=dict(size=12, color="tomato"),
        name=f"{source} → {dest}",
    ))

    fig_map.update_layout(
        geo=dict(
            scope="asia", showland=True,
            landcolor="rgb(210, 235, 210)",
            showocean=True, oceancolor="rgb(180, 210, 250)",
            showcountries=True, countrycolor="white",
            showcoastlines=True, coastlinecolor="white",
            showlakes=True, lakecolor="rgb(180, 210, 250)",
            showrivers=True, rivercolor="rgb(180, 210, 250)",
            center=dict(lat=20, lon=80), projection_scale=4,
            bgcolor="rgb(240, 248, 255)",
        ),
        paper_bgcolor="rgb(240, 248, 255)",
        margin=dict(l=0, r=0, t=30, b=0), height=500,
    )

    st.plotly_chart(fig_map, use_container_width=True)

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

    st.subheader("📈 Price by Departure Time")
    time_order = ["Early_Morning", "Morning", "Afternoon", "Evening", "Night", "Late_Night"]
    route_all = df[(df["source_city"] == source) & (df["destination_city"] == dest)]
    if ticket_class != "Both":
        route_all = route_all[route_all["class"] == ticket_class]

    price_by_time = (
        route_all.groupby("departure_time")["price"]
        .median().reindex(time_order).dropna()
    )

    if len(price_by_time) > 0:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=price_by_time.index, y=price_by_time.values,
            mode="lines+markers",
            line=dict(color="steelblue", width=3),
            marker=dict(size=10, color="tomato"),
            fill="tozeroy", fillcolor="rgba(70, 130, 180, 0.15)",
            name="Median price",
        ))
        fig_line.update_layout(
            title=f"Median price by departure time ({source} → {dest})",
            xaxis_title="Departure time", yaxis_title="Median price (INR)",
            height=400, hovermode="x unified", plot_bgcolor="white",
            yaxis=dict(gridcolor="rgb(230,230,230)"),
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Not enough data to build the chart for this route.")

# ==================== PRICE EXPLORER ====================
else:
    st.header("🔍 Price Explorer")
    st.markdown("Use the filters to explore how price depends on different factors.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")

    selected_airlines = st.sidebar.multiselect(
        "Airlines", df["airline"].unique().tolist(),
        default=df["airline"].unique().tolist()
    )
    selected_class = st.sidebar.radio("Class", ["Both", "Economy", "Business"])
    price_range = st.sidebar.slider(
        "Price range (INR)",
        int(df["price"].min()), int(df["price"].max()),
        (int(df["price"].min()), int(df["price"].max()))
    )
    selected_stops = st.sidebar.multiselect(
        "Number of stops", [0, 1, 2], default=[0, 1, 2]
    )

    filtered = df[
        (df["airline"].isin(selected_airlines)) &
        (df["price"] >= price_range[0]) &
        (df["price"] <= price_range[1]) &
        (df["num_stops"].isin(selected_stops))
    ]
    if selected_class != "Both":
        filtered = filtered[filtered["class"] == selected_class]

    st.markdown(f"**{len(filtered):,} flights match your filters**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg price", f"₹{filtered['price'].mean():,.0f}" if len(filtered) > 0 else "—")
    col2.metric("Median price", f"₹{filtered['price'].median():,.0f}" if len(filtered) > 0 else "—")
    col3.metric("Avg duration", f"{filtered['duration'].mean():.1f}h" if len(filtered) > 0 else "—")

    if len(filtered) == 0:
        st.warning("No flights match your filters. Try adjusting them.")
        st.stop()

    st.markdown("---")

    # График 1 — boxplot
    st.subheader("Price by Airline")
    fig1 = px.box(
        filtered, x="airline", y="price", color="class",
        title="Price distribution by airline",
        labels={"price": "Price (INR)", "airline": "Airline"},
        color_discrete_map={"Economy": "steelblue", "Business": "tomato"}
    )
    fig1.update_layout(plot_bgcolor="white", height=450)
    st.plotly_chart(fig1, use_container_width=True)

    # Анимированный график
    st.subheader("🎬 Price by Airline over Days Before Departure")
    st.caption("Press ▶ to animate — watch how prices change as departure approaches")

    anim_data = (
        filtered.groupby(["days_left", "airline"])["price"]
        .median().reset_index()
    )

    fig_anim = px.bar(
        anim_data,
        x="airline", y="price",
        animation_frame="days_left",
        animation_group="airline",
        color="airline",
        range_y=[0, anim_data["price"].max() * 1.1],
        title="Median price by airline — animated by days before departure",
        labels={"price": "Median price (INR)", "airline": "Airline"},
    )
    fig_anim.update_layout(
        plot_bgcolor="white", height=500,
        showlegend=False,
        yaxis=dict(gridcolor="rgb(230,230,230)"),
    )
    fig_anim.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 100
    fig_anim.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 50

    st.plotly_chart(fig_anim, use_container_width=True)

    # График 2 — lines days_left
    st.subheader("📈 How Price Changes with Days Before Departure")
    fig2 = go.Figure()
    for cls in filtered["class"].unique():
        subset = filtered[filtered["class"] == cls].groupby("days_left")["price"].median()
        fig2.add_trace(go.Scatter(
            x=subset.index, y=subset.values,
            mode="lines", name=cls,
            fill="tozeroy" if cls == "Economy" else None,
            fillcolor="rgba(70,130,180,0.1)",
            line=dict(width=2.5)
        ))
    fig2.update_layout(
        title="Median price vs days before departure",
        xaxis_title="Days left", yaxis_title="Median price (INR)",
        hovermode="x unified", plot_bgcolor="white",
        yaxis=dict(gridcolor="rgb(230,230,230)"), height=400
    )
    st.plotly_chart(fig2, use_container_width=True)

    # График 3 — scatter
    st.subheader("Duration vs Price")
    fig3 = px.scatter(
        filtered.sample(min(3000, len(filtered))),
        x="duration", y="price", color="class",
        opacity=0.4, title="Flight duration vs price",
        labels={"duration": "Duration (hours)", "price": "Price (INR)"},
        color_discrete_map={"Economy": "steelblue", "Business": "tomato"}
    )
    fig3.update_layout(plot_bgcolor="white", height=400)
    st.plotly_chart(fig3, use_container_width=True)

    # Таблица
    st.subheader("Filtered Data")
    with st.expander("Show table"):
        st.dataframe(
            filtered[["airline", "source_city", "destination_city",
                      "class", "price", "duration", "days_left", "num_stops"]]
            .sort_values("price").head(50),
            use_container_width=True
        )

    st.feedback("stars")