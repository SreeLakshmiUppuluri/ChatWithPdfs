import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
import os

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ✅ Correct Gemini Embedding Model
embeddings = GoogleGenerativeAIEmbeddings(
    api_key=GOOGLE_API_KEY,
    model="models/embedding-001"  # ✅ Correct model name
)

# Function to extract text from PDFs
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Function to split text into chunks
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Function to create vectorstore (FAISS)
def get_vectorstore(text_chunks):
    # ✅ Now using Gemini embeddings (no HuggingFace)
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

# Function to create conversation chain
def get_conversation_chain(vectorstore):
    llm = ChatGoogleGenerativeAI(
        api_key=GOOGLE_API_KEY,
        model="gemini-1.5-flash",  # ✅ Chat model (different from embedding model)
        temperature=0.5
    )

    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

# Function to handle user input
def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(f"**You:** {message.content}")
        else:
            st.write(f"**Bot:** {message.content}")

# Function to download chat history as text file
def download_chat_history():
    if st.session_state.chat_history:
        chat_text = "\n".join(
            [f"You: {m.content}" if i % 2 == 0 else f"Bot: {m.content}"
             for i, m in enumerate(st.session_state.chat_history)]
        )
        st.download_button(
            label="📥 Download Chat History",
            data=chat_text,
            file_name="chat_history.txt",
            mime="text/plain"
        )

# Streamlit UI
def main():
    st.set_page_config(page_title="Chat with multiple PDFs", page_icon=":books:")
    st.header("Chat with multiple PDFs 📄")

    # Session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    # User input
    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)

    # File uploader
    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader("Upload your PDFs here and click on 'Process'", accept_multiple_files=True)
        if st.button("Process"):
            with st.spinner("Processing..."):
                # Extract text
                raw_text = get_pdf_text(pdf_docs)

                # Split text
                text_chunks = get_text_chunks(raw_text)

                # Create vectorstore
                vectorstore = get_vectorstore(text_chunks)

                # Create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)

    # Download chat history button
    if st.session_state.chat_history:
        download_chat_history()

if __name__ == '__main__':
    main()
