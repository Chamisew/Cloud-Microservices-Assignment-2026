"""
Unit tests for Notification Service
Tests core functionality including notification processing, validation, and data handling
"""

import unittest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notification_service.app import app, validate_notification_data, sanitize_input

class TestNotificationValidation(unittest.TestCase):
    """Test notification data validation and sanitization functions"""

    def setUp(self):
        """Set up test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_notification_data_validation(self):
        """Test notification data validation"""
        # Valid notification data
        valid_data = {
            "type": "token_generated",
            "user_id": "507f1f77bcf86cd799439011",
            "user_name": "John Doe",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Your token Q001 is ready in General Service",
            "priority": 3
        }
        is_valid, error = validate_notification_data(valid_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Missing required fields
        invalid_data = {
            "type": "token_generated",
            "user_id": "507f1f77bcf86cd799439011"
        }
        is_valid, error = validate_notification_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Missing required field", error)
        
        # Invalid ObjectId format
        invalid_data = {
            "type": "token_generated",
            "user_id": "invalid-id",
            "user_name": "John Doe",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Your token is ready"
        }
        is_valid, error = validate_notification_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Invalid user_id or token_id format", error)
        
        # Invalid message length
        invalid_data = {
            "type": "token_generated",
            "user_id": "507f1f77bcf86cd799439011",
            "user_name": "John Doe",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Short"
        }
        is_valid, error = validate_notification_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Message must be between 10 and 500 characters", error)
        
        # Invalid notification type
        invalid_data = {
            "type": "invalid_type",
            "user_id": "507f1f77bcf86cd799439011",
            "user_name": "John Doe",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Your token Q001 is ready in General Service"
        }
        is_valid, error = validate_notification_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertIn("Invalid notification type", error)

    def test_input_sanitization(self):
        """Test input data sanitization"""
        # Test valid input sanitization
        dirty_data = {
            "type": " token_generated ",
            "user_id": "507f1f77bcf86cd799439011",
            "user_name": " John Doe ",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": " Q001 ",
            "queue_name": " General Service ",
            "message": " Your token is ready ",
            "priority": 3
        }
        
        sanitized = sanitize_input(dirty_data)
        self.assertEqual(sanitized['type'], 'token_generated')
        self.assertEqual(sanitized['user_name'], 'John Doe')
        self.assertEqual(sanitized['token_number'], 'Q001')
        self.assertEqual(sanitized['queue_name'], 'General Service')
        self.assertEqual(sanitized['message'], 'Your token is ready')
        
        # Test invalid input handling
        invalid_input = "not a dictionary"
        sanitized = sanitize_input(invalid_input)
        self.assertEqual(sanitized, {})
        
        # Test malicious input (should be sanitized, not executed)
        malicious_data = {
            "type": "token_generated",
            "user_id": "507f1f77bcf86cd799439011",
            "user_name": "John'; DROP TABLE users; --",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Your token is ready"
        }
        
        sanitized = sanitize_input(malicious_data)
        # Should not crash and should sanitize the malicious content
        self.assertIsInstance(sanitized, dict)
        self.assertIn('user_name', sanitized)

class TestNotificationAPI(unittest.TestCase):
    """Test Notification Service API endpoints"""

    def setUp(self):
        """Set up test environment"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('notification_service.app.client')
    def test_health_check(self, mock_client):
        """Test health check endpoint"""
        # Mock successful database connection
        mock_client.admin.command.return_value = {'ok': 1}
        
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'Notification Service')
        self.assertEqual(data['role'], 'final_integration_point')

    @patch('notification_service.app.notifications_collection')
    def test_send_notification_success(self, mock_collection):
        """Test successful notification sending"""
        # Mock successful insertion
        mock_result = MagicMock()
        mock_result.inserted_id = "507f1f77bcf86cd799439013"
        mock_collection.insert_one.return_value = mock_result
        
        notification_data = {
            "type": "token_generated",
            "user_id": "507f1f77bcf86cd799439011",
            "user_name": "John Doe",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Your token Q001 is ready in General Service",
            "priority": 3,
            "service_type": "priority"
        }
        
        response = self.client.post('/api/notifications/send',
                                  data=json.dumps(notification_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'sent')
        self.assertEqual(data['user_name'], 'John Doe')
        self.assertEqual(data['token_number'], 'Q001')

    @patch('notification_service.app.notifications_collection')
    def test_send_notification_invalid_data(self, mock_collection):
        """Test notification sending with invalid data"""
        # Test missing data
        response = self.client.post('/api/notifications/send',
                                  data=json.dumps({}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test invalid ObjectId
        notification_data = {
            "type": "token_generated",
            "user_id": "invalid-id",
            "user_name": "John Doe",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Your token is ready"
        }
        
        response = self.client.post('/api/notifications/send',
                                  data=json.dumps(notification_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("Invalid user_id or token_id format", data['error'])

    @patch('notification_service.app.notifications_collection')
    def test_send_notification_database_error(self, mock_collection):
        """Test notification sending with database error"""
        # Mock database insertion failure
        mock_collection.insert_one.side_effect = Exception("Database connection failed")
        
        notification_data = {
            "type": "token_generated",
            "user_id": "507f1f77bcf86cd799439011",
            "user_name": "John Doe",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Your token is ready"
        }
        
        response = self.client.post('/api/notifications/send',
                                  data=json.dumps(notification_data),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("Database save failed", data['error'])

    @patch('notification_service.app.notifications_collection')
    def test_get_notifications(self, mock_collection):
        """Test retrieving notifications with pagination"""
        # Mock database response
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value.sort.return_value = [
            {
                "notification_id": "notif_123",
                "type": "token_generated",
                "user_name": "John Doe",
                "token_number": "Q001",
                "queue_name": "General Service",
                "message": "Your token is ready",
                "status": "sent",
                "priority": 3,
                "created_at": datetime.utcnow()
            }
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 1
        
        response = self.client.get('/api/notifications?page=1&limit=10')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['notifications']), 1)
        self.assertEqual(data['notifications'][0]['user_name'], "John Doe")

    @patch('notification_service.app.notifications_collection')
    def test_get_notification_by_id(self, mock_collection):
        """Test retrieving specific notification by ID"""
        # Mock notification found
        mock_notification = {
            "notification_id": "notif_123",
            "type": "token_generated",
            "user_id": "507f1f77bcf86cd799439011",
            "user_name": "John Doe",
            "token_id": "507f1f77bcf86cd799439012",
            "token_number": "Q001",
            "queue_name": "General Service",
            "message": "Your token is ready",
            "status": "sent",
            "priority": 3,
            "service_type": "priority",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "sent_at": datetime.utcnow()
        }
        mock_collection.find_one.return_value = mock_notification
        
        response = self.client.get('/api/notifications/notif_123')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['notification_id'], "notif_123")
        self.assertEqual(data['user_name'], "John Doe")

    @patch('notification_service.app.notifications_collection')
    def test_get_notification_not_found(self, mock_collection):
        """Test retrieving non-existent notification"""
        mock_collection.find_one.return_value = None
        
        response = self.client.get('/api/notifications/nonexistent_notification')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("not found", data['error'])

    @patch('notification_service.app.notifications_collection')
    def test_get_notification_stats(self, mock_collection):
        """Test retrieving notification statistics"""
        # Mock aggregation results
        mock_collection.count_documents.return_value = 100
        mock_collection.aggregate.side_effect = [
            [{'_id': 'token_generated', 'count': 80}, {'_id': 'token_called', 'count': 20}],
            [{'_id': 'sent', 'count': 100}],
        ]
        
        response = self.client.get('/api/notifications/stats')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total_notifications'], 100)
        self.assertIn('token_generated', data['notifications_by_type'])
        self.assertIn('sent', data['notifications_by_status'])

    def test_robust_error_handling(self):
        """Test that service handles errors gracefully without crashing"""
        # Test with malformed JSON
        response = self.client.post('/api/notifications/send',
                                  data='invalid json',
                                  content_type='application/json')
        # Should return 400, not crash
        self.assertEqual(response.status_code, 400)
        
        # Test with empty request
        response = self.client.post('/api/notifications/send')
        # Should return 400, not crash
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()