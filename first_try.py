import streamlit as st
import os
from google import genai
from PIL import Image
import re
import json
import pandas as pd
from io import BytesIO

# --- Streamlit UI ---
st.set_page_config(page_title="Image Text Extractor - Gemini", layout="wide")
st.title("🧠 Gemini Vision Extractor")
st.write("Upload multiple advertisement images to extract structured information in JSON format and download all results in a single Excel file.")

# --- API Key ---
api_key = (
    os.getenv("GENAI_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
    or os.getenv("API_KEY")
)

MODEL_NAME = "gemini-2.5-flash"

# --- Updated Prompt for Multiple Hostel Posters ---
prompt = """You are analyzing an advertisement image that may contain one or multiple hostel posters. 
For each distinct hostel advertisement visible, extract details in the following JSON format. 
If multiple hostels are found, return an array of objects — one per hostel. Ensure all contact numbers and 
location details are accurately captured.

Return ONLY valid JSON (no explanations, no markdown).

Expected structure:
[
  {
    "EstablishmentType": "...",
    "HostelName": "...",
    "LocationDetails": {
      "Landmark1": "...",
      "Landmark2": "..."
    },
    "KeyService": "...",
    "AccommodationOptions": "...",
    "ContactNumbers": [
      "...",
      "...",
      "..."
    ]
  }
]
"""

# --- File Upload ---
uploaded_images = st.file_uploader("📤 Upload Advertisement Images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_images and api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing Gemini client: {e}")
        st.stop()

    if st.button("🚀 Extract Text from All Images"):
        all_data = []

        with st.spinner("Analyzing all images using Gemini... Please wait..."):
            for idx, uploaded_image in enumerate(uploaded_images, start=1):
                try:
                    img = Image.open(uploaded_image)
                    contents = [prompt, img]

                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=contents
                    )

                    clean_text = re.sub(r"^```(?:json)?|```$", "", response.text, flags=re.MULTILINE).strip()

                    # Parse as JSON (can be list or single object)
                    parsed = json.loads(clean_text)
                    if isinstance(parsed, dict):
                        parsed = [parsed]  # normalize single to list

                    for entry in parsed:
                        flat_data = {
                            "EstablishmentType": entry.get("EstablishmentType", ""),
                            "HostelName": entry.get("HostelName", ""),
                            "Landmark1": entry.get("LocationDetails", {}).get("Landmark1", ""),
                            "Landmark2": entry.get("LocationDetails", {}).get("Landmark2", ""),
                            "KeyService": entry.get("KeyService", ""),
                            "AccommodationOptions": entry.get("AccommodationOptions", ""),
                            "ContactNumbers": ", ".join(entry.get("ContactNumbers", []))
                        }
                        all_data.append(flat_data)

                    st.success(f"✅ Extracted {len(parsed)} hostel(s) from: {uploaded_image.name}")

                except Exception as e:
                    st.warning(f"⚠️ Failed to process {uploaded_image.name}: {e}")

        # --- Combine and Download Excel ---
        if all_data:
            df = pd.DataFrame(all_data)

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Extracted Data")

            st.subheader("📊 Combined Extracted Data:")
            st.dataframe(df)

            st.download_button(
                label="📥 Download All Extracted Data as Excel",
                data=output.getvalue(),
                file_name="Combined_Extracted_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No valid data was extracted from the uploaded images.")
else:
    st.info("👆 Upload one or more images to start.")
