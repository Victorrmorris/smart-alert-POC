import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set page config
st.set_page_config(page_title="ICU Alert Dashboard", layout="wide")

# ====== Data Initialization ======
def init_patients():
    # Simulate a roster of patients
    names = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Tom Clark"]
    rooms = [101, 102, 103, 104, 105]
    diagnoses = ["Sepsis", "ARDS", "MI", "Stroke", "Post-op"]
    patients = pd.DataFrame({
        "patient_id": range(1, len(names)+1),
        "name": names,
        "room": rooms,
        "diagnosis": diagnoses
    })
    return patients

@st.cache_data
def generate_alerts(patients_df):
    # Simulate alerts for each patient
    alerts = []
    categories = ["Airway", "Breathing", "Circulation"]
    for _, p in patients_df.iterrows():
        for _ in range(random.randint(1, 5)):
            severity = np.random.choice(["Critical", "Warning", "Monitoring"], p=[0.2, 0.3, 0.5])
            alerts.append({
                "patient_id": p.patient_id,
                "category": random.choice(categories),
                "severity": severity,
                "timestamp": datetime.now() - timedelta(minutes=random.randint(0, 60)),
                "status": "Active"
            })
    return pd.DataFrame(alerts)

# Initialize in session state
if "patients" not in st.session_state:
    st.session_state.patients = init_patients()
if "alerts" not in st.session_state:
    st.session_state.alerts = generate_alerts(st.session_state.patients)

# ====== Sidebar Filters ======
st.sidebar.header("Filters & Search")
# Severity filter
selections = st.sidebar.multiselect("Severity", ["Critical", "Warning", "Monitoring"], default=["Critical", "Warning", "Monitoring"])
# Category filter
cat_selections = st.sidebar.multiselect("Category", ["Airway", "Breathing", "Circulation"], default=["Airway", "Breathing", "Circulation"])
# Search
search_term = st.sidebar.text_input("Search (Name / Room)")
# Quiet mode
quiet_mode = st.sidebar.checkbox("Quiet Mode (hide Warning/Monitoring)")

# Apply filters
alerts = st.session_state.alerts.copy()
if quiet_mode:
    alerts = alerts[alerts.severity == "Critical"]
alerts = alerts[alerts.severity.isin(selections) & alerts.category.isin(cat_selections)]
# Join with patient data for search
alerts = alerts.merge(st.session_state.patients, on="patient_id")
if search_term:
    alerts = alerts[alerts.name.str.contains(search_term, case=False) | alerts.room.astype(str).str.contains(search_term)]

# Determine patient status
status_map = {"Critical": 3, "Warning": 2, "Monitoring": 1}
pat_status = {}
for pid, group in alerts.groupby("patient_id"):
    max_sev = group.severity.map(status_map).max()
    rev_map = {v: k for k, v in status_map.items()}
    pat_status[pid] = rev_map[max_sev]

# Merge patient status back
patients = st.session_state.patients.copy()
patients["status"] = patients.patient_id.map(lambda x: pat_status.get(x, "Stable"))

# ====== Metrics ======
st.title("ICU Alert Dashboard")
critical_count = list(pat_status.values()).count("Critical")
warning_count = list(pat_status.values()).count("Warning")
stable_count = len(patients) - critical_count - warning_count
col1, col2, col3 = st.columns(3)
col1.metric("Critical Patients", critical_count)
col2.metric("Warning Patients", warning_count)
col3.metric("Stable Patients", stable_count)

# ====== Patient Grid View ======
cols = st.columns(3)
for idx, row in patients.iterrows():
    with cols[idx % 3]:
        # Color code based on status
        color = "#ff4c4c" if row.status == "Critical" else ("#ffcc00" if row.status == "Warning" else "#66b2ff")
        st.markdown(f"<div style='background-color:{color};padding:10px;border-radius:5px'>", unsafe_allow_html=True)
        st.subheader(f"{row.name} (Room {row.room})")
        st.write(row.diagnosis)
        st.write(f"Status: **{row.status}**")
        # Alert summary
        count = alerts[alerts.patient_id == row.patient_id].shape[0]
        st.write(f"Active Alerts: {count}")
        # Actions
        col_a, col_b, col_c = st.columns(3)
        if col_a.button("Acknowledge", key=f"ack_{row.patient_id}"):
            st.session_state.alerts.loc[(st.session_state.alerts.patient_id == row.patient_id) & (st.session_state.alerts.status == "Active"), "status"] = "Acknowledged"
        if col_b.button("Snooze 30m", key=f"snooze_{row.patient_id}"):
            st.session_state.alerts.loc[(st.session_state.alerts.patient_id == row.patient_id) & (st.session_state.alerts.status == "Active"), "timestamp"] += timedelta(minutes=30)
        if col_c.button("Escalate", key=f"escalate_{row.patient_id}"):
            # Placeholder for escalation logic
            st.toast(f"Escalated alerts for {row.name}")
        st.markdown("</div>", unsafe_allow_html=True)

# ====== Patient Detail Drill-down ======
st.sidebar.markdown("---")
selected = st.sidebar.selectbox("Patient Details", options=["None"] + patients.name.tolist())
if selected != "None":
    p = patients[patients.name == selected].iloc[0]
    st.header(f"Details: {p.name} (Room {p.room})")
    st.write(f"**Diagnosis:** {p.diagnosis}")
    pat_alerts = st.session_state.alerts[st.session_state.alerts.patient_id == p.patient_id]
    st.write("**Alert History:**")
    st.dataframe(pat_alerts.sort_values("timestamp", ascending=False)[["timestamp", "category", "severity", "status"]])

# Auto-refresh simulation button
if st.button("Refresh Data"):
    st.session_state.alerts = generate_alerts(st.session_state.patients)
    st.experimental_rerun()
