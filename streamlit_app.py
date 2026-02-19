import streamlit as st
import os
from dotenv import load_dotenv
from agent_factory.factory import AgentFactory # Importerar logiken från din mapp

# Ladda API-nyckeln från din .env-fil
load_dotenv()

st.set_page_config(page_title="Agent Factory", page_icon="🤖")

st.title("🤖 BV Agent Factory")
st.markdown("Skriv in en rollbeskrivning nedan för att generera en komplett agent-mapp.")

# Inmatningsfält
role = st.text_input("Vilken roll ska agenten ha?", placeholder="t.ex. SaaS Legal Expert")

if st.button("Generera Agent", type="primary"):
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("Hittade ingen API-nyckel! Se till att du har skapat en .env-fil.")
    elif role:
        try:
            with st.spinner(f"Snickrar på din {role}..."):
                factory = AgentFactory()
                # Skapar agenten fysiskt på din dator
                result = factory.create_agent(role)
                st.success(f"Klart! Agenten har skapats i mappen: `{result}`")
                st.balloons()
        except Exception as e:
            st.error(f"Något gick fel: {e}")
    else:
        st.warning("Du måste skriva in en roll först!")