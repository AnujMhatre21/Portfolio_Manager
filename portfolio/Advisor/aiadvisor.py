import streamlit as st
import pandas as pd
import time
import yfinance as yf
from sqlalchemy import create_engine
import google.generativeai as genai


class aiAdvisor:
    @staticmethod
    def get_engine():
        config = st.secrets["mysql"]
        connection_string = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        return create_engine(connection_string)

    @staticmethod
    def get_model():
        config = st.secrets["apikey"]
        genai.configure(api_key=config["api_key"])
        return genai.GenerativeModel("gemini-1.5-flash")

    @staticmethod
    def get_portfolio_summary():
        engine = aiAdvisor.get_engine()
        df = pd.read_sql(
            "SELECT id, ticker_symbol, ticker_name, amount_invested, purchase_price, buy_date, asset_type, quantity FROM holdings", con=engine)
        if df.empty:
            return "The user currently has no investments in their portfolio."
        summary = ""
        for _, row in df.iterrows():
            summary += f"- {row['ticker_name']}: amount_invested ₹{row['amount_invested']}, Qty: {row['quantity']}, buy_date: {row['buy_date']}, purchase_price: {row['purchase_price']}, asset_type: {row['asset_type']}\n"
            # print(summary)
        return summary

    @staticmethod
    def get_nifty_return():
        try:
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="YTD")
            start = hist["Close"].iloc[0]
            end = hist["Close"].iloc[-1]
            return_percent = ((end - start) / start) * 100
            return f"Nifty 50 YTD return: **{return_percent:.2f}%**."
        except Exception:
            return "Could not fetch Nifty 50 data."


def classify_user_intent(model, user_message):
    """Uses Gemini to classify user intent."""
    prompt = f"""
You are an intent classifier for a financial assistant app.

Classify the user's message into one of:
- casual
- goal
- portfolio

Return ONLY one of the above.

User message:
\"{user_message}\"
"""
    try:
        result = model.generate_content(prompt)
        intent = result.text.strip().lower()
        return intent if intent in ["casual", "goal", "portfolio"] else "portfolio"
    except Exception:
        return "portfolio"


# def render_ai_chat(holdings_df):
#     st.title("🤖 AI Financial Advisor")
#     st.markdown("Get smart, contextual advice from your AI investment expert.")

#     mode = st.radio("Advisor Mode", [
#                     "💼 Portfolio Review", "🎯 Goal Planning", "📊 Compare with Nifty"])

#     model = aiAdvisor.get_model()
#     portfolio_summary = aiAdvisor.get_portfolio_summary()
#     dfFrommain = holdings_df
#     nifty_summary = aiAdvisor.get_nifty_return(
#     ) if mode == "📊 Compare with Nifty" else ""

#     if "chat_history" not in st.session_state:
#         st.session_state.chat_history = []

#     # Show chat history
#     for msg in st.session_state.chat_history:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

#     if prompt := st.chat_input("Ask your financial advisor..."):
#         st.chat_message("user").markdown(prompt)
#         st.session_state.chat_history.append(
#             {"role": "user", "content": prompt})

#         # 🔍 Intent Detection
#         intent = classify_user_intent(model, prompt)

#         # 💬 Prepare response
#         with st.chat_message("assistant"):
#             # message_placeholder = st.empty()
#             typing_placeholder = st.empty()
#             final_message_placeholder = st.empty()
#             reply = ""

#             try:
#                 if intent == "casual":
#                     casual_prompt = f"Respond conversationally to: {prompt}"
#                     result = model.generate_content(casual_prompt)
#                     reply = result.text

#                 else:
#                     # Portfolio or goal prompt
#                     system_prompt = f"""
# As a certified financial advisor and a Chartered accountant with expertise in investment analysis, risk planning, and long-term wealth strategy, you are well-equipped to guide individuals towards financial success. In our conversation, let's approach it as a casual chat rather than a formal Q&A session.
# You have the unique ability to access the user's portfolio details, allowing you to offer personalized advice tailored to their specific investments. Feel free to draw insights from the user's portfolio summary whenever necessary.
# Moreover, you can provide comparisons between the user's investments and the performance of the Nifty 50 index in the Indian stock market upon request. This contextual backdrop will ensure that the recommendations and insights provided are relevant and practical for the user's financial journey. 
# and also avoid giving long answers unless specifically asked for detailed explanations.and also make sure to user tabluar format and markdown formatting to make the response more readable.and also make sure to use emojis to make the response more engaging.
#                     ### User Portfolio:
# {portfolio_summary} 
# {dfFrommain}
# """

#                     if intent == "goal":
#                         system_prompt += """
# The user is discussing a financial goal. Assess feasibility and give strategic, tailored advice for reaching the goal based on their investments.
# """
#                     elif mode == "📊 Compare with Nifty":
#                         system_prompt += f"""
# Compare the user's investment returns to this benchmark:
# {nifty_summary}
# """

#                     system_prompt += f"\n\n### User's Question:\n{prompt}"

#                     result = model.generate_content(system_prompt)
#                     reply = result.text

#             except Exception as e:
#                 reply = f"⚠️ Gemini API error: {e}"

#             # Simulated typing
#             simulated = ""
#             for word in reply.split():
#                 simulated += word + " "
#                 typing_placeholder.markdown(simulated + "▌")
#                 time.sleep(0.03)

#             typing_placeholder.empty()  # Clear the typing placeholder
#             final_message_placeholder.markdown(reply, unsafe_allow_html=True)

#             # Save reply to history
#             st.session_state.chat_history.append(
#                 {"role": "assistant", "content": reply})


def render_ai_chat(holdings_df):
    st.title("🤖 AI Financial Advisor")
    st.markdown("Get smart, contextual advice from your AI investment expert.")

    mode = st.radio("Advisor Mode", [
                    "💼 Portfolio Review", "🎯 Goal Planning", "📊 Compare with Nifty"])

    model = aiAdvisor.get_model()
    portfolio_summary = aiAdvisor.get_portfolio_summary()
    dfFrommain = holdings_df
    nifty_summary = aiAdvisor.get_nifty_return() if mode == "📊 Compare with Nifty" else ""

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Show chat history at the top
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 👉 Chat input should be last so it stays at the bottom
    if prompt := st.chat_input("Ask your financial advisor..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            typing_placeholder = st.empty()
            final_message_placeholder = st.empty()
            reply = ""

            try:
                # 🔍 Intent Detection
                intent = classify_user_intent(model, prompt)

                if intent == "casual":
                    casual_prompt = f"Respond conversationally to: {prompt}"
                    result = model.generate_content(casual_prompt)
                    reply = result.text
                else:
                    # 🎯 Portfolio or Goal prompt with context
                    system_prompt = f"""
As a certified financial advisor, respond to the user casually but helpfully.
Use markdown formatting and emojis. Be brief unless asked for detail.
Show portfolio details if relevant.

### User Portfolio:
{portfolio_summary}

{dfFrommain}

"""
                    if intent == "goal":
                        system_prompt += "\nThe user is discussing a financial goal. Provide advice based on portfolio.\n"
                    if mode == "📊 Compare with Nifty":
                        system_prompt += f"\nCompare investments to this benchmark:\n{nifty_summary}\n"

                    system_prompt += f"\n\n### User's Question:\n{prompt}"
                    result = model.generate_content(system_prompt)
                    reply = result.text

            except Exception as e:
                reply = f"⚠️ Gemini API error: {e}"

            # Simulate typing
            simulated = ""
            for word in reply.split():
                simulated += word + " "
                typing_placeholder.markdown(simulated + "▌")
                time.sleep(0.03)

            typing_placeholder.empty()
            final_message_placeholder.markdown(reply, unsafe_allow_html=True)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
