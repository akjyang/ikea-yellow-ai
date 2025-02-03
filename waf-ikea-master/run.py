from llmapi import get_llm_api
from typing import List, Dict
import streamlit as st
from vertexai.generative_models import GenerativeModel, Part
from contextframe import ContextFrame

# Constants
MAX_CONTEXT_SIZE = 2

def setup_page(): 
    st.set_page_config(
        page_title="IKEA Data Analysis Tool",
        page_icon="ikea.png",
        layout="wide",
    )

    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("IKEA Data Analysis Tool")
    with col2:
        st.title("Insert Image")
        # st.image("ikea.png")

def initialize_app():
    """
    Initialize the Streamlit app and load database context.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "chat" not in st.session_state:
        st.session_state.chat = GenerativeModel(
            "gemini-1.5-pro",
            generation_config={"temperature": 0},
            tools=[get_llm_api()],
        )

def get_chat_context(messages: List[Dict]) -> str:
    """
    Create a context string from previous messages.
    """
    context = ""
    for msg in messages[-(MAX_CONTEXT_SIZE * 2):]:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"]
        context += f"{role}: {content}\n\n"
    return context

def get_global_context(prompt: str):
    chat_context = get_chat_context(st.session_state.messages)
    full_prompt = f"""
    You are the IKEA Data Analysis Tool.
    Only use information that you learn from context refinements, do not make up information.

    Previous conversation:
    {chat_context}

    Current question: {prompt} 
    """
    return full_prompt

def main():
    setup_page()
    initialize_app()

# Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if "refinements" in message:
                refinements = message["refinements"]
                if refinements[-1].completely_intermediate():
                    with st.expander("Extended Reasoning"):
                        for refinement in refinements:
                            refinement.display_refinement()
                    st.markdown(message["content"])
                else:
                    with st.expander("Extended Reasoning"):
                        for refinement in refinements[:-1]:
                            refinement.display_refinement()
                    st.markdown(message["content"])
                    refinements[-1].display_refinement()
            else:
                st.markdown(message["content"])

    # Handle user input
    if prompt := st.chat_input("Ask me about information in the database..."):
        global_context = get_global_context(prompt)
        frame = ContextFrame()
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        message_placeholder = st.empty()

        chat = st.session_state.chat.start_chat()
        with st.chat_message("assistant"):
            first_interaction = True
            while True:
                whole_prompt = ""
                if first_interaction:
                    whole_prompt += global_context
                    first_interaction = False
                whole_prompt += frame.get_local_context()
                print("-----------")
                print(whole_prompt)
                response = chat.send_message(whole_prompt)
                response = response.candidates[0].content
                try:
                    cleaned_text = response.text.replace("$", r"\$")  # noqa: W605
                    frame.set_response(cleaned_text)
                    print(frame.get_response())
                    print("-----------")
                    break
                except:
                    part = response.parts[0]
                    params = {}
                    for key, value in part.function_call.args.items():
                        params[key] = value
                    func_name = part.function_call.name
                    print(func_name)
                    print(params)
                    frame.execute_refinement(func_name, params)
                    print("-----------")
            frame_history = frame.extract_history()
            frame_response = frame.get_response()
            with message_placeholder.container():
                st.markdown(frame_response)
                if not frame_history[-1].completely_intermediate():
                    frame_history[-1].display_refinement()
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": frame_response,
                    "refinements": frame_history,
                }
            )

if __name__ == "__main__":
    main()
