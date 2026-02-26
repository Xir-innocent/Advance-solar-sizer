# app.py - The Streamlit app

import streamlit as st
from xir_sizer import xir_smart_sizer
from fpdf import FPDF
from io import BytesIO
import matplotlib.pyplot as plt
import base64

# PSH lookup for Nigerian cities (from research)
PSH_DICT = {
    'Lagos': 4.8,
    'Abuja': 5.6,
    'Port Harcourt': 5.2,
    'Enugu': 4.5,
    'Kano': 6.0,
    'Ibadan': 4.9,
    'Other': 5.0
}

st.title('XIR Smart Solar System Sizer')
st.subheader('Enter your details for a personalized, optimized solar recommendation')
st.markdown('''This tool calculates the ideal system size to balance cost, reliability, and sustainability — avoiding over or under-design.''')

# Smart Input Layout (Grouped Sections)
with st.expander("Load & Location Details", expanded=True):
    city = st.selectbox('Select City (for accurate PSH)', list(PSH_DICT.keys()))
    PSH = PSH_DICT[city]
    st.info(f'Peak Sun Hours (PSH) for {city}: {PSH}')
    
    E_load_daily = st.number_input('Daily Energy Consumption (kWh)', min_value=1.0, max_value=1000.0, value=10.0, step=1.0, help='From your electricity bill or meter readings')
    D_aut = st.slider('Autonomy Days (Backup without sun)', min_value=1, max_value=5, value=2, help='For off-grid/hybrid systems')

with st.expander("Advanced Parameters (Optional)", expanded=False):
    eta_PV = st.number_input('PV Panel Efficiency', min_value=0.1, max_value=0.25, value=0.18, step=0.01)
    eta_sys = st.number_input('System Efficiency (losses)', min_value=0.5, max_value=0.9, value=0.75, step=0.01)
    DoD = st.number_input('Battery Depth of Discharge', min_value=0.4, max_value=0.95, value=0.8, step=0.05)
    eta_bat = st.number_input('Battery Efficiency', min_value=0.7, max_value=0.98, value=0.9, step=0.01)
    target_LPSP = st.number_input('Max Acceptable LPSP (%)', min_value=0.01, max_value=0.2, value=0.05, step=0.01, help='Lower = more reliable, but higher cost')

if st.button('Calculate & Recommend System', type='primary'):
    with st.spinner('Optimizing your solar system...'):
        result = xir_smart_sizer(
            E_load_daily=E_load_daily, PSH=PSH, eta_PV=eta_PV, eta_sys=eta_sys, D_aut=D_aut, 
            DoD=DoD, eta_bat=eta_bat, target_LPSP=target_LPSP
        )

    st.success('Optimized System Recommendation:')
    col1, col2 = st.columns(2)
    with col1:
        for key in ['PV Capacity (kW)', 'Number of Panels (300W)', 'Inverter Capacity (kW)', 'Battery Capacity (kWh)', 'Charge Controller (A)']:
            st.metric(key, result[key])
    with col2:
        for key in ['DC Breaker (A)', 'AC Breaker (A)', 'Wire Gauge Recommendation', 'Total Estimated Cost (₦)', 'LCOE (₦/kWh)']:
            st.metric(key, result[key])

    st.metric('Payback Period (years)', result['Payback Period (years)'])
    st.metric('Annual CO2 Saved (kg)', result['Annual CO2 Saved (kg)'])

    # Cost Breakdown Chart
    costs = {
        'PV': result['PV Capacity (kW)'] * 1200000,
        'Battery': result['Battery Capacity (kWh)'] * 200000,
        'Inverter': result['Inverter Capacity (kW)'] * 150000,
        'Other': result['Total Estimated Cost (₦)'] * 0.1  # Estimate
    }
    fig, ax = plt.subplots()
    ax.pie(costs.values(), labels=costs.keys(), autopct='%1.1f%%', colors=['#4B0082', '#7B2CBF', '#301934', '#666666'])
    ax.set_title('Cost Breakdown')
    st.pyplot(fig)

    # PDF Download - Branded Report
    class BrandedPDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, 'XIR Solar Solutions - System Recommendation', 0, 1, 'C')
            self.set_font('Arial', '', 10)
            self.cell(0, 10, 'Powering Progress Sustainably', 0, 1, 'C')
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()} | XIR - {st.session_state.get("report_date", "2026")}', 0, 0, 'C')

    pdf = BrandedPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Optimized Solar System Specs', 0, 1)
    pdf.set_font('Arial', '', 11)
    for key, value in result.items():
        pdf.cell(0, 10, f'{key}: {value}', 0, 1)

    pdf_output = BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin1'))
    pdf_output.seek(0)

    st.download_button(
        label="Download Branded PDF Report",
        data=pdf_output,
        file_name="XIR_Solar_Recommendation.pdf",
        mime="application/pdf"
    )