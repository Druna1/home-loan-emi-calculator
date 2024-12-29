import streamlit as st

def calculate_emi(home_value, down_payment_percentage, interest_rate, loan_tenure_years, 
                  loan_insurance, property_taxes, home_insurance, maintenance_expenses):
    # Calculate loan amount
    loan_amount = home_value - (home_value * down_payment_percentage / 100) - loan_insurance
    
    # Monthly interest rate (annual rate divided by 12)
    monthly_interest_rate = (interest_rate / 100) / 12
    
    # Loan tenure in months
    loan_tenure_months = loan_tenure_years * 12
    
    # EMI calculation formula
    emi = (loan_amount * monthly_interest_rate * (1 + monthly_interest_rate)**loan_tenure_months) / \
          ((1 + monthly_interest_rate)**loan_tenure_months - 1)
    
    # Total property taxes and home insurance per month
    monthly_property_taxes = property_taxes / 12
    monthly_home_insurance = home_insurance / 12
    
    # Total monthly expenses
    total_monthly_expenses = emi + monthly_property_taxes + monthly_home_insurance + maintenance_expenses
    
    return emi, total_monthly_expenses

# Streamlit app
st.title("Home Loan EMI Calculator")

# Create input fields
home_value = st.number_input("Home Value (₹)", min_value=1000000, step=100000)
down_payment_percentage = st.number_input("Down Payment Percentage (%)", min_value=0, max_value=100, step=1)
interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.1)
loan_tenure_years = st.number_input("Loan Tenure (Years)", min_value=1, max_value=40, step=1)
loan_insurance = st.number_input("Loan Insurance (₹)", min_value=0, step=1000)
property_taxes = st.number_input("Property Taxes per Year (₹)", min_value=0, step=500)
home_insurance = st.number_input("Home Insurance per Year (₹)", min_value=0, step=500)
maintenance_expenses = st.number_input("Maintenance Expenses per Month (₹)", min_value=0, step=100)

# Calculate button
if st.button("Calculate EMI"):
    emi, total_expenses = calculate_emi(home_value, down_payment_percentage, interest_rate, loan_tenure_years, 
                                         loan_insurance, property_taxes, home_insurance, maintenance_expenses)
    # Display results
    st.write(f"**EMI: ₹ {emi:.2f}**")
    st.write(f"**Total Monthly Expenses: ₹ {total_expenses:.2f}**")
