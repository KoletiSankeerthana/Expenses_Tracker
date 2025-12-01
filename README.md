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

### **1️⃣ Clone the repository**
```bash
git clone https://github.com/your-username/expense-tracker.git
cd expense-tracker

2️⃣ Install dependencies

Create a virtual environment (optional but recommended):
pip install -r requirements.txt

3️⃣ Run the app
streamlit run app.py
4️⃣ The app opens automatically in your browser

📤 Deployment on Streamlit Cloud

Push your project to GitHub

Go to https://share.streamlit.io

Connect GitHub → select your repository

Deploy

Done 🎉

Make sure your repository includes:

app.py
requirements.txt


