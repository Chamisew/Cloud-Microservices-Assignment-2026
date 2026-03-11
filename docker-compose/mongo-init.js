// MongoDB initialization script for Smart Queue Management System
// This script creates the database and collections with proper indexes

print("Starting Smart Queue Management System database initialization...");

// Switch to the smart_queue_db database
db = db.getSiblingDB('smart_queue_db');

// Create users collection with indexes
db.createCollection('users');
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "phone": 1 }, { unique: true });
db.users.createIndex({ "created_at": -1 });
db.users.createIndex({ "is_active": 1 });

// Create queues collection with indexes
db.createCollection('queues');
db.queues.createIndex({ "name": 1 }, { unique: true });
db.queues.createIndex({ "status": 1 });
db.queues.createIndex({ "created_at": -1 });

// Create tokens collection with indexes
db.createCollection('tokens');
db.tokens.createIndex({ "token_number": 1 }, { unique: true });
db.tokens.createIndex({ "user_id": 1 });
db.tokens.createIndex({ "queue_id": 1 });
db.tokens.createIndex({ "status": 1 });
db.tokens.createIndex({ "created_at": -1 });
db.tokens.createIndex({ "expires_at": 1 });

// Create notifications collection with indexes
db.createCollection('notifications');
db.notifications.createIndex({ "user_id": 1 });
db.notifications.createIndex({ "type": 1 });
db.notifications.createIndex({ "status": 1 });
db.notifications.createIndex({ "created_at": -1 });
db.notifications.createIndex({ "scheduled_time": 1 });

// Create sample data for testing
print("Creating sample data...");

// Sample users
db.users.insertMany([
  {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+94771234567",
    "nic": "123456789V",
    "created_at": new Date(),
    "updated_at": new Date(),
    "is_active": true
  },
  {
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "phone": "+94712345678",
    "nic": "987654321V",
    "created_at": new Date(),
    "updated_at": new Date(),
    "is_active": true
  }
]);

// Sample queues
db.queues.insertMany([
  {
    "name": "General Service",
    "description": "General customer service queue",
    "status": "active",
    "max_capacity": 50,
    "current_count": 0,
    "average_wait_time": 10,
    "created_at": new Date(),
    "updated_at": new Date()
  },
  {
    "name": "Technical Support",
    "description": "IT and technical support queue",
    "status": "active",
    "max_capacity": 30,
    "current_count": 0,
    "average_wait_time": 15,
    "created_at": new Date(),
    "updated_at": new Date()
  }
]);

print("Database initialization completed successfully!");
print("Database: smart_queue_db");
print("Collections created: users, queues, tokens, notifications");
print("Sample data inserted for testing");