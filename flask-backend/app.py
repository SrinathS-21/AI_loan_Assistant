from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import bcrypt
import os
import re
from dotenv import load_dotenv
import weaviate
from weaviate.auth import AuthApiKey
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from langchain_community.vectorstores import Weaviate
from community import community_bp
from profile import profile_bp
import requests
from langdetect import detect, DetectorFactory
import logging
import base64  # Added for voice handling
from werkzeug.utils import secure_filename  # Added for secure file handling

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

# Initialize Weaviate Client (v3 syntax)
try:
    if WEAVIATE_URL and WEAVIATE_API_KEY:
        weaviate_client = weaviate.Client(
            url=WEAVIATE_URL,
            auth_client_secret=AuthApiKey(api_key=WEAVIATE_API_KEY)
        )
        weaviate_client.get_meta()
        print("Successfully connected to Weaviate Cloud")
    else:
        print("Weaviate URL or API key not provided, skipping Weaviate initialization")
        weaviate_client = None
except Exception as e:
    print(f"Failed to initialize Weaviate client: {str(e)}")
    weaviate_client = None

app = Flask(__name__)
CORS(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET', 'your_jwt_secret_key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# MongoDB Atlas Connection
mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    raise ValueError("MONGODB_URI not set in environment variables")

try:
    mongo_client = MongoClient(mongodb_uri)
    mongo_client.server_info()
    print("Successfully connected to MongoDB Atlas")
except ConnectionFailure as e:
    print(f"Failed to connect to MongoDB Atlas: {e}")
    raise

db = mongo_client['loanadvisor']
users_collection = db['users']

# Register blueprints
app.register_blueprint(community_bp)
app.register_blueprint(profile_bp)

# Initialize Embedding Model
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)

# Sarvam API Configuration
SARVAM_API_KEY = "cf07b2de-ce8b-40b8-ae96-b26faeef4acd"
SARVAM_STT_ENDPOINT = "https://api.sarvam.ai/speech-to-text"
SARVAM_TRANSLATE_ENDPOINT = "https://api.sarvam.ai/translate"
SARVAM_TTS_ENDPOINT = "https://api.sarvam.ai/text-to-speech"  # Confirm this endpoint with Sarvam documentation
SUPPORTED_AUDIO_FORMATS = ["wav", "mp3"]
SUPPORTED_LANGUAGES = ["en", "hi", "ta", "te", "kn", "ml", "gu", "mr", "bn", "pa", "or", "es"]
MAX_TRANSLATE_CHARS = 900

# File upload configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'wav', 'mp3'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure consistent language detection
DetectorFactory.seed = 0

# Custom exception for multilingual support errors
class MultilingualError(Exception):
    """Custom exception for multilingual support errors."""
    pass

# Detect the language of the input text
def detect_language(text):
    """Detect the language of the input text."""
    if not text.strip():
        logger.error("Cannot detect language: Input text is empty")
        raise MultilingualError("Cannot detect language: Input text is empty")

    try:
        lang = detect(text)
        logger.debug(f"Detected language: {lang}")
        return lang
    except Exception as e:
        logger.error(f"Language detection failed: {str(e)}")
        raise MultilingualError(f"Language detection failed: {str(e)}")

# Translate the input text to English using Sarvam's Translation API
def translate_to_english(text, source_language=None):
    """Translate the input text to English using Sarvam's Translation API."""
    try:
        if not source_language:
            source_language = detect_language(text)

        if source_language == "en":
            logger.debug("Text is already in English, skipping translation")
            return text

        if source_language not in SUPPORTED_LANGUAGES:
            logger.warning(
                f"Language '{source_language}' is not supported by Sarvam API. Returning original text: {text}")
            return text

        language_mapping = {
            'en': 'en-IN', 'hi': 'hi-IN', 'ta': 'ta-IN', 'te': 'te-IN', 'kn': 'kn-IN',
            'ml': 'ml-IN', 'gu': 'gu-IN', 'mr': 'mr-IN', 'bn': 'bn-IN', 'pa': 'pa-IN',
            'or': 'od-IN', 'es': 'es'
        }
        source_lang_code = language_mapping.get(source_language, source_language + '-IN')
        target_lang_code = 'en-IN'

        if len(text) > MAX_TRANSLATE_CHARS:
            chunks = [text[i:i + MAX_TRANSLATE_CHARS] for i in range(0, len(text), MAX_TRANSLATE_CHARS)]
            translated_chunks = []
            for chunk in chunks:
                payload = {
                    'input': chunk,
                    'source_language_code': source_lang_code,
                    'target_language_code': target_lang_code
                }
                headers = {
                    'api-subscription-key': SARVAM_API_KEY,
                    'Content-Type': 'application/json'
                }
                logger.debug(f"Sending translation request - Payload: {payload}")
                response = requests.post(SARVAM_TRANSLATE_ENDPOINT, json=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    translated_text = result.get('translated_text', result.get('output', ''))
                    if not translated_text:
                        raise MultilingualError("Translation API returned empty text")
                    translated_chunks.append(translated_text)
                else:
                    raise MultilingualError(f"Translation API error: {response.status_code} - {response.text}")
            return ' '.join(translated_chunks)

        payload = {
            'input': text,
            'source_language_code': source_lang_code,
            'target_language_code': target_lang_code
        }
        headers = {
            'api-subscription-key': SARVAM_API_KEY,
            'Content-Type': 'application/json'
        }
        logger.debug(f"Sending translation request - Payload: {payload}")
        response = requests.post(SARVAM_TRANSLATE_ENDPOINT, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            translated_text = result.get('translated_text', result.get('output', ''))
            if not translated_text:
                logger.error("Translation API returned empty text")
                raise MultilingualError("Translation API returned empty text")
            logger.debug(f"Translation successful: {translated_text}")
            return translated_text
        else:
            logger.error(f"Translation API error: {response.status_code} - {response.text}")
            raise MultilingualError(f"Translation API error: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during translation: {str(e)}")
        raise MultilingualError(f"Network error during translation: {str(e)}")
    except Exception as e:
        logger.error(f"Error in translate_to_english: {str(e)}")
        raise MultilingualError(f"Error in translate_to_english: {str(e)}")

# Translate English response back to the user's language
def translate_to_user_language(text, target_language):
    """Translate the English response back to the user's language using Sarvam API."""
    if target_language == "en":
        return text

    try:
        language_mapping = {
            'en': 'en-IN', 'hi': 'hi-IN', 'ta': 'ta-IN', 'te': 'te-IN', 'kn': 'kn-IN',
            'ml': 'ml-IN', 'gu': 'gu-IN', 'mr': 'mr-IN', 'bn': 'bn-IN', 'pa': 'pa-IN',
            'or': 'od-IN', 'es': 'es'
        }
        source_lang_code = 'en-IN'
        target_lang_code = language_mapping.get(target_language, target_language)

        if len(text) > MAX_TRANSLATE_CHARS:
            chunks = [text[i:i + MAX_TRANSLATE_CHARS] for i in range(0, len(text), MAX_TRANSLATE_CHARS)]
            translated_chunks = []
            for chunk in chunks:
                payload = {
                    'input': chunk,
                    'source_language_code': source_lang_code,
                    'target_language_code': target_lang_code
                }
                headers = {
                    'api-subscription-key': SARVAM_API_KEY,
                    'Content-Type': 'application/json'
                }
                print(f"Sending translation request (English to {target_language}) - Payload: {payload}")
                response = requests.post(SARVAM_TRANSLATE_ENDPOINT, json=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    translated_text = result.get('translated_text', result.get('output', ''))
                    if not translated_text:
                        raise MultilingualError("Translation API returned empty text for response translation")
                    translated_chunks.append(translated_text)
                else:
                    raise MultilingualError(f"Translation API error: {response.status_code} - {response.text}")
            return ' '.join(translated_chunks)

        payload = {
            'input': text,
            'source_language_code': source_lang_code,
            'target_language_code': target_lang_code
        }
        headers = {
            'api-subscription-key': SARVAM_API_KEY,
            'Content-Type': 'application/json'
        }
        print(f"Sending translation request (English to {target_language}) - Payload: {payload}")
        response = requests.post(SARVAM_TRANSLATE_ENDPOINT, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            translated_text = result.get('translated_text', result.get('output', ''))
            if not translated_text:
                raise MultilingualError("Translation API returned empty text for response translation")
            print(f"Translated response to {target_language}: {translated_text}")
            return translated_text
        else:
            print(f"Translation API error (English to {target_language}): {response.status_code} - {response.text}")
            return f"Translation failed, response in English: {text}"
    except Exception as e:
        print(f"Error translating response to {target_language}: {str(e)}")
        return f"Translation failed, response in English: {text}"

# Helper function for voice file validation
def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Speech-to-Text using Sarvam AI
def speech_to_text(audio_file_path, language_code="ta-IN"):
    """Convert audio to text using Sarvam AI's Speech-to-Text API."""
    try:
        with open(audio_file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        payload = {
            "audio": audio_base64,
            "language_code": language_code
        }
        headers = {
            'api-subscription-key': SARVAM_API_KEY,
            'Content-Type': 'application/json'
        }
        logger.debug(f"Sending STT request - Payload: {payload}")
        response = requests.post(SARVAM_STT_ENDPOINT, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            transcribed_text = result.get('transcription', '')
            if not transcribed_text:
                raise MultilingualError("STT API returned empty transcription")
            logger.debug(f"STT successful: {transcribed_text}")
            return transcribed_text
        else:
            logger.error(f"STT API error: {response.status_code} - {response.text}")
            raise MultilingualError(f"STT API error: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"Error in speech_to_text: {str(e)}")
        raise MultilingualError(f"Error in speech_to_text: {str(e)}")

# Text-to-Speech using Sarvam AI
def text_to_speech(text, language_code="ta-IN", voice_id="default"):
    """Convert text to audio using Sarvam AI's Text-to-Speech API."""
    try:
        payload = {
            "text": text,
            "language_code": language_code,
            "voice_id": voice_id
        }
        headers = {
            'api-subscription-key': SARVAM_API_KEY,
            'Content-Type': 'application/json'
        }
        logger.debug(f"Sending TTS request - Payload: {payload}")
        response = requests.post(SARVAM_TTS_ENDPOINT, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            audio_base64 = result.get('audio', '')
            if not audio_base64:
                raise MultilingualError("TTS API returned empty audio")
            
            audio_data = base64.b64decode(audio_base64)
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], "response_audio.wav")
            with open(output_path, "wb") as f:
                f.write(audio_data)
            logger.debug(f"TTS successful, audio saved to: {output_path}")
            return output_path
        else:
            logger.error(f"TTS API error: {response.status_code} - {response.text}")
            raise MultilingualError(f"TTS API error: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}")
        raise MultilingualError(f"Error in text_to_speech: {str(e)}")

# Helper function to format user data
def format_user_data(user):
    fields = {
        'name': user.get('name', 'N/A'),
        'email': user.get('email', 'N/A'),
        'contactNumber': user.get('contactNumber', 'N/A'),
        'dateOfBirth': user.get('dateOfBirth', 'N/A'),
        'gender': user.get('gender', 'N/A'),
        'maritalStatus': user.get('maritalStatus', 'N/A'),
        'nationality': user.get('nationality', 'N/A'),
        'residentialAddressCurrent': user.get('residentialAddressCurrent', 'N/A'),
        'residentialAddressPermanent': user.get('residentialAddressPermanent', 'N/A')
    }
    formatted_string = ', '.join(f"{key}: {value}" for key, value in fields.items())
    return formatted_string

# Function to create Weaviate schema for a user
def create_user_schema(client, user_id):
    class_name = f"User_{user_id}"
    schema = {
        "class": class_name,
        "vectorizer": "none",
        "properties": [
            {"name": "content", "dataType": ["text"]}
        ]
    }
    exists = client.schema.exists(class_name)
    if not exists:
        client.schema.create_class(schema)
        print(f"Created Weaviate class: {class_name}")
    else:
        print(f"Class {class_name} already exists")
    return class_name, exists

# Chunk text for Weaviate
def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    print(f"Text chunked into {len(chunks)} segments")
    return chunks

# Generate embeddings
def generate_embeddings(chunks):
    try:
        embeddings_list = embeddings.embed_documents(chunks)
        print(f"Generated embeddings for {len(embeddings_list)} chunks")
        return embeddings_list
    except Exception as e:
        raise Exception(f"Error generating embedding for chunk: {str(e)}")

# QA Chain Setup
def get_conversational_chain():
    prompt_template = """You are a professional and friendly loan advisor for all banks. Assist users with loan-related queries based on their profile and general admin guidelines stored in Weaviate. Provide concise, structured, and user-friendly responses in the same language as the user’s question, limited to 150-200 words.

    *Admin Context:* {context}  
    *User Profile:* {user_profile}  
    *Current Question:* {question}  

    ### *Response Guidelines:*
    - **Greeting & Acknowledgment**:  
      Greet the user by name (if available) or generically and acknowledge the query briefly. This should be a standalone paragraph before any section.  

    - **Eligibility Criteria** (if applicable or assumed):  
      List 2-3 key eligibility points as bullet points using '* - '. Flag profile issues (e.g., future date of birth) under a separate section '- **Profile Issue:**'.  

    - **Loan Details** (if applicable):  
      List 2-3 key details (e.g., tenure, interest rate) as bullet points using '* - '.  

    - **Required Information** (if needed):  
      List up to 3 missing details as numbered points (e.g., '1. ', '2. '). Provide a brief explanation for each.  

    - **Next Steps & Support**:  
      Offer 1-2 actionable steps and include a call to action (e.g., "Would you like help with this?").  

    *Constraints:*  
    - Always start sections with '- **Section Name:**' (e.g., '- **Eligibility Criteria:**').  
    - Use '* - ' for bullet points under sections.  
    - Use numbered lists (e.g., '1. ') for required information.  
    - Avoid markdown symbols like '**' within the content (e.g., do not bold individual words in sentences).  
    - Avoid jargon unless explained.  
    - Focus on general bank loan data from the admin context.  
    - If the query is vague, assume it’s about loan eligibility or application and provide relevant details.

    *Answer:*  
    (Generate a structured response following the guidelines.)"""

    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.2, google_api_key=GOOGLE_API_KEY)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "user_profile", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

# General conversational response
def get_general_response(user_message, user_profile):
    model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.2, google_api_key=GOOGLE_API_KEY)
    if "hi" in user_message.lower() or "hello" in user_message.lower():
        return "Hi there! Welcome to your loan assistant. How can I help you with your loan needs today?"
    elif "name" in user_message.lower() and "?" in user_message:
        try:
            name_part = user_profile.split("name:")[1].split(",")[0].strip()
            return f"Nice to meet you! Your name is {name_part}, according to your profile."
        except IndexError:
            return "I don’t have your name yet. Please update your profile so I can assist you better!"
    else:
        response = model.invoke(f"Respond conversationally to: '{user_message}' as a loan assistant")
        return response.content

# Function to convert structured text to HTML string
def format_response_to_html(text):
    if not text or not isinstance(text, str):
        return "<p>Error: Invalid response format.</p>"

    lines = text.split('\n')
    html_lines = []
    in_list = False
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('- **'):
            if in_list:
                html_lines.append('</ul>' if current_section == 'bulleted' else '</ol>')
                in_list = False
            section_title = line[4:line.rfind(':**')].strip() if line.endswith(':**') else line[4:].strip()
            html_lines.append(f'<strong>{section_title}:</strong>')
            continue
        elif line.startswith('* - '):
            if not in_list or current_section == 'numbered':
                if in_list:
                    html_lines.append('</ol>' if current_section == 'numbered' else '</ul>')
                html_lines.append('<ul>')
                in_list = True
                current_section = 'bulleted'
            item = line.replace('* - ', '').strip()
            html_lines.append(f'<li>{item}</li>')
        elif re.match(r'^\d+\.', line):
            if not in_list or current_section == 'bulleted':
                if in_list:
                    html_lines.append('</ul>' if current_section == 'bulleted' else '</ol>')
                html_lines.append('<ol>')
                in_list = True
                current_section = 'numbered'
            item = line[line.find(' ') + 1:].strip()
            html_lines.append(f'<li>{item}</li>')
        else:
            if in_list:
                html_lines.append('</ul>' if current_section == 'bulleted' else '</ol>')
                in_list = False
            html_lines.append(f'<p>{line}</p>')

    if in_list:
        html_lines.append('</ul>' if current_section == 'bulleted' else '</ol>')

    return ''.join(html_lines)

# Root route
@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Flask server is running!'})

# Register Route
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        date_of_birth = data.get('dateOfBirth')
        gender = data.get('gender')
        marital_status = data.get('maritalStatus')
        contact_number = data.get('contactNumber')
        residential_address_current = data.get('residentialAddressCurrent')
        residential_address_permanent = data.get('residentialAddressPermanent')
        nationality = data.get('nationality')

        required_fields = ['name', 'email', 'password']
        if not all(data.get(field) for field in required_fields):
            return jsonify({'message': 'Missing required fields: name, email, password'}), 400

        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            return jsonify({'message': 'User already exists'}), 400

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        profile_completed = all([date_of_birth, gender, marital_status, contact_number,
                               residential_address_current, residential_address_permanent, nationality])
        user = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'dateOfBirth': date_of_birth,
            'gender': gender,
            'maritalStatus': marital_status,
            'contactNumber': contact_number,
            'residentialAddressCurrent': residential_address_current,
            'residentialAddressPermanent': residential_address_permanent,
            'nationality': nationality,
            'profileCompleted': profile_completed,
            'createdAt': datetime.utcnow()
        }
        result = users_collection.insert_one(user)
        user_id = str(result.inserted_id)
        print(f"Registered user with _id: {user_id}")

        access_token = create_access_token(identity=user_id)
        return jsonify({
            'token': access_token,
            'user': {
                'id': user_id,
                'name': name,
                'email': email,
                'profileCompleted': profile_completed,
                'requiresProfileCompletion': not profile_completed
            }
        }), 201

    except Exception as e:
        print(f"Register error: {e}")
        return jsonify({'message': f'Server error: {str(e)}'}), 500

# Login Route
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({'message': 'Missing required fields: email, password'}), 400

        user = users_collection.find_one({'email': email})
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return jsonify({'message': 'Invalid credentials'}), 400

        access_token = create_access_token(identity=str(user['_id']))
        return jsonify({
            'token': access_token,
            'user': {
                'id': str(user['_id']),
                'name': user.get('name'),
                'email': user.get('email'),
                'profileCompleted': user.get('profileCompleted', False)
            }
        })

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'message': f'Server error: {str(e)}'}), 500

# Profile Update Route
@app.route('/api/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        update_data = {
            'dateOfBirth': data.get('dateOfBirth'),
            'gender': data.get('gender'),
            'maritalStatus': data.get('maritalStatus'),
            'contactNumber': data.get('contactNumber'),
            'residentialAddressCurrent': data.get('residentialAddressCurrent'),
            'residentialAddressPermanent': data.get('residentialAddressPermanent'),
            'nationality': data.get('nationality'),
            'profileCompleted': True,
            'updatedAt': datetime.utcnow()
        }
        user = users_collection.find_one_and_update(
            {'_id': ObjectId(user_id)},
            {'$set': {k: v for k, v in update_data.items() if v is not None}},
            return_document=True
        )
        if not user:
            return jsonify({'message': 'User not found'}), 400

        formatted_data = format_user_data(user)
        print(f"Updated user data for _id {user_id}: {formatted_data}")

        if weaviate_client:
            class_name, exists = create_user_schema(weaviate_client, user_id)
            try:
                if exists:
                    result = weaviate_client.data_object.get(class_name=class_name)
                    if result and 'objects' in result:
                        for obj in result['objects']:
                            weaviate_client.data_object.delete(
                                uuid=obj['_additional']['id'],
                                class_name=class_name
                            )
                    print(f"Deleted existing objects in Weaviate class: {class_name}")

                chunks = chunk_text(formatted_data, chunk_size=500)
                embeddings_list = generate_embeddings(chunks)
                user_vector_store = Weaviate(
                    client=weaviate_client,
                    index_name=class_name,
                    text_key="content",
                    embedding=embeddings,
                    by_text=False
                )
                user_vector_store.add_texts(chunks, embeddings=embeddings_list)
                print(f"Stored/Updated user data in Weaviate class: {class_name}")
            except Exception as e:
                print(f"Error storing/updating data in Weaviate: {str(e)}")

        return jsonify({
            'user': {
                'id': str(user['_id']),
                'name': user.get('name'),
                'email': user.get('email'),
                'profileCompleted': user.get('profileCompleted', True)
            }
        })

    except Exception as e:
        print(f"Profile update error: {e}")
        return jsonify({'message': f'Error updating profile: {str(e)}'}), 500

# Loan Eligibility Route
@app.route('/api/loan-eligibility', methods=['POST'])
@jwt_required()
def check_loan_eligibility():
    try:
        data = request.get_json()
        income = float(data.get('income', 0))
        debt = float(data.get('debt', 0))
        eligibility = income > debt * 3
        return jsonify({
            'eligible': eligibility,
            'message': 'Eligible' if eligibility else 'Not eligible based on income vs debt ratio'
        })
    except Exception as e:
        print(f"Loan eligibility error: {e}")
        return jsonify({'message': f'Error checking eligibility: {str(e)}'}), 500

# Fetch User Details
@app.route('/api/user-details', methods=['GET'])
@jwt_required()
def get_user_details():
    try:
        user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'User not found'}), 404

        formatted_data = format_user_data(user)
        print(f"Fetched user details for _id {user_id}: {formatted_data}")
        return jsonify({'userDetails': formatted_data})

    except Exception as e:
        print(f"User details error: {e}")
        return jsonify({'message': f'Error fetching user details: {str(e)}'}), 500

# Debug route to test MongoDB connection
@app.route('/api/debug-db', methods=['GET'])
def debug_db():
    try:
        user_count = users_collection.count_documents({})
        return jsonify({'message': f'Connected to MongoDB! User count: {user_count}'})
    except Exception as e:
        return jsonify({'message': f'Failed to connect to MongoDB: {str(e)}'}), 500

# Chat Route for Text-Based Conversation
@app.route('/api/chat', methods=['POST'])
@jwt_required()
def chat():
    data = request.get_json()
    user_message = data.get('message')
    user_id = get_jwt_identity()
    print(f"User {user_id} entered in chat: {user_message}")

    if not user_message:
        return jsonify({'error': 'Message required'}), 400

    try:
        original_language = detect_language(user_message)
        print(f"Original language detected: {original_language}")
        if original_language != "en":
            user_message_english = translate_to_english(user_message, original_language)
            print(f"Translated user message to English: {user_message_english}")
        else:
            user_message_english = user_message

        eligibility_keywords = ["eligible", "eligibility", "criteria", "requirements", "verify", "check", "checking", "assess", "qualify", "suitability"]
        apply_keywords = ["apply", "application", "how to", "steps"]
        interest_keywords = ["interest", "rate", "cost"]
        help_keywords = ["help", "guide"]

        is_eligibility = any(keyword in user_message_english.lower() for keyword in eligibility_keywords)
        if not is_eligibility and "loan" in user_message_english.lower():
            user_message_english = f"{user_message_english} Please check eligibility."
            print(f"Rephrased query for eligibility: {user_message_english}")

        user_class_name = f"User_{user_id}"
        user_vector_store = Weaviate(
            client=weaviate_client,
            index_name=user_class_name,
            text_key="content",
            embedding=embeddings,
            by_text=False
        )
        user_docs = user_vector_store.similarity_search(user_message_english, k=1)
        user_profile = "\n".join([d.page_content for d in user_docs]) if user_docs else "No profile data available."

        user_name = "there"
        try:
            if user_profile and "name:" in user_profile:
                user_name = user_profile.split("name:")[1].split(",")[0].strip()
        except IndexError:
            user_name = "there"

        admin_vector_store = Weaviate(
            client=weaviate_client,
            index_name="Admin",
            text_key="text",
            embedding=embeddings,
            by_text=False
        )
        admin_docs = admin_vector_store.similarity_search(user_message_english, k=10)
        print(f"Retrieved admin documents: {admin_docs}")

        chain = get_conversational_chain()

        is_eligibility = any(keyword in user_message_english.lower() for keyword in eligibility_keywords)
        is_apply = any(keyword in user_message_english.lower() for keyword in apply_keywords)
        is_interest = any(keyword in user_message_english.lower() for keyword in interest_keywords)
        is_help = any(keyword in user_message_english.lower() for keyword in help_keywords)

        print(f"Keyword checks - Eligibility: {is_eligibility}, Apply: {is_apply}, Interest: {is_interest}, Help: {is_help}")

        if any(keyword in user_message_english.lower() for keyword in ["hi", "hello", "hey"]):
            response = get_general_response(user_message_english, user_profile)
        elif "name" in user_message_english.lower() and "?" in user_message_english:
            response = get_general_response(user_message_english, user_profile)
        elif is_eligibility:
            print(f"Matched eligibility query: {user_message_english}")
            response = chain.invoke({
                "input_documents": admin_docs,
                "user_profile": user_profile,
                "question": f"Hi {user_name}! {user_message_english} Provide eligibility criteria for a car loan based on the admin guidelines. If income, debt, or other details are needed, guide me to provide them."
            })['output_text']
        elif is_apply:
            response = chain.invoke({
                "input_documents": admin_docs,
                "user_profile": user_profile,
                "question": f"Hi {user_name}! {user_message_english} Provide steps to apply for a car loan based on the admin guidelines."
            })['output_text']
        elif is_interest:
            response = chain.invoke({
                "input_documents": admin_docs,
                "user_profile": user_profile,
                "question": f"Hi {user_name}! {user_message_english} Provide interest rates for car loans based on the admin guidelines."
            })['output_text']
        elif is_help:
            response = chain.invoke({
                "input_documents": admin_docs,
                "user_profile": user_profile,
                "question": f"Hi {user_name}! I’m here to guide you! {user_message_english} How can I assist with your loan process today?"
            })['output_text']
        else:
            print(f"No specific match, assuming eligibility for loan query: {user_message_english}")
            response = chain.invoke({
                "input_documents": admin_docs,
                "user_profile": user_profile,
                "question": f"Hi {user_name}! {user_message_english} Provide eligibility criteria or general information for a car loan based on the admin guidelines."
            })['output_text']

        if original_language != "en":
            response = translate_to_user_language(response, original_language)

        formatted_response = format_response_to_html(response)
        print(f"Raw response: {response}")
        print(f"Formatted response: {formatted_response}")
        return jsonify({'response': formatted_response})
    except Exception as e:
        print(f"Error processing chat request: {str(e)}")
        return jsonify({'error': f"Oops! Something went wrong. Please try again later. Error: {str(e)}"}), 500

# Voice Chat Route for Voice-Based Conversation
@app.route('/api/voice-chat', methods=['POST'])
@jwt_required()
def voice_chat():
    user_id = get_jwt_identity()
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if audio_file and allowed_file(audio_file.filename):
        filename = secure_filename(audio_file.filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_file.save(audio_path)
        print(f"User {user_id} uploaded audio: {audio_path}")

        try:
            # Step 1: Convert audio to text (Speech-to-Text)
            user_language = "ta-IN"  # Assume Tamil for now
            user_message = speech_to_text(audio_path, language_code=user_language)
            print(f"Transcribed audio to text: {user_message}")

            # Step 2: Detect language of the transcribed text
            original_language = detect_language(user_message)
            print(f"Original language detected: {original_language}")

            # Step 3: Translate to English if non-English
            if original_language != "en":
                user_message_english = translate_to_english(user_message, original_language)
                print(f"Translated user message to English: {user_message_english}")
            else:
                user_message_english = user_message

            # Step 4: Process the query
            eligibility_keywords = ["eligible", "eligibility", "criteria", "requirements", "verify", "check", "checking", "assess", "qualify", "suitability"]
            apply_keywords = ["apply", "application", "how to", "steps"]
            interest_keywords = ["interest", "rate", "cost"]
            help_keywords = ["help", "guide"]

            is_eligibility = any(keyword in user_message_english.lower() for keyword in eligibility_keywords)
            if not is_eligibility and "loan" in user_message_english.lower():
                user_message_english = f"{user_message_english} Please check eligibility."
                print(f"Rephrased query for eligibility: {user_message_english}")

            user_class_name = f"User_{user_id}"
            user_vector_store = Weaviate(
                client=weaviate_client,
                index_name=user_class_name,
                text_key="content",
                embedding=embeddings,
                by_text=False
            )
            user_docs = user_vector_store.similarity_search(user_message_english, k=1)
            user_profile = "\n".join([d.page_content for d in user_docs]) if user_docs else "No profile data available."

            user_name = "there"
            try:
                if user_profile and "name:" in user_profile:
                    user_name = user_profile.split("name:")[1].split(",")[0].strip()
            except IndexError:
                user_name = "there"

            admin_vector_store = Weaviate(
                client=weaviate_client,
                index_name="Admin",
                text_key="text",
                embedding=embeddings,
                by_text=False
            )
            admin_docs = admin_vector_store.similarity_search(user_message_english, k=10)
            print(f"Retrieved admin documents: {admin_docs}")

            chain = get_conversational_chain()

            is_eligibility = any(keyword in user_message_english.lower() for keyword in eligibility_keywords)
            is_apply = any(keyword in user_message_english.lower() for keyword in apply_keywords)
            is_interest = any(keyword in user_message_english.lower() for keyword in interest_keywords)
            is_help = any(keyword in user_message_english.lower() for keyword in help_keywords)

            print(f"Keyword checks - Eligibility: {is_eligibility}, Apply: {is_apply}, Interest: {is_interest}, Help: {is_help}")

            if any(keyword in user_message_english.lower() for keyword in ["hi", "hello", "hey"]):
                response = get_general_response(user_message_english, user_profile)
            elif "name" in user_message_english.lower() and "?" in user_message_english:
                response = get_general_response(user_message_english, user_profile)
            elif is_eligibility:
                print(f"Matched eligibility query: {user_message_english}")
                response = chain.invoke({
                    "input_documents": admin_docs,
                    "user_profile": user_profile,
                    "question": f"Hi {user_name}! {user_message_english} Provide eligibility criteria for a car loan based on the admin guidelines. If income, debt, or other details are needed, guide me to provide them."
                })['output_text']
            elif is_apply:
                response = chain.invoke({
                    "input_documents": admin_docs,
                    "user_profile": user_profile,
                    "question": f"Hi {user_name}! {user_message_english} Provide steps to apply for a car loan based on the admin guidelines."
                })['output_text']
            elif is_interest:
                response = chain.invoke({
                    "input_documents": admin_docs,
                    "user_profile": user_profile,
                    "question": f"Hi {user_name}! {user_message_english} Provide interest rates for car loans based on the admin guidelines."
                })['output_text']
            elif is_help:
                response = chain.invoke({
                    "input_documents": admin_docs,
                    "user_profile": user_profile,
                    "question": f"Hi {user_name}! I’m here to guide you! {user_message_english} How can I assist with your loan process today?"
                })['output_text']
            else:
                print(f"No specific match, assuming eligibility for loan query: {user_message_english}")
                response = chain.invoke({
                    "input_documents": admin_docs,
                    "user_profile": user_profile,
                    "question": f"Hi {user_name}! {user_message_english} Provide eligibility criteria or general information for a car loan based on the admin guidelines."
                })['output_text']

            # Step 5: Translate the response back to the user's language
            if original_language != "en":
                response = translate_to_user_language(response, original_language)
                print(f"Translated response to {original_language}: {response}")

            # Step 6: Convert the response text to audio (Text-to-Speech)
            audio_output_path = text_to_speech(response, language_code=user_language)

            # Step 7: Read the audio file and encode it as base64
            with open(audio_output_path, "rb") as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Clean up temporary files
            os.remove(audio_path)
            os.remove(audio_output_path)

            return jsonify({
                'transcribed_text': user_message,
                'response_text': response,
                'response_audio': audio_base64
            })
        except Exception as e:
            print(f"Error processing voice chat request: {str(e)}")
            return jsonify({'error': f"Oops! Something went wrong. Please try again later. Error: {str(e)}"}), 500
    else:
        return jsonify({'error': 'Invalid file format. Only WAV and MP3 are supported.'}), 400

# Admin Setup Route
@app.route('/api/setup-admin', methods=['POST'])
def setup_admin():
    if not weaviate_client:
        return jsonify({'error': 'Weaviate not initialized'}), 500

    class_name = "Admin"
    schema = {
        "class": class_name,
        "vectorizer": "none",
        "properties": [
            {"name": "text", "dataType": ["text"]}
        ]
    }
    if not weaviate_client.schema.exists(class_name):
        weaviate_client.schema.create_class(schema)
        print("Created Weaviate class: Admin")

    admin_data = [
        "General steps to apply for a car loan or auto loan with SBI: 1) Visit SBI’s website (sbi.co.in) or a branch. 2) Submit an application with personal and financial details. 3) Provide documents (ID proof, address proof, income proof). 4) SBI verifies and approves based on eligibility. 5) Loan is disbursed upon agreement.",
        "General eligibility criteria for car loans, auto loans, or vehicle loans with SBI: - Age: 18-70 years. - Nationality: Indian resident or NRI. - Income: Stable monthly income (varies by loan amount). - Credit Score: Minimum 700-750. - Debt-to-Income Ratio: Typically below 40-50%.",
        "General car loan or auto loan details with SBI: - Tenure: Up to 7 years. - Interest Rate: 8.5%-12% per annum (floating rates based on SBI Base Rate). - Pre-closure Charges: 2-3% if prepaid within 2 years.",
        "Required documents for SBI car loans, auto loans, or vehicle loans: ID proof (Aadhaar, PAN), address proof, income proof (salary slips, bank statements), vehicle quotation.",
        "Repayment options for SBI car loans or auto loans: EMI via bank account; prepayment fees may apply (0-3%)."
    ]
    chunks = chunk_text("\n".join(admin_data), chunk_size=500)
    embeddings_list = generate_embeddings(chunks)
    admin_vector_store = Weaviate(
        client=weaviate_client,
        index_name=class_name,
        text_key="text",
        embedding=embeddings,
        by_text=False
    )
    admin_vector_store.add_texts(chunks, embeddings=embeddings_list)
    print(f"Stored admin guidelines in Weaviate class: {class_name}")
    return jsonify({'message': 'Admin data initialized'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)