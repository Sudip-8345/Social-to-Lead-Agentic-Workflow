from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')

llm = ChatGroq(
    model="llama-3.3-70b-versatile",  
    temperature=0.2,
    max_tokens=1024,
    max_retries=3,
)

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
