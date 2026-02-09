import streamlit as st
from PIL import Image
import pytesseract
import pandas as pd

from ocr.text_parser import parse_receipt
from ui.validation_ui import validate_receipt
from database.queries import save_receipt, receipt_exists


def render_upload_ui():
    st.header("📤 Upload Receipt")

    uploaded = st.file_uploader(
        "Upload receipt image or PDF",
        type=["png", "jpg", "jpeg", "pdf"]
    )

    if not uploaded:
        st.info("Please upload a receipt image or PDF to begin")
        return

    # ================= IMAGE PROCESSING =================
    if uploaded.type == "application/pdf":
        from ocr.pdf_processor import pdf_to_images
        with st.spinner("Converting PDF to image..."):
            try:
                pdf_images = pdf_to_images(uploaded.read())
                if not pdf_images:
                    st.error("Could not convert PDF to image")
                    return
                img = pdf_images[0] # Take first page
            except Exception as e:
                st.error(f"PDF Processing Error: {e}")
                st.info("Ensure Poppler is installed and path is correct in `ocr/pdf_processor.py`.")
                return
    else:
        img = Image.open(uploaded)

    col1, col2 = st.columns(2)
    with col1:
        st.image(img, caption="Original Image", use_container_width=True)

    with col2:
        gray = img.convert("L")
        st.image(gray, caption="Processed Image", use_container_width=True)

    st.divider()

    # ================= OCR + PARSE =================
    if not st.button("📄 Extract & Save Receipt", use_container_width=True):
        return

    data = None
    items = []
    
    api_key = st.session_state.get("GEMINI_API_KEY")
    use_ai = bool(api_key)

    with st.spinner("Extracting receipt data..."):
        if use_ai:
            from ai.gemini_client import GeminiClient
            try:
                client = GeminiClient(api_key)
                # Gemini takes PIL image directly
                result = client.extract_receipt(img)
                if result:
                    items = result.pop("items", [])
                    data = result
                    st.success("✨ AI Extraction Successful")
            except Exception as e:
                st.error(f"AI Extraction failed: {e}. Falling back to OCR.")
                use_ai = False

        if not data:
            # Fallback to Tesseract
            import numpy as np
            import cv2
            # Use image_preprocessing if available
            from ocr.image_preprocessing import preprocess_image
            gray_preprocessed = preprocess_image(img)
            text = pytesseract.image_to_string(gray_preprocessed)
            if not text.strip():
                st.error("❌ No readable text detected from the image")
                return
            data, items = parse_receipt(text)

    st.session_state["LAST_EXTRACTED_RECEIPT"] = data

    # ================= RECEIPT SUMMARY (HORIZONTAL TABLE) =================
    st.subheader("🧾 Receipt Summary")

    summary_df = pd.DataFrame([{
        "Bill ID": data["bill_id"],
        "Vendor": data["vendor"],
        "Category": data.get("category", "Uncategorized"),
        "Date": data["date"],
        "Subtotal (₹)": round(data.get("subtotal", 0.0), 2),
        "Tax (₹)": round(data["tax"], 2),
        "Amount (₹)": round(data["amount"], 2),
    }])

    st.dataframe(summary_df, use_container_width=True)

    # ================= ITEM WISE EXTRACTION =================
    st.subheader("🛒 Item-wise Details")

    if items and len(items) > 0:
        st.dataframe(items, use_container_width=True)
    else:
        st.info("No item-wise details detected from this receipt")

    st.divider()

    # ================= DUPLICATE CHECK =================
    if receipt_exists(data["bill_id"]):
        st.error("❌ Duplicate detected — receipt NOT saved to database")
        return
    else:
        st.success("✅ No duplicate found")

    # ================= VALIDATION =================
    validation = validate_receipt(data)
    st.session_state["LAST_VALIDATION_REPORT"] = validation

    # ================= SAVE (EVEN IF VALIDATION FAILS) =================
    save_receipt(data)

    if validation["passed"]:
        st.success("🎉 Receipt passed validation and was saved successfully")
    else:
        st.error("❌ Receipt failed validation")
