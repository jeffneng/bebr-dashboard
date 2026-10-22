import streamlit as st

from lib.data import setup

setup("BEBR Dashboard")
pg = st.navigation(
    [
        st.Page("views/home.py", title="Home", icon="🏠", default=True),
        st.Page("views/my_building.py", title="My Building", icon="🏢"),
        st.Page("views/sector_insights.py", title="Sector Insights", icon="📊"),
    ]
)
pg.run()
