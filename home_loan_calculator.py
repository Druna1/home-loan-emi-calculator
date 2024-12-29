import streamlit as st
import pandas as pd

def calculate_emi(home_value, down_payment_percentage, interest_rate, loan_tenure_years, 
                  loan_insurance, property_taxes, home_insurance, maintenance_expenses, 
                  extra_payment=0, prepayments_monthly=0, prepayments_quarterly=0, prepayments_one_time=0):
    # Calculate loan amount
    loan_amount = home_value - (home_value * down_payment_percentage / 100) - loan_insurance
    
    # Apply extra payment/prepayment towards the principal
    loan_amount -= extra_payment
    
    # Apply prepayments
    # Monthly prepayment: Reduce loan amount by the monthly prepayment amount
    if prepayments_monthly > 0:
        loan_amount -= prepayments_monthly * loan_tenure_years * 12
    
    # Quarterly prepayment: Reduce loan amount by the quarterly prepayment amount
    if prepayments_quarterly > 0:
        loan_amount -= prepayments_quarterly * (loan_tenure_years * 4)
    
    # One-time prepayment: Apply the one-time prepayment directly
    if prepayments_one_time > 0:
        loan_amount -= prepayments_one_time
    
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
    
    return emi, total_monthly_expenses, loan_amount

# Streamlit app
st.title("Home Loan EMI Calculator with Partial Prepayments")

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
    emi, total_expenses, remaining_loan = calculate_emi
