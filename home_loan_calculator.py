import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

def calculate_emi_and_schedule(home_value, down_payment_percentage, interest_rate, loan_tenure_years, 
                                loan_insurance, property_taxes, home_insurance, maintenance_expenses, 
                                extra_payment=0, prepayments_monthly=0, prepayments_quarterly=0, prepayments_one_time=0):
    
    # Check for zero interest rate and loan tenure to avoid division by zero error
    if interest_rate == 0:
        st.error("Interest rate cannot be zero.")
        return None, None, None

    if loan_tenure_years == 0:
        st.error("Loan tenure cannot be zero.")
        return None, None, None
    
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

    # Track the amortization schedule: year, remaining balance, interest paid, principal paid
    year = []
    remaining_balance = []
    principal_paid = []
    interest_paid = []
    
    balance = loan_amount
    for i in range(1, loan_tenure_years + 1):
        total_interest_for_year = 0
        total_principal_for_year = 0
        
        # Apply monthly prepayments and EMI payments
        for j in range(12):  # Each month
            interest_payment = balance * monthly_interest_rate
            principal_payment = emi - interest_payment
            balance -= principal_payment
            
            # Apply monthly prepayment
            if prepayments_monthly > 0:
                balance -= prepayments_monthly

            # Apply quarterly prepayment at the end of every 3 months
            if (j + 1) % 3 == 0 and prepayments_quarterly > 0:
                balance -= prepayments_quarterly

            # Track interest and principal paid for the year
            total_interest_for_year += interest_payment
            total_principal_for_year += principal_payment
        
        # Ensure the balance does not go negative
        remaining_balance.append(max(balance, 0))
        interest_paid.append(total_interest_for_year)
        principal_paid.append(total_principal_for_year)
        year.append(i)
    
    # Create a DataFrame for the table
    schedule_df = pd.DataFrame({
        'Year': year,
        'Remaining Balance (₹)': remaining_balance,
        'Interest Paid (₹)': interest_paid,
        'Principal Paid (₹)': principal_paid
    })
    
    # Create a plot for the remaining balance and principal vs interest
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(year, remaining_balance, label='Remaining Balance', marker='o')
    ax.bar(year, principal_paid, label='Principal Paid', alpha=0.5)
    ax.bar(year, interest_paid, label='Interest Paid', alpha=0.5)
    
    # Formatting Y-axis to show amounts in Lakhs (₹ 1 Lakh = ₹ 100,000)
    ax.set_xlabel('Year')
    ax.set_ylabel('Amount (₹ in Lakhs)')
    ax.set_title('Yearly Loan Payment Breakdown')
    
    # Format Y-axis labels in Lakhs
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'{x/100000:.1f}L'))
    
    ax.legend()
    
    # Display the plot and table
    st.pyplot(fig)
    st.write("### Yearly Payment Schedule")
    st.dataframe(schedule_df)

    return emi, schedule_df, fig

# Streamlit app
st.title("Home Loan EMI Calculator with Yearly Breakdown and Prepayments")

# Create input fields
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
    emi, schedule_df, fig = calculate_emi_and_schedule(home_value, down_payment_percentage, interest_rate, loan_tenure_years, 
                                                      loan_insurance, property_taxes, home_insurance, maintenance_expenses, 
                                                      prepayments_monthly, prepayments_quarterly, prepayments_one_time)
    
    if emi is not None and schedule_df is not None:
        # Display the EMI
        st.write(f"**EMI: ₹ {emi:.2f}**")
