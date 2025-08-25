import asyncio

import nest_asyncio
import streamlit as st
from agno.tools.streamlit.components import check_password

from ui.css import CUSTOM_CSS
from ui.utils import about_agno, footer

nest_asyncio.apply()

st.set_page_config(
    page_title="Agno Agents",
    page_icon=":orange_heart:",
    layout="wide",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


async def header():
    st.markdown("<h1 class='heading'>Agno Agents</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subheading'>Welcome to the Agno Agents platform! We've provided some sample agents to get you started.</p>",
        unsafe_allow_html=True,
    )


async def body():
    st.markdown("### Available Tools")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
        <div style="padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px;">
            <h3>Excel Processor</h3>
            <p>Upload an Excel file with keywords and analyze them for SEO value.</p>
            <p>Perfect for processing keyword lists and generating SEO insights.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Excel Processor", key="excel_processor_button"):
            st.switch_page("pages/7_Excel_processor.py")

    with col2:
        st.markdown(
            """
        <div style="padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px;">
            <h3>Enova Deep Research Team</h3>
            <p>A multi-agent research team for deep investigation, analysis, and comprehensive reporting.</p>
            <p>Perfect for in-depth research and analysis tasks.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Deep Research", key="deep_research_button"):
            st.switch_page("pages/8_Enova_Deep_Research.py")

async def main():
    await header()
    await body()
    await footer()
    await about_agno()


if __name__ == "__main__":
    if check_password():
        asyncio.run(main())
