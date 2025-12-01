# 💰 Expense Tracker (Streamlit App)

A simple, clean, and user-friendly **Expense Tracker Web App** built using **Streamlit**, **SQLite**, and **Python**.  
It allows users to track daily expenses, manage categories, view summaries, and analyze spending patterns with charts.

🌐 **Live App:** *https://noteyourexpensesinexpensestracker.streamlit.app/*  
📂 **Tech Stack:** Python, Streamlit, SQLite, Pandas, Plotly

---

## 🚀 Features

### 🔐 **User Authentication**
- Register new users
- Secure login with hashed passwords (PBKDF2 + SHA256)
- Logout functionality

### 💸 **Expense Management**
- Add expenses with:
  - Amount  
  - Category  
  - Description  
  - Date  
- View all expenses in a sortable table
- Delete selected expenses

### 🗂️ **Category Management**
- Add custom categories with emoji icons  
- View list of categories  
- Delete categories  
- Input fields reset automatically after adding a category

### 📊 **Dashboard & Analysis**
- Total expenses summary
- Filter expenses by:
  - Category  
  - Month  
  - Year  
- View filtered expenses in a table
- Pie chart of category-wise spending
- Bar chart of daily spending trends

### 🔄 **Smooth UX**
- Form fields in **Add Expense** and **Categories** pages automatically reset after submission
- No duplicated pages or unnecessary reruns
- Works perfectly on **Streamlit Cloud**

---

## 🛠️ Tech Stack

| Component | Technology |
|----------|------------|
| Frontend | Streamlit |
| Backend | Python |
| Database | SQLite |
| Data Handling | Pandas |
| Visualization | Plotly Express |

---

## 📁 Project Structure
📦 expense-tracker
┣ 📜 app.py # Main Streamlit application
┣ 📜 expenses.db # SQLite database (auto-created)
┣ 📜 requirements.txt # Python dependencies
┗ 📜 README.md # Project documentation


---

## 📦 Installation & Setup

Follow these steps to run the project locally:

Here is the **clean and correct final format** for your **README / deployment instructions**, exactly as Streamlit Cloud expects.

I fixed:

✔ Correct Markdown formatting
✔ Proper code blocks
✔ Correct steps
✔ No broken formatting
✔ Easy to copy–paste into GitHub

---

# ✅ **FINAL README (Clean & Correct Format)**

````markdown
# Expense Tracker – Streamlit App

A simple and clean personal expense tracker built using Streamlit + SQLite.

---

## 🚀 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/expense-tracker.git
cd expense-tracker
````

---

## 📦 2️⃣ Install Dependencies

Create a virtual environment (optional but recommended):

```bash
python -m venv venv
```

Activate it:

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

Install required packages:

```bash
pip install -r requirements.txt
```

---

## ▶️ 3️⃣ Run the App Locally

```bash
streamlit run app.py
```

The app will automatically open in your browser:
👉 [http://localhost:8501/](http://localhost:8501/)

---

## 🌐 4️⃣ Deploy on Streamlit Cloud

1. Push your project to GitHub
2. Go to **[https://share.streamlit.io](https://share.streamlit.io)**
3. Click **New App**
4. Connect your GitHub repository
5. Select the branch and app file → `app.py`
6. Click **Deploy**

Done 🎉 Your app is now live.

---

## 📁 Required Files

Your repository **must include**:

```
app.py
requirements.txt
```

Optional recommended files:

```
README.md
images/
```

---

## 📄 Example `requirements.txt`

```txt
streamlit
pandas
plotly
```

---


