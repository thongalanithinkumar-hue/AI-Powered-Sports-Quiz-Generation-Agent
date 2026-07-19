import os
import warnings
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root
# Try loading it from the current working directory, and also standard locations
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    warnings.warn(
        "GROQ_API_KEY environment variable is not set. "
        "Make sure to create a .env file or set it in your environment."
    )

def get_api_key():
    """Return the current GROQ API key or search env again."""
    return os.getenv("GROQ_API_KEY")
