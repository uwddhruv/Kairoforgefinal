# KAIROFORGE Memory

- [Natural Language Search](nl-search.md) — Parse plain-English queries into stock filters. Use word-boundary regex for sector matching, avoid "with" matching "it".
- [Yahoo NSE valuation fields](yahoo-nse-data.md) — `.info` often omits FCF/shares; use statement FCF and total-share sources, never float shares or EPS as FCF.
- [HTML Rendering in Streamlit](streamlit-html.md) — st.markdown with triple-quoted block strings and unsafe_allow_html=True may render raw text in newer Streamlit. Use st.columns + short inline strings instead.
- [Download Button Keys](streamlit-download.md) — Unique key="..." required on each st.download_button to prevent MediaFileHandler 404 cache collisions.
