import streamlit as st
import tempfile
import os
from docling.document_converter import DocumentConverter
import backend

st.set_page_config(page_title="Smart Recruiter AI", layout="wide")

# --- Session State ---
if "results" not in st.session_state: st.session_state.results = None
if "criteria" not in st.session_state: st.session_state.criteria = None

# --- Custom CSS (Restoring the nice look) ---
st.markdown("""
<style>
    .score-high { color: #2e7d32; font-weight: bold; font-size: 24px; }
    .score-med { color: #f57c00; font-weight: bold; font-size: 24px; }
    .score-low { color: #c62828; font-weight: bold; font-size: 24px; }
    .metric-card { background-color: #f9f9f9; padding: 10px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Controls")
    blind_mode = st.toggle("🕵️ Blind Resume Mode", value=False)
    st.divider()
    uploaded_file = st.file_uploader("Upload JD (PDF)", type="pdf")
    
    if st.button("🚀 Analyze Candidates", type="primary"):
        if uploaded_file:
            with st.spinner("Processing JD & Scanning Database..."):
                # Save temp JD
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                # Parse
                doc = DocumentConverter().convert(tmp_path)
                jd_text = doc.document.export_to_markdown()
                os.remove(tmp_path)
                
                # Backend Logic
                st.session_state.criteria = backend.extract_jd_criteria(jd_text)
                raw_hits = backend.search_candidates(st.session_state.criteria)
                
                # Analyze Results
                st.session_state.results = [
                    backend.analyze_candidate(hit['_source'].get('full_text', hit['_source']['text']), st.session_state.criteria, blind_mode)
                    for hit in raw_hits
                ]

# --- Main Page ---
st.title("🤖 AI Smart Recruiter")

if st.session_state.results:
    # --- 1. Top Section: Comparison Trigger ---
    # We check which checkboxes are active
    selected_indices = []
    for i in range(len(st.session_state.results)):
        if st.session_state.get(f"chk_{i}", False):
            selected_indices.append(i)

    # Show "Compare" button ONLY if exactly 2 are selected
    if len(selected_indices) == 2:
        st.info("✅ Two candidates selected. Ready to compare.")
        if st.button("⚖️ Generate Head-to-Head Comparison", type="primary"):
            cand_a = st.session_state.results[selected_indices[0]]
            cand_b = st.session_state.results[selected_indices[1]]
            
            with st.spinner("Asking Gemini to compare..."):
                table = backend.compare_candidates_side_by_side([cand_a, cand_b], st.session_state.criteria)
                
                # Render the Table
                st.markdown("### 🥊 Comparison Results")
                
                # Header Row
                c1, c2, c3 = st.columns([1, 2, 2])
                c1.markdown("#### Feature")
                c2.markdown(f"#### {cand_a['candidate_name']}")
                c3.markdown(f"#### {cand_b['candidate_name']}")
                st.divider()
                
                # Data Rows
                for row in table.get('rows', []):
                    rc1, rc2, rc3 = st.columns([1, 2, 2])
                    rc1.write(f"**{row['feature']}**")
                    rc2.info(row['cand_a'])
                    rc3.info(row['cand_b'])
                st.divider()
    
    elif len(selected_indices) > 2:
        st.warning("⚠️ You can only compare 2 candidates at a time. Please deselect some.")

    # --- 2. Candidate List ---
    st.subheader(f"Top Matches for: {st.session_state.criteria.get('job_title', 'Role')}")
    
    for idx, cand in enumerate(st.session_state.results):
        score = cand.get('fit_score', 0)
        # Determine Color Class
        s_class = "score-high" if score >= 80 else "score-med" if score >= 60 else "score-low"
        
        with st.container(border=True):
            # Layout: Left (Info) | Mid (Score) | Right (Actions)
            col1, col2, col3 = st.columns([4, 1, 2])
            
            with col1:
                st.markdown(f"### {cand['candidate_name']}")
                st.caption(f"**Seniority Level:** {cand.get('seniority_level', 'N/A')}")
                
                # Expandable Details
                with st.expander("See Strengths & Weaknesses"):
                    st.write("**✅ Strengths:**")
                    for s in cand.get('strengths', []): st.write(f"- {s}")
                    st.write("**⚠️ Weaknesses:**")
                    for w in cand.get('weaknesses', []): st.write(f"- {w}")

            with col2:
                # The Color-Coded Score
                st.markdown(f"<div class='{s_class}'>{score}%</div>", unsafe_allow_html=True)
                st.caption("Fit Score")
                
                # The Selection Checkbox
                st.checkbox("Compare", key=f"chk_{idx}")

            with col3:
                st.markdown("**Actions**")
                
                # 1. Interview Questions (Restored!)
                with st.popover("❓ Interview Questions"):
                    st.write("Ask these to test their weaknesses:")
                    for q in cand.get('interview_questions', []):
                        st.info(f"Q: {q}")
                
                # 2. Rejection Email
                if st.button("✉️ Draft Rejection", key=f"btn_rej_{idx}"):
                    email = backend.generate_rejection_email(cand['candidate_name'], cand.get('rejection_reason', 'Not a fit'))
                    st.text_area("Email Draft", email, height=150)