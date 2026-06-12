import streamlit as st
import pandas as pd
import time
from nsepython import nse_optionchain_scrapper

# Set up the look of your app window
st.set_page_config(page_title="NSE Options Terminal", layout="wide")
st.title("🎯 NSE Options Risk Management Terminal")

# Persistent memory tracker so data doesn't wipe out when the screen refreshes
if "watchlist" not in st.session_state:
    st.session_state.watchlist = None
if "alerts" not in st.session_state:
    st.session_state.alerts = []

def get_option_price(underlying, strike, option_type):
    """Safely extracts the price from nsepython option matrix."""
    try:
        payload = nse_optionchain_scrapper(underlying.upper().strip())
        data = payload['filtered']['data']
        for row in data:
            if float(row['strikePrice']) == float(strike):
                return float(row[option_type.upper()]['lastPrice'])
    except Exception:
        return 0.0

# 1. & 2. The Upload File Button and Explorer Pop-up
uploaded_file = st.file_uploader("Choose your Tickers Excel File (.xlsx)", type=["xlsx"])

if uploaded_file:
    if st.session_state.watchlist is None:
        df = pd.read_excel(uploaded_file)
        
        # This line forces all column names to be uppercase and stripped of spaces
        df.columns = df.columns.astype(str).str.upper().str.strip()
        
        # Now we look for 'TICKER' no matter how you typed it in Excel
        if 'TICKER' in df.columns:
            rows = []
            for idx, r in df.iterrows():
                tkr = str(r['TICKER']).upper().strip()
                default_strike = 23500.0 if "NIFTY" in tkr else 50000.0
                rows.append({"Select": False, "Ticker": tkr, "Strike": default_strike, "Type": "CE", "Current LTP": 0.0})
            st.session_state.watchlist = pd.DataFrame(rows)
        else:
            st.error("Error: Could not find your stock column. Please make sure your Excel header row says 'Ticker'.")

if st.session_state.watchlist is not None:
    st.subheader("💡 Interactive Options Watchlist Workspace")
    st.info("Double click inside 'Strike' or 'Type' columns to manually edit them!")
    
    # 4. & 5. Displays options data matrix with dynamically editable values
    edited_df = st.data_editor(
        st.session_state.watchlist,
        column_config={
            "Select": st.column_config.CheckboxColumn(help="Select rows to arm alerts"),
            "Strike": st.column_config.NumberColumn(help="Change target strike target number"),
            "Type": st.column_config.SelectboxColumn(options=["CE", "PE"], help="Pick Option Call or Put contract")
        },
        disabled=["Ticker", "Current LTP"],
        hide_index=True,
        key="editor"
    )
    st.session_state.watchlist = edited_df

    # Button to fetch fresh prices for the edited strikes
    if st.button("🔄 Fetch/Refresh Contract Live Prices"):
        with st.spinner("Talking to NSE Option Chain Matrix..."):
            for idx, row in st.session_state.watchlist.iterrows():
                live_ltp = get_option_price(row['Ticker'], row['Strike'], row['Type'])
                st.session_state.watchlist.at[idx, "Current LTP"] = live_ltp
        st.rerun()

    # 6. Set Boundary Bars for Selected Group
    st.markdown("---")
    st.subheader("🚨 Configure Sentinel Boundary Alert Bars")
    
    col1, col2 = st.columns(2)
    with col1:
        condition = col2.selectbox("Alert direction condition rule:", ["GOES ABOVE (>=)", "DROPS BELOW (<=)"])
    with col2:
        target_price = st.number_input("Target Contract Threshold Price (₹):", min_value=0.0, value=10.0)

    if st.button("🚀 Deploy Live Background Scanning Radar"):
        selected_rows = edited_df[edited_df["Select"] == True]
        if selected_rows.empty:
            st.warning("Please check the 'Select' box on at least one ticker above first!")
        else:
            for _, r in selected_rows.iterrows():
                alert_item = {
                    "Ticker": r['Ticker'], "Strike": r['Strike'], "Type": r['Type'],
                    "Condition": "ABOVE" if "ABOVE" in condition else "BELOW", "Target": target_price
                }
                st.session_state.alerts.append(alert_item)
            st.success(f"Successfully armed scanning engine for {len(selected_rows)} options contracts!")

# 7. Background Loop Output Drawer
if st.session_state.alerts:
    st.markdown("---")
    st.subheader("📡 Live Boundary Sentinels Active")
    st.json(st.session_state.alerts)
    
    # Active scanning engine running inside screen session
    st.write("Radar running... prices refresh in background loops. Triggers throw notifications below:")
    for alert in st.session_state.alerts:
        current_price = get_option_price(alert['Ticker'], alert['Strike'], alert['Type'])
        if alert['Condition'] == "ABOVE" and current_price >= alert['Target']:
            st.toast(f"🔔 ALERT TRIGGERED! {alert['Ticker']} {alert['Strike']}{alert['Type']} crossed above {alert['Target']}!", icon="⚠️")
            st.error(f"🚨 MATCH BOUNDARY EXCEEDED: {alert['Ticker']} {alert['Strike']}{alert['Type']} is now trading at ₹{current_price}!")
        elif alert['Condition'] == "BELOW" and current_price <= alert['Target'] and current_price > 0:
            st.toast(f"🔔 ALERT TRIGGERED! {alert['Ticker']} {alert['Strike']}{alert['Type']} dropped below {alert['Target']}!", icon="⚠️")
            st.error(f"🚨 MATCH BOUNDARY TRAILED: {alert['Ticker']} {alert['Strike']}{alert['Type']} dropped to ₹{current_price}!")
