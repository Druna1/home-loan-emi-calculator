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
        return None, None, None, None

    if loan_tenure_years == 0:
        st.error("Loan tenure cannot be zero.")
        return None, None, None, None
    
    # Calculate loan amount
    loan_amount = home_value - (home_value * down_payment_percentage / 100) - loan_insurance
    
    # Apply extra payment/prepayment towards the principal (only applied once)
    loan_amount -= extra_payment
    
    # Apply one-time prepayment: Apply the one-time prepayment directly (only subtracted once)
    if prepayments_one_time > 0:
        loan_amount -= prepayments_one_time
    
    # Monthly interest rate (annual rate divided by 12)
    monthly_interest_rate = (interest_rate / 100) / 12
    
    # Loan tenure in months
    loan_tenure_months = loan_tenure_years * 12
    
    # EMI calculation formula
    emi = (loan_amount * monthly_interest_rate * (1 + monthly_interest_rate)**loan_tenure_months) / \
    
