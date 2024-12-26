# Import JamAI Library
import streamlit as st
from jamaibase import JamAI, protocol as p
import time
import os
from dotenv import load_dotenv


# Constant
PROJECT_ID = "proj_28b0f6977fbde2e0ea0017a4"  # Replace with your project ID
PAT = "jamai_pat_05e6df34ab93b1eb61ce32e51d4fd634f5cab4b4aedfe6b2"        # Replace with your PAT
TABLE_TYPE = p.TableType.chat
OPENER = "Hello! How can I help you today?"

# Initialize JamAI
jamai = JamAI(project_id=PROJECT_ID, token=PAT)

# Create chat session: Each chat session is created by duplicating your base agent table
def create_new_chat():
    timestamp = int(time.time())
    new_table_id = f"Chat_{timestamp}" # create a new table id

    try:
        jamai.table.duplicate_table(
            table_type = p.TableType.chat,
            table_id_src="Synthia", # get agent name
            table_id_dst=new_table_id,
            include_data=True,
            create_as_child=True
        )
        return new_table_id
    except Exception as e:
        print(f"Error creating new chat: {str(e)}")
        return None


def main():
    st.title("Simple Chat Demo")

    # Initialize session state
    if "table_id" not in st.session_state:
        new_table_id=create_new_chat()
        st.session_state.table_id = new_table_id
        st.session_state.messages = [{"role":"assistant","content":OPENER}]

    # Create New Chat Button
    if st.button("New Chat"):
        new_table_id = create_new_chat()
        if new_table_id:
            st.session_state.table_id = new_table_id
            st.session_state.messages = [{"role":"assistant","content":OPENER}]
            st.rerun()
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here"):
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state.messages.append({"role":"user","content":prompt})

        # Get AI Response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response=""

            # Stream the response
            for chunk in jamai.table.add_table_rows(
                table_type = TABLE_TYPE,
                request = p.RowAddRequest(
                    table_id=st.session_state.table_id,
                    data=[{"User":prompt}],
                    stream=True
                )
            ):
                if isinstance(chunk,p.GenTableStreamChatCompletionChunk):
                    if chunk.output_column_name == 'AI':
                        full_response += chunk.choices[0].message.content
                        message_placeholder.write(full_response + " ")
            
            message_placeholder.write(full_response)
            st.session_state.messages.append({"role":"assistant","content":full_response})


if __name__ == "__main__":
    main()
