# KAIROFORGE Memory

- [Natural Language Search](nl-search.md) — Parse plain-English queries into stock filters. Use word-boundary regex for sector matching, avoid "with" matching "it".
- [DCF Stage-2 Interpolation](dcf-fix.md) — growth_stage2 was ignored before terminal growth; must interpolate g1 → g2 first, then g2 → gT for perpetuity.
- [HTML Rendering in Streamlit](streamlit-html.md) — st.markdown with triple-quoted block strings and unsafe_allow_html=True may render raw text in newer Streamlit. Use st.columns + short inline strings instead.
- [Download Button Keys](streamlit-download.md) — Unique key="..." required on each st.download_button to prevent MediaFileHandler 404 cache collisions.
