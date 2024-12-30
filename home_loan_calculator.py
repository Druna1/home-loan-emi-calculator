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
    Where:
      - 'Year' is the actual calendar year.
      - 'MonthNum' is the sequential month of the loan (1..n).
      - 'CalendarMonthIndex' = 1..12 for Jan..Dec.
      - 'CalendarMonthAbbr' = 'Jan', 'Feb', etc.
    """

    balance = initial_principal
    data_rows = []

    current_month = 1
    while balance > 0 and current_month <= total_months:
        # Determine calendar year/month
        year_offset = (current_month - 1) // 12
        this_year = start_year + year_offset
        this_month_index = (current_month - 1) % 12  # 0..11

        # For display
        month_abbr = calendar.month_abbr[this_month_index + 1]  # e.g., 'Jan', 'Feb'
        calendar_month_index = this_month_index + 1             # 1..12

        # Interest & principal from EMI
        interest_payment = balance * monthly_interest_rate
        principal_payment = emi - interest_payment

        # Prepayment for this month
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
            'MonthNum': current_month,        # overall month in the loan
            'CalendarMonthIndex': calendar_month_index,  
            'CalendarMonthAbbr': month_abbr,
            'InterestPaid': interest_payment,
            'PrincipalPaid': principal_payment,
            'Prepayment': prepay_this_month,
            'OldBalance': old_balance,
            'NewBalance': balance,
        })

        current_month += 1

    df_monthly = pd.DataFrame(data_rows)
    return df_monthly

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
    and a MONTHLY breakdown (for expanders) so that you can see monthly details.
    """

    # --- 1) INITIAL CALCULATIONS ---
    down_payment_value = home_value * down_payment_percentage / 100
    down_payment_fees_one_time = down_payment_value + loan_insurance + prepayments_one_time

    initial_principal = home_value - down_payment_value - loan_insurance
    loan_amount = initial_principal - prepayments_one_time
    if loan_amount < 0:
        loan_amount = 0

    monthly_interest_rate = (interest_rate / 100.0) / 12.0
    total_months = loan_tenure_years * 12

    # --- 2) EMI ---
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

    # --- 3) FULL MONTHLY SCHEDULE ---
    df_monthly = calculate_monthly_schedule(
        initial_principal=loan_amount,
        monthly_interest_rate=monthly_interest_rate,
        total_months=total_months,
        emi=emi,
        prepayments_monthly=prepayments_monthly,
        prepayments_quarterly=prepayments_quarterly,
        start_year=start_year
    )

    # --- 4) GROUP MONTHLY -> YEARLY ---
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

    import numpy as np

    if df_monthly.empty:
        df_yearly = pd.DataFrame(columns=['Year','PrincipalSum','PrepaymentSum','InterestSum','FinalBalance'])
    else:
        df_monthly['Year'] = df_monthly['Year'].astype(int)
        df_yearly = df_monthly.groupby('Year').apply(aggregator).reset_index()

    all_years = list(range(start_year, start_year + loan_tenure_years))
    df_full_years = pd.DataFrame({'Year': all_years})
    df_yearly = pd.merge(df_full_years, df_yearly, on='Year', how='left')
    df_yearly.fillna(0, inplace=True)
    df_yearly.sort_values(by='Year', inplace=True)

    df_yearly['TotalPayment'] = df_yearly['PrincipalSum'] + df_yearly['InterestSum'] + df_yearly['PrepaymentSum']
    df_yearly['TaxesInsuranceMaintenance'] = (property_taxes + home_insurance + (maintenance_expenses * 12))

    # Cumulative principal+prepayments => % of Loan Paid
    if initial_principal > 0:
        df_yearly['CumulativePrincipalPrepay'] = df_yearly['PrincipalSum'].cumsum() + df_yearly['PrepaymentSum'].cumsum()
        df_yearly['PctLoanPaid'] = ((df_yearly['CumulativePrincipalPrepay'] / initial_principal) * 100).clip(upper=100)
    else:
        df_yearly['PctLoanPaid'] = 100

    df_yearly['BalanceClamped'] = df_yearly['FinalBalance'].apply(lambda x: max(0, x))

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

    fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
    ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    ax_pie.axis('equal')
    ax_pie.set_title("Total Payments Breakdown")

    fig_bar, ax_bar = plt.subplots(figsize=(8, 5))
    numeric_years = df_yearly['Year'].astype(int).values
    principal_list = df_yearly['PrincipalSum'].values
    interest_list = df_yearly['InterestSum'].values
    prepay_list = df_yearly['PrepaymentSum'].values
    balance_list = df_yearly['BalanceClamped'].values

    bar_width = 0.6

    # Stacked bars
    ax_bar.bar(
        numeric_years,
        principal_list,
        color='#B0C4DE',
        label='Principal',
        width=bar_width
    )
    bottom_interest = principal_list
    ax_bar.bar(
        numeric_years,
        interest_list,
        bottom=bottom_interest,
        color='#4169E1',
        label='Interest',
        width=bar_width
    )
    bottom_prepay = principal_list + interest_list
    ax_bar.bar(
        numeric_years,
        prepay_list,
        bottom=bottom_prepay,
        color='#FFB6C1',
        label='Prepayments',
        width=bar_width
    )
    ax_bar.plot(
        numeric_years,
        balance_list,
        'k--o',
        label='Remaining Balance'
    )
    ax_bar.set_xlabel("Year")
    ax_bar.set_ylabel("Amount (₹)")
    ax_bar.set_title("Yearly Breakdown of Principal, Interest, Prepayments, & Balance")
    ax_bar.legend()
    ax_bar.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, pos: f"₹{x:,.0f}")
    )

    total_monthly_payment = emi + prepayments_monthly

    return (
        emi,
        schedule_df,
        fig_pie,
        fig_bar,
        total_monthly_payment,
        total_interest_paid,
        summary_dict,
        df_monthly
    )


# ---------------------- STREAMLIT APP --------------------------------
st.title("Home Loan EMI Calculator with Prepayments")

start_year = st.number_input("Starting Year", value=2024, step=1)

home_value = st.number_input("Home Value (₹)", min_value=1_000_000, step=100000, value=1_000_000)
down_payment_percentage = st.number_input("Down Payment Percentage (%)", min_value=0, max_value=100, step=1, value=20)
interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.1, value=8.0)
loan_tenure_years = st.number_input("Loan Tenure (Years)", min_value=1, max_value=40, step=1, value=15)
loan_insurance = st.number_input("Loan Insurance (₹)", min_value=0, step=1000, value=0)
property_taxes = st.number_input("Property Taxes per Year (₹)", min_value=0, step=500, value=0)
home_insurance = st.number_input("Home Insurance per Year (₹)", min_value=0, step=500, value=0)
maintenance_expenses = st.number_input("Maintenance Expenses per Month (₹)", min_value=0, step=100, value=0)

prepayments_monthly = st.number_input("Monthly Prepayment (₹)", min_value=0, step=1000, value=0)
prepayments_quarterly = st.number_input("Quarterly Prepayment (₹)", min_value=0, step=1000, value=0)
prepayments_one_time = st.number_input("One-time Prepayment (₹)", min_value=0, step=1000, value=0)

if st.button("Calculate EMI"):
    (
        emi,
        schedule_df,
        fig_pie,
        fig_bar,
        total_monthly_payment,
        total_interest_paid,
        summary_dict,
        df_monthly
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
        prepayments_one_time,
        start_year
    )

    # ---- SUMMARY ----
    st.write("## Summary")
    st.write(f"**Down Payment, Fees & One-time Expenses**: {format_inr(summary_dict['down_payment_fees_onetime'])}")
    st.write(f"**Principal**: {format_inr(summary_dict['principal'])}")
    st.write(f"**Prepayments**: {format_inr(summary_dict['prepayments'])}")
    st.write(f"**Interest**: {format_inr(summary_dict['interest'])}")
    st.write(f"**Taxes, Home Insurance & Maintenance (Total)**: {format_inr(summary_dict['taxes_ins_maint'])}")

    st.write(f"**Base EMI**: {format_inr(emi)}")
    st.write(f"**Approx. Total Monthly Payment (EMI + Monthly Prepayment)**: {format_inr(total_monthly_payment)}")
    st.write(f"**Total Interest Paid (Approx)**: {format_inr(total_interest_paid)}")

    st.pyplot(fig_pie)
    st.pyplot(fig_bar)

    # YEARLY SCHEDULE
    st.write("### Yearly Payment Schedule")
    st.dataframe(
        schedule_df.style
        .set_table_styles([
            {
                'selector': 'th',
                'props': [
                    ('background-color', '#5DADE2'),
                    ('color', 'white'),
                    ('font-weight', 'bold')
                ]
            },
            {'selector': 'td', 'props': [('color', 'black')]},
        ])
    )

    # Hide past months if it's the current year
    today = datetime.datetime.now()
    current_year_system = today.year
    current_month_system = today.month

    st.write("### Monthly Breakdown")
    if not df_monthly.empty:
        years_in_monthly = sorted(df_monthly['Year'].unique())
        for y in years_in_monthly:
            # Filter for that year
            subset = df_monthly[df_monthly['Year'] == y].copy()

            # If y == current system year, filter out months < current system month
            if y == current_year_system:
                subset = subset[subset['CalendarMonthIndex'] >= current_month_system]

            # Convert numeric columns to currency for display
            numeric_cols = ['InterestPaid','PrincipalPaid','Prepayment','OldBalance','NewBalance']
            for col in numeric_cols:
                if col in subset.columns:
                    subset[col] = subset[col].apply(format_inr)

            subset.reset_index(drop=True, inplace=True)

            if not subset.empty:
                with st.expander(f"Year {y}"):
                    st.dataframe(
                        subset.style
                        .set_table_styles([
                            {
                                'selector': 'th',
                                'props': [
                                    ('background-color', '#85C1E9'),
                                    ('color', 'black'),
                                    ('font-weight', 'bold')
                                ]
                            },
                            {'selector': 'td', 'props': [('color', 'black')]},
                        ])
                    )
            else:
                # If it empties out for the current year (i.e., we were in a month < current month, no future months)
                st.write(f"**Year {y}:** No upcoming months left (all were in the past).")
    else:
        st.write("**No monthly data** (possibly loan is 0 or no valid months).")
