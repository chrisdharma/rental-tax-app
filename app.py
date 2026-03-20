import streamlit as st
from PIL import Image
import google.generativeai as genai
import json

# --- Session State Initialization ---
if "repairs_val" not in st.session_state: st.session_state.repairs_val = 0.0
if "utilities_val" not in st.session_state: st.session_state.utilities_val = 0.0
if "prof_fees_val" not in st.session_state: st.session_state.prof_fees_val = 0.0
if "appliances_val" not in st.session_state: st.session_state.appliances_val = 0.0
if "prop_tax_val" not in st.session_state: st.session_state.prop_tax_val = 0.0
if "mortgage_val" not in st.session_state: st.session_state.mortgage_val = 0.0

# --- AI API Setup ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    ai_enabled = True
except KeyError:
    ai_enabled = False

# --- Tax Brackets & Logic ---
FED_BRACKETS = [(58523, 0.14), (117045, 0.205), (181440, 0.26), (258482, 0.29), (float('inf'), 0.33)]
ON_BRACKETS = [(53891, 0.0505), (107785, 0.0915), (150000, 0.1116), (220000, 0.1216), (float('inf'), 0.1316)]

def calculate_tax(income, brackets):
    tax = 0
    prev_limit = 0
    for limit, rate in brackets:
        if income > prev_limit:
            taxable_amount = min(income, limit) - prev_limit
            tax += taxable_amount * rate
            prev_limit = limit
        else:
            break
    return tax

# --- UI Setup ---
st.set_page_config(page_title="2026 Rental Tax Estimator Pro", page_icon="🏢", layout="wide")
st.title("🍁 2026 Ontario Rental Tax Estimator (Pro)")
st.warning("**Disclaimer:** This tool is for estimation purposes only. It is not professional tax advice. No personal data or images are saved.")
st.markdown("---")

# --- FEATURE: AI Document Scanner ---
if ai_enabled:
    with st.expander("📄 Optional: Scan a Receipt or Statement with AI"):
        uploaded_file = st.file_uploader("Upload a document (JPG, PNG, PDF)", type=["jpg", "jpeg", "png", "pdf"])

        if uploaded_file is not None:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            if file_extension in ['jpg', 'jpeg', 'png']:
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", width=250)
            elif file_extension == 'pdf':
                st.info(f"📄 PDF Document loaded: {uploaded_file.name}")

            if st.button("Process Document"):
                with st.spinner("Scanning and categorizing..."):
                    prompt = """
                    You are an expert Canadian tax assistant. Analyze this financial document and extract the information STRICTLY as a JSON object with no markdown formatting.
                    CRITICAL RULES FOR MORTGAGE STATEMENTS: I ONLY want the "Interest" paid. Do NOT extract the "Principal" or "Total Payment".
                    Keys required: "vendor", "total" (number only), "category" (Must be exactly one of: [Mortgage Interest, Repairs & Maintenance, Utilities, Professional Fees, Appliances (Class 8), Property Taxes, Uncategorized]).
                    """
                    try:
                        if file_extension == 'pdf':
                            doc_data = {"mime_type": "application/pdf", "data": uploaded_file.getvalue()}
                            payload = [prompt, doc_data]
                        else:
                            payload = [prompt, image]

                        response = model.generate_content(payload)
                        raw_json = response.text.strip().replace('```json', '').replace('```', '')
                        expense_data = json.loads(raw_json)
                        
                        st.success("Document processed successfully!")
                        category = expense_data.get('category', 'Uncategorized')
                        extracted_total = float(expense_data.get('total', 0))
                        
                        colA, colB, colC = st.columns(3)
                        colA.metric("Vendor", expense_data.get('vendor', 'Unknown'))
                        colB.metric("Extracted Total", f"${extracted_total:.2f}")
                        colC.metric("CRA Category", category)

                        if category == "Repairs & Maintenance": st.session_state.repairs_val += extracted_total
                        elif category == "Utilities": st.session_state.utilities_val += extracted_total
                        elif category == "Professional Fees": st.session_state.prof_fees_val += extracted_total
                        elif category == "Appliances (Class 8)": st.session_state.appliances_val += extracted_total
                        elif category == "Property Taxes": st.session_state.prop_tax_val += extracted_total
                        elif category == "Mortgage Interest": st.session_state.mortgage_val += extracted_total
                            
                    except Exception as e:
                        st.error(f"Could not parse the document clearly. Please enter manually. Error: {e}")

st.markdown("---")

# --- Manual Inputs ---
st.header("1. Income & Ownership")
col_inc1, col_inc2 = st.columns(2)
with col_inc1:
    base_income = st.number_input("Your Gross Personal Income", min_value=0.0, step=1000.0)
with col_inc2:
    ownership_pct = st.slider("Your Ownership % of the Property", min_value=1, max_value=100, value=100, help="If you co-own this property with a spouse/partner, adjust this slider to reflect your share on the title.")

st.header("2. Total Property Rental Income")
col1, col2 = st.columns(2)
with col1:
    gross_rent = st.number_input("Total Gross Rent Collected", min_value=0.0, step=100.0)
with col2:
    other_income = st.number_input("Other Income (Parking, Laundry, etc.)", min_value=0.0, step=50.0)

total_income = gross_rent + other_income

st.header("3. Total Property Deductible Expenses")
exp_col1, exp_col2, exp_col3 = st.columns(3)

with exp_col1:
    property_tax = st.number_input("Property Taxes", min_value=0.0, step=100.0, key="prop_tax_val")
    mortgage_interest = st.number_input("Mortgage Interest (Not Principal)", min_value=0.0, step=100.0, key="mortgage_val")
    insurance = st.number_input("Home Insurance", min_value=0.0, step=100.0)

with exp_col2:
    repairs = st.number_input("Repairs & Maintenance", min_value=0.0, step=100.0, key="repairs_val")
    utilities = st.number_input("Utilities (Heat, Hydro, Water)", min_value=0.0, step=100.0, key="utilities_val")
    condo_fees = st.number_input("Strata / Condo Fees", min_value=0.0, step=100.0)

with exp_col3:
    prof_fees = st.number_input("Professional Fees (Lawyer, CPA)", min_value=0.0, step=50.0, key="prof_fees_val")
    advertising = st.number_input("Advertising", min_value=0.0, step=10.0)
    new_appliances = st.number_input("New Appliances (Class 8 CCA)", min_value=0.0, step=100.0, key="appliances_val")

cca_deduction = (new_appliances * 0.5) * 0.20 
current_expenses = property_tax + mortgage_interest + insurance + repairs + utilities + condo_fees + prof_fees + advertising

st.header("4. RRSP Tax Offset Strategy")
rrsp_room = st.number_input("Your Available RRSP Contribution Room", min_value=0.0, step=1000.0)

# --- Calculations ---
total_deductions = current_expenses + cca_deduction
property_net_income = total_income - total_deductions

# Apply Ownership Percentage
user_net_rental_income = property_net_income * (ownership_pct / 100.0)
total_taxable_income = base_income + user_net_rental_income

# Tax Math
total_base_tax = calculate_tax(base_income, FED_BRACKETS) + calculate_tax(base_income, ON_BRACKETS)
total_combined_tax = calculate_tax(total_taxable_income, FED_BRACKETS) + calculate_tax(total_taxable_income, ON_BRACKETS)
rental_tax_owed = total_combined_tax - total_base_tax

st.markdown("---")

# --- Results & Strategy Recommendations ---
st.header("📊 Your Year-End Tax Estimate")

if user_net_rental_income > 0:
    st.success(f"**Your Share of Net Taxable Rental Income ({ownership_pct}%):** ${user_net_rental_income:,.2f}")
    st.error(f"**Estimated Tax Owed on Your Share:** ${rental_tax_owed:,.2f}")
    
    st.markdown("### 💡 Financial Strategies")
    colA, colB, colC = st.columns(3)
    
    with colA:
        set_aside = (rental_tax_owed / user_net_rental_income) * 100
        st.info(f"**Option 1: Standard Path**\n\nSet aside **{set_aside:.1f}%** (**${rental_tax_owed:,.2f}**) of your profits in a standard account for tax season.")
        
    with colB:
        ideal_rrsp = user_net_rental_income
        if rrsp_room >= ideal_rrsp:
            st.success(f"**Option 2: RRSP Eraser**\n\nContribute **${ideal_rrsp:,.2f}** to your RRSP.\n\n**New Tax Bill: $0.00**")
        elif rrsp_room > 0:
            new_taxable = total_taxable_income - rrsp_room
            new_tax = calculate_tax(new_taxable, FED_BRACKETS) + calculate_tax(new_taxable, ON_BRACKETS)
            new_rental_tax = new_tax - total_base_tax
            tax_saved = rental_tax_owed - new_rental_tax
            
            st.warning(f"**Option 2: Max RRSP Offset**\n\nContribute your max **${rrsp_room:,.2f}**.\n\n* **Tax Saved:** ${tax_saved:,.2f}\n* **New Bill:** ${new_rental_tax:,.2f}")
        else:
            st.error("**Option 2: RRSP Offset**\n\nYou need available RRSP room to use this strategy.")

    with colC:
        float_interest = rental_tax_owed * 0.04 * 0.5 
        st.success(f"**Option 3: The Tax Float**\n\nPark your **${rental_tax_owed:,.2f}** tax bill in a 4% HISA.\n\n**Estimated Free Interest: ${float_interest:,.2f}**")

    st.markdown("> **Pro-Tip:** If your personal income will be much higher next year, consider delaying major repairs until January 1st to deduct them against a higher tax bracket!")

elif user_net_rental_income < 0:
    st.info(f"**Your Share of Net Taxable Rental Income ({ownership_pct}%):** ${user_net_rental_income:,.2f}")
    st.success("You operated at a tax loss. You may be able to deduct this loss against your base income to lower your overall tax bill!")
else:
    st.info(f"**Your Share of Net Taxable Rental Income ({ownership_pct}%):** $0.00")
    st.success("You broke exactly even. No additional rental tax owed!")