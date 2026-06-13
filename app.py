import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests

st.set_page_config(page_title="Flight Analysis", layout="wide")

st.title("Flight Analysis Dashboard")
st.markdown("Analysis of air ticket price structure for domestic flights in India")
st.markdown("---")

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose section",
    ["Overview", "Route Map", "Price Explorer", "Hypotheses"]
)

API_URL = "http://localhost:8000"

@st.cache_data
def load_data():
    df = pd.read_csv('Clean_Dataset.csv', index_col=0)
    df["num_stops"] = df["stops"].map({"zero": 0, "one": 1, "two_or_more": 2})
    df["price_per_hour"] = df["price"] / df["duration"]
    return df

df = load_data()

#Overview

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

    st.subheader("Additional Insights")

    flights_per_airline = df["airline"].value_counts().reset_index()
    flights_per_airline.columns = ["airline", "count"]
    fig1 = px.bar(
        flights_per_airline, x="airline", y="count", color="airline",
        title="Number of flights by airline",
        labels={"airline": "Airline", "count": "Number of flights"}
    )
    fig1.update_layout(showlegend=False, xaxis_tickangle=-45)
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.box(
        df, x="departure_time", y="price", color="class",
        title="Price distribution by departure time and class",
        labels={"departure_time": "Departure time", "price": "Price (INR)"},
        color_discrete_map={"Economy": "steelblue", "Business": "tomato"}
    )
    fig2.update_layout(height=500)
    st.plotly_chart(fig2, use_container_width=True)

    avg_price_by_days = df.groupby(["days_left", "class"])["price"].mean().reset_index()
    fig3 = px.line(
        avg_price_by_days, x="days_left", y="price", color="class",
        title="Average price vs days before departure",
        labels={"days_left": "Days left", "price": "Average price (INR)"},
        color_discrete_map={"Economy": "steelblue", "Business": "tomato"}
    )
    fig3.update_layout(height=400)
    st.plotly_chart(fig3, use_container_width=True)

    if st.button("Show random flight"):
        flight = df.sample(1).iloc[0]
        st.subheader(f"Flight: {flight['source_city']} -> {flight['destination_city']}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Airline", flight["airline"])
        col2.metric("Price", f"₹{flight['price']:,.0f}")
        col3.metric("Class", flight["class"])

#Route Map

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
        name=f"{source} -> {dest}",
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
        st.info(f"No direct flights found for {source} -> {dest} with class {ticket_class}.")
    st.subheader("Price by Departure Time")
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
            title=f"Median price by departure time ({source} -> {dest})",
            xaxis_title="Departure time", yaxis_title="Median price (INR)",
            height=400, hovermode="x unified", plot_bgcolor="white",
            yaxis=dict(gridcolor="rgb(230,230,230)"),
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Not enough data to build the chart for this route.")

#Price Explorer

elif page == "Price Explorer":
    st.header("Price Explorer")
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

    with st.expander("Test API GET with two arguments"):
        col1, col2 = st.columns(2)
        with col1:
            test_airline = st.selectbox("Airline", df["airline"].unique().tolist(), key="test_airline")
        with col2:
            test_price_max = st.number_input("Max price (INR)", min_value=500, max_value=200000, value=10000, step=500)

        st.markdown(f"Request: `/flights?airline={test_airline}&price_max={test_price_max}`")

        if st.button("Run API GET test"):
            result = df.copy()
            if test_airline:
                result = result[result["airline"].str.lower() == test_airline.lower()]
            result = result[result["price"] <= test_price_max]
            st.write(f"Total matching flights: {len(result)}")
            st.dataframe(result[["airline", "source_city", "destination_city", "class", "price", "duration"]].head())

    st.subheader("Price by Airline")
    fig1 = px.box(
        filtered, x="airline", y="price", color="class",
        title="Price distribution by airline",
        labels={"price": "Price (INR)", "airline": "Airline"},
        color_discrete_map={"Economy": "steelblue", "Business": "tomato"}
    )
    fig1.update_layout(plot_bgcolor="white", height=450)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Price by Airline over Days Before Departure")
    st.caption("Press play to animate — watch how prices change as departure approaches")
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
    fig_anim.update_layout(plot_bgcolor="white", height=500, showlegend=False, yaxis=dict(gridcolor="rgb(230,230,230)"))
    fig_anim.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 100
    fig_anim.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 50
    st.plotly_chart(fig_anim, use_container_width=True)

    st.subheader("How Price Changes with Days Before Departure")
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

    st.subheader("Filtered Data")
    with st.expander("Show table"):
        st.dataframe(
            filtered[["airline", "source_city", "destination_city",
                      "class", "price", "duration", "days_left", "num_stops"]]
            .sort_values("price").head(50),
            use_container_width=True
        )

    with st.expander("Add a new flight (POST to API)"):
        with st.form("add_flight_form"):
            st.subheader("New Flight Details")
            col1, col2 = st.columns(2)
            with col1:
                airline = st.text_input("Airline", "IndiGo")
                source = st.selectbox("Source city", df["source_city"].unique())
                dest = st.selectbox("Destination city", df["destination_city"].unique())
                dep_time = st.selectbox("Departure time", ["Early_Morning","Morning","Afternoon","Evening","Night","Late_Night"])
                arr_time = st.selectbox("Arrival time", ["Early_Morning","Morning","Afternoon","Evening","Night","Late_Night"])
                stops = st.selectbox("Stops", ["zero", "one", "two_or_more"])
            with col2:
                flight_class = st.selectbox("Class", ["Economy", "Business"])
                duration = st.number_input("Duration (hours)", min_value=0.5, max_value=24.0, step=0.1)
                days_left = st.number_input("Days left", min_value=1, max_value=49, step=1)
                price = st.number_input("Price (INR)", min_value=500, max_value=200000, step=100)

            submitted = st.form_submit_button("Add Flight")
            if submitted:
                new_flight = {
                    "airline": airline,
                    "source_city": source,
                    "destination_city": dest,
                    "departure_time": dep_time,
                    "arrival_time": arr_time,
                    "stops": stops,
                    "class": flight_class,
                    "duration": duration,
                    "days_left": days_left,
                    "price": price,
                }
                try:
                    resp = requests.post(f"{API_URL}/flights", json=new_flight)
                    if resp.status_code == 201:
                        st.success("Flight added successfully! Refresh the page to see changes.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Failed to add flight: {resp.text}")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.feedback("stars")
    
    
#Hypotheses

elif page == "Hypotheses":
    st.header("Hypothesis Testing")
    st.markdown("We tested two hypotheses about flight prices and durations.")

    st.subheader("Hypothesis 1")
    st.markdown("""
    **Evening and Night flights have a significantly longer median duration 
    than Morning and Late_Night flights — even with the same number of stops.**
    """)

    time_order = ["Early_Morning", "Morning", "Afternoon", "Evening", "Night", "Late_Night"]
    one_stop = df[df["num_stops"] == 1]

    medians = one_stop.groupby("departure_time")["duration"].median().reindex(time_order)

    fig_h1 = go.Figure()
    colors = ["#a8d8ea", "#a8d8ea", "#a8d8ea", "#ff6b6b", "#ff6b6b", "#a8d8ea"]

    for i, time in enumerate(time_order):
        if time in medians.index and not pd.isna(medians[time]):
            fig_h1.add_trace(go.Box(
                y=one_stop[one_stop["departure_time"] == time]["duration"],
                name=time,
                marker_color=colors[i],
                boxpoints=False,
                line=dict(width=1.5),
            ))

    fig_h1.update_layout(
        title="Duration of 1-stop flights by departure time",
        xaxis_title="Departure time",
        yaxis_title="Duration (hours)",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="rgb(230,230,230)"),
        height=500,
        showlegend=False,
    )

    st.plotly_chart(fig_h1, use_container_width=True)

    st.markdown("**Median duration by departure time:**")
    st.dataframe(
        medians.dropna().sort_values()
        .reset_index()
        .rename(columns={"departure_time": "Departure time", "duration": "Median duration (h)"})
        .round(2),
        use_container_width=True
    )

    st.info("""
    **Result: Hypothesis partially confirmed.**
    Evening (15.2h) and Night (14.8h) flights have the longest durations.
    Late_Night (7.8h) and Morning (10.4h) are the shortest as expected.
    However, Afternoon (8.5h) is also short — contradicting a simple "later = longer" pattern.
    """)

    st.markdown("---")

    st.subheader("Hypothesis 2")
    st.markdown("""
    **Price per hour of flight is lower for the most frequent airlines 
    (IndiGo, Air India) compared to other airlines.**
    """)

    df["is_leader"] = df["airline"].isin(["Indigo", "Air_India"])
    order = df.groupby("airline")["price_per_hour"].median().sort_values().index.tolist()

    fig_h2 = go.Figure()
    for airline in order:
        subset = df[df["airline"] == airline]["price_per_hour"]
        is_leader = airline in ["Indigo", "Air_India"]
        fig_h2.add_trace(go.Box(
            y=subset,
            name=airline,
            marker_color="tomato" if is_leader else "steelblue",
            boxpoints=False,
            line=dict(width=1.5),
        ))

    fig_h2.update_layout(
        title="Price per hour by airline (leaders in red)",
        xaxis_title="Airline",
        yaxis_title="Price per hour (INR)",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="rgb(230,230,230)"),
        height=500,
        showlegend=False,
    )

    st.plotly_chart(fig_h2, use_container_width=True)

    st.markdown("**Median price per hour:**")
    median_pph = df.groupby("airline")["price_per_hour"].median().sort_values().reset_index()
    median_pph.columns = ["Airline", "Median price per hour (INR)"]
    median_pph["Is leader"] = median_pph["Airline"].isin(["Indigo", "Air_India"])
    st.dataframe(median_pph.round(2), use_container_width=True)

    st.info("""
    **Result: Hypothesis not confirmed.**
    Air India shows a higher median price per hour than most budget airlines.
    IndiGo has a low median price per hour, consistent with its budget positioning,
    but Air India behaves more like a premium carrier.
    The hypothesis holds for IndiGo but not for Air India.
    """)