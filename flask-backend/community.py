import os
from flask import Blueprint, request, jsonify, send_from_directory
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename
import re
from dotenv import load_dotenv
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

# Create a Blueprint for community routes
community_bp = Blueprint('community', __name__)

# MongoDB connection using MONGODB_URI from environment variables
mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    raise ValueError("MONGODB_URI not set in environment variables")

try:
    client = MongoClient(mongodb_uri)
    client.server_info()  # Test the connection
    print("Successfully connected to MongoDB Atlas for community routes")
except ConnectionFailure as e:
    print(f"Failed to connect to MongoDB Atlas in community.py: {e}")
    raise

db = client['loan_advisor_db']
community_collection = db['community_posts']

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    logging.debug(f"Creating upload folder at: {UPLOAD_FOLDER}")
    os.makedirs(UPLOAD_FOLDER)
else:
    logging.debug(f"Upload folder already exists at: {UPLOAD_FOLDER}")

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# POST endpoint to create a new community post
@community_bp.route('/api/community', methods=['POST'])
@jwt_required()
def create_community_post():
    try:
        logging.debug("Received POST request to /api/community")
        if 'title' not in request.form or 'author' not in request.form or 'description' not in request.form:
            logging.error("Missing required fields: title, author, or description")
            return jsonify({'error': 'Title, author, and description are required'}), 400

        user_id = get_jwt_identity()  # Get the user ID from the JWT token
        logging.debug(f"User ID from JWT: {user_id}")
        title = request.form['title']
        author = request.form['author']
        description = request.form['description']
        image_url = None

        logging.debug("Checking for image in request.files")
        if 'image' in request.files:
            file = request.files['image']
            logging.debug(f"Image file received: {file.filename if file else 'None'}")
            if file and file.filename:
                if not allowed_file(file.filename):
                    logging.error(f"File extension not allowed: {file.filename}")
                    return jsonify({'error': 'File type not allowed. Only PNG, JPG, JPEG, and GIF are supported.'}), 400
                
                # Check if the file is empty
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)  # Reset file pointer to the beginning
                if file_size == 0:
                    logging.error("Uploaded file is empty")
                    return jsonify({'error': 'Uploaded file is empty'}), 400

                # Use a unique filename based on timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                original_filename = secure_filename(file.filename)
                unique_filename = f"{timestamp}_{original_filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                logging.debug(f"Attempting to save image to: {file_path}")

                try:
                    file.save(file_path)
                    if os.path.exists(file_path):
                        logging.debug(f"Image saved successfully: {file_path}")
                        image_url = f"/uploads/{unique_filename}"
                    else:
                        logging.error(f"Failed to save image: {file_path} does not exist after save")
                        return jsonify({'error': 'Failed to save image'}), 500
                except Exception as e:
                    logging.error(f"Error saving image: {str(e)}")
                    return jsonify({'error': f'Failed to save image: {str(e)}'}), 500
            else:
                logging.warning("No valid image file provided (empty filename)")
        else:
            logging.warning("No 'image' key in request.files")

        post = {
            'title': title,
            'author': author,
            'description': description,
            'image_url': image_url,
            'created_at': datetime.utcnow(),
            'likes': 0,
            'liked_by': [],  # List to store user IDs who liked the post
            'dislikes': 0,  # New field for dislike count
            'disliked_by': [],  # New field to store user IDs who disliked the post
            'comments': 0,
        }

        result = community_collection.insert_one(post)
        logging.debug(f"Post created with image_url: {image_url}")
        return jsonify({
            'message': 'Post created successfully',
            'post_id': str(result.inserted_id)
        }), 201

    except Exception as e:
        logging.error(f"Error creating post: {str(e)}")
        return jsonify({'error': str(e)}), 500

# GET endpoint to fetch all community posts with like and dislike status
@community_bp.route('/api/community', methods=['GET'])
@jwt_required()
def get_community_posts():
    try:
        user_id = get_jwt_identity()
        logging.debug(f"Fetching posts for user: {user_id}")
        posts = list(community_collection.find().sort('created_at', -1))
        for post in posts:
            post['_id'] = str(post['_id'])
            post['created_at'] = post['created_at'].isoformat()
            # Add fields to indicate if the current user has liked/disliked this post
            post['is_liked'] = user_id in post.get('liked_by', [])
            post['is_disliked'] = user_id in post.get('disliked_by', [])
        logging.debug(f"Returning {len(posts)} posts")
        return jsonify(posts), 200
    except Exception as e:
        logging.error(f"Error fetching posts: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Serve uploaded images
@community_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        logging.debug(f"Serving file: {filename}")
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        logging.error(f"Error serving file {filename}: {str(e)}")
        return jsonify({'error': 'File not found'}), 404

# POST endpoint to toggle like on a post
@community_bp.route('/api/community/<post_id>/like', methods=['POST'])
@jwt_required()
def like_post(post_id):
    try:
        user_id = get_jwt_identity()
        post = community_collection.find_one({'_id': ObjectId(post_id)})
        if not post:
            logging.error(f"Post not found: {post_id}")
            return jsonify({'error': 'Post not found'}), 404

        liked_by = post.get('liked_by', [])
        disliked_by = post.get('disliked_by', [])

        # If the user has already disliked the post, remove the dislike before liking
        if user_id in disliked_by:
            community_collection.update_one(
                {'_id': ObjectId(post_id)},
                {'$pull': {'disliked_by': user_id}, '$inc': {'dislikes': -1}}
            )

        # Toggle the like
        if user_id in liked_by:
            # User already liked the post, so unlike it
            community_collection.update_one(
                {'_id': ObjectId(post_id)},
                {'$pull': {'liked_by': user_id}, '$inc': {'likes': -1}}
            )
            updated_likes = post['likes'] - 1
            is_liked = False
        else:
            # User hasn't liked the post, so like it
            community_collection.update_one(
                {'_id': ObjectId(post_id)},
                {'$addToSet': {'liked_by': user_id}, '$inc': {'likes': 1}}
            )
            updated_likes = post['likes'] + 1
            is_liked = True

        # Fetch the updated post to get the latest dislike count
        updated_post = community_collection.find_one({'_id': ObjectId(post_id)})
        logging.debug(f"Like toggled for post {post_id}: likes={updated_likes}, is_liked={is_liked}")
        return jsonify({
            'message': 'Like toggled successfully',
            'likes': updated_likes,
            'is_liked': is_liked,
            'dislikes': updated_post['dislikes'],
            'is_disliked': user_id in updated_post.get('disliked_by', [])
        }), 200
    except Exception as e:
        logging.error(f"Error toggling like: {str(e)}")
        return jsonify({'error': str(e)}), 500

# POST endpoint to toggle dislike on a post
@community_bp.route('/api/community/<post_id>/dislike', methods=['POST'])
@jwt_required()
def dislike_post(post_id):
    try:
        user_id = get_jwt_identity()
        post = community_collection.find_one({'_id': ObjectId(post_id)})
        if not post:
            logging.error(f"Post not found: {post_id}")
            return jsonify({'error': 'Post not found'}), 404

        liked_by = post.get('liked_by', [])
        disliked_by = post.get('disliked_by', [])

        # If the user has already liked the post, remove the like before disliking
        if user_id in liked_by:
            community_collection.update_one(
                {'_id': ObjectId(post_id)},
                {'$pull': {'liked_by': user_id}, '$inc': {'likes': -1}}
            )

        # Toggle the dislike
        if user_id in disliked_by:
            # User already disliked the post, so remove the dislike
            community_collection.update_one(
                {'_id': ObjectId(post_id)},
                {'$pull': {'disliked_by': user_id}, '$inc': {'dislikes': -1}}
            )
            updated_dislikes = post['dislikes'] - 1
            is_disliked = False
        else:
            # User hasn't disliked the post, so dislike it
            community_collection.update_one(
                {'_id': ObjectId(post_id)},
                {'$addToSet': {'disliked_by': user_id}, '$inc': {'dislikes': 1}}
            )
            updated_dislikes = post['dislikes'] + 1
            is_disliked = True

        # Fetch the updated post to get the latest like count
        updated_post = community_collection.find_one({'_id': ObjectId(post_id)})
        logging.debug(f"Dislike toggled for post {post_id}: dislikes={updated_dislikes}, is_disliked={is_disliked}")
        return jsonify({
            'message': 'Dislike toggled successfully',
            'dislikes': updated_dislikes,
            'is_disliked': is_disliked,
            'likes': updated_post['likes'],
            'is_liked': user_id in updated_post.get('liked_by', [])
        }), 200
    except Exception as e:
        logging.error(f"Error toggling dislike: {str(e)}")
        return jsonify({'error': str(e)}), 500