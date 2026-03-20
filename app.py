import streamlit as st
from PIL import Image
import google.generativeai as genai
import json

# --- Session State Initialization (The App's Memory) ---
if "repairs_val" not in st.session_state: st.session_state.repairs_val = 0.0
if "utilities_val" not in st.session_state: st.session_state.utilities_val = 0.0
if "prof_fees_val" not in st.session_state: st.session_state.prof_fees_val = 0.0
if "appliances_val" not in st.session_state: st.session_state.appliances_val = 0.0
if "prop_tax_val" not in st.session_state: st.session_state.prop_tax_val = 0.0
if "mortgage_val" not in st.session_state: st.session_state.mortgage_val = 0.0 # THE FIX

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
        st.write("Upload a receipt or a PDF statement. The AI will extract the total and categorize it.")
        
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
                    
                    CRITICAL RULES FOR MORTGAGE STATEMENTS:
                    - I ONLY want the "Interest" paid. Do NOT extract the "Principal" or "Total Payment".
                    
                    Keys required:
                    - "vendor": The name of the bank or store.
                    - "total": The specific deductible amount (number only, no $).
                    - "category": Categorize into EXACTLY one of these: [Mortgage Interest, Repairs & Maintenance, Utilities, Professional Fees, Appliances (Class 8), Property Taxes, Uncategorized]
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

                        # THE PIPELINE: Now includes Mortgage Interest!
                        if category == "Repairs & Maintenance":
                            st.session_state.repairs_val += extracted_total
                        elif category == "Utilities":
                            st.session_state.utilities_val += extracted_total
                        elif category == "Professional Fees":
                            st.session_state.prof_fees_val += extracted_total
                        elif category == "Appliances (Class 8)":
                            st.session_state.appliances_val += extracted_total
                        elif category == "Property Taxes":
                            st.session_state.prop_tax_val += extracted_total
                        elif category == "Mortgage Interest":
                            st.session_state.mortgage_val += extracted_total # THE FIX
                            
                    except Exception as e:
                        st.error(f"Could not parse the document clearly. Please enter manually. Error: {e}")
else:
    st.error("AI functionality is disabled. Please check your API key in Streamlit Secrets.")

st.markdown("---")

# --- Manual Inputs ---
st.header("1. Your Base Income")
base_income = st.number_input("Gross Income", min_value=0.0, step=1000.0)

st.header("2. Rental Income")
col1, col2 = st.columns(2)
with col1:
    gross_rent = st.number_input("Total Gross Rent Collected", min_value=0.0, step=100.0)
with col2:
    other_income = st.number_input("Other Income (Parking, Laundry, etc.)", min_value=0.0, step=50.0)

total_income = gross_rent + other_income

st.header("3. Deductible Expenses")
exp_col1, exp_col2, exp_col3 = st.columns(3)

with exp_col1:
    property_tax = st.number_input("Property Taxes", min_value=0.0, step=100.0, key="prop_tax_val")
    # THE FIX: Added the key="mortgage_val" here so it knows where to receive the memory data
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

# --- Calculations ---
total_deductions = current_expenses + cca_deduction
net_rental_income = total_income - total_deductions
total_taxable_income = base_income + net_rental_income

# Tax Math
total_base_tax = calculate_tax(base_income, FED_BRACKETS) + calculate_tax(base_income, ON_BRACKETS)
total_combined_tax = calculate_tax(total_taxable_income, FED_BRACKETS) + calculate_tax(total_taxable_income, ON_BRACKETS)
rental_tax_owed = total_combined_tax - total_base_tax

st.markdown("---")

# --- Results ---
st.header("📊 Your Year-End Tax Estimate")

if net_rental_income > 0:
    st.success(f"**Net Taxable Rental Income:** ${net_rental_income:,.2f}")
    st.error(f"**Estimated Tax Owed on Rental:** ${rental_tax_owed:,.2f}")
    set_aside = (rental_tax_owed / net_rental_income) * 100 if net_rental_income > 0 else 0
    st.info(f"💡 **Actionable Takeaway:** Set aside **{set_aside:.1f}%** of your net rental profits.")
else:
    st.info(f"**Net Taxable Rental Income:** ${net_rental_income:,.2f}")
    st.success("You operated at a tax loss or broke even. No additional rental tax owed!")