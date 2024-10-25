# app.py
import streamlit as st
from PyPDF2 import PdfReader
import google.generativeai as genai
from typing import Dict, Any
from datetime import datetime

# Configure Google AI with API key from Streamlit secrets
if 'GOOGLE_API_KEY' not in st.secrets:
    st.error('GOOGLE_API_KEY not found in secrets. Please add it to your secrets.toml file.')
    st.stop()

genai.configure(api_key=st.secrets['GOOGLE_API_KEY'])


class BookAnalyzer:
    def __init__(self):
        try:
            self.model = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            st.error(f"Error initializing Gemini model: {str(e)}")
            st.stop()

    def read_pdf(self, file) -> str:
        """Read PDF file content"""
        try:
            pdf = PdfReader(file)
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
            return None

    def analyze_book(self, content: str) -> Dict[str, Any]:
        """Analyze book content using Gemini"""
        try:
            prompt = """
            Analyze this book content and provide the following in a well-formatted way:

            1. Brief Summary (2-3 sentences)
            2. 5 Interesting Questions Readers Might Ask (numbered list)

            Keep the analysis concise and focused on the most important aspects.

            Book content: {content}
            """

            response = self.model.generate_content(prompt.format(content=content[:5000]))
            return {
                'success': True,
                'analysis': response.text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def answer_question(self, question: str, content: str) -> str:
        """Get answer from Gemini"""
        try:
            prompt = """
            Based on the following book content, answer this question: {question}

            Book content: {content}

            Provide a clear, detailed answer using specific information from the book.
            If the answer cannot be found in the content, clearly state that.
            """

            response = self.model.generate_content(
                prompt.format(question=question, content=content[:5000])
            )
            return response.text
        except Exception as e:
            return f"Error generating answer: {str(e)}"


def initialize_session_state():
    """Initialize session state variables"""
    if 'book_content' not in st.session_state:
        st.session_state.book_content = None
    if 'book_analysis' not in st.session_state:
        st.session_state.book_analysis = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_book' not in st.session_state:
        st.session_state.current_book = None


def add_to_chat_history(question: str, answer: str):
    """Add a Q&A pair to chat history"""
    st.session_state.chat_history.append({
        'timestamp': datetime.now(),
        'question': question,
        'answer': answer
    })


def display_chat_message(role: str, content: str, timestamp: datetime = None):
    """Display a chat message with proper styling"""
    if role == "user":
        st.write(f'<div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">'
                 f'<div style="background-color: #000000; padding: 1rem; border-radius: 10px; max-width: 80%;">'
                 f'<p style="margin: 0;"><strong>You:</strong> {content}</p>'
                 f'</div></div>', unsafe_allow_html=True)
    else:
        st.write(f'<div style="display: flex; justify-content: flex-start; margin-bottom: 1rem;">'
                 f'<div style="background-color: #000000; padding: 1rem; border-radius: 10px; max-width: 80%;">'
                 f'<p style="margin: 0;"><strong>Assistant:</strong> {content}</p>'
                 f'</div></div>', unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="Interactive Book Analyzer",
        page_icon="📚",
        layout="wide"
    )

    initialize_session_state()

    # Initialize analyzer
    analyzer = BookAnalyzer()

    # Sidebar for book upload and analysis
    with st.sidebar:
        st.title("📚 Book Upload")
        uploaded_file = st.file_uploader("Upload your book (PDF or TXT):", type=["pdf", "txt"])

        if uploaded_file is not None and uploaded_file != st.session_state.current_book:
            with st.spinner("Reading and analyzing your book..."):
                if uploaded_file.type == "application/pdf":
                    content = analyzer.read_pdf(uploaded_file)
                else:
                    try:
                        content = uploaded_file.read().decode("utf-8")
                    except Exception as e:
                        st.error("Error reading the file. Please try again.")
                        content = None

                if content:
                    st.session_state.book_content = content
                    analysis_result = analyzer.analyze_book(content)

                    if analysis_result['success']:
                        st.session_state.book_analysis = analysis_result['analysis']
                        st.session_state.current_book = uploaded_file
                        st.session_state.chat_history = []  # Reset chat history for new book
                        st.success("Book analyzed successfully!")
                    else:
                        st.error(f"Error analyzing book: {analysis_result['error']}")

        if st.session_state.book_analysis:
            with st.expander("📊 Book Analysis", expanded=True):
                st.write(st.session_state.book_analysis)

    # Main chat interface
    st.title("💬 Book Q&A Chat")

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for chat in st.session_state.chat_history:
            display_chat_message("user", chat['question'], chat['timestamp'])
            display_chat_message("assistant", chat['answer'], chat['timestamp'])

    # Question input
    st.markdown("---")
    if st.session_state.book_content:
        question = st.chat_input("Ask a question about the book...")

        if question:
            display_chat_message("user", question)

            with st.spinner("Thinking..."):
                answer = analyzer.answer_question(question, st.session_state.book_content)
                display_chat_message("assistant", answer)
                add_to_chat_history(question, answer)

            # Scroll to bottom (doesn't always work perfectly in Streamlit)
            js = f"""
                <script>
                    function scroll() {{
                        var chatContainer = document.querySelector('.stChatFloatingInputContainer');
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }}
                    scroll();
                </script>
                """
            st.components.v1.html(js)
    else:
        st.info("👈 Please upload a book to start the conversation!")


if __name__ == "__main__":
    main()