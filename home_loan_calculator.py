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

    Returns:
    --------
    emi : float
        The standard monthly EMI (no extra prepayments).
    schedule_df : pd.DataFrame
        A yearly summary of principal, interest, prepayments, etc.
    fig_pie : matplotlib.figure.Figure
        A pie chart figure showing total payment breakdown.
    fig_bar : matplotlib.figure.Figure
        A stacked bar chart (Principal, Interest, Prepayments) plus a dotted line of remaining balance (yearly).
    total_monthly_payment : float
        EMI + monthly prepayment.
    total_interest_paid : float
        Approx. total interest paid over the life of the loan.
    summary_dict : dict
        Contains values for the final summary (down payment, fees, etc.).
    """

    # -------- 1) INITIAL CALCULATIONS --------
    # Down Payment
    down_payment_value = home_value * down_payment_percentage / 100
    # Sum of Down Payment + Fees + One-time Expenses
    down_payment_fees_one_time = down_payment_value + loan_insurance + prepayments_one_time

    # Effective Loan Amount
    loan_amount = home_value - down_payment_value - loan_insurance

    # Subtract one-time prepayment
    loan_amount -= prepayments_one_time
    if loan_amount < 0:
        loan_amount = 0

    # Monthly interest rate
    monthly_interest_rate = (interest_rate / 100) / 12

    # Total scheduled months
    loan_tenure_months = loan_tenure_years * 12

    # -------- 2) EMI --------
    if loan_tenure_months == 0:
        emi = 0
    elif monthly_interest_rate == 0:
        emi = loan_amount / loan_tenure_months
    else:
        emi = (
            loan_amount
            * monthly_interest_rate
            * (1 + monthly_interest_rate) ** loan_tenure_months
        ) / (
            (1 + monthly_interest_rate) ** loan_tenure_months - 1
        )

    # -------- 3) AMORTIZATION (YEARLY) --------
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

    # We'll store a yearly "snapshot" of the balance for plotting the dotted line
    # (Because monthly might be too granular; let's keep it year-based for a smoother chart)
    balance_yearly_snapshots = [balance]  # initial snapshot before any payment

    while balance > 0 and current_month <= loan_tenure_months:
        # Interest portion
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

        total_interest_for_year += interest_payment
        total_principal_for_year += principal_payment

        if balance < 0:
            balance = 0

        # End of year or if the loan finishes
        if (current_month % 12 == 0) or (balance <= 0):
            this_year = (current_month + 11) // 12
            years_list.append(this_year)
            remaining_balance_list.append(balance)
            interest_paid_list.append(total_interest_for_year)
            principal_paid_list.append(total_principal_for_year)

            # Approx total prepayments for the year
            year_prepayments = prepayments_monthly * 12 + prepayments_quarterly * 4
            prepayments_list.append(year_prepayments)

            total_payment_list.append(emi * 12 + year_prepayments)

            # Save a snapshot for the dotted line
            balance_yearly_snapshots.append(balance)

            # Reset accumulators
            total_interest_for_year = 0
            total_principal_for_year = 0

        current_month += 1
        if balance <= 0:
            break

    # Fill remaining years if loan ends early
    total_years_recorded = len(years_list)
    if total_years_recorded < loan_tenure_years:
        for y in range(total_years_recorded + 1, loan_tenure_years + 1):
            years_list.append(y)
            remaining_balance_list.append(0)
            interest_paid_list.append(0)
            principal_paid_list.append(0)
            prepayments_list.append(0)
            total_payment_list.append(0)
            balance_yearly_snapshots.append(0)

    # -------- 4) YEARLY SCHEDULE DATAFRAME --------
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

    # -------- 5) SUMMARIES FOR CHARTS & FINAL SUMMARY --------
    total_principal_paid = sum(principal_paid_list)
    total_prepayments = sum(prepayments_list) + prepayments_one_time
    total_interest_paid = sum(interest_paid_list)

    # Pie chart data
    labels = ['Principal', 'Prepayments', 'Interest']
    sizes = [total_principal_paid, total_prepayments, total_interest_paid]
    colors = ['#B0C4DE', '#FFB6C1', '#4169E1']

    # Taxes, home insurance & maintenance for entire loan period
    total_taxes_ins_maint = (
        property_taxes * loan_tenure_years
        + home_insurance * loan_tenure_years
        + maintenance_expenses * 12 * loan_tenure_years
    )

    summary_dict = {
        'down_payment_fees_onetime': down_payment_fees_one_time,
        'principal': total_principal_paid,
        'prepayments': total_prepayments,
        'interest': total_interest_paid,
        'taxes_ins_maint': total_taxes_ins_maint
    }

    # -------- 6) CREATE PIE CHART --------
    fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
    ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    ax_pie.axis('equal')
    ax_pie.set_title("Total Payments Breakdown")

    # -------- 7) CREATE STACKED BAR CHART + DOTTED LINE (YEARLY) --------
    numeric_years = [int(y) for y in years_list]

    fig_bar, ax_bar = plt.subplots(figsize=(8, 5))

    # Stacked bars for Principal, Interest, Prepayments
    bar_width = 0.6

    # Plot Principal
    ax_bar.bar(
        numeric_years,
        principal_paid_list,
        color='#B0C4DE',
        label='Principal',
        width=bar_width
    )

    # Plot Interest (stacked)
    bottom_interest = principal_paid_list
    ax_bar.bar(
        numeric_years,
        interest_paid_list,
        bottom=bottom_interest,
        color='#4169E1',
        label='Interest',
        width=bar_width
    )

    # Plot Prepayments (stacked)
    bottom_prepayments = [
        principal_paid_list[i] + interest_paid_list[i]
        for i in range(len(years_list))
    ]
    ax_bar.bar(
        numeric_years,
        prepayments_list,
        bottom=bottom_prepayments,
        color='#FFB6C1',
        label='Prepayments',
        width=bar_width
    )

    # Dotted line for remaining balance (yearly snapshots)
    ax_bar.plot(
        numeric_years,
        remaining_balance_list,
        'k--o',  # dotted black line with circle markers
        label='Remaining Balance'
    )

    ax_bar.set_xlabel("Year")
    ax_bar.set_ylabel("Amount (₹)")
    ax_bar.set_title("Yearly Breakdown of Principal, Interest, Prepayments, & Balance")
    ax_bar.legend()

    # Format y-axis
    ax_bar.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, pos: f"₹{x:,.0f}")
    )

    # -------- 8) TOTAL MONTHLY PAYMENT --------
    total_monthly_payment = emi + prepayments_monthly

    return emi, schedule_df, fig_pie, fig_bar, total_monthly_payment, total_interest_paid, summary_dict


# -------------- STREAMLIT APP --------------
st.title("Home Loan EMI Calculator with Prepayments (Revised)")

# Default values
home_value = st.number_input("Home Value (₹)", min_value=1_000_000, step=100000, value=1_000_000)
down_payment_percentage = st.number_input("Down Payment Percentage (%)", min_value=0, max_value=100, step=1, value=20)
interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.1, value=8.0)
loan_tenure_years = st.number_input("Loan Tenure (Years)", min_value=1, max_value=40, step=1, value=15)
loan_insurance = st.number_input("Loan Insurance (₹)", min_value=0, step=1000, value=0)
property_taxes = st.number_input("Property Taxes per Year (₹)", min_value=0, step=500, value=0)
home_insurance = st.number_input("Home Insurance per Year (₹)", min_value=0, step=500, value=0)
maintenance_expenses = st.number_input("Maintenance Expenses per Month (₹)", min_value=0, step=100, value=0)

# Prepayments
prepayments_monthly = st.number_input("Monthly Prepayment (₹)", min_value=0, step=1000, value=0,
                                      help="Monthly extra payment towards principal")
prepayments_quarterly = st.number_input("Quarterly Prepayment (₹)", min_value=0, step=1000, value=0,
                                        help="Every 3rd month, extra payment towards principal")
prepayments_one_time = st.number_input("One-time Prepayment (₹)", min_value=0, step=1000, value=0,
                                       help="One-time amount deducted immediately from loan")

if st.button("Calculate EMI"):
    (
        emi, 
        schedule_df, 
        fig_pie, 
        fig_bar, 
        total_monthly_payment, 
        total_interest_paid,
        summary_dict
    ) = calculate_emi_and_schedule(
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

    # -------------------------
    # Show SUMMARY (ABOVE charts)
    # -------------------------
    st.write("## Summary")
    st.write(
        f"**Down Payment, Fees & One-time Expenses**: {format_inr(summary_dict['down_payment_fees_onetime'])}"
    )
    st.write(
        f"**Principal**: {format_inr(summary_dict['principal'])}"
    )
    st.write(
        f"**Prepayments**: {format_inr(summary_dict['prepayments'])}"
    )
    st.write(
        f"**Interest**: {format_inr(summary_dict['interest'])}"
    )
    st.write(
        f"**Taxes, Home Insurance & Maintenance (Total)**: {format_inr(summary_dict['taxes_ins_maint'])}"
    )

    # -------------------------
    # Base EMI and total monthly payment
    # -------------------------
    st.write(f"**Base EMI: {format_inr(emi)}**")
    st.write(f"**Approx. Total Monthly Payment (EMI + Monthly Prepayment): {format_inr(total_monthly_payment)}**")
    st.write(f"**Total Interest Paid (Approx): {format_inr(total_interest_paid)}**")

    # -------------------------
    # Show PIE chart
    # -------------------------
    st.pyplot(fig_pie)

    # -------------------------
    # Show BAR chart
    # -------------------------
    st.pyplot(fig_bar)

    # -------------------------
    # Show Yearly Payment Schedule with colorful header
    # -------------------------
    st.write("### Yearly Payment Schedule")
    st.dataframe(
        schedule_df.style.set_table_styles([
            {
                'selector': 'th',
                'props': [
                    ('background-color', '#5DADE2'),  # a nice shade of blue
                    ('color', 'white'),
                    ('font-weight', 'bold')
                ]
            },
            {'selector': 'td', 'props': [('color', 'black')]},
        ])
    )
