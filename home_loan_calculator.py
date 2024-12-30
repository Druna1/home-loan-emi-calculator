import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import math
import calendar
import datetime

# Function to format amounts as INR (no decimals, comma-separated)
def format_inr(amount):
    return f"₹ {amount:,.0f}"

def calculate_monthly_schedule(
    initial_principal,
    monthly_interest_rate,
    total_months,
    emi,
    prepayments_monthly,
    prepayments_quarterly,
    start_year
):
    """
    Generate a MONTH-BY-MONTH amortization schedule.
    Returns a DataFrame with columns:
      [Year, MonthNum, CalendarMonthIndex, CalendarMonthAbbr,
       InterestPaid, PrincipalPaid, Prepayment, OldBalance, NewBalance]
    """
    balance = initial_principal
    data_rows = []

    current_month = 1
    while balance > 0 and current_month <= total_months:
        # Determine calendar year/month
        year_offset = (current_month - 1) // 12
        this_year = start_year + year_offset
        this_month_index = (current_month - 1) % 12  # 0..11
        month_abbr = calendar.month_abbr[this_month_index + 1]  # e.g., 'Jan', 'Feb'
        calendar_month_index = this_month_index + 1             # 1..12

        # Interest & principal from EMI
        interest_payment = balance * monthly_interest_rate
        principal_payment = emi - interest_payment

        # Prepayments
        prepay_this_month = 0
        if prepayments_monthly > 0:
            prepay_this_month += prepayments_monthly
        if (current_month % 3 == 0) and (prepayments_quarterly > 0):
            prepay_this_month += prepayments_quarterly

        old_balance = balance
        balance -= principal_payment
        balance -= prepay_this_month

        if balance < 0:
            balance = 0

        data_rows.append({
            'Year': this_year,
            'MonthNum': current_month,        # overall loan month index
            'CalendarMonthIndex': calendar_month_index,
            'CalendarMonthAbbr': month_abbr,
            'InterestPaid': interest_payment,
            'PrincipalPaid': principal_payment,
            'Prepayment': prepay_this_month,
            'OldBalance': old_balance,
            'NewBalance': balance,
        })

        current_month += 1

    return pd.DataFrame(data_rows)


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
    prepayments_one_time=0,
    start_year=2024
):
    """
    Calculates both a YEARLY aggregated schedule (for the main table and charts)
    and a MONTHLY breakdown (for expanders).
    EXCLUDES past months in the current year from both
    monthly and yearly calculations to keep them consistent.
    """

    # -------- 1) BASIC LOAN SETUP --------
    down_payment_value = home_value * down_payment_percentage / 100
    down_payment_fees_one_time = down_payment_value + loan_insurance + prepayments_one_time

    initial_principal = home_value - down_payment_value - loan_insurance
    loan_amount = initial_principal - prepayments_one_time
    if loan_amount < 0:
        loan_amount = 0

    monthly_interest_rate = (interest_rate / 100.0) / 12.0
    total_months = loan_tenure_years * 12

    # -------- 2) EMI --------
    if total_months == 0:
        emi = 0
    elif monthly_interest_rate == 0:
        emi = loan_amount / total_months
    else:
        emi = (
            loan_amount
            * monthly_interest_rate
            * (1 + monthly_interest_rate) ** total_months
        ) / (
            (1 + monthly_interest_rate) ** total_months - 1
        )

    # -------- 3) FULL MONTHLY SCHEDULE --------
    df_monthly = calculate_monthly_schedule(
        initial_principal=loan_amount,
        monthly_interest_rate=monthly_interest_rate,
        total_months=total_months,
        emi=emi,
        prepayments_monthly=prepayments_monthly,
        prepayments_quarterly=prepayments_quarterly,
        start_year=start_year
    )

    # -------- 4) FILTER OUT PAST MONTHS OF CURRENT YEAR --------
    # So that partial data is consistent between monthly + yearly aggregator
    today = datetime.datetime.now()
    current_year_system = today.year
    current_month_system = today.month

    if not df_monthly.empty:
        # For any row in the current system year, skip if CalendarMonthIndex < current_month_system
        # Also if that row's year < current system year => keep it? or remove it entirely?
        # The user specifically wants to skip only *past months of the current year*.
        # Past entire years are presumably in the future or older. Decide if we keep them or not?
        # The question specifically says: "For the current year, show current month and next months only, not the before ones."
        # => So we keep all data for older or future years, but for the current system year, skip months < current_month_system.

        # Step 1: Mark which rows to keep
        # Keep everything if year < current_year_system or year > current_year_system
        # If year == current_year_system => keep only rows with CalendarMonthIndex >= current_month_system
        condition_keep = (
            (df_monthly['Year'] < current_year_system)
            | (df_monthly['Year'] > current_year_system)
            | (
                (df_monthly['Year'] == current_year_system)
                & (df_monthly['CalendarMonthIndex'] >= current_month_system)
            )
        )
        df_monthly = df_monthly[condition_keep].copy()

    # -------- 5) AGGREGATE YEARLY FROM FILTERED MONTHLY --------
    if df_monthly.empty:
        df_yearly = pd.DataFrame(columns=['Year','PrincipalSum','PrepaymentSum','InterestSum','FinalBalance'])
    else:
        df_monthly['Year'] = df_monthly['Year'].astype(int)

        def aggregator(x):
            principal_sum = x['PrincipalPaid'].sum()
            prepay_sum = x['Prepayment'].sum()
            interest_sum = x['InterestPaid'].sum()
            final_balance = x['NewBalance'].iloc[-1]
            return pd.Series({
                'PrincipalSum': principal_sum,
                'PrepaymentSum': prepay_sum,
                'InterestSum': interest_sum,
                'FinalBalance': final_balance
            })

        df_yearly = df_monthly.groupby('Year').apply(aggregator).reset_index()

    # Build a list of all relevant years from start_year..start_year+loan_tenure_years-1
    all_years = list(range(start_year, start_year + loan_tenure_years))
    df_full_years = pd.DataFrame({'Year': all_years})
    df_yearly = pd.merge(df_full_years, df_yearly, on='Year', how='left').fillna(0)
    df_yearly.sort_values(by='Year', inplace=True)

    # totalPayment = principal+interest+prepay for that year
    df_yearly['TotalPayment'] = (
        df_yearly['PrincipalSum'] + df_yearly['InterestSum'] + df_yearly['PrepaymentSum']
    )
    df_yearly['TaxesInsuranceMaintenance'] = property_taxes + home_insurance + (maintenance_expenses * 12)

    # % of loan paid => cumulative principal+prepay / initial_principal, clipped at 100
    df_yearly['CumulativePP'] = df_yearly['PrincipalSum'].cumsum() + df_yearly['PrepaymentSum'].cumsum()
    if initial_principal > 0:
        df_yearly['PctLoanPaid'] = (df_yearly['CumulativePP'] / initial_principal * 100).clip(upper=100)
    else:
        df_yearly['PctLoanPaid'] = 100

    # FinalBalance might not be the actual if skipping months, but we show what's left
    df_yearly['BalanceClamped'] = df_yearly['FinalBalance'].apply(lambda x: max(0, x))

    # Create the schedule DataFrame
    schedule_df = pd.DataFrame({
        'Year': df_yearly['Year'].astype(str),
        'Principal (₹)': df_yearly['PrincipalSum'].apply(format_inr),
        'Prepayments (₹)': df_yearly['PrepaymentSum'].apply(format_inr),
        'Interest (₹)': df_yearly['InterestSum'].apply(format_inr),
        'Taxes, Insurance, Expenses (₹)': df_yearly['TaxesInsuranceMaintenance'].apply(format_inr),
        'Total Payment (₹)': df_yearly['TotalPayment'].apply(format_inr),
        'Balance (₹)': df_yearly['BalanceClamped'].apply(format_inr),
        '% of Loan Paid': df_yearly['PctLoanPaid'].apply(lambda x: f"{x:.2f}%"),
    })
    schedule_df.reset_index(drop=True, inplace=True)

    # Summaries
    total_principal_paid = df_yearly['PrincipalSum'].sum()
    total_prepayments = df_yearly['PrepaymentSum'].sum() + prepayments_one_time
    total_interest_paid = df_yearly['InterestSum'].sum()

    labels = ['Principal', 'Prepayments', 'Interest']
    sizes = [total_principal_paid, total_prepayments, total_interest_paid]
    colors = ['#B0C4DE', '#FFB6C1', '#4169E1']

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

    # Pie chart
    fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
    ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    ax_pie.axis('equal')
    ax_pie.set_title("Total Payments Breakdown")

    # Bar chart
    fig_bar, ax_bar = plt.subplots(figsize=(8, 5))
    numeric_years = df_yearly['Year'].astype(int).values
    principal_list = df_yearly['PrincipalSum'].values
    interest_list = df_yearly['InterestSum'].values
    prepay_list = df_yearly['PrepaymentSum'].values
    balance_list = df_yearly['BalanceClamped'].values

    bar_width = 0.6
    ax_bar.bar(
        numeric
