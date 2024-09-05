import pandas as pd
import streamlit as st
import io
import base64
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter
from traitlets import default

from generate_LOI import handle_generate_lois
from Export_data import handle_export
from refresh_button import reset_session_state

def process_spreadsheet(df):
    # Remove the dollar sign from the 'Asking Price' and 'Loan Balance' columns
    # df['Loan Balance'] = df['Loan Balance'].replace(r'[\$,]', '', regex=True).astype(float)
    # df['Asking Price'] = df['Asking Price'].replace(r'[\$,]', '', regex=True).astype(float)

    # # Calculate Percent Equity and Equity columns
    # df['Percent Equity'] = (df['Asking Price'] - df['Loan Balance']) / df['Asking Price'] * 100
    # df['Percent Equity'] = df['Percent Equity'].round(2)
    df['Equity'] = df['Asking Price'] - df['Loan Balance']

    # Highlight rows with low equity
    low_equity_mask = df['Percent Equity'] < 15

    # Format numeric columns
    df['Loan Balance'] = df['Loan Balance'].apply(lambda x: f"${x:,.2f}")
    df['Asking Price'] = df['Asking Price'].apply(lambda x: f"${x:,.2f}")
    df['Percent Equity'] = df['Percent Equity'].apply(lambda x: f"{x:.2f}%")
    df['Equity'] = df['Equity'].apply(lambda x: f"${x:,.2f}")

    return df, low_equity_mask

def style_excel(writer, df, low_equity_mask):
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    
    # Apply yellow background to low equity rows in 'Address' column
    yellow_fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
    address_col_index = df.columns.get_loc('Address') + 1  # openpyxl is 1-indexed
    for row_idx, is_low_equity in enumerate(low_equity_mask, start=2):  # start=2 because Excel is 1-indexed and we have a header row
        if is_low_equity:
            cell = worksheet.cell(row=row_idx, column=address_col_index)
            cell.fill = yellow_fill

    # Set column widths
    for idx, col in enumerate(df.columns):
        column_letter = get_column_letter(idx + 1)
        column_width = max(df[col].astype(str).map(len).max(), len(col))
        worksheet.column_dimensions[column_letter].width = column_width + 2

def get_excel_download_link(df, low_equity_mask):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        style_excel(writer, df, low_equity_mask)
    
    output.seek(0)
    b64 = base64.b64encode(output.getvalue()).decode()
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="processed_data.xlsx">Download Processed Excel</a>'

def handle_scan_data(df):
    processed_df, low_equity_mask = process_spreadsheet(df)
    st.write("Processed Data Preview:")
    st.dataframe(processed_df.style.apply(lambda x: ['background-color: green' if v else '' for v in low_equity_mask], subset=['Address'], axis=0))
    
    # Statistics
    st.write(f"Total rows: {len(df)}")
    st.write(f"Rows with low equity (< 15%): {low_equity_mask.sum()}")

    return processed_df, low_equity_mask


def main():
    st.title("Contract Creator APP")
    st.subheader("We Buy Houses Anywhere LLC")
    # st.write(" ") Is we wanna to write something that is needed we can write here.

    # Add this at the top of your main app code, before any other UI elements
    if st.button("Refresh"):
        reset_session_state()
        st.rerun() # using rerun instead of experimental_rerun() vcz it is depreciated

    # Initialize session state variables if they don't exist
    if 'use_default_template' not in st.session_state:
        st.session_state.use_default_template = False
    if 'uploaded_template' not in st.session_state:
        st.session_state.uploaded_template = None
    if 'company_name' not in st.session_state:
        st.session_state.company_name = "We Buy Houses Anywhere LLC"
    if 'your_name' not in st.session_state:
        st.session_state.your_name = "Justin Pickell"
    if 'executed' not in st.session_state:
        st.session_state.executed = False

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        st.write("Original Data Preview:")
        st.dataframe(df.head(10))
        st.write(f"Rows count: {len(df)}")

        # Calculate Percent Equity here
        df['Loan Balance'] = df['Loan Balance'].replace(r'[\$,]', '', regex=True).astype(float)
        df['Asking Price'] = df['Asking Price'].replace(r'[\$,]', '', regex=True).astype(float)
        df['Percent Equity'] = (df['Asking Price'] - df['Loan Balance']) / df['Asking Price'] * 100
        df['Percent Equity'] = df['Percent Equity'].round(2)
      

        # Sidebar filters
        with st.sidebar:
            st.header("Filters")
            loan_types = st.multiselect("Loan Types", options=["ANY", "FHA", "VA", "NEW CONVENTIONAL"], default=None)
            status = st.multiselect("Status", options=["ACTIVE", "FAIL", "PENDING"], default=None)
            max_equity = st.selectbox("Max Equity (%)", options=[None, 5, 10, 15, 20, 25], index=4)
            max_interest_rate = st.selectbox("Max Interest Rate", options=[None, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7], index=7)

        # Apply filters
        filtered_df = df.copy()

        if loan_types:
            filtered_df = filtered_df[filtered_df['Loan Type'].isin(loan_types)]
        if status:
            filtered_df = filtered_df[filtered_df['Status'].isin(status)]
        if max_equity:
            filtered_df = filtered_df[filtered_df['Percent Equity'].replace(r'[%]', '', regex=True).astype(float) <= max_equity]
        if max_interest_rate:
            filtered_df = filtered_df[filtered_df['Interest Rate'] <= max_interest_rate]

        st.write("Filtered Data Preview:")
        st.dataframe(filtered_df.head(10))
        st.write(f"Rows count: {len(filtered_df)}")

        menu_options = ["1. Scan Data", "2. Generate LOIs", "3. Export"]
        choice = st.selectbox("Select an action:", menu_options)

        if st.button("Execute"):
            st.session_state.executed = True

        if st.session_state.executed:
            processed_df, low_equity_mask = handle_scan_data(filtered_df)
            if choice == "1. Scan Data":              
                st.markdown(get_excel_download_link(processed_df, low_equity_mask), unsafe_allow_html=True)
            elif choice == "2. Generate LOIs":
                handle_generate_lois(processed_df)
            elif choice == "3. Export":
                handle_export(processed_df)
        # if st.button("Execute"):
        #     processed_df, low_equity_mask = handle_scan_data(filtered_df)
        #     if choice == "1. Scan Data":
        #         # processed_df, low_equity_mask = handle_scan_data(filtered_df)
        #         st.markdown(get_excel_download_link(processed_df, low_equity_mask), unsafe_allow_html=True)
        #     elif choice == "2. Generate LOIs":
        #         handle_generate_lois(processed_df)
        #     elif choice == "3. Export":
        #         handle_export(filtered_df)

if __name__ == "__main__":
    main()


# import pandas as pd
# import streamlit as st
# import io
# import base64
# from openpyxl.styles import PatternFill
# from openpyxl.utils import get_column_letter

# def process_spreadsheet(df):
#     # Remove the dollar sign from the 'Asking Price' and 'Loan Balance' columns
#     df['Loan Balance'] = df['Loan Balance'].replace(r'[\$,]', '', regex=True).astype(float)
#     df['Asking Price'] = df['Asking Price'].replace(r'[\$,]', '', regex=True).astype(float)


#     # Calculate Percent Equity and Equity columns
#     df['Percent Equity'] = (df['Asking Price'] - df['Loan Balance']) / df['Asking Price'] * 100
#     df['Percent Equity'] = df['Percent Equity'].round(2)
#     df['Equity'] = df['Asking Price'] - df['Loan Balance']

#     # Highlight rows with low equity
#     low_equity_mask = df['Percent Equity'] < 15

#     # Format numeric columns
#     df['Loan Balance'] = df['Loan Balance'].apply(lambda x: f"${x:,.2f}")
#     df['Asking Price'] = df['Asking Price'].apply(lambda x: f"${x:,.2f}")
#     df['Percent Equity'] = df['Percent Equity'].apply(lambda x: f"{x:.2f}%")
#     df['Equity'] = df['Equity'].apply(lambda x: f"${x:,.2f}")

#     return df, low_equity_mask

# def style_excel(writer, df, low_equity_mask):
#     workbook = writer.book
#     worksheet = writer.sheets['Sheet1']
    
#     # Apply yellow background to low equity rows in 'Address' column
#     yellow_fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
#     address_col_index = df.columns.get_loc('Address') + 1  # openpyxl is 1-indexed
#     for row_idx, is_low_equity in enumerate(low_equity_mask, start=2):  # start=2 because Excel is 1-indexed and we have a header row
#         if is_low_equity:
#             cell = worksheet.cell(row=row_idx, column=address_col_index)
#             cell.fill = yellow_fill

#     # Set column widths
#     for idx, col in enumerate(df.columns):
#         column_letter = get_column_letter(idx + 1)
#         column_width = max(df[col].astype(str).map(len).max(), len(col))
#         worksheet.column_dimensions[column_letter].width = column_width + 2

# def get_excel_download_link(df, low_equity_mask):
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         df.to_excel(writer, index=False, sheet_name='Sheet1')
#         style_excel(writer, df, low_equity_mask)
    
#     output.seek(0)
#     b64 = base64.b64encode(output.getvalue()).decode()
#     return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="processed_data.xlsx">Download Processed Excel</a>'

# def handle_scan_data(df):
#     processed_df, low_equity_mask = process_spreadsheet(df)
#     st.write("Processed Data Preview:")
#     st.dataframe(processed_df.style.apply(lambda x: ['background-color: yellow' if v else '' for v in low_equity_mask], subset=['Address'], axis=0))
    
#     # Statistics
#     st.write(f"Total rows: {len(df)}")
#     st.write(f"Rows with low equity (< 15%): {low_equity_mask.sum()}")
    
#     return processed_df, low_equity_mask

# def handle_generate_lois(df):
#     st.write("Generating LOIs... (This is a placeholder for the LOI generation process)")
#     # Here you would implement the actual LOI generation logic

# def handle_export(df):
#     st.write("Exporting data... (This is a placeholder for the export process)")
#     # Here you would implement the actual export logic

# def main():
#     st.title("Contract Creator")

#     uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
#     if uploaded_file is not None:
#         df = pd.read_csv(uploaded_file)
#         st.write("Original Data Preview:")
#         st.dataframe(df.head())

#         menu_options = ["1. Scan Data", "2. Generate LOIs", "3. Export"]
#         choice = st.selectbox("Select an action:", menu_options)

#         if st.button("Execute"):
#             if choice == "1. Scan Data":
#                 processed_df, low_equity_mask = handle_scan_data(df)
#                 st.markdown(get_excel_download_link(processed_df, low_equity_mask), unsafe_allow_html=True)
#             elif choice == "2. Generate LOIs":
#                 handle_generate_lois(df)
#             elif choice == "3. Export":
#                 handle_export(df)

# if __name__ == "__main__":
#     main()

