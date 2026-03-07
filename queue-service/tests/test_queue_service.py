"""
Unit tests for Queue Service
Tests core functionality including queue management, validation, and service integration
"""

import unittest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from queue_service.app import app, validate_queue_data, validate_join_queue_data

class TestQueueValidation(unittest.TestCase):
    """Test queue data validation functions"""

    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_queue_data_validation(self):
        """Test queue creation data validation"""
        # Valid queue data
        valid_data = {
            "name": "General Service",
            "description": "General customer service queue for all inquiries",
            "max_capacity": 50
        }
        is_valid, error = validate_queue_data(valid_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Missing required fields
        invalid_data = {"name": "Test Queue"}
        is_valid, error = validate_queue_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Missing required field", error)
        
        # Invalid name length
        invalid_data = {
            "name": "AB",
            "description": "Valid description here"
        }
        is_valid, error = validate_queue_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Queue name must be between 3 and 50 characters", error)
        
        # Invalid description length
        invalid_data = {
            "name": "Valid Name",
            "description": "Too short"
        }
        is_valid, error = validate_queue_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Description must be between 10 and 200 characters", error)
        
        # Invalid capacity
        invalid_data = {
            "name": "Valid Name",
            "description": "Valid description with sufficient length",
            "max_capacity": 1500
        }
        is_valid, error = validate_queue_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Max capacity must be between 1 and 1000", error)

    def test_join_queue_data_validation(self):
        """Test queue join request validation"""
        # Valid join data
        valid_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012"
        }
        is_valid, error = validate_join_queue_data(valid_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Missing required fields
        invalid_data = {"user_id": "507f1f77bcf86cd799439011"}
        is_valid, error = validate_join_queue_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Missing required field", error)
        
        # Invalid ObjectId format
        invalid_data = {
            "user_id": "invalid-id",
            "queue_id": "507f1f77bcf86cd799439012"
        }
        is_valid, error = validate_join_queue_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Invalid user_id or queue_id format", error)

class TestQueueAPI(unittest.TestCase):
    """Test Queue Service API endpoints"""

    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('queue_service.app.client')
    @patch('queue_service.app.requests')
    def test_health_check(self, mock_requests, mock_client):
        """Test health check endpoint"""
        # Mock successful database connection
        mock_client.admin.command.return_value = {'ok': 1}
        
        # Mock service responses
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        
        mock_requests.get.side_effect = [mock_user_response, mock_token_response]
        
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'Queue Service')

    @patch('queue_service.app.queues_collection')
    def test_create_queue_success(self, mock_collection):
        """Test successful queue creation"""
        # Mock successful insertion
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439011"
        mock_collection.insert_one.return_value = mock_result
        mock_collection.find_one.return_value = None
        
        queue_data = {
            "name": "General Service",
            "description": "General customer service queue",
            "max_capacity": 50,
            "service_type": "customer-service"
        }
        
        response = self.client.post('/api/queues',
                                  data=json.dumps(queue_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['name'], "General Service")
        self.assertEqual(data['max_capacity'], 50)

    @patch('queue_service.app.queues_collection')
    def test_create_queue_duplicate_name(self, mock_collection):
        """Test queue creation with duplicate name"""
        # Mock existing queue
        mock_collection.find_one.return_value = {"name": "General Service"}
        
        queue_data = {
            "name": "General Service",
            "description": "General customer service queue",
            "max_capacity": 50
        }
        
        response = self.client.post('/api/queues',
                                  data=json.dumps(queue_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 409)
        data = json.loads(response.data)
        self.assertIn("already exists", data['error'])

    @patch('queue_service.app.queues_collection')
    def test_get_queues(self, mock_collection):
        """Test retrieving all queues"""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = [
            {
                "_id": "507f1f77bcf86cd799439011",
                "name": "General Service",
                "description": "General queue",
                "max_capacity": 50,
                "current_count": 10,
                "average_wait_time": 15,
                "service_type": "general",
                "created_at": datetime.utcnow()
            }
        ]
        mock_collection.find.return_value = mock_cursor
        
        response = self.client.get('/api/queues')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['queues']), 1)
        self.assertEqual(data['queues'][0]['name'], "General Service")

    @patch('queue_service.app.queues_collection')
    def test_get_queue_by_id(self, mock_collection):
        """Test retrieving queue by ID"""
        # Mock queue found
        mock_queue = {
            "_id": "507f1f77bcf86cd799439011",
            "name": "General Service",
            "description": "General queue",
            "max_capacity": 50,
            "current_count": 10,
            "average_wait_time": 15,
            "service_type": "general",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        mock_collection.find_one.return_value = mock_queue
        
        response = self.client.get('/api/queues/507f1f77bcf86cd799439011')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['name'], "General Service")

    @patch('queue_service.app.requests')
    @patch('queue_service.app.queues_collection')
    @patch('queue_service.app.queue_assignments_collection')
    def test_join_queue_integration_success(self, mock_assignments, mock_queues, mock_requests):
        """Test successful queue join with full integration flow"""
        # Mock user service response
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "name": "John Doe",
            "email": "john@example.com"
        }
        mock_requests.get.return_value = mock_user_response
        
        # Mock queue data
        mock_queue = {
            "_id": "507f1f77bcf86cd799439012",
            "name": "General Service",
            "max_capacity": 50,
            "current_count": 10,
            "average_wait_time": 15
        }
        mock_queues.find_one.return_value = mock_queue
        
        # Mock token service response
        mock_token_response = MagicMock()
        mock_token_response.status_code = 201
        mock_token_response.json.return_value = {
            "token_id": "token_123",
            "token_number": "Q001",
            "status": "active"
        }
        mock_requests.post.return_value = mock_token_response
        
        # Mock assignment insertion
        mock_assignment_result = MagicMock()
        mock_assignment_result.inserted_id = "assignment_123"
        mock_assignments.insert_one.return_value = mock_assignment_result
        
        # Mock queue update
        mock_queues.update_one.return_value = MagicMock()
        
        join_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012",
            "service_type": "priority"
        }
        
        response = self.client.post('/api/queues/join',
                                  data=json.dumps(join_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['user']['name'], "John Doe")
        self.assertEqual(data['queue']['name'], "General Service")
        self.assertEqual(data['token']['number'], "Q001")

    @patch('queue_service.app.requests')
    def test_join_queue_user_not_found(self, mock_requests):
        """Test queue join when user doesn't exist"""
        # Mock user service response - user not found
        mock_user_response = MagicMock()
        mock_user_response.status_code = 404
        mock_requests.get.return_value = mock_user_response
        
        join_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012"
        }
        
        response = self.client.post('/api/queues/join',
                                  data=json.dumps(join_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("not found", data['error'])

    @patch('queue_service.app.requests')
    @patch('queue_service.app.queues_collection')
    def test_join_queue_service_unavailable(self, mock_queues, mock_requests):
        """Test queue join when external service is unavailable"""
        # Mock user service response - success
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {"name": "John Doe"}
        mock_requests.get.return_value = mock_user_response
        
        # Mock queue data
        mock_queue = {
            "_id": "507f1f77bcf86cd799439012",
            "name": "General Service",
            "max_capacity": 50,
            "current_count": 10
        }
        mock_queues.find_one.return_value = mock_queue
        
        # Mock token service failure
        mock_requests.post.side_effect = Exception("Connection refused")
        
        join_data = {
            "user_id": "507f1f77bcf86cd799439011",
            "queue_id": "507f1f77bcf86cd799439012"
        }
        
        response = self.client.post('/api/queues/join',
                                  data=json.dumps(join_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.data)
        self.assertIn("Service communication failed", data['error'])

if __name__ == '__main__':
    unittest.main()