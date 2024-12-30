import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

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
      [Year, MonthNum, CalendarMonth, PrincipalPaid, InterestPaid, Prepayment, Balance]
    Where 'MonthNum' is 1..n of the entire loan, 'CalendarMonth' = Jan, Feb, etc. with start_year.

    This will help us create monthly breakdowns for each year.
    """
    import math
    import calendar

    balance = initial_principal
    data_rows = []

    current_month = 1
    while balance > 0 and current_month <= total_months:
        # Compute year+month for display
        # E.g. month_index=0 => start_year, Jan. We'll shift for current_month - 1
        year_offset = (current_month - 1) // 12
        this_year = start_year + year_offset
        this_month_index = (current_month - 1) % 12  # 0..11
        month_name = calendar.month_abbr[this_month_index + 1]  # e.g. 'Jan', 'Feb'

        # Calculate interest & principal from EMI
        interest_payment = balance * monthly_interest_rate
        principal_payment = emi - interest_payment

        # Prepayment for this month
        prepay_this_month = 0
        # monthly prepayment
        if prepayments_monthly > 0:
            prepay_this_month += prepayments_monthly
        # quarterly prepayment
        if (current_month % 3 == 0) and (prepayments_quarterly > 0):
            prepay_this_month += prepayments_quarterly

        # Update balance
        old_balance = balance
        balance -= principal_payment
        balance -= prepay_this_month

        if balance < 0:
            balance = 0

        row = {
            'Year': this_year,
            'MonthNum': current_month,
            'CalendarMonth': f"{month_name}",
            'InterestPaid': interest_payment,
            'PrincipalPaid': principal_payment,
            'Prepayment': prepay_this_month,
            'OldBalance': old_balance,
            'NewBalance': balance,
        }
        data_rows.append(row)

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
    # Down Payment
    down_payment_value = home_value * down_payment_percentage / 100
    # Sum of Down Payment + Fees + One-time Expenses
    down_payment_fees_one_time = down_payment_value + loan_insurance + prepayments_one_time

    # Effective Loan Amount (before one-time prepayment)
    initial_principal = home_value - down_payment_value - loan_insurance

    # Subtract one-time prepayment from the loan principal
    loan_amount = initial_principal - prepayments_one_time
    if loan_amount < 0:
        loan_amount = 0

    # Monthly interest rate
    monthly_interest_rate = (interest_rate / 100.0) / 12.0

    # Total scheduled months
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

    # --- 3) Get FULL monthly schedule ---
    df_monthly = calculate_monthly_schedule(
        initial_principal=loan_amount,
        monthly_interest_rate=monthly_interest_rate,
        total_months=total_months,
        emi=emi,
        prepayments_monthly=prepayments_monthly,
        prepayments_quarterly=prepayments_quarterly,
        start_year=start_year
    )

    # If no rows, means zero or immediate payoff
    if df_monthly.empty:
        # Then there's no normal monthly schedule
        # We'll produce an empty data
        # Let the rest of code handle the edge case
        pass

    # --- 4) YEAR-BY-YEAR AGGREGATION ---
    # We'll group the monthly DataFrame by Year
    # summing up principal, interest, prepayment
    # and get final Balance in that year
    # This is more accurate than the old approximate approach.

    df_monthly['Year'] = df_monthly['Year'].astype(int)

    # interestPaid
    # principalPaid
    # prepayment
    # newBalance

    # We’ll define an aggregator function for each year
    def aggregator(x):
        principal_sum = x['PrincipalPaid'].sum()
        prepay_sum = x['Prepayment'].sum()
        interest_sum = x['InterestPaid'].sum()
        final_balance = x['NewBalance'].iloc[-1]  # last row's NewBalance
        return pd.Series({
            'PrincipalSum': principal_sum,
            'PrepaymentSum': prepay_sum,
            'InterestSum': interest_sum,
            'FinalBalance': final_balance
        })

    df_yearly = df_monthly.groupby('Year').apply(aggregator).reset_index()

    # We'll also handle the scenario if the loan ends early, we might not have all years up to loan_tenure_years
    # We'll fill missing years with zero

    # Build a complete set of years from start_year to start_year + loan_tenure_years - 1
    all_years = list(range(start_year, start_year + loan_tenure_years))
    df_full_years = pd.DataFrame({'Year': all_years})

    df_yearly = pd.merge(df_full_years, df_yearly, on='Year', how='left')
    df_yearly.fillna(0, inplace=True)

    # Ensure sorting by Year
    df_yearly.sort_values(by='Year', inplace=True)

    # We'll now compute totalPayment per year and keep track of the balance
    # finalBalance is from aggregator
    # totalPayment is EMI+prepay. But monthly aggregator is more precise.
    # We'll do monthly sum from aggregator:
    # totalPayment = principalSum + interestSum + prepaymentSum
    df_yearly['TotalPayment'] = df_yearly['PrincipalSum'] + df_yearly['InterestSum'] + df_yearly['PrepaymentSum']
    df_yearly['TaxesInsuranceMaintenance'] = (property_taxes + home_insurance + maintenance_expenses * 12)

    # For the next year, we set the "start" as last year's finalBalance.

    # --- 5) Building the final schedule for display
    # We'll also compute a cumulative principal+prepayment (to get % of loan paid).
    df_yearly['CumulativePrincipalPrepay'] = df_yearly['PrincipalSum'].cumsum() + df_yearly['PrepaymentSum'].cumsum()
    # Limit so we never exceed 100% (in case large lumpsum)
    df_yearly['PctLoanPaid'] = (
        (df_yearly['CumulativePrincipalPrepay'] / initial_principal) * 100
        if initial_principal > 0 else 100
    )
    df_yearly['PctLoanPaid'] = df_yearly['PctLoanPaid'].clip(upper=100)  # ensure max 100

    # Create the final DataFrame columns in the order we want
    schedule_df = pd.DataFrame({
        'Year': df_yearly['Year'].astype(str),
        'Principal (₹)': df_yearly['PrincipalSum'].apply(format_inr),
        'Prepayments (₹)': df_yearly['PrepaymentSum'].apply(format_inr),
        'Interest (₹)': df_yearly['InterestSum'].apply(format_inr),
        'Taxes, Insurance, Expenses (₹)': df_yearly['TaxesInsuranceMaintenance'].apply(format_inr),
        'Total Payment (₹)': df_yearly['TotalPayment'].apply(format_inr),
        'Balance (₹)': df_yearly['FinalBalance'].apply(lambda x: format_inr(max(x,0))),
        '% of Loan Paid': df_yearly['PctLoanPaid'].apply(lambda x: f"{x:.2f}%"),
    })

    # Drop default index to avoid an empty first column
    schedule_df.reset_index(drop=True, inplace=True)

    # Summaries for the final outputs
    total_principal_paid = df_yearly['PrincipalSum'].sum()
    total_prepayments = df_yearly['PrepaymentSum'].sum() + prepayments_one_time
    total_interest_paid = df_yearly['InterestSum'].sum()

    # Payment breakdown
    labels = ['Principal', 'Prepayments', 'Interest']
    sizes = [total_principal_paid, total_prepayments, total_interest_paid]
    colors = ['#B0C4DE', '#FFB6C1', '#4169E1']

    # Taxes, home insurance & maintenance for entire loan
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
    import matplotlib.pyplot as plt
    fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
    ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    ax_pie.axis('equal')
    ax_pie.set_title("Total Payments Breakdown")

    # Stacked bar chart
    fig_bar, ax_bar = plt.subplots(figsize=(8, 5))
    numeric_years = df_yearly['Year'].astype(int).values
    principal_list = df_yearly['PrincipalSum'].values
    interest_list = df_yearly['InterestSum'].values
    prepay_list = df_yearly['PrepaymentSum'].values
    balance_list = df_yearly['FinalBalance'].values

    bar_width = 0.6

    # Plot Principal
    ax_bar.bar(
        numeric_years,
        principal_list,
        color='#B0C4DE',
        label='Principal',
        width=bar_width
    )
    # Plot Interest
    bottom_interest = principal_list
    ax_bar.bar(
        numeric_years,
        interest_list,
        bottom=bottom_interest,
        color='#4169E1',
        label='Interest',
        width=bar_width
    )
    # Plot Prepayments
    bottom_prepayments = bottom_interest + prepay_list*0  # or see the next line
    # Actually, we want to stack prepayments on top of principal+interest
    bottom_prepay = []
    for i in range(len(principal_list)):
        bottom_val = principal_list[i] + interest_list[i]
        bottom_prepay.append(bottom_val)

    ax_bar.bar(
        numeric_years,
        prepay_list,
        bottom=bottom_prepay,
        color='#FFB6C1',
        label='Prepayments',
        width=bar_width
    )

    # Dotted line for balance
    ax_bar.plot(
        numeric_years,
        balance_list,
        'k--o',  # dotted black line with circle markers
        label='Remaining Balance'
    )

    ax_bar.set_xlabel("Year")
    ax_bar.set_ylabel("Amount (₹)")
    ax_bar.set_title("Yearly Breakdown of Principal, Interest, Prepayments, & Balance")
    ax_bar.legend()
    import matplotlib.ticker as ticker
    ax_bar.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, pos: f"₹{x:,.0f}")
    )

    # total monthly payment
    total_monthly_payment = emi + prepayments_monthly

    # Return everything
    return (
        emi,
        schedule_df,
        fig_pie,
        fig_bar,
        total_monthly_payment,
        total_interest_paid,
        summary_dict,
        df_monthly  # return monthly schedule for expanders
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
    st.write(
        f"**Down Payment, Fees & One-time Expenses**: {format_inr(summary_dict['down_payment_fees_onetime'])}"
    )
    st.write(f"**Principal**: {format_inr(summary_dict['principal'])}")
    st.write(f"**Prepayments**: {format_inr(summary_dict['prepayments'])}")
    st.write(f"**Interest**: {format_inr(summary_dict['interest'])}")
    st.write(f"**Taxes, Home Insurance & Maintenance (Total)**: {format_inr(summary_dict['taxes_ins_maint'])}")

    # ---- EMI + Interest ----
    st.write(f"**Base EMI**: {format_inr(emi)}")
    st.write(f"**Approx. Total Monthly Payment (EMI + Monthly Prepayment)**: {format_inr(total_monthly_payment)}")
    st.write(f"**Total Interest Paid (Approx)**: {format_inr(total_interest_paid)}")

    # ---- PIE + BAR CHARTS ----
    st.pyplot(fig_pie)
    st.pyplot(fig_bar)

    # ---- YEARLY SCHEDULE TABLE (no extra index col) ----
    st.write("### Yearly Payment Schedule")
    st.dataframe(
        schedule_df.style
        .hide_index()
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

    # ---- COLLAPSIBLE MONTHLY TABLES PER YEAR ----
    st.write("### Monthly Breakdown (Click on each year to expand)")
    if not df_monthly.empty:
        # For each unique year in df_monthly, create an expander
        years_in_monthly = sorted(df_monthly['Year'].unique())
        for y in years_in_monthly:
            subset = df_monthly[df_monthly['Year'] == y].copy()
            # Build a small table for that year
            # Convert amounts to INR
            subset['InterestPaid'] = subset['InterestPaid'].apply(format_inr)
            subset['PrincipalPaid'] = subset['PrincipalPaid'].apply(format_inr)
            subset['Prepayment'] = subset['Prepayment'].apply(format_inr)
            subset['OldBalance'] = subset['OldBalance'].apply(format_inr)
            subset['NewBalance'] = subset['NewBalance'].apply(format_inr)

            subset.reset_index(drop=True, inplace=True)

            with st.expander(f"Year {y}"):
                st.dataframe(
                    subset.style
                    .hide_index()
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
        st.write("**No monthly data** (possibly loan is 0 or no valid months).")
