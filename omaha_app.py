import streamlit as st
import os
import base64
import dotenv
import uuid
from datetime import datetime
from docx import Document
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

# Load environment variables
dotenv.load_dotenv()

# Initialize LLM
chat_model = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0.9)

# Set Streamlit page config
st.set_page_config(page_title="Omaha Zoo Letter Generator", page_icon="🦒", layout="wide", initial_sidebar_state="expanded")

# Read .docx file content
def read_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

# Fixed base directory
base_directory = "/Users/yashakaushal/Documents/app_testing/omaha_test/data/templates/CCS1/"


# Load template from fixed directory
def get_relevant_templates(selected_type, selected_style):
    subdirectory = selected_style.lower()
    folder_name = selected_type.lower().replace(" ", "_")
    folder_path = os.path.join(base_directory, subdirectory, folder_name)
    if not os.path.exists(folder_path):
        return "No folder found."
    relevant_templates = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".docx") and not filename.startswith("~$"):
            file_path = os.path.join(folder_path, filename)
            relevant_templates.append(read_docx(file_path))
    return "\n\n---\n\n".join(relevant_templates) if relevant_templates else "No templates found."

# Prompt template
letter_prompt_template = PromptTemplate(
    input_variables=["letter_type", "letter_context", "selected_style", "context", "individual_details", "template_letter", "donation_details", "extra_details", "user_query", "variation_id"],
    template="""Your job is to create a customized {letter_type} letter for donors contributing to the Omaha Zoo and each letter generated should be unique and different...\n[TRUNCATED for brevity: include original prompt here]
"""
)

individual_details = "<<Donor Name>> , <<Donor Address - XX, YY, ZZ>>, <<Donor Phone>>"

donation_details = "Last Activity : DD/MM/YYYY + Number of Memberships : 0 + Total Membership Amount : 0 + Total Gifts : more than <<Amount>> + First Gift Amount : <<Amount>> \
+ First Gift Date : DD/MM/YYYY + Last Gift Amount : <<Amount>> + Largest Gift : <<Amount>> \
Total Number of Gifts : <<Total Gifts>>"

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
    template="""Your job is to create a customized {letter_type} letter for donors contributing to the Omaha Zoo. Each letter should be unique, respectful, and emotionally compelling. You are encouraged to be creative with language and tone, but must not invent any facts.

    ### Variables Substitutions:
    - **Donor Details**: Keep the template variables of donors at the top (name, address, date, amount etc.) as it is in the output letter. Do not substitute names.

    ### Instructions:
    - Use all the provided donor and event information to personalize the letter.
    - Follow the feedback and requests in the **User Feedback** section carefully. If the feedback requests you to **remove** or **avoid** mentioning something (e.g., "do not mention giraffes\"), ensure it is completely excluded from the letter.
    - Similarly, if the user asks to **emphasize or add** specific themes, reflect that directly in the language, even if that means modifying the template language to add more creativity.

    ### Report Type
    - If the donor supported a specific report or initiative, incorporate that context. The system provides this detail below.
    - **Report Context**: include {letter_context} in a sentence in the letter body, important.
    - **Expanded Report Sentence** (to include directly or paraphrase meaningfully): This may be found in the 'Additional Information' section.

    ### Provided Information:
    - **Zoo Background**: {context}
    - **Donation Summary**: {donation_details}
    - **User Query and Feedback**: The following guidance includes the original user instruction, followed by any additional feedback: {user_query}
    - **Template Examples for Style & Tone**: {template_letter}
    - **Seasonal & Special Tags**: take details from {extra_details} and put in a sentence in the letter body, blending with existing text natually, very important.
    
    ### Task:
    - Write a personalized {letter_type} letter using the tone/style: {selected_style}.
    - Do NOT use exact sentences from the templates — paraphrase and inject variety.
    - Incorporate all relevant details and follow the user feedback with high priority.
    - Use the **Variation ID**: {variation_id} to add creative language differences, but never at the expense of user instructions.

    Generate a professional, emotionally engaging letter now.
    """
)

# def prepare_letter_inputs_chain(input_dict):
#     return {
#         "letter_type": selected_letter_type,
#         "letter_context": letter_context,
#         "extra_details": " ".join([
#             "XYZ sentnce" if letter_context == '' else "",
            
#         ]).strip() or "No additional information.",
#         "selected_style": selected_style,
#         "context": context,
#         "variation_id": variation_id,
#         "individual_details": individual_details,
#         "template_letter": selected_templates,
#         "user_query": user_query.strip() if user_query else "No additional details provided.",
#         "donation_details": donation_details if add_donation_details else "Not applicable",
#         "extra_details": " ".join([
#             "This donation is a memorial gift." if specify_memorial_gift else "",
#             "This donation is in honor of someone." if in_honor_of_gift else "",
#             "We are very grateful for your valuable support as a member of our Zoo" if specify_membership else "",
#             "Your thoughtful in-kind gift helps us continue our mission and brings real value to our daily operations and the care we provide." if in_kind_gift else "",
#             "Summer brings the zoo to life with longer days, lively animal activity, and joyful visits from families and children" if summer else "",
#             "Spring awakens the zoo with blooming gardens, playful newborn animals, and a renewed sense of energy throughout the park" if spring else "",
#             "Fall transforms the zoo with crisp air, colorful foliage, and animals preparing for the changing season." if fall else "",
#             "Winter brings a quiet beauty to the zoo, with peaceful landscapes and animals adapting to the colder months in unique and fascinating ways." if winter else ""
#         ]).strip() or "No additional information."
#     }

def prepare_letter_inputs_chain(input_dict):
    # Map each report type to a custom sentence
    report_context_sentences = {
        "Adopt Test": "Thank you for supporting the Adopt Test initiative, which brings meaningful enrichment to the animals.",
        "Annual": "Your contribution helps us publish and share our Annual Report that highlights conservation milestones and achievements.",
        "Adopt Specials": "We deeply appreciate your participation in Adopt Specials, supporting specific species in a special way.",
        "Gorilla Plaques": "Your gift to the Gorilla Plaques program celebrates these magnificent creatures and their stories.",
        "HDZ": "Thank you for supporting the HDZ initiative that advances our mission through special campaigns.",
        "Zoo Hospital": "Your support of the Zoo Hospital helps us deliver critical care to our animals.",
        "Patron": "We are grateful for your patron-level commitment to the zoo's mission.",
        "Postcards": "Your gift supports our outreach and communications through unique Postcards that connect with our community.",
    }

    # Get the matching sentence if it exists (None if 'None' is selected)
    report_sentence = report_context_sentences.get(letter_context, "")

    # Build extra details string
    extra_sentences = [
        report_sentence,
        "This donation is a memorial gift." if specify_memorial_gift else "",
        "This donation is in honor of someone." if in_honor_of_gift else "",
        "We are very grateful for your valuable support as a member of our Zoo" if specify_membership else "",
        "Your thoughtful in-kind gift helps us continue our mission and brings real value to our daily operations and the care we provide." if in_kind_gift else "",
        "Summer brings the zoo to life with longer days, lively animal activity, and joyful visits from families and children" if summer else "",
        "Spring awakens the zoo with blooming gardens, playful newborn animals, and a renewed sense of energy throughout the park" if spring else "",
        "Fall transforms the zoo with crisp air, colorful foliage, and animals preparing for the changing season." if fall else "",
        "Winter brings a quiet beauty to the zoo, with peaceful landscapes and animals adapting to the colder months in unique and fascinating ways."
    ]

    return {
        "letter_type": selected_letter_type,
        "letter_context": letter_context,
        "selected_style": selected_style,
        "context": context,
        "variation_id": variation_id,
        "individual_details": individual_details,
        "template_letter": selected_templates,
        "user_query": user_query.strip() if user_query else "No additional details provided.",
        "donation_details": donation_details if add_donation_details else "Not applicable",
        "extra_details": " ".join(extra_sentences).strip() or "No additional information."
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


st.sidebar.subheader("Step 3: Add Report Details (optional)")
letter_context = st.sidebar.selectbox(
    "Choose a report type:",
    ['None','Adopt Test', 'Annual', 'Adopt Specials', 'Gorilla Plaques', 'HDZ', 'Zoo Hospital', 'Patron','Postcards' ]
)

st.sidebar.subheader("Step 4: Customize Letter Content")
add_donation_details = st.sidebar.checkbox("Add donation details")
specify_membership = st.sidebar.checkbox("Specify membership")
specify_memorial_gift = st.sidebar.checkbox("Specify memorial gift")
in_honor_of_gift = st.sidebar.checkbox("Specify in-honor-of gift")
in_kind_gift = st.sidebar.checkbox("Specify in-kind gift")
in_pledge = st.sidebar.checkbox("Specify pledge")

st.sidebar.subheader("Step 5: Select Season (optional)")
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
        selected_templates = get_relevant_templates(
            selected_letter_type, selected_style
        )
        variation_id = str(uuid.uuid4())
        letter_inputs_runnable = RunnableLambda(prepare_letter_inputs_chain)
        letter_chain = letter_inputs_runnable | letter_prompt_template | chat_model
        letter = letter_chain.invoke({})
        letter_text = letter.content if hasattr(letter, "content") else str(letter).strip()

        st.session_state.letters.append({
            "letter": letter_text,
            "templates": selected_templates,
            "type": selected_letter_type,
            "style": selected_style,
            "season": selected_seasons,
            "timestamp": datetime.now()
        })
        st.session_state.current_index = len(st.session_state.letters) - 1

# Show letter and manage history
if st.session_state.current_index >= 0 and st.session_state.letters:

    current = st.session_state.letters[st.session_state.current_index]
    st.subheader(f"✉️ Generated {current['type']} Letter:")
    st.text_area("Letter Content", current["letter"], height=500)

    # 🔁 NEW: Feedback text input
    user_feedback_variation = st.text_input("💬 Enter feedback to guide the next variation (optional):", "")

    # 🔘 Action Buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        if st.button("⬅️ Previous") and st.session_state.current_index > 0:
            st.session_state.current_index -= 1
            st.rerun()

    with col2:
        if st.button("🔄 Refresh Letter"):
            variation_id = str(uuid.uuid4())  # ensure fresh generation
            # user_query = user_feedback_variation  # override with user input
            selected_templates = current["templates"]  # use same template

            # Combine original and feedback
            combined_user_query = user_query.strip()
            if user_feedback_variation.strip():
                combined_user_query += f"\nAdditional feedback: {user_feedback_variation.strip()}"

            # Inject feedback for refresh
            def prepare_letter_inputs_chain_override(_):
                return {
                    "letter_type": current["type"],
                    "letter_context": letter_context,
                    "selected_style": selected_style,
                    "context": context,
                    "variation_id": variation_id,
                    "individual_details": individual_details,
                    "template_letter": current["templates"],
                    "user_query": combined_user_query,
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

            letter_inputs_runnable = RunnableLambda(prepare_letter_inputs_chain_override)
            letter_chain = letter_inputs_runnable | letter_prompt_template | chat_model
            letter = letter_chain.invoke({})
            letter_text = letter.content if hasattr(letter, "content") else str(letter).strip()

            st.session_state.letters.append({
                "letter": letter_text,
                "templates": selected_templates,
                "type": current["type"],
                "style": selected_style,
                "season": selected_seasons,
                "timestamp": datetime.now()
            })
            st.session_state.current_index = len(st.session_state.letters) - 1

            # ⬅️ FORCE rerun so Streamlit re-evaluates `current`
            st.rerun()

    with col3:
        if st.button("Next ➡️") and st.session_state.current_index < len(st.session_state.letters) - 1:
            st.session_state.current_index += 1
            st.rerun()

    with col4:
        if st.button("🧹 Clear History"):
            st.session_state.letters.clear()
            st.session_state.current_index = -1
            st.rerun()
        
    # 🗂️ Letter Selector + Download
    st.markdown("### 📄 Download a Letter from History")

    def normalize(val):
        if isinstance(val, list):
            return "_".join([str(v).replace(" ", "_").lower() for v in val])
        return str(val).replace(" ", "_").lower()

    # Build selector options
    options = [
        f"{i + 1}: {normalize(l.get('type', ''))}_{normalize(l.get('season', []))}_{normalize(l.get('style', ''))}_{i + 1}"
        for i, l in enumerate(st.session_state.letters)
    ]

    # Ensure selector stays synced to current_index after refresh
    selected_download = st.selectbox(
        "Choose a letter to download:",
        options,
        index=st.session_state.current_index,
        key="letter_selector"  # Ensures re-render with updated state
    )

    # Force the current_index to follow the selector
    selected_letter_index = int(selected_download.split(":")[0]) - 1
    st.session_state.current_index = selected_letter_index  # sync state

    selected_letter = st.session_state.letters[selected_letter_index]

    file_name = f"{normalize(selected_letter.get('type'))}_{normalize(selected_letter.get('season', []))}_{normalize(selected_letter.get('style'))}_{selected_letter_index + 1}.txt"

    st.download_button("📄 Download Selected Letter", selected_letter["letter"], file_name=file_name)
