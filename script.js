let expenses = [];

function addExpense() {
    let amount = document.getElementById("amount").value;
    let category = document.getElementById("category").value;
    let description = document.getElementById("description").value;

    if (!amount || !category) {
        alert("Please fill amount and category");
        return;
    }

    let expense = {
        amount: parseFloat(amount),
        category,
        description
    };

    expenses.push(expense);
    showExpenses();

    document.getElementById("amount").value = "";
    document.getElementById("category").value = "";
    document.getElementById("description").value = "";
}

function showExpenses() {
    let list = document.getElementById("expenseList");
    list.innerHTML = "";

    expenses.forEach((exp, index) => {
        list.innerHTML += `
            <li>
                ₹${exp.amount} - ${exp.category} <br>
                ${exp.description || ""}
            </li>
        `;
    });
}
