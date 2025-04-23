import weaviate
from pypdf import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize Weaviate Client
client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Step 1: Extract text from PDF
def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file path."""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            reader = PdfReader(pdf_file)
            text = ''
            for page in reader.pages:
                text += page.extract_text() or ""
            if not text.strip():
                raise ValueError("No text extracted from PDF")
            print("Text extracted from PDF successfully")
            return text
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

# Step 2: Chunk the text
def chunk_text(text, chunk_size=500):
    """Chunk text into segments of specified word size."""
    words = text.split()
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    print(f"Text chunked into {len(chunks)} segments")
    return chunks

# Step 3: Generate embeddings using Gemini
def generate_embeddings(chunks):
    """Generate embeddings for text chunks using Gemini."""
    embeddings = []
    for chunk in chunks:
        try:
            response = genai.embed_content(
                model="models/embedding-001",
                content=chunk,
                task_type="retrieval_document"
            )
            embeddings.append(response['embedding'])
        except Exception as e:
            raise Exception(f"Error generating embedding for chunk: {str(e)}")
    print(f"Generated embeddings for {len(embeddings)} chunks")
    return embeddings

# Step 4: Upload to Weaviate
def upload_to_weaviate(chunks, embeddings, collection_name="Books_data"):
    """Upload chunks and embeddings to Weaviate Books_data collection with sequence."""
    try:
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            data_object = {
                "text": chunk,
                "sequence": i  # Add sequence number (0, 1, 2, ...)
            }
            client.data_object.create(
                data_object=data_object,
                class_name=collection_name,
                vector=embedding
            )
            print(f"Uploaded chunk {i+1}/{len(chunks)} with sequence {i}")
        print(f"Total number of chunks uploaded: {len(chunks)}")
    except Exception as e:
        raise Exception(f"Error uploading to Weaviate: {str(e)}")


# Step 5: Count objects in the Admin collection
def count_objects_in_collection(collection_name="Books_data"):
    """Count the number of objects in the specified Weaviate collection."""
    try:
        response = client.query.aggregate(collection_name).with_meta_count().do()
        count = response["data"]["Aggregate"][collection_name][0]["meta"]["count"]
        print(f"Total number of objects in the {collection_name} collection: {count}")
        return count
    except Exception as e:
        raise Exception(f"Error counting objects in {collection_name}: {str(e)}")

# Main function to process admin PDF
def process_admin_pdf(pdf_path):
    """Process the admin PDF and upload to Weaviate."""
    try:
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)
        upload_to_weaviate(chunks, embeddings)
        count = count_objects_in_collection()
        return f"Processed and uploaded {len(chunks)} chunks successfully. Total objects in Admin: {count}"
    except Exception as e:
        raise Exception(f"Failed to process admin PDF: {str(e)}")

if __name__ == "__main__":
    # Example usage for testing
    test_pdf_path = "path/to/test.pdf"
    print(process_admin_pdf(test_pdf_path))