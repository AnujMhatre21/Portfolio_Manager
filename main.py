import streamlit as st
import pandas as pd
import numpy as np
import time
import yfinance as yf
from sqlalchemy import create_engine
import google.generativeai as genai
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import warnings
from yahooquery import search, Ticker
from portfolio.stocks.treeMap import treeMap
from portfolio.stocks.tickerSearch import search_ticker_symbols
from portfolio.Advisor.aiadvisor import render_ai_chat

warnings.filterwarnings('ignore')


class AdvancedFinancialAdvisor:
    def __init__(self):
        self.engine = self._get_engine()
        self.model = self._get_model()
        self.market_data = {}
    
    

    @staticmethod
    def _get_engine():
        """Initialize database connection"""
        try:
            config = st.secrets["mysql"]
            connection_string = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
            return create_engine(connection_string)
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            return None

    @staticmethod
    def _get_model():
        """Initialize Gemini AI model"""
        try:
            config = st.secrets["apikey"]
            genai.configure(api_key=config["api_key"])
            return genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            st.error(f"AI model initialization failed: {e}")
            return None

    def get_comprehensive_portfolio_analysis(self):
        """Get detailed portfolio analysis with current market data"""
        if not self.engine:
            return "Database connection unavailable."

        try:
            # Fetch portfolio data
            df = pd.read_sql("""
                SELECT id, ticker_symbol, ticker_name, amount_invested, 
                       purchase_price, buy_date, asset_type, quantity 
                FROM holdings
            """, con=self.engine)

            if df.empty:
                return self._generate_empty_portfolio_advice()

            # Enrich with current market data
            enriched_data = []
            total_invested = 0
            total_current_value = 0

            for _, row in df.iterrows():
                try:
                    # Get current market data with extended history
                    ticker = yf.Ticker(row['ticker_symbol'])
                    hist_data = ticker.history(
                        period="6mo")  # Get 6 months of data
                    current_price = hist_data['Close'].iloc[-1]

                    # Calculate metrics
                    current_value = current_price * row['quantity']
                    gain_loss = current_value - row['amount_invested']
                    gain_loss_pct = (gain_loss / row['amount_invested']) * 100

                    # Days held
                    days_held = (datetime.now() -
                                 pd.to_datetime(row['buy_date'])).days

                    # Calculate volatility and other metrics
                    returns = hist_data['Close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252) * 100  # Annualized volatility
                    max_price_6mo = hist_data['Close'].max()
                    min_price_6mo = hist_data['Close'].min()

                    # Price momentum (30-day vs current)
                    if len(hist_data) >= 30:
                        price_30d_ago = hist_data['Close'].iloc[-30]
                        momentum_30d = (
                            (current_price - price_30d_ago) / price_30d_ago) * 100
                    else:
                        momentum_30d = 0

                    enriched_data.append({
                        'name': row['ticker_name'],
                        'symbol': row['ticker_symbol'],
                        'asset_type': row['asset_type'],
                        'quantity': row['quantity'],
                        'invested': row['amount_invested'],
                        'current_price': current_price,
                        'purchase_price': row['purchase_price'],
                        'current_value': current_value,
                        'gain_loss': gain_loss,
                        'gain_loss_pct': gain_loss_pct,
                        'days_held': days_held,
                        'buy_date': row['buy_date'],
                        'volatility': volatility,
                        'max_price_6mo': max_price_6mo,
                        'min_price_6mo': min_price_6mo,
                        'momentum_30d': momentum_30d,
                        'historical_data': hist_data.reset_index().to_dict('records')
                    })

                    total_invested += row['amount_invested']
                    total_current_value += current_value

                except Exception as e:
                    st.warning(
                        f"Could not fetch data for {row['ticker_symbol']}: {e}")
                    continue

            # Calculate portfolio metrics
            portfolio_return = ((total_current_value - total_invested) /
                                total_invested) * 100 if total_invested > 0 else 0

            return {
                'holdings': enriched_data,
                'total_invested': total_invested,
                'total_current_value': total_current_value,
                'portfolio_return': portfolio_return,
                'portfolio_summary': self._generate_portfolio_summary(enriched_data, total_invested, total_current_value, portfolio_return)
            }

        except Exception as e:
            return f"Error analyzing portfolio: {e}"

    def _generate_empty_portfolio_advice(self):
        """Generate advice for users with no investments"""
        return {
            'holdings': [],
            'total_invested': 0,
            'total_current_value': 0,
            'portfolio_return': 0,
            'portfolio_summary': """
            🎯 **Ready to Start Your Investment Journey?**
            
            You don't have any investments yet - that's perfectly fine! Everyone starts somewhere.
            
            **Quick Start Recommendations:**
            - Consider starting with a diversified equity fund (SIP)
            - Emergency fund: 6-12 months of expenses in liquid funds
            - Start small but start now - time is your biggest asset
            
            **Next Steps:**
            1. Define your financial goals
            2. Assess your risk tolerance  
            3. Start with small, regular investments
            """
        }

    def _generate_portfolio_summary(self, holdings, total_invested, total_current_value, portfolio_return):
        """Generate a comprehensive portfolio summary"""
        if not holdings:
            return "No holdings to analyze."

        # Asset allocation
        asset_allocation = {}
        for holding in holdings:
            asset_type = holding['asset_type']
            if asset_type in asset_allocation:
                asset_allocation[asset_type] += holding['current_value']
            else:
                asset_allocation[asset_type] = holding['current_value']

        # Top performers
        top_performers = sorted(
            holdings, key=lambda x: x['gain_loss_pct'], reverse=True)[:3]
        underperformers = sorted(
            holdings, key=lambda x: x['gain_loss_pct'])[:3]

        summary = f"""
        📊 **Portfolio Health Check**
        
        **Overall Performance:**
        - Total Invested: ₹{total_invested:,.2f}
        - Current Value: ₹{total_current_value:,.2f}
        - Overall Return: {portfolio_return:.2f}%
        
        **Asset Allocation:**
        """

        for asset_type, value in asset_allocation.items():
            percentage = (value / total_current_value) * 100
            summary += f"\n- {asset_type}: {percentage:.1f}% (₹{value:,.2f})"

        summary += f"\n\n**Top Performers:**"
        for i, holding in enumerate(top_performers, 1):
            summary += f"\n{i}. {holding['name']}: {holding['gain_loss_pct']:.2f}% (₹{holding['gain_loss']:,.2f})"

        if underperformers[0]['gain_loss_pct'] < 0:
            summary += f"\n\n**Needs Attention:**"
            for holding in underperformers:
                if holding['gain_loss_pct'] < 0:
                    summary += f"\n- {holding['name']}: {holding['gain_loss_pct']:.2f}% (₹{holding['gain_loss']:,.2f})"

        return summary

    def get_market_context(self):
        """Get current market context and indices performance"""
        try:
            indices = {
                "Nifty 50": "^NSEI",
                "Sensex": "^BSESN",
                "Nifty Bank": "^NSEBANK",
                "Nifty IT": "^CNXIT"
            }

            market_summary = "📈 **Market Context (YTD Performance):**\n"

            for name, symbol in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="YTD")
                    if not hist.empty:
                        start_price = hist["Close"].iloc[0]
                        current_price = hist["Close"].iloc[-1]
                        ytd_return = (
                            (current_price - start_price) / start_price) * 100
                        market_summary += f"- {name}: {ytd_return:.2f}%\n"
                except:
                    continue

            return market_summary

        except Exception as e:
            return f"Could not fetch market data: {e}"

    def generate_personalized_advice(self, user_query, portfolio_data, context_mode="comprehensive"):
        """Generate personalized financial advice using AI"""
        if not self.model:
            return "AI advisor is currently unavailable."

        try:
            # Prepare context based on mode
            if context_mode == "comprehensive":
                context = self._build_comprehensive_context(portfolio_data)
            elif context_mode == "goals":
                context = self._build_goals_context(portfolio_data)
            elif context_mode == "risk":
                context = self._build_risk_context(portfolio_data)
            else:
                context = self._build_basic_context(portfolio_data)

            # Market context
            market_context = self.get_market_context()

            # Construct the prompt
            system_prompt = f"""
You are an experienced SEBI-registered Investment Advisor and Chartered Financial Analyst with 15+ years in Indian markets. 

**Your Expertise:**
- Deep knowledge of Indian taxation, market regulations, and investment products
- Specialization in goal-based investing, tax optimization, and risk management
- Experience with mutual funds, stocks, bonds, PPF, ELSS, NPS, and other Indian instruments

**Communication Style:**
- Conversational yet professional, like a trusted family financial advisor
- Use Indian context (₹, tax slabs, Indian investment products)
- Provide actionable, specific recommendations
- Use emojis and formatting for better readability
- Give examples and calculations when helpful

**Current Portfolio Analysis:**
{context}

**Market Context:**
{market_context}

**User Query:** {user_query}

**Response Guidelines:**
- Always relate advice to their current portfolio
- Consider Indian tax implications (STCG, LTCG, Section 80C, etc.)
- Suggest specific actions they can take
- Warn about risks without being overly conservative
- Use tables/bullet points for better clarity
- Keep responses engaging but informative

Please provide personalized advice based on their specific situation.
"""

            response = self.model.generate_content(system_prompt)
            return response.text

        except Exception as e:
            return f"⚠️ Error generating advice: {e}"

    def _build_comprehensive_context(self, portfolio_data):
        """Build comprehensive context for AI advisor"""
        if not portfolio_data['holdings']:
            return "User has no current investments. Focus on investment basics and getting started."

        context = f"""
**Portfolio Summary:**
- Total Invested: ₹{portfolio_data['total_invested']:,.2f}
- Current Value: ₹{portfolio_data['total_current_value']:,.2f}
- Overall Return: {portfolio_data['portfolio_return']:.2f}%
- Number of Holdings: {len(portfolio_data['holdings'])}

**Individual Holdings:**
"""

        for holding in portfolio_data['holdings']:
            context += f"""
- {holding['name']} ({holding['symbol']}):
  * Asset Type: {holding['asset_type']}
  * Invested: ₹{holding['invested']:,.2f} | Current: ₹{holding['current_value']:,.2f}
  * Return: {holding['gain_loss_pct']:.2f}% (₹{holding['gain_loss']:,.2f})
  * Holding Period: {holding['days_held']} days
  * Volatility: {holding.get('volatility', 0):.2f}%
"""

        return context

    def _build_goals_context(self, portfolio_data):
        """Build context focused on financial goals"""
        basic_context = self._build_basic_context(portfolio_data)
        return f"""
{basic_context}

**Goal Planning Focus:**
- Current investment corpus: ₹{portfolio_data['total_current_value']:,.2f}
- Monthly investment capacity assessment needed
- Time horizon and risk tolerance evaluation required
- Goal prioritization and allocation strategy needed
"""

    def _build_risk_context(self, portfolio_data):
        """Build context focused on risk analysis"""
        basic_context = self._build_basic_context(portfolio_data)

        if portfolio_data['holdings']:
            # Calculate risk metrics
            equity_exposure = sum(h['current_value'] for h in portfolio_data['holdings']
                                  if h['asset_type'].lower() in ['equity', 'stock'])
            equity_percentage = (
                equity_exposure / portfolio_data['total_current_value']) * 100

            return f"""
{basic_context}

**Risk Analysis Focus:**
- Equity Exposure: {equity_percentage:.1f}% (₹{equity_exposure:,.2f})
- Portfolio concentration risk assessment needed
- Volatility and downside protection analysis required
- Diversification recommendations needed
"""

        return basic_context

    def _build_basic_context(self, portfolio_data):
        """Build basic context for AI advisor"""
        return f"""
**Current Portfolio Status:**
- Total Invested: ₹{portfolio_data['total_invested']:,.2f}
- Current Value: ₹{portfolio_data['total_current_value']:,.2f}
- Overall Return: {portfolio_data['portfolio_return']:.2f}%
- Holdings: {len(portfolio_data['holdings'])} investments
"""

    def create_individual_stock_chart(self, holding):
        """Create detailed chart for individual stock/mutual fund"""
        try:
            # Convert historical data back to DataFrame
            hist_df = pd.DataFrame(holding['historical_data'])
            hist_df['Date'] = pd.to_datetime(hist_df['Date'])

            # Create subplots
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=(
                    f"{holding['name']} - Price Movement", "Volume", "Technical Indicators"),
                vertical_spacing=0.08,
                row_heights=[0.6, 0.2, 0.2]
            )

            # Price chart with candlestick
            fig.add_trace(
                go.Candlestick(
                    x=hist_df['Date'],
                    open=hist_df['Open'],
                    high=hist_df['High'],
                    low=hist_df['Low'],
                    close=hist_df['Close'],
                    name="Price"
                ),
                row=1, col=1
            )

            # Add purchase price line
            fig.add_hline(
                y=holding['purchase_price'],
                line_dash="dash",
                line_color="blue",
                annotation_text=f"Purchase Price: ₹{holding['purchase_price']:.2f}",
                row=1, col=1
            )

            # Add current price line
            fig.add_hline(
                y=holding['current_price'],
                line_dash="dash",
                line_color="green" if holding['gain_loss'] > 0 else "red",
                annotation_text=f"Current Price: ₹{holding['current_price']:.2f}",
                row=1, col=1
            )

            # Volume chart
            colors = ['red' if close < open else 'green' for close,
                      open in zip(hist_df['Close'], hist_df['Open'])]
            fig.add_trace(
                go.Bar(
                    x=hist_df['Date'],
                    y=hist_df['Volume'],
                    marker_color=colors,
                    name="Volume",
                    opacity=0.7
                ),
                row=2, col=1
            )

            # Technical indicators - Moving averages
            hist_df['MA20'] = hist_df['Close'].rolling(window=20).mean()
            hist_df['MA50'] = hist_df['Close'].rolling(window=50).mean()

            fig.add_trace(
                go.Scatter(
                    x=hist_df['Date'],
                    y=hist_df['MA20'],
                    name="MA20",
                    line=dict(color='orange', width=1)
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=hist_df['Date'],
                    y=hist_df['MA50'],
                    name="MA50",
                    line=dict(color='purple', width=1)
                ),
                row=1, col=1
            )

            # RSI calculation and display
            def calculate_rsi(prices, period=14):
                delta = prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(
                    window=period).mean()
                loss = (-delta.where(delta < 0, 0)
                        ).rolling(window=period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return rsi

            hist_df['RSI'] = calculate_rsi(hist_df['Close'])

            fig.add_trace(
                go.Scatter(
                    x=hist_df['Date'],
                    y=hist_df['RSI'],
                    name="RSI",
                    line=dict(color='blue', width=2)
                ),
                row=3, col=1
            )

            # Add RSI overbought/oversold lines
            fig.add_hline(y=70, line_dash="dash",
                          line_color="red", opacity=0.7, row=3, col=1)
            fig.add_hline(y=30, line_dash="dash",
                          line_color="green", opacity=0.7, row=3, col=1)

            # Update layout
            fig.update_layout(
                title=f"{holding['name']} ({holding['symbol']}) - Detailed Analysis",
                height=800,
                xaxis_rangeslider_visible=False,
                showlegend=True
            )

            fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)
            fig.update_yaxes(title_text="RSI", row=3, col=1)

            return fig

        except Exception as e:
            st.error(f"Error creating individual chart: {e}")
            return None

    def create_portfolio_visualization(self, portfolio_data):
        """Create comprehensive interactive portfolio visualizations"""
        if not portfolio_data['holdings']:
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

                            if typ == "ETF":
                                sector = "ETF"
                            if typ == "Mutual Fund":
                                sector = "Mutual Fund"
                                # if (sector == " "):
                                #     sector = "Others"

                            t = yf.Ticker(ticker)
                            info = t.info

                            quote_type = info.get("quoteType")
                            long_name = info.get("longName", "").lower()
                            sector = info.get("sector")
                            # print(f"Quote Type: {quote_type}")
                            # print(f"Long Name: {long_name}")

                            if quote_type == "ETF":
                                sector = "ETF"
                            if "etf" in long_name:
                                sector = "ETF"


                            if st.form_submit_button("Add") and ticker:
                                # print(ticker, ticker_name, amount, broughtAtPrice, qty, buy_date, typ, sector, current_price)
                                engine = AdvancedFinancialAdvisor._get_engine()
                                conn = engine.raw_connection()
                                cur = conn.cursor()
                                cur.execute("INSERT INTO holdings (ticker_symbol, ticker_name, amount_invested, purchase_price, quantity, buy_date, asset_type,sector,LTP) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                            (ticker, ticker_name, amount, broughtAtPrice, qty, buy_date, typ, sector, current_price))
                                conn.commit()
                                conn.close()
                                st.success("Added")
            st.info(
                "📊 No investments to visualize yet. Start investing to see your portfolio analytics!")
            return

        holdings_df = pd.DataFrame(portfolio_data['holdings'])

        # Create tabs for different visualizations
        viz_tabs = st.tabs([
            "💰 Portfolio Overview",
            "📊 Performance Analysis",
            "🎯 Asset Allocation",
            "📈 Risk Analysis",
            "🌳 Portfolio Treemap",
            "📉 Individual Analysis"
        ])

        with viz_tabs[0]:  # Portfolio Overview
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Total Invested",
                    f"₹{portfolio_data['total_invested']:,.2f}"
                )

            with col2:
                st.metric(
                    "Current Value",
                    f"₹{portfolio_data['total_current_value']:,.2f}"

                )
            amount_invested_all = portfolio_data['total_invested']
            profit_loss = portfolio_data['total_current_value'] - \
                amount_invested_all

            profit_loss_percent = profit_loss / \
                amount_invested_all if amount_invested_all != 0 else 0

            # Determine delta display and direction
            if profit_loss > 0:
                color = "#00C853"
                sign = "+"
            elif profit_loss < 0:
                color = "red"
                sign = "-"
            else:
                color = "white"
                sign = ""
            with col3:
                # Use Markdown + HTML for custom styling
                styled_text = f"""
                <div style='
                    font-size: 18px;
                    margin-bottom: 4px;
                '>P/L</div>
                <div style='
                    color: {color};
                    font-size: 32px;
                    line-height: 1.1;
                    margin-top: 0;
                '>
                    {sign}₹{abs(profit_loss):,.2f} ({sign}{abs(profit_loss_percent * 100):.2f}%)
                </div>
                """

                with col3:
                    st.markdown(styled_text, unsafe_allow_html=True)

            # with col4:
            #     avg_holding_period = holdings_df['days_held'].mean()
            #     st.metric(
            #         "Avg Holding Period",
            #         f"{avg_holding_period:.0f} days"
            #     )
            # print(holdings_df)

            # Portfolio composition donut chart

            # Detailed holdings table with enhanced formatting
            if portfolio_data['holdings']:
                st.subheader("📋 Detailed Holdings Analysis")

                holdings_df = pd.DataFrame(portfolio_data['holdings'])

                # Enhanced display dataframe
                # display_df = holdings_df[[
                #     'name', 'asset_type', 'quantity', 'purchase_price',
                #     'current_price', 'invested', 'current_value', 'gain_loss_pct',
                #     'volatility', 'momentum_30d', 'days_held'
                # ]].copy()
                display_df = holdings_df[['symbol',
                    'name', 'invested', 'quantity', 'purchase_price',
                    'current_price',  'current_value', 'gain_loss_pct', 'gain_loss'
                ]].copy()

                # Format columns
                # display_df['gain_loss_pct'] = display_df['gain_loss_pct'].apply(
                #     lambda x: f"{x:.2f}%")
                # display_df['gain_loss'] = display_df['gain_loss'].apply(
                #     lambda x: f"{x:.2f}%")
                # display_df['invested'] = display_df['invested'].apply(
                #     lambda x: f"₹{x:,.2f}")
                # display_df['current_value'] = display_df['current_value'].apply(
                #     lambda x: f"₹{x:,.2f}")
                # display_df['purchase_price'] = display_df['purchase_price'].apply(
                #     lambda x: f"₹{x:.2f}")
                # display_df['current_price'] = display_df['current_price'].apply(
                #     lambda x: f"₹{x:.2f}")
                
                if display_df.empty:
                    st.info("No holdings added yet.")
                else:
                    tickers = list(display_df["symbol"].unique())
                    prices = Ticker(tickers).price

                rows = []
                for _, row in display_df.iterrows():
                    ticker = row["symbol"]
                    ticker_name = row["name"]
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
                        "Avg. Buy Price": f"₹{buy_price:.2f}",
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


                st.dataframe(styled_df, use_container_width=True)
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

                            if typ == "ETF":
                                sector = "ETF"
                            if typ == "Mutual Fund":
                                sector = "Mutual Fund"
                                # if (sector == " "):
                                #     sector = "Others"

                            t = yf.Ticker(ticker)
                            info = t.info

                            quote_type = info.get("quoteType")
                            long_name = info.get("longName", "").lower()
                            sector = info.get("sector")
                            # print(f"Quote Type: {quote_type}")
                            # print(f"Long Name: {long_name}")

                            if quote_type == "ETF":
                                sector = "ETF"
                            if "etf" in long_name:
                                sector = "ETF"


                            if st.form_submit_button("Add") and ticker:
                                # print(ticker, ticker_name, amount, broughtAtPrice, qty, buy_date, typ, sector, current_price)
                                engine = AdvancedFinancialAdvisor._get_engine()
                                conn = engine.raw_connection()
                                cur = conn.cursor()
                                cur.execute("INSERT INTO holdings (ticker_symbol, ticker_name, amount_invested, purchase_price, quantity, buy_date, asset_type,sector,LTP) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                            (ticker, ticker_name, amount, broughtAtPrice, qty, buy_date, typ, sector, current_price))
                                conn.commit()
                                conn.close()
                                st.success("Added")

            st.subheader("Portfolio Composition")

            fig_donut = px.pie(
                holdings_df,
                values='current_value',
                names='name',
                hole=0.4,
                title="Current Portfolio Value Distribution"
            )
            fig_donut.update_traces(
                textinfo='percent+label')
            st.plotly_chart(fig_donut, use_container_width=True)


                # --- Sector Wise Chart ---
            engine = AdvancedFinancialAdvisor._get_engine()
            df = pd.read_sql(
                "SELECT sector, SUM(amount_invested) as total_invested FROM holdings GROUP BY sector", con=engine)
            
            fig_donut = px.pie(
                df,
                names="sector",
                values="total_invested",
                title="Sector Wise Investment Distribution",
                hole=0.4
            )
            fig_donut.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_donut)

        with viz_tabs[1]:  # Performance Analysis
            st.subheader("📊 Performance Analysis")

            # Performance bar chart
            fig_perf = px.bar(
                holdings_df.sort_values('gain_loss_pct', ascending=True),
                x='gain_loss_pct',
                y='name',
                orientation='h',
                title="Investment Performance (%)",
                color='gain_loss_pct',
                color_continuous_scale='RdYlGn',
                text='gain_loss_pct'
            )
            fig_perf.update_traces(
                texttemplate='%{text:.1f}%', textposition='outside')
            fig_perf.update_layout(height=400)
            st.plotly_chart(fig_perf, use_container_width=True)

            # Scatter plot: Risk vs Return
            # st.subheader("Risk vs Return Analysis")
            # fig_scatter = px.scatter(
            #     holdings_df,
            #     x='volatility',
            #     y='gain_loss_pct',
            #     size='current_value',
            #     color='asset_type',
            #     hover_data=['name', 'invested', 'current_value'],
            #     title="Risk vs Return (Bubble size = Current Value)",
            #     labels={'volatility': 'Volatility (%)', 'gain_loss_pct': 'Return (%)'}
            # )
            # st.plotly_chart(fig_scatter, use_container_width=True)

            # Momentum analysis
            # st.subheader("30-Day Momentum Analysis")
            # fig_momentum = px.bar(
            #     holdings_df.sort_values('momentum_30d', ascending=True),
            #     x='momentum_30d',
            #     y='name',
            #     orientation='h',
            #     title="30-Day Price Momentum (%)",
            #     color='momentum_30d',
            #     color_continuous_scale='RdYlGn'
            # )
            # fig_momentum.update_layout(height=400)
            # st.plotly_chart(fig_momentum, use_container_width=True)

        with viz_tabs[2]:  # Asset Allocation
            st.subheader("🎯 Asset Allocation Analysis")

            # Asset allocation pie chart
            asset_allocation = holdings_df.groupby(
                'asset_type')['current_value'].sum().reset_index()
            asset_allocation.index = asset_allocation.index + 1
            
            col1, col2 = st.columns(2)

            with col1:
                fig_pie = px.pie(
                    asset_allocation,
                    values='current_value',
                    names='asset_type',
                    title="Asset Allocation by Value"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                # Asset allocation table
                asset_allocation['percentage'] = (
                    asset_allocation['current_value'] / asset_allocation['current_value'].sum()) * 100
                asset_allocation['current_value_formatted'] = asset_allocation['current_value'].apply(
                    lambda x: f"₹{x:,.0f}")
                asset_allocation['percentage_formatted'] = asset_allocation['percentage'].apply(
                    lambda x: f"{x:.1f}%")

                st.dataframe(
                    asset_allocation[['asset_type', 'current_value_formatted', 'percentage_formatted']].rename(columns={
                        'asset_type': 'Asset Type',
                        'current_value_formatted': 'Value',
                        'percentage_formatted': 'Percentage'
                    }),
                    use_container_width=True
                )

            # Sunburst chart for hierarchical view
            st.subheader("Hierarchical Portfolio View")
            fig_sunburst = px.sunburst(
                holdings_df,
                path=['asset_type', 'name',],
                values='current_value',
                title="Portfolio Hierarchy - Asset Type → Individual Holdings"
            )
            st.plotly_chart(fig_sunburst, use_container_width=True)

            
            st.markdown(
                "Note: Please Click on each sector to expand. This chart shows the distribution of your portfolio across different asset types. A well-diversified portfolio can help manage risk and improve returns over time.")

        with viz_tabs[3]:  # Risk Analysis
            st.subheader("⚠️ Risk Analysis Dashboard")

            # Risk metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                avg_volatility = holdings_df['volatility'].mean()
                st.metric("Avg Portfolio Volatility", f"{avg_volatility:.2f}%")

            with col2:
                max_exposure = holdings_df['current_value'].max()
                max_exposure_pct = (
                    max_exposure / portfolio_data['total_current_value']) * 100
                st.metric("Max Single Exposure", f"{max_exposure_pct:.1f}%")

            with col3:
                diversification_ratio = len(
                    holdings_df) / (holdings_df['current_value'].std() / holdings_df['current_value'].mean())
                st.metric("Diversification Score",
                          f"{diversification_ratio:.2f}")

            # Volatility distribution
            fig_vol = px.histogram(
                holdings_df,
                x='volatility',
                title="Volatility Distribution of Holdings",
                nbins=20,
                labels={
                    'volatility': 'Volatility (%)', 'count': 'Number of Holdings'}
            )
            st.plotly_chart(fig_vol, use_container_width=True)

            # Risk heatmap
            risk_matrix = holdings_df.pivot_table(
                values='current_value',
                index='asset_type',
                columns=pd.cut(holdings_df['volatility'], bins=3, labels=[
                               'Low Risk', 'Medium Risk', 'High Risk']),
                aggfunc='sum',
                fill_value=0
            )

            fig_heatmap = px.imshow(
                risk_matrix.values,
                x=risk_matrix.columns,
                y=risk_matrix.index,
                aspect="auto",
                title="Risk Distribution Heatmap (Value in ₹)"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

        with viz_tabs[4]:  # Portfolio Treemap
            st.subheader("🌳 Portfolio Treemap")

            treeMap().render(overview_df)

            # Create treemap
            fig_treemap = px.treemap(
                holdings_df,
                path=[px.Constant("Portfolio"), 'asset_type', 'name'],
                values='current_value',
                color='gain_loss_pct',
                color_continuous_scale='RdYlGn',
                title="Portfolio Treemap - Size by Value, Color by Performance"
            )
            fig_treemap.update_layout(height=600)
            st.plotly_chart(fig_treemap, use_container_width=True)

            # Alternative treemap by volatility
            fig_treemap_vol = px.treemap(
                holdings_df,
                path=[px.Constant("Portfolio"), 'asset_type', 'name'],
                values='current_value',
                color='volatility',
                color_continuous_scale='Reds',
                title="Portfolio Treemap - Size by Value, Color by Volatility"
            )
            fig_treemap_vol.update_layout(height=600)
            st.plotly_chart(fig_treemap_vol, use_container_width=True)

        with viz_tabs[5]:  # Individual Analysis
            st.subheader("📉 Individual Stock/Fund Analysis")

            # Dropdown to select individual holding
            selected_holding = st.selectbox(
                "Select a holding for detailed analysis:",
                options=holdings_df['name'].tolist(),
                format_func=lambda x: f"{x} ({holdings_df[holdings_df['name']==x]['symbol'].iloc[0]})"
            )

            if selected_holding:
                holding_data = holdings_df[holdings_df['name']
                                           == selected_holding].iloc[0].to_dict()

                # Display key metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Current Price",
                              f"₹{holding_data['current_price']:.2f}")

                with col2:
                    st.metric("Purchase Price",
                              f"₹{holding_data['purchase_price']:.2f}")

                with col3:
                    st.metric(
                        "Return", f"{holding_data['gain_loss_pct']:.2f}%")

                with col4:
                    st.metric("Volatility",
                              f"{holding_data['volatility']:.2f}%")

                # Create detailed chart
                detailed_chart = self.create_individual_stock_chart(
                    holding_data)
                if detailed_chart:
                    st.plotly_chart(detailed_chart, use_container_width=True)

                # Additional metrics table
                st.subheader("Detailed Metrics")
                metrics_data = {
                    "Metric": [
                        "Investment Amount", "Current Value", "Gain/Loss", "Quantity",
                        "Days Held", "6-Month High", "6-Month Low", "30-Day Momentum"
                    ],
                    "Value": [
                        f"₹{holding_data['invested']:,.2f}",
                        f"₹{holding_data['current_value']:,.2f}",
                        f"₹{holding_data['gain_loss']:,.2f}",
                        f"{holding_data['quantity']:.2f}",
                        f"{holding_data['days_held']} days",
                        f"₹{holding_data['max_price_6mo']:.2f}",
                        f"₹{holding_data['min_price_6mo']:.2f}",
                        f"{holding_data['momentum_30d']:.2f}%"
                    ]
                }

                metrics_df = pd.DataFrame(metrics_data)
                st.dataframe(metrics_df, use_container_width=True,
                             hide_index=True)

    def create_market_overview_dashboard(self):
        """Create comprehensive market overview dashboard"""
        st.subheader("📈 Market Overview Dashboard")

        try:
            # Indian market indices
            indices = {
                "Nifty 50": "^NSEI",
                "Sensex": "^BSESN",
                "Nifty Bank": "^NSEBANK",
                "Nifty IT": "^CNXIT",
                "Nifty Auto": "^CNXAUTO",
                "Nifty Pharma": "^CNXPHARMA"
            }

            market_data = []

            for name, symbol in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="1y")
                    info = ticker.info

                    if not hist.empty:
                        current_price = hist["Close"].iloc[-1]
                        prev_close = hist["Close"].iloc[-2] if len(
                            hist) > 1 else current_price
                        change = current_price - prev_close
                        change_pct = (change / prev_close) * 100

                        # YTD performance
                        ytd_hist = ticker.history(period="YTD")
                        if not ytd_hist.empty:
                            ytd_start = ytd_hist["Close"].iloc[0]
                            ytd_return = (
                                (current_price - ytd_start) / ytd_start) * 100
                        else:
                            ytd_return = 0

                        market_data.append({
                            'Index': name,
                            'Symbol': symbol,
                            'Current': current_price,
                            'Change': change,
                            'Change %': change_pct,
                            'YTD Return %': ytd_return,
                            'Historical': hist.reset_index().to_dict('records')
                        })

                except Exception as e:
                    continue

            if market_data:
                market_df = pd.DataFrame(market_data)

                # Market overview metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    nifty_change = market_df[market_df['Index'] == 'Nifty 50']['Change %'].iloc[0] if len(
                        market_df) > 0 else 0
                    st.metric("Nifty 50", f"{nifty_change:.2f}%")

                with col2:
                    sensex_change = market_df[market_df['Index'] == 'Sensex']['Change %'].iloc[0] if len(
                        market_df) > 0 else 0
                    st.metric("Sensex", f"{sensex_change:.2f}%")

                with col3:
                    avg_ytd = market_df['YTD Return %'].mean()
                    st.metric("Avg YTD Return", f"{avg_ytd:.2f}%")

                with col4:
                    positive_indices = len(
                        market_df[market_df['Change %'] > 0])
                    st.metric("Positive Indices",
                              f"{positive_indices}/{len(market_df)}")

                # Market performance chart
                fig_market = px.bar(
                    market_df,
                    x='Index',
                    y='Change %',
                    title="Today's Market Performance",
                    color='Change %',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig_market, use_container_width=True)

                # YTD performance comparison
                fig_ytd = px.bar(
                    market_df,
                    x='Index',
                    y='YTD Return %',
                    title="Year-to-Date Performance",
                    color='YTD Return %',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig_ytd, use_container_width=True)

                # Market correlation heatmap (if we have historical data)
                # if len(market_data) > 1:
                #     try:
                #         correlation_data = {}
                #         for item in market_data:
                #             hist_df = pd.DataFrame(item['Historical'])
                #             if not hist_df.empty:
                #                 hist_df['Date'] = pd.to_datetime(
                #                     hist_df['Date'])
                #                 hist_df = hist_df.set_index('Date')
                #                 correlation_data[item['Index']
                #                                  ] = hist_df['Close'].pct_change()

                #         if correlation_data:
                #             corr_df = pd.DataFrame(correlation_data).corr()

                #             fig_corr = px.imshow(
                #                 corr_df.values,
                #                 x=corr_df.columns,
                #                 y=corr_df.index,
                #                 color_continuous_scale='RdYlBu',
                #                 aspect="auto",
                #                 title="Market Indices Correlation Matrix"
                #             )
                #             st.plotly_chart(fig_corr, use_container_width=True)

                #     except Exception as e:
                #         st.info("Correlation analysis unavailable")

        except Exception as e:
            st.error(f"Error loading market data: {e}")

    def create_sector_analysis(self, portfolio_data):
        """Create sector-wise analysis of portfolio"""
        if not portfolio_data['holdings']:
            return

        st.subheader("🏭 Sector Analysis")

        # Mock sector mapping - in real implementation, you'd fetch this from APIs
        sector_mapping = {
            'IT': ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM'],
            'Banking': ['HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK'],
            'Auto': ['MARUTI', 'TATA', 'BAJAJ', 'HERO', 'M&M'],
            'Pharma': ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'BIOCON'],
            'Energy': ['RELIANCE', 'ONGC', 'IOC', 'BPCL'],
            'FMCG': ['HUL', 'ITC', 'NESTLE', 'BRITANNIA']
        }

        holdings_df = pd.DataFrame(portfolio_data['holdings'])

        # Assign sectors based on symbol (simplified logic)
        def assign_sector(symbol):
            for sector, stocks in sector_mapping.items():
                if any(stock in symbol.upper() for stock in stocks):
                    return sector
            return 'Others'

        holdings_df['sector'] = holdings_df['symbol'].apply(assign_sector)

        # Sector allocation
        sector_allocation = holdings_df.groupby('sector').agg({
            'current_value': 'sum',
            'gain_loss_pct': 'mean',
            'volatility': 'mean'
        }).reset_index()

        sector_allocation['percentage'] = (
            sector_allocation['current_value'] / sector_allocation['current_value'].sum()) * 100

        col1, col2 = st.columns(2)

        with col1:
            # Sector allocation pie chart
            fig_sector = px.pie(
                sector_allocation,
                values='current_value',
                names='sector',
                title="Sector Allocation"
            )
            st.plotly_chart(fig_sector, use_container_width=True)

        with col2:
            # Sector performance bar chart
            fig_sector_perf = px.bar(
                sector_allocation,
                x='sector',
                y='gain_loss_pct',
                title="Sector-wise Performance",
                color='gain_loss_pct',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig_sector_perf, use_container_width=True)

        # Sector metrics table
        st.subheader("Sector Metrics")
        sector_display = sector_allocation.copy()
        sector_display['current_value'] = sector_display['current_value'].apply(
            lambda x: f"₹{x:,.0f}")
        sector_display['percentage'] = sector_display['percentage'].apply(
            lambda x: f"{x:.1f}%")
        sector_display['gain_loss_pct'] = sector_display['gain_loss_pct'].apply(
            lambda x: f"{x:.2f}%")
        sector_display['volatility'] = sector_display['volatility'].apply(
            lambda x: f"{x:.2f}%")

        sector_display.columns = [
            'Sector', 'Value', 'Portfolio %', 'Avg Return %', 'Avg Volatility %']
        st.dataframe(sector_display, use_container_width=True, hide_index=True)

    def create_goal_planning_module(self):
        """Create goal-based investment planning module"""
        st.subheader("🎯 Goal-Based Investment Planning")

        # Goal input form
        with st.expander("➕ Add New Financial Goal", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                goal_name = st.text_input(
                    "Goal Name", placeholder="e.g., House Down Payment")
                target_amount = st.number_input(
                    "Target Amount (₹)", min_value=0, value=1000000)
                time_horizon = st.number_input(
                    "Time Horizon (Years)", min_value=1, value=5)

            with col2:
                current_savings = st.number_input(
                    "Current Savings (₹)", min_value=0, value=0)
                monthly_sip = st.number_input(
                    "Monthly SIP Capacity (₹)", min_value=0, value=10000)
                expected_return = st.slider(
                    "Expected Annual Return (%)", min_value=1, max_value=20, value=12)

            if st.button("Calculate Goal Strategy"):
                # Goal calculation logic
                future_value_current = current_savings * \
                    ((1 + expected_return/100) ** time_horizon)

                # SIP calculation
                monthly_rate = expected_return / (12 * 100)
                months = time_horizon * 12
                future_value_sip = monthly_sip * \
                    (((1 + monthly_rate) ** months - 1) / monthly_rate)

                total_projected = future_value_current + future_value_sip
                shortfall = max(0, target_amount - total_projected)

                # Display results
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Target Amount", f"₹{target_amount:,.0f}")

                with col2:
                    st.metric("Projected Amount", f"₹{total_projected:,.0f}")

                with col3:
                    if shortfall > 0:
                        st.metric(
                            "Shortfall", f"₹{shortfall:,.0f}", delta=f"-₹{shortfall:,.0f}")
                    else:
                        surplus = total_projected - target_amount
                        st.metric(
                            "Surplus", f"₹{surplus:,.0f}", delta=f"+₹{surplus:,.0f}")

                # Recommendations
                st.subheader("💡 Recommendations")

                if shortfall > 0:
                    additional_monthly = shortfall / \
                        (((1 + monthly_rate) ** months - 1) / monthly_rate)
                    st.warning(
                        f"To meet your goal, consider increasing your monthly SIP by ₹{additional_monthly:,.0f}")
                else:
                    st.success(
                        "🎉 Your current plan is on track to meet your goal!")

                # Goal progress visualization
                years = list(range(1, time_horizon + 1))
                projected_values = []

                for year in years:
                    fv_current = current_savings * \
                        ((1 + expected_return/100) ** year)
                    months_elapsed = year * 12
                    fv_sip = monthly_sip * \
                        (((1 + monthly_rate) ** months_elapsed - 1) / monthly_rate)
                    projected_values.append(fv_current + fv_sip)

                progress_df = pd.DataFrame({
                    'Year': years,
                    'Projected Value': projected_values,
                    'Target': [target_amount] * len(years)
                })

                fig_goal = px.line(
                    progress_df,
                    x='Year',
                    y=['Projected Value', 'Target'],
                    title=f"Goal Progress: {goal_name}",
                    labels={'value': 'Amount (₹)', 'variable': 'Metric'}
                )
                st.plotly_chart(fig_goal, use_container_width=True)


def render_enhanced_ai_advisor():
    """Main function to render the enhanced AI advisor interface"""
    st.set_page_config(
        page_title="🧠 AI Financial Advisor",
        page_icon="💰",
        layout="wide"
    )

    # Initialize advisor
    if 'advisor' not in st.session_state:
        st.session_state.advisor = AdvancedFinancialAdvisor()

    advisor = st.session_state.advisor

    # Header
    st.title("🧠 Your Personal AI Financial Advisor")
    st.markdown(
        "*Making smart financial decisions with AI-powered insights and advanced analytics*")

    # Sidebar for mode selection and portfolio overview
    with st.sidebar:
        st.header("🎯 Advisory Modes")

        advisory_mode = st.selectbox(
            "Choose your focus area:",
            [
                "💬 General Financial Advice",
                "📊 Portfolio Analysis",
                "🎯 Goal Planning",
                "⚠️ Risk Assessment",
                "📈 Market Insights",
                "💡 Tax Optimization"
            ]
        )

        # Quick portfolio snapshot
        st.header("📋 Portfolio Snapshot")
        if st.button("🔄 Refresh Portfolio Data"):
            st.session_state.portfolio_data = advisor.get_comprehensive_portfolio_analysis()

        # Load portfolio data
        if 'portfolio_data' not in st.session_state:
            with st.spinner("Loading portfolio data..."):
                st.session_state.portfolio_data = advisor.get_comprehensive_portfolio_analysis()

        portfolio_data = st.session_state.portfolio_data

        if isinstance(portfolio_data, dict) and portfolio_data['holdings']:
            st.metric("Total Value",
                      f"₹{portfolio_data['total_current_value']:,.0f}")
            st.metric("Total Return",
                      f"{portfolio_data['portfolio_return']:.2f}%")
            st.metric("Holdings", len(portfolio_data['holdings']))
        else:
            st.info("No portfolio data available")

    # Main content area with expanded tabs
    main_tabs = st.tabs([
        "💬 AI Advisor Chat",
        "📊 Portfolio Dashboard",
        "📈 Market Overview",
        "🎯 Goal Planning",
        "🏭 Sector Analysis"
    ])

    with main_tabs[0]:  # AI Advisor Chat
        st.header("💬 Chat with Your AI Advisor")
        holdings_df_1 = pd.DataFrame(portfolio_data['holdings']) if portfolio_data and 'holdings' in portfolio_data else pd.DataFrame()
        render_ai_chat(holdings_df_1)
        # Initialize chat history
    #     if "chat_history" not in st.session_state:
    #         st.session_state.chat_history = [
    #             {
    #                 "role": "assistant",
    #                 "content": "👋 Hello! I'm your personal AI financial advisor with advanced analytics capabilities. I can help you with:\n\n• Portfolio analysis with detailed visualizations\n• Individual stock/mutual fund tracking\n• Risk assessment and sector analysis\n• Goal-based investment planning\n• Market insights and correlations\n• Tax optimization strategies\n\nWhat would you like to explore today?"
    #             }
    #         ]

    #     # Display chat history
    #     for message in st.session_state.chat_history:
    #         with st.chat_message(message["role"]):
    #             st.markdown(message["content"])

    #     # Chat input
    #     if user_input := st.chat_input("Ask me anything about your finances..."):
    #         # Add user message to chat history
    #         st.session_state.chat_history.append(
    #             {"role": "user", "content": user_input})

    #         # Display user message
    #         with st.chat_message("user"):
    #             st.markdown(user_input)

    #         # Generate AI response
    #         with st.chat_message("assistant"):
    #             with st.spinner("Analyzing your query..."):
    #                 # Determine context mode based on advisory mode
    #                 context_mode_map = {
    #                     "💬 General Financial Advice": "comprehensive",
    #                     "📊 Portfolio Analysis": "comprehensive",
    #                     "🎯 Goal Planning": "goals",
    #                     "⚠️ Risk Assessment": "risk",
    #                     "📈 Market Insights": "comprehensive",
    #                     "💡 Tax Optimization": "comprehensive"
    #                 }

    #                 context_mode = context_mode_map.get(
    #                     advisory_mode, "comprehensive")

    #                 # Generate response
    #                 response = advisor.generate_personalized_advice(
    #                     user_input,
    #                     portfolio_data,
    #                     context_mode
    #                 )

    #                 # Display response with typing effect
    #                 message_placeholder = st.empty()
    #                 full_response = ""

    #                 for chunk in response.split():
    #                     full_response += chunk + " "
    #                     message_placeholder.markdown(full_response + "▌")
    #                     time.sleep(0.02)

    #                 message_placeholder.markdown(full_response)

    #                 # Add assistant response to chat history
    #                 st.session_state.chat_history.append(
    #                     {"role": "assistant", "content": full_response})

    with main_tabs[1]:  # Portfolio Dashboard
        st.header("📊 Advanced Portfolio Dashboard")

        if isinstance(portfolio_data, dict):
            # Create comprehensive visualizations
            advisor.create_portfolio_visualization(portfolio_data)

        else:
            st.info(
                "Portfolio data not available. Please check your database connection.")

    with main_tabs[2]:  # Market Overview
        advisor.create_market_overview_dashboard()

    with main_tabs[3]:  # Goal Planning
        advisor.create_goal_planning_module()

    with main_tabs[4]:  # Sector Analysis
        if isinstance(portfolio_data, dict):
            advisor.create_sector_analysis(portfolio_data)
        else:
            st.info("Portfolio data needed for sector analysis")

    # Footer
    st.markdown("---")
    st.markdown("💡 **Disclaimer:** This AI advisor provides general guidance based on your portfolio data and market analysis. Please consult with a certified financial advisor for personalized investment advice.")


# Run the application
if __name__ == "__main__":
    render_enhanced_ai_advisor()
