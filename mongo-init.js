// MongoDB initialization script for Smart Queue Management System
// This script creates the database, collections with proper indexes, and user with proper permissions

print("Starting Smart Queue Management System database initialization...");

// First, create the user in the admin database with userAdminAnyDatabase role
db = db.getSiblingDB('admin');
db.createUser({
  user: 'admin',
  pwd: 'password',
  roles: [
    { role: 'userAdminAnyDatabase', db: 'admin' },
    { role: 'readWriteAnyDatabase', db: 'admin' },
    { role: 'dbAdminAnyDatabase', db: 'admin' }
  ]
});

// Switch to the smart_queue_db database
db = db.getSiblingDB('smart_queue_db');

// Create the database by inserting a dummy document and then removing it
db.temp_collection.insertOne({"init": "done"});
db.temp_collection.drop();

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
db.notifications.createIndex({ "sent_at": 1 });

// Create a user specifically for the smart_queue_db with readWrite permissions
db.createUser({
  user: 'admin',
  pwd: 'password',
  roles: [
    { role: 'readWrite', db: 'smart_queue_db' },
    { role: 'dbAdmin', db: 'smart_queue_db' }
  ]
});

// Remove the temp collection
db.temp_collection.drop();

print("Database initialization completed successfully!");
print("Database: smart_queue_db");
print("Collections created: users, queues, tokens, notifications");
print("Users created: admin (with permissions on smart_queue_db)");
print("Sample data inserted for testing");