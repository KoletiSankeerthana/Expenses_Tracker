import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import hashlib, os, binascii
import plotly.express as px

# =========================================================
# SAFE RERUN
# =========================================================
def safe_rerun():
    try:
        st.rerun()
    except Exception:
        st.stop()

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Expense Tracker", layout="wide")
DB_PATH = "expenses.db"
FLAG_FILE = "db_initialized.flag"

# =========================================================
# DATABASE INITIAL SETUP
# =========================================================
if not os.path.exists(FLAG_FILE):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    with open(FLAG_FILE, "w") as f:
        f.write("initialized")

REQUIRED_TABLES = {
    "users": """
        CREATE TABLE users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            pwd_hash TEXT,
            salt TEXT
        );
    """,
    "categories": """
        CREATE TABLE categories(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            color TEXT,
            icon TEXT
        );
    """,
    "expenses": """
        CREATE TABLE expenses(
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
    for tname, ddl in REQUIRED_TABLES.items():
        try:
            cur.execute(f"SELECT 1 FROM {tname} LIMIT 1")
        except:
            cur.execute(ddl)
    conn.commit()
    conn.close()

init_db()

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

def verify_pw(salt_hex, hashed_hex, password):
    _, new_hash = hash_pw(password, salt_hex)
    return new_hash == hashed_hex

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
        uid = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()[0]
        conn.close()
        return True, uid
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
# CATEGORY FUNCTIONS
# =========================================================
def get_categories():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM categories ORDER BY name", conn)
    conn.close()
    return df

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
    return True

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
                st.success("Account created! Please login again.")
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
# DASHBOARD (WITH FILTERS)  -- unchanged except date formatting fix
# =========================================================
if page == "Dashboard":
    st.header("Dashboard Overview")

    df = fetch_expenses(uid)
    # ensure date column as pandas datetime then .date for display/filter logic
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    total = df["amount"].sum() if not df.empty else 0
    st.metric("Total Amount Spent", f"₹ {total:,.2f}")

    st.markdown("### Filters")

    col1, col2, col3 = st.columns(3)

    categories = ["All"] + sorted(df["category"].dropna().unique().tolist()) if not df.empty else ["All"]
    selected_cat = col1.selectbox("Category", categories)

    months = ["All"] + [str(m) for m in range(1, 13)]
    selected_month = col2.selectbox("Month", months)

    # build years list from df (if available)
    if not df.empty:
        yr_list = sorted(df["date"].dt.year.dropna().astype(int).astype(str).unique().tolist())
        years = ["All"] + yr_list
    else:
        years = ["All"]
    selected_year = col3.selectbox("Year", years)

    # FILTER LOGIC
    filtered = df.copy()
    if not filtered.empty:
        if selected_cat != "All":
            filtered = filtered[filtered["category"] == selected_cat]
        if selected_month != "All":
            filtered = filtered[filtered["date"].dt.month == int(selected_month)]
        if selected_year != "All":
            filtered = filtered[filtered["date"].dt.year == int(selected_year)]

    st.markdown("### Your Expenses (Table Format)")

    if filtered.empty:
        st.info("No expenses match the filter.")
    else:
        # create display table with date as YYYY-MM-DD (no time)
        disp = filtered[["amount", "category", "description", "date"]].copy()
        disp["date"] = disp["date"].dt.date  # remove time portion
        disp = disp.rename(columns={"amount": "Amount (₹)", "category": "Category", "description": "Description", "date": "Date"})
        st.dataframe(disp.reset_index(drop=True), use_container_width=True)

# =========================================================
# ADD EXPENSE (unchanged)
# =========================================================
elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")

elif page == "Add Expense":
    st.header("Add New Expense")

    cats = get_categories()
    cat_list = ["Select Category"] + (cats["name"].tolist() if not cats.empty else [])

    # Default amount is now 0
    amt = st.number_input("Amount (₹)", min_value=0.0, value=0.0, step=1.0)

    cat = st.selectbox("Category", cat_list)
    desc = st.text_input("Description")
    dt = st.date_input("Date", value=date.today())

    if st.button("Add Expense"):
        if amt <= 0:
            st.error("⚠ Please enter an amount greater than 0")
        elif cat == "Select Category":
            st.error("⚠ Please select a category")
        else:
            add_expense(uid, amt, cat, desc, dt.isoformat())
            st.success("Expense added!")


# =========================================================
# EXPENSES PAGE  <-- ADD TABLE (date fixed) + DELETE BUTTONS
# =========================================================
elif page == "Expenses":
    st.header("All Expenses")

    df_all = fetch_expenses(uid)
    if df_all.empty:
        st.info("No expenses yet.")
    else:
        # ensure date column parsed and formatted
        df_all["date"] = pd.to_datetime(df_all["date"], errors="coerce").dt.date

        # Display a clean table (no time portion)
        disp = df_all[["id", "amount", "category", "description", "date"]].copy()
        disp = disp.rename(columns={
            "id": "ID",
            "amount": "Amount (₹)",
            "category": "Category",
            "description": "Description",
            "date": "Date"
        })
        st.dataframe(disp.reset_index(drop=True), use_container_width=True)

        # For convenience show a selectbox to pick expense id, plus an inline delete button.
        ids = df_all["id"].astype(int).tolist()
        # present readable labels: "ID — ₹amount — category — date"
        labels = [f"{int(r['id'])} — ₹{r['amount']} — {r['category']} — {r['date']}" for _, r in df_all.iterrows()]
        sel_label = st.selectbox("Select expense to delete", options=[""] + labels)
        if sel_label:
            # extract id from label
            sel_id = int(sel_label.split("—")[0].strip())
            if st.button("Delete Selected Expense"):
                delete_expense(sel_id, uid)
                st.success("Deleted.")
                safe_rerun()

        # Also provide per-row delete buttons laid out compactly (if user prefers)
    
        for _, r in df_all.iterrows():
            cols = st.columns([2, 2, 3, 2, 1])
            cols[0].write(f"₹ {r['amount']}")
            cols[1].write(r["category"])
            cols[2].write(r["description"] or "-")
            cols[3].write(str(r["date"]))
            if cols[4].button("Delete", key=f"del_{int(r['id'])}"):
                delete_expense(int(r["id"]), uid)
                st.success("Deleted.")
                safe_rerun()

# =========================================================
# CATEGORIES PAGE (unchanged)
# =========================================================
elif page == "Categories":
    st.header("Categories")

    # FETCH CATEGORIES
    df = get_categories()

    # ================================
    # SHOW CATEGORY LIST (WITH ICONS)
    # ================================
    
    if df.empty:
        st.info("No categories yet.")
    else:
        for _, row in df.iterrows():
            icon = row["icon"] if row["icon"] else "•"
            st.markdown(f"### {icon} {row['name']}")

    st.markdown("---")

    # ================================
    # ADD CATEGORY SECTION
    # ================================
    st.subheader("Add Category")

    new_cat = st.text_input("Category Name")
    new_icon = st.text_input("Icon (emoji)")

    if st.button("Add Category"):
        if not new_cat.strip():
            st.error("Category name cannot be empty.")
        else:
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO categories(name, icon) VALUES (?, ?)",
                    (new_cat.strip(), new_icon.strip())
                )
                conn.commit()
                conn.close()
                st.success("Category added!")
                safe_rerun()
            except sqlite3.IntegrityError:
                st.error("Category already exists.")

    st.markdown("---")

    # ================================
    # DELETE CATEGORY SECTION
    # ================================
    st.subheader("Delete Category")

    if df.empty:
        st.info("No categories available to delete.")
    else:
        delete_opt = st.selectbox("Select category to delete", df["name"].tolist())

        if st.button("Delete Selected Category"):
            conn = get_conn()
            conn.execute("DELETE FROM categories WHERE name=?", (delete_opt,))
            conn.commit()
            conn.close()
            st.success("Category deleted!")
            safe_rerun()

elif page == "Categories":
    st.header("Categories")

    # FETCH CATEGORIES
    df = get_categories()

    # ================================
    # SHOW CATEGORY LIST (WITH ICONS)
    # ================================
    st.subheader("Current Categories")
    if df.empty:
        st.info("No categories yet.")
    else:
        for _, row in df.iterrows():
            icon = row["icon"] if row["icon"] else "•"
            st.markdown(f"### {icon} {row['name']}")

    st.markdown("---")

    # ================================
    # ADD CATEGORY SECTION
    # ================================
    st.subheader("Add Category")

    new_cat = st.text_input("Category Name")
    new_icon = st.text_input("Icon (emoji)")

    if st.button("Add Category"):
        if not new_cat.strip():
            st.error("Category name cannot be empty.")
        else:
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO categories(name, icon) VALUES (?, ?)",
                    (new_cat.strip(), new_icon.strip())
                )
                conn.commit()
                conn.close()
                st.success("Category added!")
                safe_rerun()
            except sqlite3.IntegrityError:
                st.error("Category already exists.")

    st.markdown("---")

    # ================================
    # DELETE CATEGORY SECTION
    # ================================
    st.subheader("Delete Category")

    if df.empty:
        st.info("No categories available to delete.")
    else:
        delete_opt = st.selectbox("Select category to delete", df["name"].tolist())

        if st.button("Delete Selected Category"):
            conn = get_conn()
            conn.execute("DELETE FROM categories WHERE name=?", (delete_opt,))
            conn.commit()
            conn.close()
            st.success("Category deleted!")
            safe_rerun()

elif page == "Categories":
    st.header("Categories")

    # FETCH CATEGORIES
    df = get_categories()

    # ================================
    # SHOW CATEGORY LIST (WITH ICONS)
    # ================================
    st.subheader("Current Categories")
    if df.empty:
        st.info("No categories yet.")
    else:
        for _, row in df.iterrows():
            icon = row["icon"] if row["icon"] else "•"
            st.markdown(f"### {icon} {row['name']}")

    st.markdown("---")

    # ================================
    # ADD CATEGORY SECTION
    # ================================
    st.subheader("Add Category")

    new_cat = st.text_input("Category Name")
    new_icon = st.text_input("Icon (emoji)")

    if st.button("Add Category"):
        if not new_cat.strip():
            st.error("Category name cannot be empty.")
        else:
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO categories(name, icon) VALUES (?, ?)",
                    (new_cat.strip(), new_icon.strip())
                )
                conn.commit()
                conn.close()
                st.success("Category added!")
                safe_rerun()
            except sqlite3.IntegrityError:
                st.error("Category already exists.")

    st.markdown("---")

    # ================================
    # DELETE CATEGORY SECTION
    # ================================
    st.subheader("Delete Category")

    if df.empty:
        st.info("No categories available to delete.")
    else:
        delete_opt = st.selectbox("Select category to delete", df["name"].tolist())

        if st.button("Delete Selected Category"):
            conn = get_conn()
            conn.execute("DELETE FROM categories WHERE name=?", (delete_opt,))
            conn.commit()
            conn.close()
            st.success("Category deleted!")
            safe_rerun()

elif page == "Categories":
    st.header("Categories")

    # FETCH CATEGORIES
    df = get_categories()

    # ================================
    # SHOW CATEGORY LIST (WITH ICONS)
    # ================================
    st.subheader("Current Categories")
    if df.empty:
        st.info("No categories yet.")
    else:
        for _, row in df.iterrows():
            icon = row["icon"] if row["icon"] else "•"
            st.markdown(f"### {icon} {row['name']}")

    st.markdown("---")

    # ================================
    # ADD CATEGORY SECTION
    # ================================
    st.subheader("Add Category")

    new_cat = st.text_input("Category Name")
    new_icon = st.text_input("Icon (emoji)")

    if st.button("Add Category"):
        if not new_cat.strip():
            st.error("Category name cannot be empty.")
        else:
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO categories(name, icon) VALUES (?, ?)",
                    (new_cat.strip(), new_icon.strip())
                )
                conn.commit()
                conn.close()
                st.success("Category added!")
                safe_rerun()
            except sqlite3.IntegrityError:
                st.error("Category already exists.")

    st.markdown("---")

    # ================================
    # DELETE CATEGORY SECTION
    # ================================
    st.subheader("Delete Category")

    if df.empty:
        st.info("No categories available to delete.")
    else:
        delete_opt = st.selectbox("Select category to delete", df["name"].tolist())

        if st.button("Delete Selected Category"):
            conn = get_conn()
            conn.execute("DELETE FROM categories WHERE name=?", (delete_opt,))
            conn.commit()
            conn.close()
            st.success("Category deleted!")
            safe_rerun()

elif page == "Categories":
    st.header("Categories")

    # FETCH CATEGORIES
    df = get_categories()

    # ================================
    # SHOW CATEGORY LIST (WITH ICONS)
    # ================================
    st.subheader("Current Categories")
    if df.empty:
        st.info("No categories yet.")
    else:
        for _, row in df.iterrows():
            icon = row["icon"] if row["icon"] else "•"
            st.markdown(f"### {icon} {row['name']}")

    st.markdown("---")

    # ================================
    # ADD CATEGORY SECTION
    # ================================
    st.subheader("Add Category")

    new_cat = st.text_input("Category Name")
    new_icon = st.text_input("Icon (emoji)")

    if st.button("Add Category"):
        if not new_cat.strip():
            st.error("Category name cannot be empty.")
        else:
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO categories(name, icon) VALUES (?, ?)",
                    (new_cat.strip(), new_icon.strip())
                )
                conn.commit()
                conn.close()
                st.success("Category added!")
                safe_rerun()
            except sqlite3.IntegrityError:
                st.error("Category already exists.")

    st.markdown("---")

    # ================================
    # DELETE CATEGORY SECTION
    # ================================
    st.subheader("Delete Category")

    if df.empty:
        st.info("No categories available to delete.")
    else:
        delete_opt = st.selectbox("Select category to delete", df["name"].tolist())

        if st.button("Delete Selected Category"):
            conn = get_conn()
            conn.execute("DELETE FROM categories WHERE name=?", (delete_opt,))
            conn.commit()
            conn.close()
            st.success("Category deleted!")
            safe_rerun()

elif page == "Categories":
    st.header("Categories")

    # FETCH CATEGORIES
    df = get_categories()

    # ================================
    # SHOW CATEGORY LIST (WITH ICONS)
    # ================================
    st.subheader("Current Categories")
    if df.empty:
        st.info("No categories yet.")
    else:
        for _, row in df.iterrows():
            icon = row["icon"] if row["icon"] else "•"
            st.markdown(f"### {icon} {row['name']}")

    st.markdown("---")

    # ================================
    # ADD CATEGORY SECTION
    # ================================
    st.subheader("Add Category")

    new_cat = st.text_input("Category Name")
    new_icon = st.text_input("Icon (emoji)")

    if st.button("Add Category"):
        if not new_cat.strip():
            st.error("Category name cannot be empty.")
        else:
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO categories(name, icon) VALUES (?, ?)",
                    (new_cat.strip(), new_icon.strip())
                )
                conn.commit()
                conn.close()
                st.success("Category added!")
                safe_rerun()
            except sqlite3.IntegrityError:
                st.error("Category already exists.")

    st.markdown("---")

    # ================================
    # DELETE CATEGORY SECTION
    # ================================
    st.subheader("Delete Category")

    if df.empty:
        st.info("No categories available to delete.")
    else:
        delete_opt = st.selectbox("Select category to delete", df["name"].tolist())

        if st.button("Delete Selected Category"):
            conn = get_conn()
            conn.execute("DELETE FROM categories WHERE name=?", (delete_opt,))
            conn.commit()
            conn.close()
            st.success("Category deleted!")
            safe_rerun()

elif page == "Categories":
    st.header("Categories")

    # FETCH CATEGORIES
    df = get_categories()

    # ================================
    # SHOW CATEGORY LIST (WITH ICONS)
    # ================================
    st.subheader("Current Categories")
    if df.empty:
        st.info("No categories yet.")
    else:
        for _, row in df.iterrows():
            icon = row["icon"] if row["icon"] else "•"
            st.markdown(f"### {icon} {row['name']}")

    st.markdown("---")

    # ================================
    # ADD CATEGORY SECTION
    # ================================
    st.subheader("Add Category")

    new_cat = st.text_input("Category Name")
    new_icon = st.text_input("Icon (emoji)")

    if st.button("Add Category"):
        if not new_cat.strip():
            st.error("Category name cannot be empty.")
        else:
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO categories(name, icon) VALUES (?, ?)",
                    (new_cat.strip(), new_icon.strip())
                )
                conn.commit()
                conn.close()
                st.success("Category added!")
                safe_rerun()
            except sqlite3.IntegrityError:
                st.error("Category already exists.")

    st.markdown("---")

    # ================================
    # DELETE CATEGORY SECTION
    # ================================
    st.subheader("Delete Category")

    if df.empty:
        st.info("No categories available to delete.")
    else:
        delete_opt = st.selectbox("Select category to delete", df["name"].tolist())

        if st.button("Delete Selected Category"):
            conn = get_conn()
            conn.execute("DELETE FROM categories WHERE name=?", (delete_opt,))
            conn.commit()
            conn.close()
            st.success("Category deleted!")
            safe_rerun()


# =========================================================
# SUMMARY PAGE (unchanged)
# =========================================================
elif page == "Summary":
    st.header("Summary & Charts")

    df = fetch_expenses(uid)
    if df.empty:
        st.info("No data.")
    else:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        by_cat = df.groupby("category", as_index=False)["amount"].sum()
        st.plotly_chart(px.pie(by_cat, values="amount", names="category"))

        daily = df.groupby(df["date"].dt.date)["amount"].sum().reset_index()
        st.plotly_chart(px.bar(daily, x="date", y="amount"))

# =========================================================
# ACCOUNT PAGE (unchanged)
# =========================================================
elif page == "Account":


    st.subheader("⚠ Reset Entire Database")

    st.warning(
        "This will *delete all users, categories, expenses, and reset everything*.\n"
        "You will need to register again."
    )

    if st.button("Reset Database"):
        try:
            # Delete database file
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)

            # Delete initialization flag
            if os.path.exists(FLAG_FILE):
                os.remove(FLAG_FILE)

            st.success("✅ Database has been reset successfully! Restarting app...")

            # Reset session + rerun
            st.session_state.user_id = None
            safe_rerun()

        except Exception as e:
            st.error(f"Error resetting database: {e}")

elif page == "Account":
    st.header("Account Settings")

    st.write("Logged in as:", st.session_state.user_id)

    st.markdown("---")
    st.subheader("⚠ Reset Entire Database")

    st.warning(
        "This will *delete all users, categories, expenses, and reset everything*.\n"
        "You will need to register again."
    )

    if st.button("Reset Database"):
        try:
            # Delete database file
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)

            # Delete initialization flag
            if os.path.exists(FLAG_FILE):
                os.remove(FLAG_FILE)

            st.success("✅ Database has been reset successfully! Restarting app...")

            # Reset session + rerun
            st.session_state.user_id = None
            safe_rerun()

        except Exception as e:
            st.error(f"Error resetting database: {e}")

elif page == "Account":
    st.header("Account Settings")

    st.write("Logged in as:", st.session_state.user_id)

    st.markdown("---")
    st.subheader("⚠ Reset Entire Database")

    st.warning(
        "This will *delete all users, categories, expenses, and reset everything*.\n"
        "You will need to register again."
    )

    if st.button("Reset Database"):
        try:
            # Delete database file
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)

            # Delete initialization flag
            if os.path.exists(FLAG_FILE):
                os.remove(FLAG_FILE)

            st.success("✅ Database has been reset successfully! Restarting app...")

            # Reset session + rerun
            st.session_state.user_id = None
            safe_rerun()

        except Exception as e:
            st.error(f"Error resetting database: {e}")