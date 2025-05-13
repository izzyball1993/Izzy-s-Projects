import streamlit as st
import sqlite3
import hashlib
import datetime
import random
import requests
import yfinance as yf
import openai
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Set your API keys here
openai.api_key = "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"    
NEWS_API_KEY = "6e40b44cdc1a49d5a4331d421896ca4b"

# ----------------------
# Accessibility Mode (High Contrast & Larger Font)
# ----------------------
accessibility_mode = st.sidebar.checkbox("Enable Accessibility Mode", value=False)

if accessibility_mode:
    st.markdown("""
        <style>
            /* Increase base font size for enhanced readability */
            html, body, [class*="css"] {
                font-size: 18px !important;
            }
            /* High contrast styling for buttons */
            .stButton > button {
                background-color: #000000 !important;
                color: #FFFFFF !important;
                border: 2px solid #FFFFFF !important;
            }
            /* Improve contrast for sidebar text */
            .css-1d391kg, .css-16huue1 {
                color: #000000 !important;
            }
            /* High contrast background on primary content */
            .css-1avcm0n {
                background-color: #FFFFFF !important;
                color: #000000 !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
# ----------------------
# Database and Helper Functions
# ----------------------

def get_db_connection():
    """Establish a database connection and return the connection and cursor."""
    conn = sqlite3.connect("bank.db", check_same_thread=False)
    return conn, conn.cursor()

def create_tables():
    """Initialize the database tables if they don't exist."""
    conn, cursor = get_db_connection()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            username TEXT PRIMARY KEY,
            balance REAL DEFAULT 0,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            amount REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    """Securely hash the password."""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    """Register a new user with a hashed password."""
    conn, cursor = get_db_connection()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return "Username already exists!"
    password_hash = hash_password(password)
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
    cursor.execute("INSERT INTO accounts (username, balance) VALUES (?, 0)", (username,))
    conn.commit()
    conn.close()
    return f"User '{username}' registered successfully!"

def verify_login(username, password):
    """Verify user credentials."""
    conn, cursor = get_db_connection()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result and hash_password(password) == result[0]

def get_balance(username):
    """Retrieve the account balance for the user."""
    conn, cursor = get_db_connection()
    cursor.execute("SELECT balance FROM accounts WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def deposit(username, amount):
    """Deposit funds into the user's account."""
    conn, cursor = get_db_connection()
    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE username = ?", (amount, username))
    conn.commit()
    conn.close()
    log_transaction(username, "Deposit", amount)
    return f"${amount:.2f} deposited successfully!"

def withdraw(username, amount):
    """Withdraw funds from the user's account after checking the balance."""
    balance = get_balance(username)
    if balance is not None and amount <= balance:
        conn, cursor = get_db_connection()
        cursor.execute("UPDATE accounts SET balance = balance - ? WHERE username = ?", (amount, username))
        conn.commit()
        conn.close()
        log_transaction(username, "Withdrawal", amount)
        return f"${amount:.2f} withdrawn successfully!"
    return "Insufficient funds."

def log_transaction(username, action, amount):
    """Log a deposit or withdrawal transaction."""
    conn, cursor = get_db_connection()
    cursor.execute("INSERT INTO transactions (username, action, amount) VALUES (?, ?, ?)",
                   (username, action, amount))
    conn.commit()
    conn.close()

def get_transactions(username):
    """Retrieve all transactions for the current user without filtering."""
    conn, cursor = get_db_connection()
    cursor.execute("SELECT action, amount, timestamp FROM transactions WHERE username = ? ORDER BY timestamp DESC", (username,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def get_filtered_transactions(username, start_date, end_date, transaction_type, search_query, sort_order):
    """
    Retrieve filtered transaction history.
    
    - start_date, end_date: date objects.
    - transaction_type: "All", "Deposit", or "Withdrawal".
    - search_query: Optional string filter.
    - sort_order: "Ascending" or "Descending".
    """
    conn, cursor = get_db_connection()
    query = "SELECT action, amount, timestamp FROM transactions WHERE username = ?"
    params = [username]
    
    if start_date:
        query += " AND DATE(timestamp) >= ?"
        params.append(str(start_date))
    if end_date:
        query += " AND DATE(timestamp) <= ?"
        params.append(str(end_date))
    if transaction_type != "All":
        query += " AND action = ?"
        params.append(transaction_type)
        
    query += " ORDER BY timestamp " + ("ASC" if sort_order == "Ascending" else "DESC")
    
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    conn.close()
    
    # Additional text filtering if provided
    if search_query:
        transactions = [txn for txn in transactions if search_query.lower() in str(txn).lower()]
    
    return transactions

# ----------------------
# Utility Functions
# ----------------------

def get_greeting():
    """Generate a greeting based on the current time."""
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "🌅 Good morning"
    elif 12 <= hour < 18:
        return "☀️ Good afternoon"
    else:
        return "🌙 Good evening"

def get_motivational_quote():
    """Return a random motivational quote."""
    quotes = [
        "💪 The secret to getting ahead is getting started.",
        "🚀 Your only limit is your mind.",
        "🔥 Success doesn’t come from what you do occasionally—it comes from what you do consistently.",
        "🎯 Believe in yourself and you will be unstoppable.",
        "🏆 Every champion was once a contender who refused to give up."
    ]
    return random.choice(quotes)

# ----------------------
# Stock & News Functions
# ----------------------

def get_stock_data():
    """Fetch real-time stock and cryptocurrency data using Yahoo Finance."""
    dow = yf.Ticker("^DJI").history(period="1d")["Close"].iloc[-1]
    nasdaq = yf.Ticker("^IXIC").history(period="1d")["Close"].iloc[-1]
    sp500 = yf.Ticker("^GSPC").history(period="1d")["Close"].iloc[-1]
    btc = yf.Ticker("BTC-USD").history(period="1d")["Close"].iloc[-1]
    eth = yf.Ticker("ETH-USD").history(period="1d")["Close"].iloc[-1]
    return dow, nasdaq, sp500, btc, eth

def get_latest_news():
    """Fetch top news headlines from NewsAPI."""
    NEWS_API_URL = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
    response = requests.get(NEWS_API_URL)
    news = response.json()
    return [article["title"] for article in news.get("articles", [])[:5]]

# ----------------------
# Exchange Rates Function
# ----------------------
def get_exchange_rates():
    """
    Fetch exchange rates for USD-CAD, USD-EUR, USD-GBP, and USD-JPY using Yahoo Finance.
    The tickers used are:
      - USDCAD=X for USD-CAD
      - USDEUR=X for USD-EUR
      - USDGBP=X for USD-GBP (if unavailable, consider using GBPUSD=X and taking the inverse)
      - USDJPY=X for USD-JPY
    """
    pairs = {
        "USD-CAD": "USDCAD=X",
        "USD-EUR": "USDEUR=X",
        "USD-GBP": "USDGBP=X",
        "USD-JPY": "USDJPY=X"
    }
    rates = {}
    for pair, ticker in pairs.items():
        try:
            data = yf.Ticker(ticker).history(period="1d")
            rate = data["Close"].iloc[-1]
            rates[pair] = rate
        except Exception as e:
            rates[pair] = f"Error: {e}"
    return rates

# ----------------------
# AI Financial Chat Assistant
# ----------------------

def ai_financial_chat(user_input):
    """Use the OpenAI API to generate financial advice based on the user's query."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful, knowledgeable financial assistant offering personal finance, budgeting, saving, and investing advice."},
                {"role": "user", "content": user_input}
            ]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error with AI Assistant: {str(e)}"

# ----------------------
# Initialize Database
# ----------------------
create_tables()

# ----------------------
# Streamlit UI
# ----------------------
st.title("🏦 Banking System Web App")

# Sidebar: Stock Market Overview
st.sidebar.title("📈 Market Overview")
dow, nasdaq, sp500, btc, eth = get_stock_data()
st.sidebar.metric("Dow Jones", f"${dow:,.2f}")
st.sidebar.metric("NASDAQ", f"${nasdaq:,.2f}")
st.sidebar.metric("S&P 500", f"${sp500:,.2f}")
st.sidebar.metric("Bitcoin (BTC)", f"${btc:,.2f}")
st.sidebar.metric("Ethereum (ETH)", f"${eth:,.2f}")

# Real-Time Scrolling Newsfeed (Auto-refresh every 30 seconds)
st_autorefresh(interval=30000, key="newsfeed")
headlines = get_latest_news()
scrolling_text = "  |  ".join(headlines)
st.markdown(f'<marquee role="contentinfo" aria-label="Latest news headlines">{scrolling_text}</marquee>', unsafe_allow_html=True)

# ----------------------
# Navigation Menu
# ----------------------
if "user" in st.session_state:
    nav = st.sidebar.selectbox("Menu", ["Banking", "Chat"])
else:
    nav = st.sidebar.selectbox("Menu", ["Register", "Login", "Chat"])

# ----------------------
# Page Routing based on Navigation Menu
# ----------------------
if nav == "Register":
    st.subheader("🔹 Register a New User")
    new_user = st.text_input("Username", key="reg_user", help="Enter your desired username")
    new_pass = st.text_input("Password", type="password", key="reg_pass", help="Enter a secure password")
    if st.button("Register", key="register_btn"):
        result = register_user(new_user, new_pass)
        st.success(result)

elif nav == "Login":
    st.subheader("🔹 User Login")
    username = st.text_input("Username", key="login_user", help="Enter your username")
    password = st.text_input("Password", type="password", key="login_pass", help="Enter your password")
    if st.button("Login", key="login_btn"):
        if verify_login(username, password):
            st.session_state["user"] = username
            st.session_state["welcome_shown"] = False
            st.rerun()
        else:
            st.error("❌ Invalid username or password!")

elif nav == "Chat":
    st.subheader("💬 AI Financial Assistant Chat")
    user_query = st.text_input("Ask me anything about finance!", key="chat_input", help="Type here to ask for financial advice.")
    if st.button("Send", key="send_chat"):
        if user_query:
            ai_response = ai_financial_chat(user_query)
            st.write(f"**Assistant:** {ai_response}")
        else:
            st.warning("Please enter a question.")

elif nav == "Banking":
    if "user" in st.session_state:
        username = st.session_state["user"]
        if not st.session_state.get("welcome_shown", False):
            st.title(f"{get_greeting()}, {username}! 🎉")
            st.write(get_motivational_quote())
            if st.button("Proceed to Banking"):
                st.session_state["welcome_shown"] = True
                st.rerun()
        else:
            st.subheader(f"🔹 Logged In as {username}")
            if st.button("Logout"):
                del st.session_state["user"]
                del st.session_state["welcome_shown"]
                st.rerun()

            action = st.selectbox("Select Action", ["Check Balance", "Deposit", "Withdraw", "Transaction History"])
            if action == "Check Balance":
                balance = get_balance(username)
                st.write(f"Your account balance is: **${balance:,.2f}**")
            elif action == "Deposit":
                amount = st.number_input("Enter deposit amount:", min_value=0.0, format="%.2f", key="deposit_amt")
                if st.button("Deposit"):
                    result = deposit(username, amount)
                    st.success(result)
            elif action == "Withdraw":
                amount = st.number_input("Enter withdrawal amount:", min_value=0.0, format="%.2f", key="withdraw_amt")
                if st.button("Withdraw"):
                    result = withdraw(username, amount)
                    if "Insufficient" in result:
                        st.error(result)
                    else:
                        st.success(result)
            elif action == "Transaction History":
                st.subheader("Transaction History")
                filter_mode = st.checkbox("Filter Transactions", value=False)
                if filter_mode:
                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input("Start Date", value=None, key="start_date")
                    with col2:
                        end_date = st.date_input("End Date", value=None, key="end_date")
                    transaction_type = st.selectbox("Transaction Type", ["All", "Deposit", "Withdrawal"], key="txn_type")
                    search_query = st.text_input("Search Query", key="search_query")
                    sort_order = st.selectbox("Sort Order", ["Descending", "Ascending"], key="sort_order")
                    if st.button("Apply Filters", key="apply_filters"):
                        transactions = get_filtered_transactions(username, start_date, end_date, transaction_type, search_query, sort_order)
                    else:
                        transactions = []  # Wait for user to click
                else:
                    transactions = get_transactions(username)
                
                if transactions:
                    df = pd.DataFrame(transactions, columns=["Action", "Amount", "Timestamp"])
                    st.dataframe(df)
                else:
                    st.write("No transactions found.")

# ----------------------
# Exchange Rates Section (Footer)
# ----------------------
st.markdown("---")
st.subheader("🌍 Exchange Rates")
exchange_rates = get_exchange_rates()
for pair, rate in exchange_rates.items():
    if isinstance(rate, float):
        st.write(f"{pair}: {rate:.4f}")
    else:
        st.write(f"{pair}: {rate}")
