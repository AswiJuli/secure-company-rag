import os

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000"
)


st.set_page_config(
    page_title="Secure Company Assistant",
    layout="centered"
)


# -------------------------------------------------
# Session-state initialization
# -------------------------------------------------

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "login_notice" not in st.session_state:
    st.session_state.login_notice = None


def get_auth_headers():
    """
    Creates the Authorization header required by FastAPI.
    """

    return {
        "Authorization": (
            f"Bearer {st.session_state.access_token}"
        )
    }


def clear_login_session(notice=None):
    """
    Removes authentication and conversation data.
    """

    st.session_state.access_token = None
    st.session_state.current_user = None
    st.session_state.messages = []
    st.session_state.login_notice = notice


# -------------------------------------------------
# Login page
# -------------------------------------------------

if st.session_state.access_token is None:

    st.title("Secure Company Assistant")

    st.write(
        "Sign in using your employee ID and password."
    )

    if st.session_state.login_notice:
        st.warning(st.session_state.login_notice)
        st.session_state.login_notice = None

    with st.form("login_form"):

        employee_id = st.text_input(
            "Employee ID",

        )

        password = st.text_input(
            "Password",
            type="password"
        )

        login_submitted = st.form_submit_button(
            "Sign in",
            use_container_width=True
        )

    if login_submitted:

        if not employee_id.strip() or not password:
            st.error(
                "Enter both your employee ID and password."
            )

        else:
            try:
                login_response = requests.post(
                    f"{API_BASE_URL}/token",
                    data={
                        "username": employee_id.strip(),
                        "password": password
                    },
                    timeout=15
                )

                if login_response.status_code == 200:

                    token_data = login_response.json()

                    st.session_state.access_token = (
                        token_data["access_token"]
                    )

                    user_response = requests.get(
                        f"{API_BASE_URL}/me",
                        headers=get_auth_headers(),
                        timeout=15
                    )

                    if user_response.status_code == 200:
                        st.session_state.current_user = (
                            user_response.json()
                        )

                        st.session_state.messages = []

                        st.rerun()

                    else:
                        clear_login_session()

                        st.error(
                            "Login succeeded, but the user "
                            "profile could not be loaded."
                        )

                elif login_response.status_code == 401:
                    st.error(
                        "Incorrect employee ID or password."
                    )

                else:
                    try:
                        error_detail = login_response.json().get(
                            "detail",
                            "Login failed."
                        )
                    except ValueError:
                        error_detail = "Login failed."

                    st.error(error_detail)

            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not connect to the API. "
                    "Make sure FastAPI is running."
                )

            except requests.exceptions.Timeout:
                st.error(
                    "The API took too long to respond."
                )

            except requests.exceptions.RequestException as error:
                st.error(
                    f"Login request failed: {error}"
                )

    # Prevent the chatbot from appearing below the login form.
    st.stop()


# -------------------------------------------------
# Authenticated chatbot page
# -------------------------------------------------

current_user = st.session_state.current_user

st.title("Secure Company Assistant")

st.write(
    "Ask questions about company documents. "
    "Access is automatically restricted according "
    "to your authenticated role."
)


# -------------------------------------------------
# Sidebar
# -------------------------------------------------

st.sidebar.header("Signed-in User")

st.sidebar.write(
    f"**Employee ID:** "
    f"{current_user['username'].upper()}"
)

st.sidebar.write(
    f"**Access role:** "
    f"{current_user['role'].title()}"
)


if st.sidebar.button(
    "Clear conversation",
    use_container_width=True
):
    st.session_state.messages = []
    st.rerun()


if st.sidebar.button(
    "Log out",
    use_container_width=True
):
    clear_login_session()
    st.rerun()


# -------------------------------------------------
# Show previous messages
# -------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.write(message["content"])

        if message.get("sources"):
            st.caption(
                "Sources: "
                + ", ".join(message["sources"])
            )


# -------------------------------------------------
# Accept a question
# -------------------------------------------------

question = st.chat_input(
    "Ask a question about the company"
)


if question:

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):

        with st.spinner(
            "Searching permitted company information..."
        ):

            try:
                chat_response = requests.post(
                    f"{API_BASE_URL}/chat",
                    headers=get_auth_headers(),
                    json={
                        "question": question
                    },
                    timeout=120
                )

                if chat_response.status_code == 200:

                    response_data = chat_response.json()

                    answer = response_data["answer"]
                    sources = response_data["sources"]

                    st.write(answer)

                    if sources:
                        st.caption(
                            "Sources: "
                            + ", ".join(sources)
                        )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })

                elif chat_response.status_code == 401:

                    clear_login_session(
                        notice=(
                            "Your login session expired. "
                            "Please sign in again."
                        )
                    )

                    st.rerun()

                else:
                    try:
                        error_detail = chat_response.json().get(
                            "detail",
                            "The request failed."
                        )
                    except ValueError:
                        error_detail = "The request failed."

                    st.error(error_detail)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_detail,
                        "sources": []
                    })

            except requests.exceptions.ConnectionError:
                error_message = (
                    "Could not connect to the API. "
                    "Make sure FastAPI is running."
                )

                st.error(error_message)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message,
                    "sources": []
                })

            except requests.exceptions.Timeout:
                error_message = (
                    "The chatbot took too long to respond."
                )

                st.error(error_message)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message,
                    "sources": []
                })

            except requests.exceptions.RequestException as error:
                error_message = (
                    f"Chat request failed: {error}"
                )

                st.error(error_message)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message,
                    "sources": []
                })