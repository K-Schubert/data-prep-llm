# parsing_visualizer.py
# -------------------------------------------------
# A super‑simple Streamlit interface to:
#   1) Upload a PDF and preview it.
#   2) Display the extracted JSON counterpart.
#   3) **Edit the JSON manually and save** (overwrite or save as new).
# -------------------------------------------------
# How to run:
#   pip install streamlit
#   streamlit run parsing_visualizer.py
# -------------------------------------------------
import streamlit as st
import json
import base64
import difflib
from pathlib import Path

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="PDF ↔ JSON Comparator & Editor", layout="wide")

st.title("PDF ↔ JSON Comparator & Editor")
st.caption(
    "Upload a PDF on the left, inspect its JSON on the right, edit as needed, and save."
)

# Two‑column layout ---------------------------------------------------------
left_panel, right_panel = st.columns(2, gap="large")

#############################################################################
# LEFT PANEL – Upload + preview PDF                                         #
#############################################################################
with left_panel:
    st.subheader("1️⃣  Upload PDF file")

    # Let user pick from PDFs in subfolders of ./pdfs/
    pdf_files = list(Path("pdfs").rglob("*.pdf"))

    # Sort by folder (d/f/i/e) then by filename using natural sort
    folder_order = {"f": 0, "d": 1, "i": 2, "e": 3}
    pdf_files = sorted(pdf_files, key=lambda p: (folder_order.get(p.parent.name, 99), p.name))

    selected_pdf_path = st.selectbox(
        "Select a PDF from the repository",
        options=pdf_files,
        format_func=lambda p: str(p.relative_to("pdfs"))  # show path like d/abc.pdf
    )

    uploaded_pdf = selected_pdf_path.open("rb")  # mimic a file-like object

    if uploaded_pdf is not None:
        # Convert the PDF to base64 so we can embed it in an <iframe>
        pdf_bytes = uploaded_pdf.read()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        st.markdown("### Preview")
        st.markdown(
            f"""
            <iframe
                src="data:application/pdf;base64,{b64_pdf}"
                width="100%"
                height="800px"
                style="border:none;">
            </iframe>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("⬆️  Select a PDF to see it here.")

#############################################################################
# RIGHT PANEL – Display, edit, and save JSON                                #
#############################################################################
with right_panel:
    st.subheader("2️⃣  Extracted JSON - view / edit / save")

    if uploaded_pdf is not None:
        # Derive JSON path from the PDF filename (without extension)
        pdf_stem = Path(uploaded_pdf.name).stem

        pdf_rel_path = Path(uploaded_pdf.name)
        pdf_stem = selected_pdf_path.stem
        subfolder = selected_pdf_path.parent.name

        # Build the matching JSON path
        default_json_path = Path("parsed_pdfs") / subfolder / f"{pdf_stem}.json"
        default_json_path.parent.mkdir(parents=True, exist_ok=True)

        # Attempt to load existing JSON (may be empty)
        data = {}
        if default_json_path.is_file():
            try:
                data = json.loads(default_json_path.read_text(encoding="utf-8"))
            except Exception as e:
                st.warning(f"⚠️ Couldn't parse JSON (showing empty template).\nError: {e}")

        # Read only JSON area
        st.json(data, expanded=False)

        # Editable JSON textarea ------------------------------------------------
        json_str = st.text_area(
            "Edit JSON below (must remain valid JSON)",
            value=json.dumps(data, indent=4),
            height=500,
        )

        # ---- Diff view -----------------------------------------------------
        st.markdown("### Diff - Original ⇄ Edited")
        try:
            edited_data = json.loads(json_str)  # validate
            original_dump = json.dumps(data, indent=4, sort_keys=True).splitlines(keepends=True)
            edited_dump = json.dumps(edited_data, indent=4, sort_keys=True).splitlines(keepends=True)
            diff_lines = difflib.unified_diff(original_dump, edited_dump, fromfile="original", tofile="edited", lineterm="")
            diff_text = "".join(diff_lines)
            if diff_text:
                st.code(diff_text, language="diff")
            else:
                st.success("No differences detected.")
        except json.JSONDecodeError:
            st.info("🛈 Enter valid JSON to see a live diff.")

        # Save options ---------------------------------------------------------
        save_mode = st.radio("Save mode", ("Overwrite original", "Save as new file"))

        # If saving as new, ask for filename
        new_filename = None
        if save_mode == "Save as new file":
            new_filename = st.text_input(
                "New JSON filename (no path)",
                value=f"{pdf_stem}_edited.json",
                help="File will be stored in the same 'json' folder.",
            )

        # Save button ----------------------------------------------------------
        if st.button("💾 Save JSON"):
            try:
                # Validate JSON first
                parsed = json.loads(json_str)

                # Determine target path
                target_path = (
                    default_json_path
                    if save_mode == "Overwrite original"
                    else default_json_path.parent / new_filename
                )

                # Write to disk
                target_path.write_text(
                    json.dumps(parsed, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                st.success(f"✅ Saved to **{target_path}**")
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON - fix errors before saving.\n\n{e}")
    else:
        st.info("JSON viewer/editor will appear once a PDF is uploaded.")
