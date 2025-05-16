import streamlit as st
import os
import base64
import dotenv
dotenv.load_dotenv()
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain_core.output_parsers import StrOutputParser

# from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.runnables import RunnableLambda

from langchain.agents import (
    create_openai_functions_agent,
    Tool,
    AgentExecutor,
)
from langchain import hub
# from langchain_intro.tools import get_current_wait_time
from docx import Document
import uuid

chat_model = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.9)

st.set_page_config(
    page_title="Omaha Zoo Letter Generator",       # Title shown in browser tab
    page_icon="🦒",                       # Emoji or local image
    layout="wide",                        # Optional: layout mode
    initial_sidebar_state="expanded"      # Optional: sidebar behavior
)

def read_docx(file_path):
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    return text

bd_list = [
    "templates/CCS1/"
]

def get_relevant_templates(selected_type, selected_style, base_directory=bd_list[0]):
    """
    Retrieves multiple relevant templates from the correct subfolder based on letter type and style.
    """
    subdirectory = selected_style.lower()  # Convert to lowercase 
    folder_name = selected_type.lower().replace(" ", "_")  # Convert to lowercase with underscores
    folder_path = os.path.join(base_directory, subdirectory, folder_name)
    print(folder_path)
    
    if not os.path.exists(folder_path):
        return f"No folder found for '{selected_type}' in '{base_directory}'."

    relevant_templates = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".docx") and not filename.startswith("~$"):
            file_path = os.path.join(folder_path, filename)
            template_text = read_docx(file_path)
            relevant_templates.append(template_text)

    return "\n\n---\n\n".join(relevant_templates) if relevant_templates else "No relevant templates found."


stop_words = [
    "Oh behalf of",
    "Critters",
    "Cages",
    "Enclosure",
    "Captive",
]

stop_context = ['Do not use too many We words in the letter']

# individual_details = "Account Name: Account ID : 0015f00000WBFIJ + Opportunity ID : 0065f00000AK0hk + Account Name: Account Name : Henkenius Household \
# + Remaining Balance : 0 + Amount : 2500 + Opportunity Record Type : Donation + Type : Cash + Close Date : 11/25/2008 \
# + General Accounting Unit: General Accounting Unit Name : Adopt 2008 + Parent Campaign : Adopt + Description : adopt an animal \
# Billing Street : 10340 North 84th St + Billing City : Omaha + Billing State/Province : NE + Billing Zip/Postal Code : 68122-2216 \
# + Board Member Society : FALSE + Board Member Foundation : FALSE + Do Not Solicit for Patron : FALSE + Do Not Solicit : FALSE \
# Last Activity : 10/3/2024 + Assigned Solicitor : Tina Cherica + Master Plan Donor : TRUE + Major Donor : FALSE + Lifetime Member : FALSE \
# + Number of Memberships : 0 + Total Membership Amount : 0 + Total Gifts : 64688639.89 + First Gift Amount : 100000 \
# + First Gift Date : 12/27/1990 + Last Gift Date : 6/6/2024 + Last Gift Amount : 26000 + Largest Gift : 50000000 \
# + Largest Gift Date : 12/19/2014 + Total Number of Gifts : 52 + Total Gifts This Year : 0"

individual_details = "<<Donor Name>> , <<Donor Address - XX, YY, ZZ>>, <<Donor Phone>>"

donation_details = "Last Activity : DD/MM/YYYY + Assigned Solicitor : Tina Cherica + Master Plan Donor : TRUE + Major Donor : FALSE + Lifetime Member : FALSE \
+ Number of Memberships : 0 + Total Membership Amount : 0 + Total Gifts : more than $$$$$$ + First Gift Amount : $$$$$ \
+ First Gift Date : DD/MM/YYYY + Last Gift Date : DD/MM/YYYY + Last Gift Amount : $$$$ + Largest Gift : $$$$$ \
+ Largest Gift Date : DD/MM/YYYY + Total Number of Gifts : 52 + Total Gifts This Year : 0"

context = "The Omaha Henry Doorly Zoo and Aquarium is a world-renowned zoological park dedicated \
to wildlife conservation, education, and immersive animal experiences. Located in Omaha, Nebraska, \
the zoo is home to over 17,000 animals from more than 900 species, housed in some of the most innovative \
and expansive exhibits in the world. It boasts attractions like the Desert Dome, the world's largest indoor desert, \
the Lied Jungle, one of the largest indoor rainforests, and the Suzanne and Walter Scott Aquarium, \
which features a stunning walk-through shark tunnel. Beyond providing an unforgettable visitor experience, \
the zoo is deeply committed to global conservation efforts, partnering with organizations worldwide to \
protect endangered species, conduct research, and promote sustainable habitats. It also plays a key role \
in education and outreach, offering programs for schools, families, and researchers to inspire future generations \
about wildlife and environmental stewardship. Through its combination of scientific research, \
conservation initiatives, and engaging exhibits, Omaha Zoo continues to be a leader in the zoological and conservation community."

output_parser = StrOutputParser()

letter_prompt_template = PromptTemplate(
    input_variables=[
        "letter_type", 
        "letter_context",
        "selected_style",
        "context", 
        "individual_details", 
        "template_letter", 
        "donation_details", 
        "extra_details", 
        "user_query",
        "variation_id"
    ],
    template="""Your job is to create a customized {letter_type} letter for donors contributing to the Omaha Zoo and each letter generated should be unique and different. You are allowed to 
    be creative with the language and tone of the letter, but not make up facts or information.
    
### Instructions:
- Use the details below to personalize the letter.
- If the user query provides specific requests, follow them closely.

#### **Provided Details**
- **Context**: {context}
- **Event Details**: If {letter_context}, add a sentence about donation to the '{letter_context} event' in the letter. 
- **Individual Details**: {individual_details}
- **Donation Details**: {donation_details}
- **Additional Information**: {extra_details}
- **User Query**: If {user_query}, then make sure you definitely add a sentence about these details in the letter
- **Templates to Guide Tone and Style**: {template_letter}

### **Task:**
- Follow the user's query when generating the letter.
- Use all relevant information to make the letter personal and engaging.
- If {donation_details} contains monetary amounts and donation history, summarize the impact in a couple sentences and add to the letter.
- If {extra_details} contains memorial or honor words in the letter, include it as a sentence of gratitude. If {extra_details} contains 'membership', add a sentence about how greatful Omaha Zoo
is for their long term membership support. If {extra_details} contains a season, mention that season in a sentence in the letter.
- Maintain a {selected_style} tone of the letter.

#### **Variation ID**: If {variation_id}, give this HIGHEST priority when generating the letter, make variations to template language when this value is given.

Now generate a professional {letter_type} letter for a donor of the Omaha Zoo.
"""
)


def prepare_letter_inputs_chain(input_dict):
    """
    Function wrapped inside RunnableLambda to dynamically generate inputs for LangChain.
    """
    return {
        "letter_type": selected_letter_type,
        "letter_context": letter_context,
        "selected_style":selected_style,
        "context": context,
        "variation_id": variation_id,
        "individual_details": individual_details,
        "template_letter": selected_templates,
        "user_query": user_query.strip() if user_query else "No additional details provided.",
        "donation_details": donation_details if add_donation_details else "Not applicable",
        "extra_details": " ".join([
            "This donation is a memorial gift." if specify_memorial_gift else "",
            "This donation is in honor of someone." if in_honor_of_gift else "",
            "We are very grateful for your valuable support as a member of our Zoo" if specify_membership else "",
            "Your thoughtful in-kind gift helps us continue our mission and brings real value to our daily operations and the care we provide." if in_kind_gift else "",
            "Summer brings the zoo to life with longer days, lively animal activity, and joyful visits from families and children" if summer else "",
            "Spring awakens the zoo with blooming gardens, playful newborn animals, and a renewed sense of energy throughout the park" if spring else "",
            "Fall transforms the zoo with crisp air, colorful foliage, and animals preparing for the changing season." if fall else "",
            "Winter brings a quiet beauty to the zoo, with peaceful landscapes and animals adapting to the colder months in unique and fascinating ways."
        ]).strip() or "No additional information."
    }

# --- STREAMLIT APP ------------------------------------------------

# st.set_page_config(layout="wide")

st.markdown("""
<style>
/* Make the sidebar wider */
section[data-testid="stSidebar"] {
    width: 450px !important;  /* Increase or decrease width here */
}

section[data-testid="stSidebar"] > div:first-child {
    width: 450px !important;
    padding-right: 1rem;
}
</style>
""", unsafe_allow_html=True)

# Custom CSS for background image ================
# st.markdown("""
# <style>
# [data-testid="stAppViewContainer"] > .main {
#     background: url("your_image.jpg");
#     background-size: cover;
#     background-position: center;
#     background-repeat: no-repeat;
#     padding: 2rem;
#     border-radius: 10px;
#     color: white; /* if image is dark */
# }
# </style>
# """, unsafe_allow_html=True)


# Function to load and encode the local background image
def get_base64_of_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Load the image (replace 'zoo_background.jpg' with your actual file)
image_path = "ccs_images/bgd4.jpeg"  # Make sure this file is in the same folder as your script
base64_image = get_base64_of_image(image_path)

page_bg_img = f"""
<style>
/* Main app container with giraffe background and subtle overlay */
[data-testid="stAppViewContainer"] {{
    # background: 
    #     linear-gradient(rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.35)),
    #     url("data:image/jpg;base64,{base64_image}");
    background-size: cover;
    background-position: center top;
    background-attachment: fixed;
    background-repeat: no-repeat;
    background-blend-mode: lighten;
    backdrop-filter: blur(2px); /* light blur, adjust as needed */
}}

/* Make sure the main content is top-aligned */
.main {{
    padding-top: -1rem !important;
    margin-top: 0 !important;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}}

/* Improve title visibility */
h1 {{
    color: #1E5631 !important;  /* Deep green for contrast */
    text-shadow: 1px 1px 2px rgba(255,255,255,0.6);  /* Light halo for readability */
}}
</style>
"""

# /* Adjust text color for better visibility */
# h1, h2, h3, h4, h5, h6, p {{
#     color: white !important;
# }}

# # /* Make the text box backgrounds semi-transparent */
# # [data-testid="stTextArea"] textarea {{
# #     background-color: rgba(255, 255, 255, 0.8) !important;
# # }}

# /* Style buttons */
# div.stButton > button {{
#     background-color: #1E5631;
#     color: white;
#     border-radius: 10px;
#     font-size: 16px;
# }}
# div.stButton > button:hover {{
#     background-color: #145214;
# }}
# </style>
# """


# Updated full-width CSS to remove padding/margin
# full_width_css = """
# <style>
# /* Remove padding from main container */
# main.st-emotion-cache-uf99v8 {{
#     padding-left: 1rem !important;
#     padding-right: 1rem !important;
#     max-width: 100% !important;
# }}

# /* Remove padding from columns */
# [data-testid="column"] {{
#     padding-left: 0.5rem;
#     padding-right: 0.5rem;
#     flex: 1 1 0%;
#     min-width: 0;
# }}

# /* Optional: wider text area */
# textarea, .stTextArea textarea {{
#     width: 100% !important;
#     min-height: 300px;
# }}
# </style>
# """

# # Apply the custom CSS
st.markdown(page_bg_img, unsafe_allow_html=True)
# st.markdown(full_width_css, unsafe_allow_html=True)

st.markdown("""
<style>
/* Target buttons inside the sidebar */
section[data-testid="stSidebar"] button {
    background-color: #1E5631 !important;
    color: white !important;
    border-radius: 8px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    border: none !important;
    padding: 0.5rem 1.2rem !important;
    margin-top: 1rem !important;
}

/* Hover effect */
section[data-testid="stSidebar"] button:hover {
    background-color: #145214 !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)


# Main Streamlit app ==============================================

# ---------- Session State Setup ----------
if "letters" not in st.session_state:
    st.session_state.letters = []
if "current_index" not in st.session_state:
    st.session_state.current_index = -1

# Sidebar Inputs
st.sidebar.title("Letter Generator Controls")

st.sidebar.subheader("Step 1: Select Letter Type (Only One)")
letter_options = {
    "Thank You": st.sidebar.checkbox("Thank You"),
    "Acknowledgement": st.sidebar.checkbox("Acknowledgement"),
    "Solicitation": st.sidebar.checkbox("Solicitation"),
    "Cultivation": st.sidebar.checkbox("Cultivation"),
    "Event Sponsorship": st.sidebar.checkbox("Event Sponsorship"),
}
selected_letter_type = None
checked_options = [key for key, value in letter_options.items() if value]
if len(checked_options) > 1:
    st.sidebar.warning("Please select only one letter type at a time.")
elif len(checked_options) == 1:
    selected_letter_type = checked_options[0]


st.sidebar.subheader("Step 2: Select Letter Tone and Style")
style_options = {
    "formal" : st.sidebar.checkbox("Professional"),
    "informal" : st.sidebar.checkbox("Informal"),
}
selected_style = None
checked_style_options = [key for key, value in style_options.items() if value]
if len(checked_style_options) > 1:
    st.sidebar.warning("Please select only one style.")
elif len(checked_style_options) == 1:
    selected_style = checked_style_options[0]

# st.sidebar.subheader("Step 3: Select Opportunity Type")
# opp_donation = st.sidebar.checkbox("Donation")
# opp_membership = st.sidebar.checkbox("Membership")
# opp_inkind = st.sidebar.checkbox("In-kind")
# opp_pledge = st.sidebar.checkbox("Pledge")

st.sidebar.subheader("Step 3: Add Event Details (optional)")
letter_context = st.sidebar.selectbox(
    "Choose an event (GAU categories - most to least frequent):",
    ['None','Patron', 'Adopt', 'General Annual', 'Hubbard Orangutan Forest', 'Zoofari',
     'Emergency Zoo Funding', 'Zoo Hospital', 'Plaques', 'Memorials', 'HDZ Society',
     'Elephamily', 'Legacy Fund', 'Earth & Wine', 'Zoo LaLa', 'Madagascar',
     'Desert Dome Plaza Update', 'Gift-in-Kind', 'Emergency Fund', 'Zoo Hospital Capital',
     'Memorial', 'Other']
)

st.sidebar.subheader("Step 4: Customize Letter Content")
add_donation_details = st.sidebar.checkbox("Add donation details")
specify_membership = st.sidebar.checkbox("Specify membership")
specify_memorial_gift = st.sidebar.checkbox("Specify memorial gift")
in_honor_of_gift = st.sidebar.checkbox("Specify in-honor-of gift")
in_kind_gift = st.sidebar.checkbox("Specify in-kind gift")
in_pledge = st.sidebar.checkbox("Specify pledge")

st.sidebar.subheader("Step 5: Select Season")
spring = st.sidebar.checkbox("Spring")
summer = st.sidebar.checkbox("Summer")
fall = st.sidebar.checkbox("Fall")
winter = st.sidebar.checkbox("Winter")

selected_seasons = []
if spring:
    selected_seasons.append("spring")
if summer:
    selected_seasons.append("summer")
if fall:
    selected_seasons.append("fall")
if winter:
    selected_seasons.append("winter")


user_query = st.sidebar.text_area("Enter any additional details for further customization:", "Can you mention that this gift is in memory of their grandmother, who loved the butterfly garden?")
generate = st.sidebar.button("Generate Letter")

st.markdown("""
<style>
/* Style for the download button */
div.stDownloadButton > button {
    background-color: #1E5631;
    color: white;
    border-radius: 8px;
    font-size: 16px;
    padding: 0.5rem 1.2rem;
    font-weight: 600;
    border: none;
}

div.stDownloadButton > button:hover {
    background-color: #145214; /* darker green on hover */
    color: white;
}
</style>
""", unsafe_allow_html=True)


# Main page ----------------------------------------

# st.title("Omaha Zoo - Automated Letter Generator")
st.markdown("""
    <style>
    .centered-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E5631; /* Your theme color */
        margin-top: 1rem;
        margin-bottom: 2rem;
    }
    </style>
    <h1 class="centered-title">Omaha Zoo - Automated Letter Generator</h1>
""", unsafe_allow_html=True)


# ----------------------------------------
# Generate and Manage Letter History
# ----------------------------------------

# Handle initial generation from sidebar
if generate:
    if not selected_letter_type:
        st.warning("Please select a letter type before generating a letter.")
    elif not selected_style:
        st.warning("Please select a letter style.")
    else:
        selected_templates = get_relevant_templates(selected_letter_type, selected_style, base_directory=bd_list[0])
        variation_id = str(uuid.uuid4())  # or use datetime for time-based variety
        print(variation_id)
        letter_inputs_runnable = RunnableLambda(prepare_letter_inputs_chain)
        letter_chain = letter_inputs_runnable | letter_prompt_template | chat_model
        letter = letter_chain.invoke({})
        letter_text = letter.content if hasattr(letter, "content") else str(letter).strip()

        st.session_state.letters.append({
            "letter": letter_text,
            "templates": selected_templates,
            "type": selected_letter_type
        })
        st.session_state.current_index = len(st.session_state.letters) - 1

# ----------------------------------------
# Main Content Area – Letter Display + Controls
# ----------------------------------------

# counter = 1

# if st.session_state.current_index >= 0 and st.session_state.letters:
#     current = st.session_state.letters[st.session_state.current_index]

#     # st.subheader(f"📑 Retrieved Templates for {current['type']}:")
#     # st.text_area("Templates Content", current["templates"], height=300)

#     st.subheader(f"✉️ Generated {current['type']} Letter:")
#     st.text_area("Letter Content", current["letter"], height=500)

#     # 🔘 Action Buttons: Refresh, Prev, Next, Clear
#     col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
#     with col1:
#         if st.button("⬅️ Previous") and st.session_state.current_index > 0:
#             st.session_state.current_index -= 1

#     with col2:
#         if st.button("🔄 Refresh Letter"):
#             selected_templates = get_relevant_templates(current["type"], selected_style,base_directory=bd_list[counter])

#             # Add a UUID or timestamp to inject variation
#             variation_id = str(uuid.uuid4())  # or use datetime for time-based variety
#             print(variation_id)
#             # Prepare the letter generation chain
#             letter_inputs_runnable = RunnableLambda(prepare_letter_inputs_chain)
#             letter_chain = letter_inputs_runnable | letter_prompt_template | chat_model

#             # Add random seed to prompt inputs for uniqueness
#             letter = letter_chain.invoke({
#                 "variation_id": variation_id,  # This key must be referenced in your prompt template
#                 "type": current["type"],
#                 "style": selected_style
#             })

#             # Extract the letter content
#             letter_text = letter.content if hasattr(letter, "content") else str(letter).strip()

#             # Save to session
#             st.session_state.letters.append({
#                 "letter": letter_text,
#                 "templates": selected_templates,
#                 "type": current["type"]
#             })
#             st.session_state.current_index = len(st.session_state.letters) - 1

#             counter = counter + 1 

#     with col3:
#         if st.button("Next ➡️") and st.session_state.current_index < len(st.session_state.letters) - 1:
#             st.session_state.current_index += 1

#     with col4:
#         if st.button("🧹 Clear History"):
#             st.session_state.letters.clear()
#             st.session_state.current_index = -1
#             st.rerun()

#     # 🗂️ Letter Selector + Download
#     st.markdown("### 📄 Download a Letter from History")
#     options = [f"{i + 1}: {l['type']}" for i, l in enumerate(st.session_state.letters)]
#     selected_download = st.selectbox("Choose a letter to download:", options, index=st.session_state.current_index)

#     selected_letter_index = int(selected_download.split(":")[0]) - 1
#     selected_letter = st.session_state.letters[selected_letter_index]
#     file_name = selected_letter["type"].replace(" ", "_").lower() + ".txt"

#     st.download_button("📄 Download Selected Letter", selected_letter["letter"], file_name=file_name)


import uuid
from datetime import datetime

# Example: define your user choices somewhere above this block
# selected_season = st.selectbox(...) or st.radio(...) or from session state
# selected_style = st.radio(...) or from session state

counter = 1

if st.session_state.current_index >= 0 and st.session_state.letters:
    current = st.session_state.letters[st.session_state.current_index]

    st.subheader(f"✉️ Generated {current['type']} Letter:")
    st.text_area("Letter Content", current["letter"], height=500)

    # 🔘 Action Buttons: Refresh, Prev, Next, Clear
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        if st.button("⬅️ Previous") and st.session_state.current_index > 0:
            st.session_state.current_index -= 1

    with col2:
        if st.button("🔄 Refresh Letter"):
            selected_templates = get_relevant_templates(
                current["type"], selected_style, base_directory=bd_list[counter]
            )

            variation_id = str(uuid.uuid4())  # or datetime.now().isoformat()
            letter_inputs_runnable = RunnableLambda(prepare_letter_inputs_chain)
            letter_chain = letter_inputs_runnable | letter_prompt_template | chat_model

            letter = letter_chain.invoke({
                "variation_id": variation_id,
                "type": current["type"],
                "style": selected_style,
                "season": selected_seasons
            })

            letter_text = letter.content if hasattr(letter, "content") else str(letter).strip()

            # Save the generated letter with additional metadata
            st.session_state.letters.append({
                "letter": letter_text,
                "templates": selected_templates,
                "type": current["type"],
                "style": selected_style,
                "season": selected_seasons,
                "timestamp": datetime.now()
            })

            st.session_state.current_index = len(st.session_state.letters) - 1
            counter += 1

    with col3:
        if st.button("Next ➡️") and st.session_state.current_index < len(st.session_state.letters) - 1:
            st.session_state.current_index += 1

    with col4:
        if st.button("🧹 Clear History"):
            st.session_state.letters.clear()
            st.session_state.current_index = -1
            st.rerun()

    # 🗂️ Letter Selector + Download
    st.markdown("### 📄 Download a Letter from History")

    # # Show options with all metadata
    # options = [
    #     f"{i + 1}: {l['type']} ({l.get('season', '')}, {l.get('style', '')})".strip(", ()")
    #     for i, l in enumerate(st.session_state.letters)
    # ]
    # selected_download = st.selectbox("Choose a letter to download:", options, index=st.session_state.current_index)

    # selected_letter_index = int(selected_download.split(":")[0]) - 1
    # selected_letter = st.session_state.letters[selected_letter_index]

    # # Build filename with type, season, and style
    # parts = [
    # selected_letter.get("type", "").replace(" ", "_").lower(),
    # "_".join(selected_letter.get("season", [])).replace(" ", "_").lower(),
    # selected_letter.get("style", "").replace(" ", "_").lower(),
    # "_".join(selected_letter.get("customizations", [])).replace(" ", "_").lower()
    # ]
    # file_name = "_".join([p for p in parts if p]) + ".txt"

    # st.download_button("📄 Download Selected Letter", selected_letter["letter"], file_name=file_name)

    # Generate nice normalized parts
    def normalize(val):
        if isinstance(val, list):
            return "_".join([str(v).replace(" ", "_").lower() for v in val])
        return str(val).replace(" ", "_").lower()

    # 🗂️ Dropdown Display Options
    options = [
        f"{i + 1}: {normalize(l.get('type', ''))}_{normalize(l.get('season', []))}_{normalize(l.get('style', ''))}_{i + 1}"
        for i, l in enumerate(st.session_state.letters)
    ]

    selected_download = st.selectbox("Choose a letter to download:", options, index=st.session_state.current_index)

    # Extract index from selection
    selected_letter_index = int(selected_download.split(":")[0]) - 1
    selected_letter = st.session_state.letters[selected_letter_index]

    # 📄 Filename
    file_name = f"{normalize(selected_letter.get('type'))}_{normalize(selected_letter.get('season', []))}_{normalize(selected_letter.get('style'))}_{selected_letter_index + 1}.txt"

    # Download button
    st.download_button("📄 Download Selected Letter", selected_letter["letter"], file_name=file_name)



# Powered BY + LOGO

logo_base64 = get_base64_of_image("ccs_images/logo2.png")

footer_html = f"""
<style>
.footer-container {{
    text-align: center;
    margin-top: 3rem;
    color: #555;
    font-size: 0.9rem;
}}

.footer-logo {{
    margin-top: 0.5rem;
}}

.footer-logo img {{
    width: 100px;
    border-radius: 2px;
    box-shadow: 0 0 0px rgba(0,0,0,0);
}}
</style>

<div class="footer-container">
    &copy; {2025} Powered by <strong>CCS Fundraising</strong>
    <div class="footer-logo">
        <img src="data:image/jpg;base64,{logo_base64}" alt="Logo">
    </div>
</div>
"""

st.markdown(footer_html, unsafe_allow_html=True)


# Old style ============================================

# st.title("Omaha Zoo - Automated Letter Generator")

# # Step 1: User selects the type of letter via checkboxes
# st.subheader("Step 1: Select a Letter Type (Only One)")

# letter_options = {
#     "Thank You": st.checkbox("Thank You"),
#     "Acknowledgement": st.checkbox("Acknowledgement"),
#     "Solicitation": st.checkbox("Solicitation"),
#     "Cultivation": st.checkbox("Cultivation"),
#     "Event Sponsorship": st.checkbox("Event Sponsorship"),
# }

# # Ensure only one checkbox is selected
# selected_letter_type = None
# checked_options = [key for key, value in letter_options.items() if value]

# if len(checked_options) > 1:
#     st.warning("Please select only one letter type at a time.")
# elif len(checked_options) == 1:
#     selected_letter_type = checked_options[0]

# # Step 2a: Letter tone and style
# st.subheader("Step 2: Letter Tone and Style")
# # New checkboxes
# style_professional = st.checkbox("Professional")
# style_playful = st.checkbox("Informal")

# # Step 2b: Letter tone and style
# st.subheader("Step 3: Letter Context (General Accounting Unit)")

# # Dropdown menu
# letter_context = st.selectbox(
#     "Choose the template context:",
#     ['Patron',
#     'Adopt',
#     'General Annual',
#     'Hubbard Orangutan Forest',
#     'Zoofari',
#     'Emergency Zoo Funding',
#     'Zoo Hospital',
#     'Plaques',
#     'Memorials',
#     'HDZ Society',
#     'Elephamily',
#     'Legacy Fund',
#     'Earth & Wine',
#     'Zoo LaLa',
#     'Madagascar',
#     'Desert Dome Plaza Update',
#     'Gift-in-Kind',
#     'Emergency Fund',
#     'Zoo Hospital Capital',
#     'Memorial',
#     'Other']
# )

# st.write(f"You selected: {letter_context}")

# # Step 2a: Capture user input for customization
# st.subheader("Step 3: Further Customize Your Letter")

# # New checkbox for adding donation details
# add_donation_details = st.checkbox("Add donation details")
# specify_memorial_gift = st.checkbox("Specify memorial gift")
# in_honor_of_gift = st.checkbox("Specify in-honor-of gift")

# # Step 2b: Capture user input for customization
# st.subheader("Step 4: Opportunity Record Type")

# # New checkbox for adding donation details
# opp_donation = st.checkbox("Donation")
# opp_membership = st.checkbox("Membership")
# opp_inkind = st.checkbox("In-kind")
# opp_pledge = st.checkbox("Pledge")

# question = st.text_area("Enter any additional details or queries:", "Can you generate a letter?")

# # Step 3: Generate the letter based on the selected type and user input

# # Run button
# if st.button("Generate Letter"):
#     if not selected_letter_type:
#         st.warning("Please select a letter type before generating a letter.")
#     else:
#         # Retrieve multiple relevant templates from the selected category
#         selected_templates = get_relevant_templates(selected_letter_type)

#         # Display retrieved templates (for debugging)
#         st.subheader(f"Retrieved Templates for {selected_letter_type}:")
#         st.text_area("Templates Content:", selected_templates, height=300)

#         # Create a RunnableLambda to dynamically process user inputs
#         letter_inputs_runnable = RunnableLambda(prepare_letter_inputs_chain)

#         # Generate letter using the structured prompt
#         # letter_chain = (
#         #     {
#         #         "letter_type": RunnableLambda(lambda _: selected_letter_type),
#         #         "context": RunnableLambda(lambda _: context),
#         #         "individual_details": RunnableLambda(lambda _: individual_details),
#         #         "donation_details": RunnableLambda(lambda _: donation_details),
#         #         "template_letter": RunnableLambda(lambda _: selected_templates),
#         #         "add_donation_details": RunnableLambda(lambda _: add_donation_details),
#         #         "specify_memorial_gift": RunnableLambda(lambda _: specify_memorial_gift),
#         #         "in_honor_of_gift": RunnableLambda(lambda _: in_honor_of_gift)
#         #     }
#         #     | letter_prompt_template
#         #     | chat_model
#         # )

#         # Define the LangChain pipeline
#         letter_chain = (letter_inputs_runnable  # Generates inputs dynamically
#                         | letter_prompt_template  # Uses the structured prompt template
#                         | chat_model  # LLM to generate the letter
#         )

#         letter = letter_chain.invoke({})
#         letter_text = letter.content if hasattr(letter, "content") else str(letter).strip()

#         # Display generated letter
#         st.subheader(f"Generated {selected_letter_type} Letter:")
#         st.text_area("Letter Content:", letter_text, height=500)

#         # Provide a download option
#         file_name = selected_letter_type.replace(" ", "_").lower() + ".txt"
#         st.download_button("Download Letter", letter_text, file_name=file_name)
    

## Left Right style ===========================================

# st.title("Omaha Zoo - Automated Letter Generator")

# # Create two columns: inputs on the left, outputs on the right
# left_col, right_col = st.columns([2, 3])  # Adjust the width ratio as needed

# with left_col:
#     st.subheader("Step 1: Select a Letter Type (Only One)")
#     letter_options = {
#         "Thank You": st.checkbox("Thank You"),
#         "Acknowledgement": st.checkbox("Acknowledgement"),
#         "Solicitation": st.checkbox("Solicitation"),
#         "Cultivation": st.checkbox("Cultivation"),
#         "Event Sponsorship": st.checkbox("Event Sponsorship"),
#     }

#     selected_letter_type = None
#     checked_options = [key for key, value in letter_options.items() if value]
#     if len(checked_options) > 1:
#         st.warning("Please select only one letter type at a time.")
#     elif len(checked_options) == 1:
#         selected_letter_type = checked_options[0]

#     st.subheader("Step 2: Letter Tone and Style")
#     style_professional = st.checkbox("Professional")
#     style_playful = st.checkbox("Informal")

#     st.subheader("Step 3: Letter Context (General Accounting Unit)")
#     letter_context = st.selectbox(
#         "Choose the template context:",
#         ['Patron', 'Adopt', 'General Annual', 'Hubbard Orangutan Forest', 'Zoofari',
#          'Emergency Zoo Funding', 'Zoo Hospital', 'Plaques', 'Memorials', 'HDZ Society',
#          'Elephamily', 'Legacy Fund', 'Earth & Wine', 'Zoo LaLa', 'Madagascar',
#          'Desert Dome Plaza Update', 'Gift-in-Kind', 'Emergency Fund', 'Zoo Hospital Capital',
#          'Memorial', 'Other']
#     )

#     st.subheader("Step 4: Further Customize Your Letter")
#     add_donation_details = st.checkbox("Add donation details")
#     specify_memorial_gift = st.checkbox("Specify memorial gift")
#     in_honor_of_gift = st.checkbox("Specify in-honor-of gift")

#     st.subheader("Step 5: Opportunity Record Type")
#     opp_donation = st.checkbox("Donation")
#     opp_membership = st.checkbox("Membership")
#     opp_inkind = st.checkbox("In-kind")
#     opp_pledge = st.checkbox("Pledge")

#     question = st.text_area("Enter any additional details or queries:", "Can you generate a letter?")

#     if st.button("Generate Letter"):
#         if not selected_letter_type:
#             st.warning("Please select a letter type before generating a letter.")
#         else:
#             selected_templates = get_relevant_templates(selected_letter_type)

#             letter_inputs_runnable = RunnableLambda(prepare_letter_inputs_chain)
#             letter_chain = letter_inputs_runnable | letter_prompt_template | chat_model
#             letter = letter_chain.invoke({})
#             letter_text = letter.content if hasattr(letter, "content") else str(letter).strip()

#             with right_col:
#                 st.subheader(f"Retrieved Templates for {selected_letter_type}:")
#                 st.text_area("Templates Content:", selected_templates, height=300)

#                 st.subheader(f"Generated {selected_letter_type} Letter:")
#                 st.text_area("Letter Content:", letter_text, height=500)

#                 file_name = selected_letter_type.replace(" ", "_").lower() + ".txt"
#                 st.download_button("Download Letter", letter_text, file_name=file_name)
