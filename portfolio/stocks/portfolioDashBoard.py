import streamlit as st
from streamlit_autorefresh import st_autorefresh
from yahooquery import search, Ticker
import mysql.connector
import yfinance as yf
import base64
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from portfolio.stocks.tickerSearch import search_ticker_symbols

# SQLAlchemy connection string


class portfolioDashBoardClass:
    def __init__(self):
        self.name = "Portfolio Dashboard"

    def get_engine():
        config = st.secrets["mysql"]
        connection_string = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        return create_engine(connection_string)
    # --- Ticker Search Helper ---

    # @st.cache_data(show_spinner=False)
    # def search_ticker_symbols(query):
    #     try:
    #         result = search(query)
    #         print(query)
    #         quotes = result.get("quotes", [])
    #         return [f"{q['symbol']} - {q['shortname']}" for q in quotes if "symbol" in q and "shortname" in q]
    #     except Exception:
    #         return []

    def render(self):
        st.markdown("### 🧾 Portfolio Overview")

        engine = portfolioDashBoardClass.get_engine()
        df = pd.read_sql(
            "SELECT ticker_symbol,amount_invested, quantity FROM holdings", con=engine)
        amount_invested_all = 0.00
        current_value_all = 0.00
        # ticker_symbol = df.iloc[0, 0] if not df.empty else 0
        for _, row in df.iterrows():
            amount_invested_all += row["amount_invested"]
            ticker_symbol = row["ticker_symbol"]
            amount_invested = row["amount_invested"]
            quantity = row["quantity"]

            # print(amount_invested)
            # print(amount_invested_all)
            # print(f"Ticker: {ticker_symbol}, Invested Amount: ₹{amount_invested}")
            prices = Ticker(ticker_symbol).price
            info = prices.get(ticker_symbol, {})
            # current_value_all += info.get("regularMarketPrice", 0.00)
            current_value = info.get("regularMarketPrice", 0.00) * quantity
            current_value_all += current_value
            # print(current_value)
            # print(f"Ticker: {ticker_symbol}, Current Value: ₹{current_value_all}")
        # current_value = df.iloc[0, 1] if not df.empty else 0
        # current_value = 0.00
        profit_loss = current_value_all - amount_invested_all
        profit_loss_percent = profit_loss / \
            amount_invested_all if amount_invested_all != 0 else 0

        # print(f"Invested Amount: {invested_amount}, Current Value: {current_value}, P/L: {profit_loss}")

        # Define a section using container
        with st.container():
            # st.markdown("---")  # horizontal line

            col1, col2, col3 = st.columns(3)

            col1.metric("Invested Amount", f"₹{amount_invested_all:,.2f}")
            col2.metric("Current Value", f"₹{current_value_all:,.2f}")

            # Determine delta display and direction
            if profit_loss > 0:
                delta = f"+₹{profit_loss:,.2f} (+{profit_loss_percent * 100:.2f}%)"
            elif profit_loss < 0:
                delta = f"-₹{abs(profit_loss):,.2f } (-{abs(profit_loss_percent * 100):.2f}%)"
            else:
                delta = "₹0.00"

            col3.metric("P/L", f"₹{profit_loss:,.2f}",
                        delta, delta_color="normal")
        # -- Loading placeholder --
        # loading_slot = st.empty()
        # with loading_slot.container():
            # st.markdown("⏳ Please wait while we load your data...")
            # Optional: display a loading GIF if you have one
            # st.image("path/to/loading.gif", width=100)

        with open("Portfolio_Manager/MyPortfolio1.png", "rb") as f:
            gif_bytes = f.read()
            gif_base64 = base64.b64encode(gif_bytes).decode()

        # Display the heading with the GIF inline
        st.markdown(
            f"""
            <h3 style="display: flex; align-items: center;">
                <img src="data:image/gif;base64,{gif_base64}" width="30" style="margin-right: 10px;">
                My Holdings
            </h3>
            """,
            unsafe_allow_html=True
        )

        engine = portfolioDashBoardClass.get_engine()
        df = pd.read_sql(
            "SELECT ticker_symbol, ticker_name, amount_invested, purchase_price, quantity FROM holdings", con=engine)
        # conn.close()

        if df.empty:
            st.info("No holdings added yet.")
        else:
            tickers = list(df["ticker_symbol"].unique())
            prices = Ticker(tickers).price

            rows = []
            for _, row in df.iterrows():
                ticker = row["ticker_symbol"]
                ticker_name = row["ticker_name"]
                qty = row["quantity"]

                buy_price = row["purchase_price"]

                info = prices.get(ticker, {})
                current_price = info.get("regularMarketPrice", 0.0)
                change_pct = info.get("regularMarketChangePercent", 0.0)
                change_pct = change_pct * 100  # Convert to percentage

                total_cost = qty * buy_price
                current_value = qty * current_price
                pl_value = current_value - total_cost
                pl_percent = (pl_value / total_cost) * 100 if total_cost else 0

                rows.append({
                    "Ticker": ticker_name,
                    "Qty": f"{int(qty)}",
                    "Buy Price": f"₹{buy_price:.2f}",
                    "Current Price": f"₹{current_price:.2f}",
                    "Change %": f"{change_pct:.2f}%",
                    "Overall P/L ₹": f"₹{pl_value:.2f}",
                    "Overall P/L %": f"{pl_percent:.2f}%",
                })

            overview_df = pd.DataFrame(rows)

            def get_color(val):
                try:
                    val = float(val.replace("₹", "").replace(
                        "%", "").replace(",", ""))
                    return "color: green" if val > 0 else "color: red"
                except:
                    return ""

            overview_df.index = overview_df.index + 1
            styled_df = overview_df.style.map(
                get_color, subset=["Change %", "Overall P/L ₹", "Overall P/L %"])
            # or just use styled_df to keep 1-based index

            # Holding table
            st.dataframe(styled_df.hide(axis="index"))

        # --- Portfolio Chart ---
        engine = portfolioDashBoardClass.get_engine()
        df = pd.read_sql(
            "SELECT ticker_name, amount_invested FROM holdings", con=engine)
        # conn.close()
        # if not df.empty:
        #     st.plotly_chart(px.pie(df, names="ticker_name",
        #                     values="amount_invested"))
        # ------------------------------------------------------------------------
        #     # --- Pie Chart ---
        # st.subheader("1. Pie Chart")
        # fig_pie = px.pie(
        #     df,
        #     names="ticker_name",
        #     values="amount_invested",
        #     title="Portfolio Distribution by Ticker"
        # )
        # fig_pie.update_traces(textinfo="percent+label")
        # st.plotly_chart(fig_pie)

        # --- Donut Chart ---
        # st.subheader("2. Donut Chart")
        fig_donut = px.pie(
            df,
            names="ticker_name",
            values="amount_invested",
            title="Portfolio Distribution",
            hole=0.4
        )
        fig_donut.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_donut)

    # ------------------------------------------------------------

        # --- Sector Wise Chart ---
        engine = portfolioDashBoardClass.get_engine()
        df = pd.read_sql(
            "SELECT sector, SUM(amount_invested) as total_invested FROM holdings GROUP BY sector", con=engine)
        # conn.close()
        # if not df.empty:
        #     st.plotly_chart(px.pie(df, names="sector",
        #                     values="total_invested"))

        # ------------------------------------------------------------------------
    # # --- Pie Chart ---
    #     st.subheader("1. Pie Chart")
    #     fig_pie = px.pie(
    #         df,
    #         names="sector",
    #         values="total_invested",
    #         title="Investment Distribution by Sector",
    #         hole=0.0
    #     )
    #     fig_pie.update_traces(textinfo="percent+label")
    #     st.plotly_chart(fig_pie)

        # --- Donut Chart ---
        # st.subheader("2. Donut Chart")
        fig_donut = px.pie(
            df,
            names="sector",
            values="total_invested",
            title="Sector Wise Investment Distribution",
            hole=0.4
        )
        fig_donut.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_donut)

        # ------------------------------------------------------------------------

        with st.expander("➕ Add New Stock"):

            # Initialize session state for form inputs if not already present
            if "broughtAtPrice" not in st.session_state:
                st.session_state.broughtAtPrice = 0.0
            if "qty" not in st.session_state:
                st.session_state.qty = 0
            if "buy_date" not in st.session_state:
                st.session_state.buy_date = pd.to_datetime("today")
            if "typ" not in st.session_state:
                st.session_state.typ = "Stock"

            query = st.text_input(
                "Search for a Ticker (e.g., INFY, TCS, RELIANCE)")

            matches = search_ticker_symbols(query) if query else []

            # Add ".NS" suffix to all NSE symbols to be consistent with yfinance requirements
            matches_ns = [
                f"{s.split(' - ')[0]}.NS - {s.split(' - ')[1]}" for s in matches]

            selected = st.selectbox(
                "Select Ticker", matches_ns, key="ticker_dropdown") if matches_ns else None

            if selected:
                ticker = selected.split(" - ")[0]  # e.g. "INFY.NS"
                ticker_name = selected.split(" - ")[1]
            else:
                ticker = ""
                ticker_name = ""

            current_price = 0.0
            name = ""
            exch = ""
            if ticker:
                try:
                    tk = Ticker(ticker)
                    info = tk.price.get(ticker, {})
                    name = info.get("shortName", "")
                    current_price = info.get("regularMarketPrice", 0.0)
                    exch = info.get("exchangeName", "")
                    change_pct = info.get("regularMarketChangePercent", 0.0)
                    change_pct = change_pct * 100

                    # Format percentage with + or - sign and 2 decimals
                    change_str = f"{change_pct:+.2f}%"

                    st.info(
                        f"**{name}** ({exch})\n💰 Current Price: ₹{current_price} ({change_str})"
                    )
                except Exception:
                    st.warning("Could not fetch price info.")

            with st.form("portfolio", clear_on_submit=False):
                broughtAtPrice = st.number_input("Brought at Price", 0.0)
                qty = st.number_input("Quantity", 0)
                amount = broughtAtPrice * qty
                buy_date = st.date_input("Buy Date")
                typ = st.selectbox("Type", ["Stock", "Mutual Fund", "ETF"])
                if ticker:
                    sector = yf.Ticker(ticker).info.get("sector", "")
                    if (sector == " "):
                        sector = "Others"

                if st.form_submit_button("Add") and ticker:
                    conn = engine.raw_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO holdings (ticker_symbol, ticker_name, amount_invested, purchase_price, quantity, buy_date, asset_type,sector,LTP) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                (ticker, ticker_name, amount, broughtAtPrice, qty, buy_date, typ, sector, current_price))
                    conn.commit()
                    conn.close()
                    st.success("Added")
        return overview_df
