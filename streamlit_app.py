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

instructions = st.text_area(
    "Instruktioner",
    height=280,
    placeholder="Beskriv här agentens beteende, mål och specifik kunskap. T.ex. hur den ska svara, vilka källor den ska använda, eller särskilda regler. Fältet är valfritt men hjälper att skräddarsy agenten.",
    help="Dina instruktioner vävs in i agentens system-prompt (instructions.md) så att beteendet speglar det du skriver här.",
)

if st.button("Generera Agent", type="primary"):
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("Hittade ingen API-nyckel! Se till att du har skapat en .env-fil.")
    elif role:
        try:
            with st.spinner(f"Snickrar på din {role}..."):
                factory = AgentFactory()
                result = factory.create_agent(role, instructions=instructions.strip() or None)
                st.success(f"Klart! Agenten har skapats i mappen: `{result['agent_dir']}`")
                st.balloons()
        except Exception as e:
            st.error(f"Något gick fel: {e}")
    else:
        st.warning("Du måste skriva in en roll först!")