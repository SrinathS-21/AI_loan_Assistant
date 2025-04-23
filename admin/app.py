from flask import Flask, render_template, request, flash, redirect, url_for, session, get_flashed_messages, jsonify
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import weaviate
from pypdf import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv
import os
from pymongo import MongoClient
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages and session

# Load environment variables
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize MongoDB Client
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['loan_advisor_db']  # Changed to loan_advisor_db
community_posts = db['community_posts']  # Changed to community_posts

# Initialize Weaviate Client
client = weaviate.Client(
    url=WEAVIATE_URL,
    auth_client_secret=weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Function to create Weaviate schema for a collection
def create_weaviate_schema(class_name):
    schema = {
        "class": class_name,
        "vectorizer": "none",
        "properties": [
            {"name": "text", "dataType": ["text"]},
            {"name": "sequence", "dataType": ["int"]}
        ]
    }
    if not client.schema.exists(class_name):
        client.schema.create_class(schema)
        print(f"Created Weaviate class: {class_name}")
    else:
        print(f"Class {class_name} already exists")
    return class_name

# Create schemas for both Admin and Books_data collections on startup
create_weaviate_schema("Admin")
create_weaviate_schema("Books_data")

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
def upload_to_weaviate(chunks, embeddings, collection_name):
    """Upload chunks and embeddings to the specified Weaviate collection with sequence."""
    try:
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            data_object = {
                "text": chunk,
                "sequence": i
            }
            client.data_object.create(
                data_object=data_object,
                class_name=collection_name,
                vector=embedding
            )
            print(f"Uploaded chunk {i+1}/{len(chunks)} with sequence {i} to {collection_name}")
        print(f"Total number of chunks uploaded to {collection_name}: {len(chunks)}")
    except Exception as e:
        raise Exception(f"Error uploading to Weaviate: {str(e)}")

# Step 5: Count objects in the specified collection
def count_objects_in_collection(collection_name):
    """Count the number of objects in the specified Weaviate collection."""
    try:
        response = client.query.aggregate(collection_name).with_meta_count().do()
        count = response["data"]["Aggregate"][collection_name][0]["meta"]["count"]
        print(f"Total number of objects in the {collection_name} collection: {count}")
        return count
    except Exception as e:
        raise Exception(f"Error counting objects in {collection_name}: {str(e)}")

# Main function to process admin PDF
def process_admin_pdf(pdf_path, collection_name):
    """Process the admin PDF and upload to the specified Weaviate collection."""
    try:
        text = extract_text_from_pdf(pdf_path)
        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)
        upload_to_weaviate(chunks, embeddings, collection_name)
        count = count_objects_in_collection(collection_name)
        return f"Processed and uploaded {len(chunks)} chunks successfully to {collection_name}. Total objects in {collection_name}: {count}"
    except Exception as e:
        raise Exception(f"Failed to process admin PDF: {str(e)}")

# Fetch data from Books_data
def fetch_books_data(limit=5):
    try:
        result = client.query.get("Books_data", ["text", "sequence"]).with_limit(limit).do()
        print(f"Weaviate query result: {result}")

        if 'data' not in result or 'Get' not in result['data'] or 'Books_data' not in result['data']['Get']:
            print("Error: Unexpected response structure from Weaviate.")
            return ""

        chunks = result['data']['Get']['Books_data']
        if not chunks:
            print("No data found in Books_data collection.")
            return ""

        sorted_chunks = sorted(chunks, key=lambda x: x['sequence'])
        context = ' '.join([item['text'] for item in sorted_chunks])
        print(f"Fetched {len(sorted_chunks)} chunks from Books_data")
        return context
    except Exception as e:
        print(f"Error fetching data from Books_data: {str(e)}")
        return ""

# Generate article using Gemini
def generate_post_from_books_data():
    try:
        context = fetch_books_data(limit=5)
        author = "Ramit Sethi"
        prompt = f"""
        Using the following context from a database, write a small article (150–200 words) with a heading and author.
        Context: {context if context else "No specific context available; use general knowledge about loans or books."}

        Set the author as '{author}'.
        Format the output as a JSON object with keys: 'heading', 'author', and 'article'.
        """
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        print(f"Gemini raw response: {response.text}")

        cleaned_response = response.text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        try:
            article_json = json.loads(cleaned_response)
            article_json['author'] = author
            return article_json
        except json.JSONDecodeError:
            print("Gemini response is not valid JSON. Using fallback.")
            return {
                "heading": "Generated Article",
                "author": author,
                "article": response.text.strip() if response.text.strip() else "No content generated."
            }
    except genai.exceptions.ResourceExhausted as e:
        print(f"Rate limit exceeded: {str(e)}")
        return {
            "heading": "Quota Exceeded",
            "author": "System",
            "article": "Unable to generate article due to API quota limits. Please try again later."
        }
    except Exception as e:
        print(f"Error generating post: {str(e)}")
        return {
            "heading": "Error Generating Post",
            "author": "System",
            "article": f"Failed to generate post due to: {str(e)}"
        }

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('D:/pythonProject1/admins.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

# Call init_db when the app starts
init_db()

# Middleware to check if admin is logged in
def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__  # Preserve the function name for Flask
    return wrapper

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return redirect(url_for('upload_pdf'))

@app.route('/admin')
def admin_page():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return redirect(url_for('upload_pdf'))

@app.route('/admin/upload', methods=['GET', 'POST'])
@login_required
def upload_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('upload_pdf'))
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('upload_pdf'))
        collection_name = request.form.get('collection_name')
        if collection_name not in ['Admin', 'Books_data']:
            flash('Invalid collection name. Please select either "Admin" or "Books_data".', 'error')
            return redirect(url_for('upload_pdf'))
        if pdf_file and pdf_file.filename.endswith('.pdf'):
            try:
                pdf_path = os.path.join("uploads", pdf_file.filename)
                pdf_file.save(pdf_path)
                message = process_admin_pdf(pdf_path, collection_name)
                flash(message, 'success')
            except Exception as e:
                flash(f"Error processing PDF: {str(e)}", 'error')
            return redirect(url_for('upload_pdf'))
        flash('Invalid file format. Please upload a PDF.', 'error')
        return redirect(url_for('upload_pdf'))
    messages = get_flashed_messages(with_categories=True)
    message = None
    success = False
    if messages:
        for category, msg in messages:
            message = msg
            success = (category == 'success')
            break
    return render_template('admin_upload.html', message=message, success=success)

@app.route('/admin/post', methods=['GET', 'POST'])
@login_required
def post_article():
    if request.method == 'POST':
        heading = request.form.get('heading')
        article = request.form.get('article')
        author = request.form.get('author')
        if heading and article and author:
            post_data = {
                "title": heading,
                "author": author,
                "description": article,
                "image_url": None,
                "created_at": datetime.utcnow(),
                "likes": 0,
                "liked_by": [],
                "dislikes": 0,
                "disliked_by": [],
                "comments": 0
            }
            result = community_posts.insert_one(post_data)  # Changed to community_posts
            print(f"Inserted post with ID: {result.inserted_id}")  # Debug log
            flash('Post created successfully!', 'success')
            return redirect(url_for('post_article'))
        flash('No post data to submit.', 'error')
        return redirect(url_for('post_article'))
    messages = get_flashed_messages(with_categories=True)
    message = None
    success = False
    if messages:
        for category, msg in messages:
            message = msg
            success = (category == 'success')
            break
    return render_template('admin_post.html', article_message=message, article_success=success, generated_heading=None, generated_article=None, generated_author=None)

@app.route('/generate_post', methods=['GET'])
@login_required
def generate_post():
    result = generate_post_from_books_data()
    if result.get("heading") and result.get("article"):  # Check if the result contains valid data
        return jsonify({
            "success": True,
            "heading": result["heading"],
            "author": result["author"],
            "article": result["article"]
        })
    return jsonify({"success": False, "message": result["article"] if "article" in result else "Failed to generate post"})

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Hash the password
        hashed_password = generate_password_hash(password)

        try:
            # Store in SQLite
            conn = sqlite3.connect('D:/pythonProject1/admins.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO admins (email, password) VALUES (?, ?)', (email, hashed_password))
            conn.commit()
            conn.close()

            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('admin_login'))
        except sqlite3.IntegrityError:
            flash('Email already exists. Please use a different email.', 'error')
            return redirect(url_for('admin_signup'))
    messages = get_flashed_messages(with_categories=True)
    message = None
    success = False
    if messages:
        for category, msg in messages:
            message = msg
            success = (category == 'success')
            break
    return render_template('admin_signup.html', message=message, success=success)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check credentials
        conn = sqlite3.connect('D:/pythonProject1/admins.db')
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM admins WHERE email = ?', (email,))
        result = cursor.fetchone()
        conn.close()

        if result and check_password_hash(result[0], password):
            session['logged_in'] = True
            session['email'] = email
            print(f"Logged in user: {session['email']}")  # Debug log
            flash('Login successful!', 'success')
            return redirect(url_for('upload_pdf'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('admin_login'))
    messages = get_flashed_messages(with_categories=True)
    message = None
    success = False
    if messages:
        for category, msg in messages:
            message = msg
            success = (category == 'success')
            break
    return render_template('admin_login.html', message=message, success=success)

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    session.pop('email', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)