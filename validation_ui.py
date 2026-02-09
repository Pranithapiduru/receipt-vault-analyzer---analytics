import streamlit as st
from datetime import datetime
from database.queries import fetch_all_receipts, receipt_exists

EXPECTED_TAX_RATE = 0.08   # 8%
TOLERANCE = 0.05           # 5% tolerance


def validate_receipt(data, skip_duplicate=False):
    results = []
    passed = True

    # ---------- Required Fields ----------
    required = ["bill_id", "vendor", "date", "amount", "tax"]
    missing = [f for f in required if data.get(f) is None]

    if missing:
        results.append({
            "title": "Required Fields",
            "status": "error",
            "message": f"Missing fields: {', '.join(missing)}"
        })
        passed = False
        # Return early if fields are missing to prevent subsequent errors
        return {
            "passed": passed,
            "results": results
        }
    else:
        results.append({
            "title": "Required Fields",
            "status": "success",
            "message": "All required fields present"
        })

    # ---------- Date Format ----------
    try:
        datetime.strptime(str(data["date"]), "%Y-%m-%d")
        results.append({
            "title": "Date Format",
            "status": "success",
            "message": f"Valid date: {data['date']}"
        })
    except Exception:
        results.append({
            "title": "Date Format",
            "status": "error",
            "message": f"Invalid date format: {data['date']}"
        })
        passed = False

    try:
        amount = float(data["amount"])
    except (ValueError, TypeError):
        amount = 0.0
        
    try:
        tax = float(data["tax"])
    except (ValueError, TypeError):
        tax = 0.0

    # ---------- Total Validation ----------
    if amount > 0:
        results.append({
            "title": "Total Validation",
            "status": "success",
            "message": f"Amount detected: ₹{amount:.2f}"
        })
    else:
        results.append({
            "title": "Total Validation",
            "status": "error",
            "message": "Invalid amount value"
        })
        passed = False

    # ---------- Tax Rate Validation (FIXED) ----------
    if tax == 0:
        results.append({
            "title": "Tax Rate Validation",
            "status": "success",
            "message": "No tax applied (valid)"
        })
    else:
        # Try both interpretations
        subtotal_option_1 = amount - tax
        subtotal_option_2 = amount

        valid = False
        used_subtotal = 0.0
        actual_rate = 0.0

        for subtotal in [subtotal_option_1, subtotal_option_2]:
            if subtotal <= 0:
                continue
            rate = tax / subtotal
            if abs(rate - EXPECTED_TAX_RATE) <= TOLERANCE:
                valid = True
                used_subtotal = subtotal
                actual_rate = rate
                break

        if valid:
            results.append({
                "title": "Tax Rate Validation",
                "status": "success",
                "message": (
                    f"Tax rate OK "
                    f"({actual_rate*100:.2f}%, Subtotal ₹{used_subtotal:.2f})"
                )
            })
        else:
            results.append({
                "title": "Tax Rate Validation",
                "status": "error",
                "message": (
                    f"Tax mismatch. Expected ~{EXPECTED_TAX_RATE*100:.1f}% "
                    f"but got ₹{tax:.2f} on amount ₹{amount:.2f}"
                )
            })
            passed = False

    # ---------- Duplicate Detection ----------
    if not skip_duplicate:
        if receipt_exists(data["bill_id"]):
            results.append({
                "title": "Duplicate Detection",
                "status": "error",
                "message": "Duplicate receipt found"
            })
            passed = False
        else:
            results.append({
                "title": "Duplicate Detection",
                "status": "success",
                "message": "No duplicate found"
            })

    return {
        "passed": passed,
        "results": results
    }


def validation_ui():
    st.header("🧾 Receipt Validation")

    # ================= CURRENT UPLOADED RECEIPT =================
    data = st.session_state.get("LAST_EXTRACTED_RECEIPT")
    report = st.session_state.get("LAST_VALIDATION_REPORT")

    if data and report:
        st.subheader("🎯 Current Uploaded Receipt")

        for r in report["results"]:
            if r["status"] == "success":
                st.success(f"✅ **{r['title']}**\n\n{r['message']}")
            else:
                st.error(f"❌ **{r['title']}**\n\n{r['message']}")

        if report["passed"]:
            st.success("🎉 Receipt passed validation")
        else:
            st.error("❌ Receipt failed validation")
    else:
        st.info("No receipt uploaded yet")

    st.divider()

    # ================= STORED RECEIPT VALIDATION =================
    st.subheader("🔍 Validate Stored Receipt")

    c1, c2, c3, c4 = st.columns(4)
    bill_id = c1.text_input("Bill ID")
    vendor = c2.text_input("Vendor")
    amount = c3.text_input("Amount")
    tax = c4.text_input("Tax")

    if st.button("Run Validation", use_container_width=True):
        receipts = fetch_all_receipts()
        match = None

        for r in receipts:
            if bill_id and bill_id not in r["bill_id"]:
                continue
            if vendor and vendor.lower() not in r["vendor"].lower():
                continue
            if amount:
                try:
                    if float(amount) != r["amount"]:
                        continue
                except ValueError:
                    pass
            if tax:
                try:
                    if float(tax) != r["tax"]:
                        continue
                except ValueError:
                    pass

            match = r
            break

        if not match:
            st.error("No matching stored receipt found")
            return

        stored_report = validate_receipt(match, skip_duplicate=True)

        st.subheader(f"🧪 Validation for {match['bill_id']}")

        for r in stored_report["results"]:
            if r["status"] == "success":
                st.success(f"✅ **{r['title']}**\n\n{r['message']}")
            else:
                st.error(f"❌ **{r['title']}**\n\n{r['message']}")

        if stored_report["passed"]:
            st.success("🎉 Stored receipt passed validation")
        else:
            st.error("❌ Stored receipt failed validation")
