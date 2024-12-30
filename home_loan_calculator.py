import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Function to format amounts as INR (no decimals, comma-separated)
def format_inr(amount):
    return f"₹ {amount:,.0f}"

def calculate_emi_and_schedule(
    home_value,
    down_payment_percentage,
    interest_rate,
    loan_tenure_years,
    loan_insurance,
    property_taxes,
    home_insurance,
    maintenance_expenses,
    prepayments_monthly=0,
    prepayments_quarterly=0,
    prepayments_one_time=0
):
    """
    Calculates an approximate loan schedule, tracking data yearly,
    and creates charts for a Streamlit app.
    """

    # 1. Calculate initial loan amount (minus down payment & insurance).
    loan_amount = home_value - (home_value * down_payment_percentage / 100) - loan_insurance

    # 2. Subtract one-time prepayment from the initial loan amount (if any).
    loan_amount -= prepayments_one_time
    if loan_amount < 0:
        loan_amount = 0

    # 3. Monthly interest rate
    monthly_interest_rate = (interest_rate / 100) / 12

    # 4. Total months (scheduled)
    loan_tenure_months = loan_tenure_years * 12

    # 5. Compute EMI (standard amortized formula)
    if monthly_interest_rate == 0:
        # Edge case: 0% interest
        emi = loan_amount / loan_tenure_months
    else:
        emi = (
            loan_amount
            * monthly_interest_rate
            * (1 + monthly_interest_rate) ** loan_tenure_months
        ) / (
            (1 + monthly_interest_rate) ** loan_tenure_months - 1
        )

    # 6. Prepare lists to track yearly data
    years_list = []
    remaining_balance_list = []
    principal_paid_list = []
    interest_paid_list = []
    prepayments_list = []
    total_payment_list = []

    balance = loan_amount
    total_interest_for_year = 0
    total_principal_for_year = 0

    current_month = 1

    while balance > 0 and current_month <= loan_tenure_months:
        # Calculate interest for this month
        interest_payment = balance * monthly_interest_rate
        # Principal portion from EMI
        principal_payment = emi - interest_payment

        # Update balance
        balance -= principal_payment

        # Monthly prepayment
        if prepayments_monthly > 0:
            balance -= prepayments_monthly

        # Quarterly prepayment (every 3rd month)
        if (current_month % 3 == 0) and (prepayments_quarterly > 0):
            balance -= prepayments_quarterly

        # Accumulate interest & principal for the year
        total_interest_for_year += interest_payment
        total_principal_for_year += principal_payment

        # If loan is fully paid off, clamp to zero
        if balance < 0:
            balance = 0

        # Record data at the end of each 12-month cycle OR if loan finishes
        if (current_month % 12 == 0) or (balance <= 0):
            this_year = (current_month + 11) // 12  # approximate year number
            years_list.append(this_year)
            remaining_balance_list.append(balance)
            interest_paid_list.append(total_interest_for_year)
            principal_paid_list.append(total_principal_for_year)

            # Approx total prepayments in a year
            year_prepayments = prepayments_monthly * 12 + prepayments_quarterly * 4
            prepayments_list.append(year_prepayments)

            # Approx total payment in that year
            total_payment_list.append(emi * 12 + year_prepayments)

            # Reset yearly accumulators
            total_interest_for_year = 0
            total_principal_for_year = 0

        current_month += 1
        if balance <= 0:
            break

    # Pad any remaining years (if loan finished early)
    total_years_recorded = len(years_list)
    if total_years_recorded < loan_tenure_years:
        for y in range(total_years_recorded + 1, loan_tenure_years + 1):
            years_list.append(y)
            remaining_balance_list.append(0)
            interest_paid_list.append(0)
            principal_paid_list.append(0)
            prepayments_list.append(0)
            total_payment_list.append(0)

    # Build final DataFrame
    schedule_df = pd.DataFrame({
        'Year': [str(y) for y in years_list],
        'Principal (₹)': [format_inr(p) for p in principal_paid_list],
        'Prepayments (₹)': [format_inr(p) for p in prepayments_list],
        'Interest (₹)': [format_inr(i) for i in interest_paid_list],
        'Taxes, Insurance, Expenses (₹)': [
            format_inr(property_taxes + home_insurance + (maintenance_expenses * 12))
            for _ in years_list
        ],
        'Total Payment (₹)': [format_inr(t) for t in total_payment_list],
        'Balance (₹)': [format_inr(b) for b in remaining_balance_list],
    })

    # Summaries for the pie chart
    total_principal_paid = sum(principal_paid_list)
    total_prepayments = sum(prepayments_list) + prepayments_one_time
    total_interest_paid = sum(interest_paid_list)

    labels = ['Principal', 'Prepayments', 'Interest']
    sizes = [total_principal_paid, total_prepayments, total_interest_paid]
    colors = ['#B0C4DE', '#FFB6C1', '#4169E1']

    fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
    ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    ax_pie.axis('equal')
    ax_pie.set_title("Total Payments Breakdown")

    # Approx total monthly payment
    total_monthly_payment = emi + prepayments_monthly

    return emi, schedule_df, fig_pie, total_monthly_payment, total_interest_paid


# -------------- STREAMLIT APP --------------
st.title("Home Loan EMI Calculator with Prepayments (Revised)")

# **Updated default values**:
**home_value = st.number_input("Home Value (₹)", min_value=1_000_000, step=100000, value=1_000_000)
down_payment_percentage = st.number_input("Down Payment Percentage (%)", min_value=0, max_value=100, step=1, value=20)
interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.1, value=8.0)
loan_tenure_years = st.number_input("Loan Tenure (Years)", min_value=1, max_value=40, step=1, value=15)
loan_insurance = st.number_input("Loan Insurance (₹)", min_value=0, step=1000, value=0)
property_taxes = st.number_input("Property Taxes per Year (₹)", min_value=0, step=500, value=0)
home_insurance = st.number_input("Home Insurance per Year (₹)", min_value=0, step=500, value=0)
maintenance_expenses = st.number_input("Maintenance Expenses per Month (₹)", min_value=0, step=100, value=0)**

prepayments_monthly = st.number_input("Monthly Prepayment (₹)", min_value=0, step=1000, value=0, 
                                      help="Monthly extra payment towards principal")
prepayments_quarterly = st.number_input("Quarterly Prepayment (₹)", min_value=0, step=1000, value=0, 
                                        help="Every 3rd month, extra payment towards principal")
prepayments_one_time = st.number_input("One-time Prepayment (₹)", min_value=0, step=1000, value=0, 
                                       help="One-time amount deducted immediately from loan")

if st.button("Calculate EMI"):
    emi, schedule_df, fig_pie, total_monthly_payment, total_interest_paid = calculate_emi_and_schedule(
        home_value,
        down_payment_percentage,
        interest_rate,
        loan_tenure_years,
        loan_insurance,
        property_taxes,
        home_insurance,
        maintenance_expenses,
        prepayments_monthly,
        prepayments_quarterly,
        prepayments_one_time
    )

    st.write(f"**Base EMI: {format_inr(emi)}**")
    st.write(f"**Approx. Total Monthly Payment (EMI + Monthly Prepayment): {format_inr(total_monthly_payment)}**")
    st.write(f"**Total Interest Paid (Approx): {format_inr(total_interest_paid)}**")

    st.pyplot(fig_pie)

    st.write("### Yearly Payment Schedule")
    st.dataframe(
        schedule_df.style.set_table_styles([
            {
                'selector': 'th',
                'props': [
                    ('background-color', 'skyblue'),
                    ('color', 'black'),
                    ('font-weight', 'bold')
                ]
            },
            {'selector': 'td', 'props': [('color', 'black')]},
        ])
    )
