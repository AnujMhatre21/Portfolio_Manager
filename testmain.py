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
import warnings
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
                    # Get current market data
                    ticker = yf.Ticker(row['ticker_symbol'])
                    current_price = ticker.history(period="1d")['Close'].iloc[-1]
                    
                    # Calculate metrics
                    current_value = current_price * row['quantity']
                    gain_loss = current_value - row['amount_invested']
                    gain_loss_pct = (gain_loss / row['amount_invested']) * 100
                    
                    # Days held
                    days_held = (datetime.now() - pd.to_datetime(row['buy_date'])).days
                    
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
                        'buy_date': row['buy_date']
                    })
                    
                    total_invested += row['amount_invested']
                    total_current_value += current_value
                    
                except Exception as e:
                    st.warning(f"Could not fetch data for {row['ticker_symbol']}: {e}")
                    continue
            
            # Calculate portfolio metrics
            portfolio_return = ((total_current_value - total_invested) / total_invested) * 100
            
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
        top_performers = sorted(holdings, key=lambda x: x['gain_loss_pct'], reverse=True)[:3]
        underperformers = sorted(holdings, key=lambda x: x['gain_loss_pct'])[:3]
        
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
                        ytd_return = ((current_price - start_price) / start_price) * 100
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
            equity_exposure = sum(h['current_value'] for h in portfolio_data['holdings'] if h['asset_type'].lower() in ['equity', 'stock'])
            equity_percentage = (equity_exposure / portfolio_data['total_current_value']) * 100
            
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

    def create_portfolio_visualization(self, portfolio_data):
        """Create interactive portfolio visualizations"""
        if not portfolio_data['holdings']:
            st.info("📊 No investments to visualize yet. Start investing to see your portfolio analytics!")
            return
        
        holdings_df = pd.DataFrame(portfolio_data['holdings'])
        
        # Create tabs for different visualizations
        viz_tab1, viz_tab2, viz_tab3 = st.tabs(["💰 Portfolio Overview", "📊 Performance", "🎯 Asset Allocation"])
        
        with viz_tab1:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Invested",
                    f"₹{portfolio_data['total_invested']:,.0f}"
                )
            
            with col2:
                st.metric(
                    "Current Value",
                    f"₹{portfolio_data['total_current_value']:,.0f}",
                    f"₹{portfolio_data['total_current_value'] - portfolio_data['total_invested']:,.0f}"
                )
            
            with col3:
                st.metric(
                    "Total Return",
                    f"{portfolio_data['portfolio_return']:.2f}%"
                )
            
            with col4:
                avg_holding_period = holdings_df['days_held'].mean()
                st.metric(
                    "Avg Holding Period",
                    f"{avg_holding_period:.0f} days"
                )
        
        with viz_tab2:
            # Performance chart
            fig = px.bar(
                holdings_df.sort_values('gain_loss_pct', ascending=True),
                x='gain_loss_pct',
                y='name',
                orientation='h',
                title="Investment Performance (%)",
                color='gain_loss_pct',
                color_continuous_scale=['red', 'yellow', 'green']
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with viz_tab3:
            # Asset allocation pie chart
            asset_allocation = holdings_df.groupby('asset_type')['current_value'].sum().reset_index()
            
            fig = px.pie(
                asset_allocation,
                values='current_value',
                names='asset_type',
                title="Asset Allocation"
            )
            st.plotly_chart(fig, use_container_width=True)


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
    st.markdown("*Making smart financial decisions with AI-powered insights*")
    
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
            st.metric("Total Value", f"₹{portfolio_data['total_current_value']:,.0f}")
            st.metric("Total Return", f"{portfolio_data['portfolio_return']:.2f}%")
            st.metric("Holdings", len(portfolio_data['holdings']))
        else:
            st.info("No portfolio data available")
    
    # Main content area
    main_tab1, main_tab2 = st.tabs(["💬 AI Advisor Chat", "📊 Portfolio Dashboard"])
    
    with main_tab1:
        # Chat interface
        st.header("💬 Chat with Your AI Advisor")
        
        # Initialize chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": "👋 Hello! I'm your personal AI financial advisor. I have access to your portfolio and can help you with investment decisions, goal planning, risk assessment, and more. What would you like to discuss today?"
                }
            ]
        
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if user_input := st.chat_input("Ask me anything about your finances..."):
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Generate AI response
            with st.chat_message("assistant"):
                with st.spinner("Analyzing your query..."):
                    # Determine context mode based on advisory mode
                    context_mode_map = {
                        "💬 General Financial Advice": "comprehensive",
                        "📊 Portfolio Analysis": "comprehensive",
                        "🎯 Goal Planning": "goals",
                        "⚠️ Risk Assessment": "risk",
                        "📈 Market Insights": "comprehensive",
                        "💡 Tax Optimization": "comprehensive"
                    }
                    
                    context_mode = context_mode_map.get(advisory_mode, "comprehensive")
                    
                    # Generate response
                    response = advisor.generate_personalized_advice(
                        user_input, 
                        portfolio_data, 
                        context_mode
                    )
                    
                    # Display response with typing effect
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    for chunk in response.split():
                        full_response += chunk + " "
                        message_placeholder.markdown(full_response + "▌")
                        time.sleep(0.02)
                    
                    message_placeholder.markdown(full_response)
                    
                    # Add assistant response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": full_response})
    
    with main_tab2:
        # Portfolio dashboard
        st.header("📊 Portfolio Dashboard")
        
        if isinstance(portfolio_data, dict):
            # Create visualizations
            advisor.create_portfolio_visualization(portfolio_data)
            
            # Detailed holdings table
            if portfolio_data['holdings']:
                st.subheader("📋 Detailed Holdings")
                
                holdings_df = pd.DataFrame(portfolio_data['holdings'])
                
                # Format the dataframe for display
                display_df = holdings_df[[
                    'name', 'asset_type', 'quantity', 'purchase_price', 
                    'current_price', 'invested', 'current_value', 'gain_loss_pct'
                ]].copy()
                
                display_df['gain_loss_pct'] = display_df['gain_loss_pct'].apply(lambda x: f"{x:.2f}%")
                display_df['invested'] = display_df['invested'].apply(lambda x: f"₹{x:,.2f}")
                display_df['current_value'] = display_df['current_value'].apply(lambda x: f"₹{x:,.2f}")
                display_df['purchase_price'] = display_df['purchase_price'].apply(lambda x: f"₹{x:.2f}")
                display_df['current_price'] = display_df['current_price'].apply(lambda x: f"₹{x:.2f}")
                
                display_df.columns = [
                    'Investment', 'Type', 'Quantity', 'Buy Price', 
                    'Current Price', 'Invested', 'Current Value', 'Return %'
                ]
                
                st.dataframe(display_df, use_container_width=True)
        else:
            st.info("Portfolio data not available. Please check your database connection.")
    
    # Footer
    st.markdown("---")
    st.markdown("💡 **Disclaimer:** This AI advisor provides general guidance based on your portfolio data. Please consult with a certified financial advisor for personalized investment advice.")


# Run the application
if __name__ == "__main__":
    render_enhanced_ai_advisor()