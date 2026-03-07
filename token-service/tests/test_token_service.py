"""
Unit tests for Token Service
Tests core functionality including token generation, validation, and Notification Service integration
"""

import unittest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from token_service.app import app, validate_token_request

class TestTokenValidation(unittest.TestCase):
    """Test token data validation functions"""

    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_token_request_validation(self):
        """Test token generation request validation"""
        # Valid token request
        valid_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012",
            "user_name": "John Doe",
            "queue_name": "General Service",
            "service_type": "priority"
        }
        is_valid, error = validate_token_request(valid_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Missing required fields
        invalid_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012"
        }
        is_valid, error = validate_token_request(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Missing required field", error)
        
        # Invalid ObjectId format
        invalid_data = {
            "user_id": "invalid-id",
            "queue_id": "507f1f77bcf86cd799439012",
            "user_name": "John Doe",
            "queue_name": "General Service"
        }
        is_valid, error = validate_token_request(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Invalid user_id or queue_id format", error)
        
        # Invalid user name length
        invalid_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012",
            "user_name": "A",
            "queue_name": "General Service"
        }
        is_valid, error = validate_token_request(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("User name must be between 2 and 100 characters", error)
        
        # Invalid service type
        invalid_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012",
            "user_name": "John Doe",
            "queue_name": "General Service",
            "service_type": "invalid-type"
        }
        is_valid, error = validate_token_request(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Invalid service type", error)

class TestTokenAPI(unittest.TestCase):
    """Test Token Service API endpoints"""

    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('token_service.app.client')
    @patch('token_service.app.requests')
    def test_health_check(self, mock_requests, mock_client):
        """Test health check endpoint"""
        # Mock successful database connection
        mock_client.admin.command.return_value = {'ok': 1}
        
        # Mock Notification Service response
        mock_notification_response = MagicMock()
        mock_notification_response.status_code = 200
        mock_requests.get.return_value = mock_notification_response
        
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'Token Service')

    @patch('token_service.app.tokens_collection')
    @patch('token_service.app.requests')
    def test_generate_token_success(self, mock_requests, mock_collection):
        """Test successful token generation with Notification Service integration"""
        # Mock successful token insertion
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439013"
        mock_collection.insert_one.return_value = mock_result
        mock_collection.count_documents.return_value = 0
        
        # Mock Notification Service response
        mock_notification_response = MagicMock()
        mock_notification_response.status_code = 201
        mock_notification_response.json.return_value = {
            'notification_id': 'notif_123',
            'status': 'sent'
        }
        mock_requests.post.return_value = mock_notification_response
        
        token_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012",
            "user_name": "John Doe",
            "queue_name": "General Service",
            "service_type": "priority"
        }
        
        response = self.client.post('/api/tokens/generate',
                                  data=json.dumps(token_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['user_name'], "John Doe")
        self.assertEqual(data['queue_name'], "General Service")
        self.assertTrue(data['notification_sent'])
        self.assertEqual(data['notification_id'], 'notif_123')

    @patch('token_service.app.tokens_collection')
    @patch('token_service.app.requests')
    def test_generate_token_notification_failure(self, mock_requests, mock_collection):
        """Test token generation when Notification Service fails"""
        # Mock successful token insertion
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439013"
        mock_collection.insert_one.return_value = mock_result
        mock_collection.count_documents.return_value = 0
        
        # Mock Notification Service failure
        mock_requests.post.side_effect = Exception("Connection refused")
        
        token_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012",
            "user_name": "John Doe",
            "queue_name": "General Service"
        }
        
        # Token generation should still succeed even if notification fails
        response = self.client.post('/api/tokens/generate',
                                  data=json.dumps(token_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['user_name'], "John Doe")
        self.assertFalse(data['notification_sent'])
        self.assertIn('notification_error', data)

    @patch('token_service.app.tokens_collection')
    def test_generate_token_invalid_data(self, mock_collection):
        """Test token generation with invalid data"""
        # Test missing data
        response = self.client.post('/api/tokens/generate',
                                  data=json.dumps({}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test invalid ObjectId
        token_data = {
            "user_id": "invalid-id",
            "queue_id": "507f1f77bcf86cd799439012",
            "user_name": "John Doe",
            "queue_name": "General Service"
        }
        
        response = self.client.post('/api/tokens/generate',
                                  data=json.dumps(token_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Invalid user_id or queue_id format", data['error'])

    @patch('token_service.app.tokens_collection')
    def test_get_token_by_id(self, mock_collection):
        """Test retrieving token by ID"""
        # Mock token found
        mock_token = {
            "token_id": "token_123",
            "token_number": "Q001",
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012",
            "user_name": "John Doe",
            "queue_name": "General Service",
            "service_type": "priority",
            "status": "active",
            "priority": 2,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow()
        }
        mock_collection.find_one.return_value = mock_token
        
        response = self.client.get('/api/tokens/token_123')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['token_number'], "Q001")
        self.assertEqual(data['user_name'], "John Doe")

    @patch('token_service.app.tokens_collection')
    def test_get_token_not_found(self, mock_collection):
        """Test retrieving non-existent token"""
        mock_collection.find_one.return_value = None
        
        response = self.client.get('/api/tokens/nonexistent_token')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("not found", data['error'])

    @patch('token_service.app.tokens_collection')
    def test_get_user_tokens(self, mock_collection):
        """Test retrieving tokens for a user"""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value.limit.return_value = [
            {
                "token_id": "token_123",
                "token_number": "Q001",
                "queue_name": "General Service",
                "service_type": "priority",
                "status": "active",
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow()
            }
        ]
        mock_collection.find.return_value = mock_cursor
        
        response = self.client.get('/api/tokens/user/507f1f77bcf86cd799439011')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['tokens']), 1)
        self.assertEqual(data['tokens'][0]['token_number'], "Q001")

    @patch('token_service.app.tokens_collection')
    def test_update_token_status(self, mock_collection):
        """Test updating token status"""
        # Mock successful update
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result
        
        # Mock updated token
        updated_token = {
            "token_id": "token_123",
            "token_number": "Q001",
            "user_name": "John Doe",
            "queue_name": "General Service",
            "status": "called",
            "called_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        mock_collection.find_one.return_value = updated_token
        
        update_data = {"status": "called"}
        
        response = self.client.put('/api/tokens/status/token_123',
                                 data=json.dumps(update_data),
                                 content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], "called")
        self.assertIsNotNone(data['called_at'])

    @patch('token_service.app.tokens_collection')
    def test_update_token_status_invalid(self, mock_collection):
        """Test updating token status with invalid data"""
        # Test missing status
        response = self.client.put('/api/tokens/status/token_123',
                                 data=json.dumps({}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test invalid status
        update_data = {"status": "invalid-status"}
        response = self.client.put('/api/tokens/status/token_123',
                                 data=json.dumps(update_data),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Invalid status", data['error'])

if __name__ == '__main__':
    unittest.main()