"""
Unit tests for User Service
Tests core functionality including user validation, CRUD operations, and API endpoints
"""

import unittest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from app import app, validate_email, validate_phone, validate_user_data

class TestUserValidation(unittest.TestCase):
    """Test user data validation functions"""

    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_email_validation(self):
        """Test email validation with various formats"""
        # Valid emails
        self.assertTrue(validate_email("user@example.com"))
        self.assertTrue(validate_email("test.user@domain.co.uk"))
        self.assertTrue(validate_email("user123@test-domain.com"))
        
        # Invalid emails
        self.assertFalse(validate_email("invalid-email"))
        self.assertFalse(validate_email("user@"))
        self.assertFalse(validate_email("@domain.com"))
        self.assertFalse(validate_email("user@domain"))
        self.assertFalse(validate_email(""))

    def test_phone_validation(self):
        """Test phone number validation (Sri Lankan format)"""
        # Valid phone numbers
        self.assertTrue(validate_phone("+94771234567"))
        self.assertTrue(validate_phone("+94712345678"))
        self.assertTrue(validate_phone("+94112345678"))
        
        # Invalid phone numbers
        self.assertFalse(validate_phone("771234567"))
        self.assertFalse(validate_phone("+9477123456"))  # Too short
        self.assertFalse(validate_phone("+947712345678"))  # Too long
        self.assertFalse(validate_phone("+91771234567"))  # Wrong country code
        self.assertFalse(validate_phone(""))

    def test_user_data_validation(self):
        """Test complete user data validation"""
        # Valid user data
        valid_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+94771234567"
        }
        is_valid, error = validate_user_data(valid_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Missing required fields
        invalid_data = {"name": "John"}
        is_valid, error = validate_user_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Missing required field", error)
        
        # Invalid email
        invalid_data = {
            "name": "John Doe",
            "email": "invalid-email",
            "phone": "+94771234567"
        }
        is_valid, error = validate_user_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Invalid email format", error)
        
        # Invalid phone
        invalid_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "771234567"
        }
        is_valid, error = validate_user_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Invalid phone number format", error)

class TestUserAPi(unittest.TestCase):
    """Test User Service API endpoints"""

    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('app.client')
    def test_health_check(self, mock_client):
        """Test health check endpoint"""
        # Mock successful database connection
        mock_client.admin.command.return_value = {'ok': 1}
        
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'User Service')

    @patch('app.users_collection')
    def test_create_user_success(self, mock_collection):
        """Test successful user creation"""
        # Mock successful insertion
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439011"
        mock_collection.insert_one.return_value = mock_result
        mock_collection.find_one.return_value = None
        
        user_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+94771234567",
            "nic": "123456789V"
        }
        
        response = self.client.post('/api/users',
                                  data=json.dumps(user_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['name'], "John Doe")
        self.assertEqual(data['email'], "john@example.com")

    @patch('app.users_collection')
    def test_create_user_duplicate_email(self, mock_collection):
        """Test user creation with duplicate email"""
        # Mock existing user
        mock_collection.find_one.return_value = {"email": "john@example.com"}
        
        user_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+94771234567"
        }
        
        response = self.client.post('/api/users',
                                  data=json.dumps(user_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 409)
        data = json.loads(response.data)
        self.assertIn("already exists", data['error'])

    @patch('app.users_collection')
    def test_create_user_invalid_data(self, mock_collection):
        """Test user creation with invalid data"""
        # Test missing data
        response = self.client.post('/api/users',
                                  data=json.dumps({}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test invalid email
        user_data = {
            "name": "John Doe",
            "email": "invalid-email",
            "phone": "+94771234567"
        }
        
        response = self.client.post('/api/users',
                                  data=json.dumps(user_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Invalid email format", data['error'])

    @patch('app.users_collection')
    def test_get_users_pagination(self, mock_collection):
        """Test user listing with pagination"""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value.sort.return_value = [
            {
                "_id": "507f1f77bcf86cd799439011",
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+94771234567",
                "created_at": datetime.utcnow()
            }
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 1
        
        response = self.client.get('/api/users?page=1&limit=10')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['users']), 1)
        self.assertEqual(data['pagination']['page'], 1)

    @patch('app.users_collection')
    def test_get_user_by_id(self, mock_collection):
        """Test retrieving user by ID"""
        # Mock user found
        mock_user = {
            "_id": "507f1f77bcf86cd799439011",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+94771234567",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        mock_collection.find_one.return_value = mock_user
        
        response = self.client.get('/api/users/507f1f77bcf86cd799439011')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['name'], "John Doe")

    @patch('app.users_collection')
    def test_get_user_not_found(self, mock_collection):
        """Test retrieving non-existent user"""
        mock_collection.find_one.return_value = None
        
        response = self.client.get('/api/users/507f1f77bcf86cd799439011')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("not found", data['error'])

    @patch('app.users_collection')
    def test_update_user_success(self, mock_collection):
        """Test successful user update"""
        # Mock successful update
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result
        
        # Mock updated user
        updated_user = {
            "_id": "507f1f77bcf86cd799439011",
            "name": "John Smith",
            "email": "john@example.com",
            "phone": "+94771234567",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        mock_collection.find_one.return_value = updated_user
        
        update_data = {"name": "John Smith"}
        
        response = self.client.put('/api/users/507f1f77bcf86cd799439011',
                                 data=json.dumps(update_data),
                                 content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['name'], "John Smith")

    @patch('app.users_collection')
    def test_delete_user_success(self, mock_collection):
        """Test successful user deletion (soft delete)"""
        # Mock successful deletion
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result
        
        response = self.client.delete('/api/users/507f1f77bcf86cd799439011')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("deleted successfully", data['message'])

if __name__ == '__main__':
    unittest.main()