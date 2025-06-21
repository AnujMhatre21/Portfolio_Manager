import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine
from yahooquery import Ticker
import os
from dotenv import load_dotenv
import numpy as np


class treeMap:

    @staticmethod
    def get_engine():
        config = st.secrets["mysql"]
        connection_string = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        return create_engine(connection_string)

    def render(self, data):
        engine = treeMap.get_engine()
        df = pd.read_sql(
            "SELECT ticker_symbol, ticker_name, amount_invested, purchase_price, quantity, sector FROM holdings",
            con=engine
        )

        if df.empty:
            st.info("No holdings added yet.")
            return

        tickers = list(df["ticker_symbol"].unique())
        prices = Ticker(tickers).price

        results = []

        for _, row in df.iterrows():
            ticker = row["ticker_symbol"]
            ticker_name = row["ticker_name"]
            qty = row["quantity"]
            sector = row["sector"]
            buy_price = row["purchase_price"]

            info = prices.get(ticker, {})
            current_price = info.get("regularMarketPrice", 0.0)

            if not current_price or current_price == 0.0:
                continue

            total_cost = qty * buy_price
            current_value = qty * current_price
            pl_value = current_value - total_cost
            pl_percent = (pl_value / total_cost) * 100 if total_cost else 0

            results.append({
                "ticker_name": ticker_name,
                "amount_invested": total_cost,
                "return_pct": pl_percent,
                "sector": sector
            })

        results_df = pd.DataFrame(results)

        if results_df.empty:
            st.warning("No valid pricing data available for any holdings.")
            return

        results_df["scaled_amount"] = np.sqrt(results_df["amount_invested"])
        results_df["portfolio_pct"] = (
            results_df["amount_invested"] / results_df["amount_invested"].sum()) * 100

        min_return = results_df["return_pct"].min()
        max_return = results_df["return_pct"].max()

        # Dynamic color scale
        if min_return >= 0:
            color_scale = px.colors.sequential.Greens
            midpoint = None
        elif max_return <= 0:
            # Reverse Reds to go dark to light
            color_scale = px.colors.sequential.Reds[::-1]
            midpoint = None
        else:
            color_scale = px.colors.diverging.RdYlGn
            midpoint = 0

        results_df["ticker_label"] = results_df.apply(
            lambda row: f"{row['ticker_name']} <br><b>({row['return_pct']:+.2f}%)</b>",
            axis=1
        )

        fig = px.treemap(
            results_df,
            path=["sector", "ticker_label"],
            values="scaled_amount",
            color="return_pct",
            color_continuous_scale=color_scale,
            range_color=[min_return, max_return],
            custom_data=["sector", "amount_invested",
                         "portfolio_pct", "return_pct"],
            title="💼 Portfolio Allocation by Sector and Ticker (Colored by Return %)",
        )

        if midpoint is not None:
            fig.update_layout(coloraxis=dict(
                cmid=midpoint))

        # Disable default hovertemplate
        fig.update_traces(hovertemplate=None, textfont_size=15)

        # Apply hovertemplate only to leaf nodes
        ids = fig.data[0].ids
        new_hovertemplates = []

        for id_val in ids:
            if id_val.count("/") > 1:  # This is a leaf node (sector/ticker)
                new_hovertemplates.append(
                    "<b>%{label}</b><br>"
                    "Sector: %{customdata[0]}<br>"
                    "Investment: ₹%{customdata[1]:,.0f}<br>"
                    "Portfolio Share: %{customdata[2]:.2f}%<br>"
                    "Return: %{customdata[3]:.2f}%"
                )
            else:  # Parent node (sector only)
                new_hovertemplates.append("")  # No hover

        # Apply the list of hovertemplates
        fig.data[0].hovertemplate = new_hovertemplates

        fig.update_layout(
            title_font=dict(size=22),
            margin=dict(t=80, l=25, r=25, b=25),
            coloraxis_colorbar=dict(
                title="Return %",
                tickformat=".1f",
                ticks="outside",
                showticksuffix="last",
                thickness=15,
                lenmode="fraction",
                len=0.8
            )
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Tip: Click on any sector to zoom in for more detail and click on outside black border to zoom out.")
