import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Function to format amounts as INR manually
def format_inr(amount):
    return f"₹ {amount:,.0f}"  # Format with comma for thousands, no decimals

# Function to calculate EMI and loan schedule
def calculate_emi_and_schedule(home_value, down_payment_percentage, interest_rate, loan_tenure_years, 
                                loan_insurance, property_taxes, home_insurance, maintenance_expenses, 
                                prepayments_monthly=0, prepayments_quarterly=0, prepayments_one_time=0):
    
    # Initial loan amount after down payment and loan insurance
    loan_amount = home_value - (home_value * down_payment_percentage / 100) - loan_insurance
    
    # Apply one-time prepayment (subtracted once from the loan amount)
    loan_amount -= prepayments_one_time

    # Monthly interest rate (annual rate divided by 12)
    monthly_interest_rate = (interest_rate / 100) / 12
    
    # Loan tenure in months
    loan_tenure_months = loan_tenure_years * 12
    
    # EMI calculation formula
    emi = (loan_amount * monthly_interest_rate * (1 + monthly_interest_rate)**loan_tenure_months) / \
          ((1 + monthly_interest_rate)**loan_tenure_months - 1)

    # Initialize lists to track yearly data
    year = []
    remaining_balance = []
    principal_paid = []
    interest_paid = []
    
    balance = loan_amount
    total_interest_paid = 0
    total_principal_paid = 0
    total_interest_for_year = 0
    total_principal_for_year = 0

    current_month = 1
    while balance > 0 and current_month <= loan_tenure_months:
        interest_payment = balance * monthly_interest_rate
        principal_payment = emi - interest_payment
        balance -= principal_payment
        
        # Apply monthly prepayment
        if prepayments_monthly > 0:
            balance -= prepayments_monthly

        # Apply quarterly prepayment every 3 months
        if current_month % 3 == 0 and prepayments_quarterly > 0:
            balance -= prepayments_quarterly
        
        total_interest_for_year += interest_payment
        total_principal_for_year += principal_payment

        # Track data every year
        if current_month % 12 == 0:
            year.append(current_month // 12)
            remaining_balance.append(balance)
            interest_paid.append(total_interest_for_year)
            principal_paid.append(total_principal_for_year)
            
            # Reset yearly totals
            total_interest_for_year = 0
            total_principal_for_year = 0

        current_month += 1

        if balance <= 0:
            break

    # If the loan is paid off early, fill the remaining months with zeros
    if balance <= 0:
        last_valid_entry = year[-1] if year else 0
        remaining_balance += [0] * (loan_tenure_years - len(remaining_balance))
        interest_paid += [0] * (loan_tenure_years - len(interest_paid))
        principal_paid += [0] * (loan_tenure_years - len(principal_paid))
        year += [last_valid_entry] * (loan_tenure_years - len(year))
    
    # Ensure all lists are of the same length by trimming or padding them
    max_length = loan_tenure_years
    year = year[:max_length]
    remaining_balance = remaining_balance[:max_length]
    interest_paid = interest_paid[:max_length]
    principal_paid = principal_paid[:max_length]

    # Create a DataFrame for the table
    schedule_df = pd.DataFrame({
        'Year': year,
        'Remaining Balance (₹)': [format_inr(balance) for balance in remaining_balance],
        'Interest Paid (₹)': [format_inr(payment) for payment in interest_paid],
        'Principal Paid (₹)': [format_inr(payment) for payment in principal_paid]
    })
    
    # Create a pie chart for the monthly breakdown
    total_principal = sum(principal_paid)
    total_prepayments = prepayments_monthly * loan_tenure_months + prepayments_one_time + prepayments_quarterly * (loan_tenure_years * 4)
    total_interest = sum(interest_paid)
    
    # Pie chart categories with updated colors
    labels = ['Principal', 'Prepayments', 'Interest']
    sizes = [total_principal, total_prepayments, total_interest]
    colors = ['#006400', '#ffcc99', '#ff4500']  # Dark Green for Principal, Pastel for Prepayments, Dark Orange for Interest
    
    # Plot pie chart with updated colors
    fig_pie, ax_pie = plt.subplots(figsize=(5, 5))  # Smaller pie chart
    ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    ax_pie.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    ax_pie.set_title("Total Payments Breakdown")

    # Calculate total monthly payment
    total_monthly_payment = emi + prepayments_monthly

    # Display the monthly payment breakdown and pie chart
    st.write(f"### Total Monthly Payment: {format_inr(total_monthly_payment)}")
    st.write("#### Monthly Payment Breakdown:")
    st.write(f"- Principal & Interest (EMI): {format_inr(emi)}")
    st.write(f"- Monthly Extra Payment (from Dec 2024): {format_inr(prepayments_monthly)}")
    st.write(f"- Property Taxes: {format_inr(property_taxes)}")
    st.write(f"- Home Insurance: {format_inr(home_insurance)}")
    st.write(f"- Maintenance Expenses: {format_inr(maintenance_expenses)}")
    st.write(f"- Total Interest Paid (Total): {format_inr(total_interest)}")

    # Display the pie chart
    st.pyplot(fig_pie)

    # Bar graph for principal, interest, and remaining balance (stacked bars)
    fig_bar, ax_bar = plt.subplots(figsize=(12, 6))  # Longer bar chart
    ax_bar.bar(year, principal_paid, label='Principal Paid', color='#006400', alpha=0.7, width=0.4, align='center')
    ax_bar.bar(year, interest_paid, label='Interest Paid', color='#ff4500', alpha=0.7, width=0.4, align='center', bottom=principal_paid)
    ax_bar.plot(year, remaining_balance, label='Remaining Balance', marker='o', color='#1f77b4')

    ax_bar.set_xlabel('Year')
    ax_bar.set_ylabel('Amount (₹ in Lakhs)')
    ax_bar.set_title('Yearly Loan Payment Breakdown')
    ax_bar.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'{x/100000:.1f}L'))
    ax_bar.legend()

    # Display the bar chart
    st.pyplot(fig_bar)

    # Display the table
    st.write("### Yearly Payment Schedule")
    st.dataframe(schedule_df)

    return emi, schedule_df, fig_pie, fig_bar


# Streamlit UI components
st.title("Home Loan EMI Calculator with Prepayments")

# Create input fields for loan parameters
home_value = st.number_input("Home Value (₹)", min_value=1000000, step=100000)
down_payment_percentage = st.number_input("Down Payment Percentage (%)", min_value=0, max_value=100, step=1)
interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.1)
loan_tenure_years = st.number_input("Loan Tenure (Years)", min_value=1, max_value=40, step=1)
loan_insurance = st.number_input("Loan Insurance (₹)", min_value=0, step=1000)
property_taxes = st.number_input("Property Taxes per Year (₹)", min_value=0, step=500)
home_insurance = st.number_input("Home Insurance per Year (₹)", min_value=0, step=500)
maintenance_expenses = st.number_input("Maintenance Expenses per Month (₹)", min_value=0, step=100)

# Add input fields for partial prepayments
prepayments_monthly = st.number_input("Monthly Prepayment (₹)", min_value=0, step=1000, help="Monthly prepayment amount")
prepayments_quarterly = st.number_input("Quarterly Prepayment (₹)", min_value=0, step=1000, help="Quarterly prepayment amount")
prepayments_one_time = st.number_input("One-time Prepayment (₹)", min_value=0, step=1000, help="One-time prepayment amount")

# Calculate button
if st.button("Calculate EMI"):
    emi, schedule_df, fig_pie, fig_bar = calculate_emi_and_schedule(home_value, down_payment_percentage, interest_rate, loan_tenure_years, 
                                                      loan_insurance, property_taxes, home_insurance, maintenance_expenses, 
                                                      prepayments_monthly, prepayments_quarterly, prepayments_one_time)
    
    if emi is not None and schedule_df is not None:
        # Display the EMI
        st.write(f"**EMI: ₹ {format_inr(emi)}**")
