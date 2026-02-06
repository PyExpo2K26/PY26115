import streamlit as st
import pandas as pd
import joblib
import numpy as np
import plotly.graph_objects as go # For the Gauge Chart

# --- CONFIGURATION ---
st.set_page_config(page_title="FloodGuard AI Dashboard", layout="wide")

# --- LOAD MODEL & SCALER ---
@st.cache_resource # This keeps the model in memory so it doesn't reload every time
def load_assets():
    model = joblib.load('flood_model.pkl')
    scaler = joblib.load('scaler.pkl')
    return model, scaler

model, scaler = load_assets()

# --- SIDEBAR: Simulation Panel (Step 5) ---
st.sidebar.title("🧪 Simulation Panel")
st.sidebar.write("Adjust environmental factors:")

input_values = []
# Loop to create 21 sliders for your 21 features
feature_names = [
    "Monsoon Intensity", "Topography Drainage", "River Management", "Deforestation", 
    "Urbanization", "Climate Change", "Dams Quality", "Siltation", "Agricultural Practices", 
    "Encroachments", "Ineffective Disaster Prep", "Drainage Systems", "Coastal Vulnerability", 
    "Landslides", "Watersheds", "Deteriorating Infra", "Population Score", "Wetland Loss", 
    "Inadequate Planning", "Political Factors", "Infrastructure Decay"
]

for name in feature_names:
    val = st.sidebar.slider(f"{name}", 0.0, 10.0, 5.0, step=0.1)
    input_values.append(val)

# --- MAIN DASHBOARD AREA ---
st.title("🌊 FloodGuard AI: Predictive Dashboard")

# STEP 4: ALERT GENERATION LOGIC
features = np.array(input_values).reshape(1, -1)
scaled_features = scaler.transform(features)
prediction = model.predict(scaled_features)[0]
prob_pct = prediction * 100

# Define Risk Levels
if prediction >= 0.70:
    risk_level = "HIGH RISK"
    risk_color = "red"
    risk_icon = "🚨"
elif prediction >= 0.40:
    risk_level = "MODERATE RISK"
    risk_color = "orange"
    risk_icon = "⚠️"
else:
    risk_level = "LOW RISK"
    risk_color = "green"
    risk_icon = "✅"

# --- TOP SUMMARY PANEL (Step 4 & 5) ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Flood Probability", value=f"{prob_pct:.2f}%")

with col2:
    st.markdown(f"### Status: :{risk_color}[{risk_icon} {risk_level}]")

with col3:
    st.write("**Recommendation:**")
    if risk_level == "HIGH RISK":
        st.error("Evacuate immediately!")
    elif risk_level == "MODERATE RISK":
        st.warning("Monitor water levels closely.")
    else:
        st.success("Area is currently safe.")

st.divider()

# --- VISUALIZATION (Step 5) ---
v_col1, v_col2 = st.columns([1, 1])

with v_col1:
    st.subheader("📊 Risk Gauge")
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = prob_pct,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Risk Percentage"},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': risk_color},
            'steps' : [
                {'range': [0, 40], 'color': "lightgreen"},
                {'range': [40, 70], 'color': "orange"},
                {'range': [70, 100], 'color': "pink"}],
        }
    ))
    st.plotly_chart(fig, use_container_width=True)

with v_col2:
    st.subheader("🗺️ Risk Map View")
    # Using dummy coordinates for a map display
    map_data = pd.DataFrame({'lat': [13.0827], 'lon': [80.2707]})
    st.map(map_data)

# --- HISTORICAL DATA SECTION ---
st.subheader("📈 Historical Trends")
chart_data = pd.DataFrame(
    np.random.randn(20, 3),
    columns=['River Level', 'Rainfall', 'Risk Index']
)
st.line_chart(chart_data)