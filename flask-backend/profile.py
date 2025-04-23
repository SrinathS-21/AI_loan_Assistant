import os
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
from dotenv import load_dotenv
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import joblib

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

# Create a Blueprint for profile routes
profile_bp = Blueprint('profile', __name__)

# MongoDB connection using MONGODB_URI from environment variables
mongodb_uri = os.getenv('MONGODB_URI')
if not mongodb_uri:
    raise ValueError("MONGODB_URI not set in environment variables")

try:
    client = MongoClient(mongodb_uri)
    client.server_info()  # Test the connection
    print("Successfully connected to MongoDB Atlas for profile routes")
except ConnectionFailure as e:
    print(f"Failed to connect to MongoDB Atlas in profile.py: {e}")
    raise

db = client['loan_advisor_db']
expense_collection = db['user_expenses']

# Load the pre-trained model with fallback
loan_safety_model = None
try:
    model_path = os.path.join(os.path.dirname(__file__), 'loan_safety_model.pkl')
    if os.path.exists(model_path):
        loan_safety_model = joblib.load(model_path)
        print("Successfully loaded loan safety model")
    else:
        print(f"Model file not found at: {model_path}")
except Exception as e:
    print(f"Warning: Failed to load loan safety model: {str(e)}. Prediction endpoint will be unavailable.")
    loan_safety_model = None

# POST endpoint to create a new expense entry
@profile_bp.route('/api/profile/expenses', methods=['POST'])
@jwt_required()
def create_expense():
    try:
        logging.debug("Received POST request to /api/profile/expenses")
        user_id = get_jwt_identity()

        income = request.form.get('income', type=float, default=0)
        expense = request.form.get('expense', type=float, default=0)
        savings = request.form.get('savings', type=float, default=0)
        date = request.form.get('date', default=datetime.utcnow().isoformat()[:10])
        notes = request.form.get('notes', default='')

        if not date:
            logging.error("Date is required")
            return jsonify({'error': 'Date is required'}), 400

        if income < 0 or expense < 0 or savings < 0:
            logging.error("Income, expense, and savings cannot be negative")
            return jsonify({'error': 'Income, expense, and savings cannot be negative'}), 400

        expense_entry = {
            'user_id': user_id,
            'income': income,
            'expense': expense,
            'savings': savings,
            'date': date,
            'notes': notes,
            'created_at': datetime.utcnow(),
        }

        result = expense_collection.insert_one(expense_entry)
        logging.debug(f"Expense created for user {user_id} with ID: {str(result.inserted_id)}")
        return jsonify({
            'message': 'Expense created successfully',
            'expense_id': str(result.inserted_id)
        }), 201

    except ValueError as e:
        logging.error(f"Invalid data type: {str(e)}")
        return jsonify({'error': 'Invalid data type'}), 400
    except Exception as e:
        logging.error(f"Error creating expense: {str(e)}")
        return jsonify({'error': str(e)}), 500

# GET endpoint to fetch all expense entries for the authenticated user
@profile_bp.route('/api/profile/expenses', methods=['GET'])
@jwt_required()
def get_expenses():
    try:
        user_id = get_jwt_identity()
        logging.debug(f"Fetching expenses for user: {user_id}")
        expenses = list(expense_collection.find({'user_id': user_id}).sort('created_at', -1))
        for expense in expenses:
            expense['_id'] = str(expense['_id'])
            expense['created_at'] = expense['created_at'].isoformat()
        logging.debug(f"Returning {len(expenses)} expenses")
        return jsonify(expenses), 200
    except Exception as e:
        logging.error(f"Error fetching expenses: {str(e)}")
        return jsonify({'error': str(e)}), 500

# DELETE endpoint to remove an expense entry for the authenticated user
@profile_bp.route('/api/profile/expenses/<expense_id>', methods=['DELETE'])
@jwt_required()
def delete_expense(expense_id):
    try:
        user_id = get_jwt_identity()
        logging.debug(f"Received DELETE request for expense ID: {expense_id} by user: {user_id}")

        try:
            expense_obj_id = ObjectId(expense_id)
        except Exception as e:
            logging.error(f"Invalid expense ID: {expense_id}")
            return jsonify({'error': 'Invalid expense ID'}), 400

        expense = expense_collection.find_one({'_id': expense_obj_id, 'user_id': user_id})
        if not expense:
            logging.error(f"Expense not found or user not authorized: {expense_id}")
            return jsonify({'error': 'Expense not found or you are not authorized to delete it'}), 404

        result = expense_collection.delete_one({'_id': expense_obj_id})
        if result.deleted_count == 0:
            logging.error(f"Failed to delete expense: {expense_id}")
            return jsonify({'error': 'Failed to delete expense'}), 500

        logging.debug(f"Successfully deleted expense ID: {expense_id}")
        return jsonify({'message': 'Expense deleted successfully'}), 200

    except Exception as e:
        logging.error(f"Error deleting expense: {str(e)}")
        return jsonify({'error': str(e)}), 500

# PUT endpoint to update an existing expense entry for the authenticated user
@profile_bp.route('/api/profile/expenses/<expense_id>', methods=['PUT'])
@jwt_required()
def update_expense(expense_id):
    try:
        user_id = get_jwt_identity()
        logging.debug(f"Received PUT request for expense ID: {expense_id} by user: {user_id}")

        try:
            expense_obj_id = ObjectId(expense_id)
        except Exception as e:
            logging.error(f"Invalid expense ID: {expense_id}")
            return jsonify({'error': 'Invalid expense ID'}), 400

        expense = expense_collection.find_one({'_id': expense_obj_id, 'user_id': user_id})
        if not expense:
            logging.error(f"Expense not found or user not authorized: {expense_id}")
            return jsonify({'error': 'Expense not found or you are not authorized to update it'}), 404

        income = request.form.get('income', type=float, default=expense['income'])
        expense_amount = request.form.get('expense', type=float, default=expense['expense'])
        savings = request.form.get('savings', type=float, default=expense['savings'])
        date = request.form.get('date', default=expense['date'])
        notes = request.form.get('notes', default=expense['notes'])

        if not date:
            logging.error("Date is required")
            return jsonify({'error': 'Date is required'}), 400

        if income < 0 or expense_amount < 0 or savings < 0:
            logging.error("Income, expense, and savings cannot be negative")
            return jsonify({'error': 'Income, expense, and savings cannot be negative'}), 400

        update_data = {
            'income': income,
            'expense': expense_amount,
            'savings': savings,
            'date': date,
            'notes': notes,
            'updated_at': datetime.utcnow(),
        }

        result = expense_collection.update_one({'_id': expense_obj_id}, {'$set': update_data})

        if result.modified_count == 0:
            logging.error(f"No changes made to expense: {expense_id}")
            return jsonify({'error': 'No changes made to the expense'}), 400

        logging.debug(f"Successfully updated expense ID: {expense_id}")
        return jsonify({
            'message': 'Expense updated successfully',
            'updated_at': update_data['updated_at'].isoformat()
        }), 200

    except ValueError as e:
        logging.error(f"Invalid data type: {str(e)}")
        return jsonify({'error': 'Invalid data type'}), 400
    except Exception as e:
        logging.error(f"Error updating expense: {str(e)}")
        return jsonify({'error': str(e)}), 500

# POST endpoint to predict loan safety
@profile_bp.route('/api/predict-loan-safety', methods=['POST'])
@jwt_required()
def predict_loan_safety():
    try:
        user_id = get_jwt_identity()
        logging.debug(f"Received predict request for user: {user_id}")

        data = request.get_json()
        total_income = float(data.get('total_income', 0))
        debt_to_income_ratio = float(data.get('debt_to_income_ratio', 0))

        if total_income < 0 or debt_to_income_ratio < 0:
            logging.error("Total income and debt-to-income ratio cannot be negative")
            return jsonify({'error': 'Invalid input data'}), 400

        if loan_safety_model is None:
            logging.error("Loan safety model is not available")
            return jsonify({'error': 'Prediction model is not available'}), 500

        features = [[total_income, debt_to_income_ratio]]

        try:
            prediction = loan_safety_model.predict(features)[0]
            prediction_text = 'Safe to get a loan' if prediction == 1 else 'Not safe to get a loan'
        except Exception as e:
            logging.error(f"Prediction failed: {str(e)}")
            return jsonify({'error': 'Model prediction failed'}), 500

        logging.debug(f"Prediction for user {user_id}: {prediction_text}")
        return jsonify({'prediction': prediction_text}), 200

    except ValueError as e:
        logging.error(f"Invalid data type: {str(e)}")
        return jsonify({'error': 'Invalid data type'}), 400
    except Exception as e:
        logging.error(f"Error predicting loan safety: {str(e)}")
        return jsonify({'error': str(e)}), 500