import streamlit as st

from guardrails import check_input
from rag import (
    ROLE_ACCESS,
    retrieve_documents,
    generate_answer
)


st.set_page_config(
    page_title="Secure Company Assistant",
    layout="centered"
)

st.title("Secure Company Assistant")

st.write(
    "Ask questions about company documents. "
    "Document access is restricted according to your role."
)


# ---------------------------
# Sidebar
# ---------------------------

st.sidebar.header("User Access")

role = st.sidebar.selectbox(
    "Select your role",
    options=list(ROLE_ACCESS.keys()),
    format_func=lambda role_name: role_name.title()
)

st.sidebar.write("Accessible departments:")

for department in ROLE_ACCESS[role]:
    st.sidebar.write(f"- {department.title()}")


# Clear the chat when the role changes.
# This prevents answers from a more powerful role remaining visible.
if st.session_state.get("active_role") != role:
    st.session_state.active_role = role
    st.session_state.messages = []


if "messages" not in st.session_state:
    st.session_state.messages = []


if st.sidebar.button("Clear conversation"):
    st.session_state.messages = []
    st.rerun()


# ---------------------------
# Show previous messages
# ---------------------------

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

        if message.get("sources"):
            st.caption(
                "Sources: " + ", ".join(message["sources"])
            )


# ---------------------------
# Accept a question
# ---------------------------

question = st.chat_input(
    "Ask a question about the company"
)

if question:
    # Save and display the user's question
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.write(question)

    # Run guardrails
    allowed, reason = check_input(question)

    if not allowed:
        blocked_message = f"Request blocked: {reason}"

        with st.chat_message("assistant"):
            st.error(blocked_message)

        st.session_state.messages.append({
            "role": "assistant",
            "content": blocked_message,
            "sources": []
        })

    else:
        with st.chat_message("assistant"):
            with st.spinner("Searching permitted documents..."):
                try:
                    results = retrieve_documents(
                        question,
                        role
                    )

                    answer, sources = generate_answer(
                        question,
                        results
                    )

                    st.write(answer)

                    if sources:
                        st.caption(
                            "Sources: " + ", ".join(sources)
                        )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })

                except Exception as error:
                    st.error(
                        f"Something went wrong: {error}"
                    )