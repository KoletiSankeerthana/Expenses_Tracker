import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import hashlib, os, binascii
import plotly.express as px

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Expense Tracker", layout="wide")
DB_PATH = "expenses.db"

# =========================================================
# DATABASE SETUP (NO DELETE, NO FLAG FILE)
# =========================================================
REQUIRED_TABLES = {
    "users": """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            pwd_hash TEXT,
            salt TEXT
        );
    """,
    "categories": """
        CREATE TABLE IF NOT EXISTS categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            color TEXT,
            icon TEXT
        );
    """,
    "expenses": """
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            description TEXT,
            date TEXT
        );
    """
}

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    for ddl in REQUIRED_TABLES.values():
        cur.execute(ddl)
    conn.commit()
    conn.close()

init_db()

# =========================================================
# SAFE RERUN
# =========================================================
def safe_rerun():
    try:
        st.rerun()
    except:
        st.stop()

# =========================================================
# PASSWORD HASHING
# =========================================================
def hash_pw(password, salt=None):
    if salt is None:
        salt_bytes = os.urandom(16)
    else:
        salt_bytes = binascii.unhexlify(salt)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, 100000)
    return binascii.hexlify(salt_bytes).decode(), binascii.hexlify(hashed).decode()

def verify_pw(salt_hex, stored_hash, password):
    _, new_hash = hash_pw(password, salt_hex)
    return new_hash == stored_hash

# =========================================================
# USER FUNCTIONS
# =========================================================
def create_user(username, password):
    try:
        salt_hex, hashed_hex = hash_pw(password)
        conn = get_conn()
        conn.execute("INSERT INTO users(username,pwd_hash,salt) VALUES (?,?,?)",
                     (username, hashed_hex, salt_hex))
        conn.commit()
        conn.close()
        return True, "User created!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."

def authenticate(username, password):
    conn = get_conn()
    row = conn.execute("SELECT id,pwd_hash,salt FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not row:
        return None
    uid, stored_hash, stored_salt = row
    return uid if verify_pw(stored_salt, stored_hash, password) else None

# =========================================================
# EXPENSE FUNCTIONS
# =========================================================
def add_expense(uid, amount, category, description, dt):
    conn = get_conn()
    conn.execute(
        "INSERT INTO expenses(user_id,amount,category,description,date) VALUES (?,?,?,?,?)",
        (uid, amount, category, description, dt)
    )
    conn.commit()
    conn.close()

def fetch_expenses(uid):
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM expenses WHERE user_id=? ORDER BY date DESC",
                     conn, params=[uid])
    conn.close()
    return df

def delete_expense(eid, uid):
    conn = get_conn()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (eid, uid))
    conn.commit()
    conn.close()

# =========================================================
# CATEGORY FUNCTIONS
# =========================================================
def get_categories():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM categories ORDER BY name", conn)
    conn.close()
    return df

# =========================================================
# SESSION DEFAULTS
# =========================================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# =========================================================
# SIDEBAR LOGIN
# =========================================================
with st.sidebar:
    st.title("Account")

    if st.session_state.user_id is None:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        col1, col2 = st.columns(2)

        if col1.button("Login"):
            uid = authenticate(u.strip(), p.strip())
            if uid:
                st.session_state.user_id = uid
                safe_rerun()
            else:
                st.error("Invalid username or password")

        if col2.button("Register"):
            ok, msg = create_user(u.strip(), p.strip())
            if ok:
                st.success("Account created! Login again.")
            else:
                st.error(msg)

        st.stop()

    if st.button("Logout"):
        st.session_state.user_id = None
        safe_rerun()

uid = st.session_state.user_id

# =========================================================
# NAVIGATION
# =========================================================
menu_items = ["Dashboard", "Add Expense", "Categories", "Expenses", "Summary", "Account"]
page = st.radio("Navigate", menu_items, horizontal=True,
                index=menu_items.index(st.session_state.page))
st.session_state.page = page

# =========================================================
# DASHBOARD
# =========================================================
if page == "Dashboard":
    st.header("Dashboard Overview")

    df = fetch_expenses(uid)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])

    total = df["amount"].sum() if not df.empty else 0
    st.metric("Total Amount Spent", f"₹ {total:,.2f}")

    st.markdown("### Filters")

    col1, col2, col3 = st.columns(3)

    categories = ["All"] + sorted(df["category"].dropna().unique().tolist()) if not df.empty else ["All"]
    selected_cat = col1.selectbox("Category", categories)

    months = ["All"] + [str(m) for m in range(1, 13)]
    selected_month = col2.selectbox("Month", months)

    years = ["All"] + sorted(df["date"].dt.year.dropna().astype(str).unique().tolist()) if not df.empty else ["All"]
    selected_year = col3.selectbox("Year", years)

    filtered = df.copy()

    if selected_cat != "All":
        filtered = filtered[filtered["category"] == selected_cat]

    if selected_month != "All":
        filtered = filtered[filtered["date"].dt.month == int(selected_month)]

    if selected_year != "All":
        filtered = filtered[filtered["date"].dt.year == int(selected_year)]

    st.markdown("### History")

    if filtered.empty:
        st.info("No matching records.")
    else:
        disp = filtered.copy()
        disp["date"] = disp["date"].dt.date
        st.dataframe(disp.reset_index(drop=True), use_container_width=True)

# =========================================================
# ADD EXPENSE
# =========================================================
elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + cats["name"].tolist() if not cats.empty else ["Select Category"]

    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0)
    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("Amount must be > 0")
        elif cat == "Select Category":
            st.error("Choose a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added successfully!")

# =========================================================
# EXPENSES PAGE
# =========================================================
elif page == "Expenses":
    st.header("All Expenses")

    df_all = fetch_expenses(uid)

    if df_all.empty:
        st.info("No expenses yet.")
    else:
        df_all["date"] = pd.to_datetime(df_all["date"]).dt.date

        disp = df_all.rename(columns={
            "amount": "Amount (₹)",
            "category": "Category",
            "description": "Description",
            "date": "Date"
        })

        st.dataframe(disp[["id", "Amount (₹)", "Category", "Description", "Date"]],
                     use_container_width=True)

        delete_opt = st.selectbox(
            "Select expense to delete",
            [""] + [f"{r['id']} — ₹{r['amount']} — {r['category']} — {r['date']}" for _, r in df_all.iterrows()]
        )

        if delete_opt and st.button("Delete Selected"):
            eid = int(delete_opt.split("—")[0].strip())
            delete_expense(eid, uid)
            st.success("Deleted successfully!")
            safe_rerun()

# =========================================================
# CATEGORIES PAGE
# =========================================================
elif page == "Categories":
    st.header("Categories")

    df = get_categories()

    st.subheader("Current Categories")
    if df.empty:
        st.info("No categories yet.")
    else:
        for _, row in df.iterrows():
            st.markdown(f"### {row['icon'] or '•'} {row['name']}")

    st.markdown("---")

    st.subheader("Add Category")
    new_cat = st.text_input("Category Name")
    new_icon = st.text_input("Icon (emoji)")

    if st.button("Add Category"):
        if not new_cat.strip():
            st.error("Name cannot be empty")
        else:
            try:
                conn = get_conn()
                conn.execute("INSERT INTO categories(name, icon) VALUES (?, ?)",
                             (new_cat.strip(), new_icon.strip()))
                conn.commit()
                conn.close()
                st.success("Category added!")
                safe_rerun()
            except sqlite3.IntegrityError:
                st.error("Category already exists")

    st.markdown("---")

    st.subheader("Delete Category")
    if df.empty:
        st.info("No categories")
    else:
        del_select = st.selectbox("Select category", df["name"].tolist())
        if st.button("Delete Category"):
            conn = get_conn()
            conn.execute("DELETE FROM categories WHERE name=?", (del_select,))
            conn.commit()
            conn.close()
            st.success("Deleted!")
            safe_rerun()

# =========================================================
# SUMMARY PAGE
# =========================================================
elif page == "Summary":
    st.header("Summary & Charts")

    df = fetch_expenses(uid)
    if df.empty:
        st.info("No data.")
    else:
        df["date"] = pd.to_datetime(df["date"])

        by_cat = df.groupby("category", as_index=False)["amount"].sum()
        st.plotly_chart(px.pie(by_cat, values="amount", names="category"))

        daily = df.groupby(df["date"].dt.date)["amount"].sum().reset_index()
        st.plotly_chart(px.bar(daily, x="date", y="amount"))

# =========================================================
# ACCOUNT PAGE
# =========================================================
elif page == "Account":
    st.header("Account Settings")


    st.warning("Database reset feature disabled to avoid cloud login issues.")
