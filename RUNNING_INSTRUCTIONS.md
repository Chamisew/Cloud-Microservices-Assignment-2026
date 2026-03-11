# Running the Smart Queue Management System

This guide provides instructions for running the Smart Queue Management System locally.

## Prerequisites

- Python 3.9+
- MongoDB Atlas account (recommended) or local MongoDB
- Git (for cloning if needed)

## Setup Instructions

### 1. MongoDB Setup

**Option A: MongoDB Atlas (Recommended)**
1. Sign up for a free account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a new cluster (M0 Free Tier)
3. Create a database user with read/write permissions
4. Whitelist your IP address (or allow access from anywhere for development)
5. Get your connection string in the format:
   ```
   mongodb+srv://<username>:<password>@<cluster-name>.mongodb.net/<database-name>
   ```

**Option B: Local MongoDB (Alternative)**
1. Install MongoDB Community Edition
2. Start the MongoDB service

### 2. Environment Configuration

Create `.env` files in each service directory with your MongoDB connection string:

**For each service directory (user-service, queue-service, token-service, notification-service):**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and replace with your MongoDB connection string
MONGO_URI=mongodb+srv://your_username:your_password@cluster0.example.mongodb.net/smart_queue_db?retryWrites=true&w=majority
```

### 3. Running the Services

**Method 1: Using the Batch Script (Windows)**

1. Double-click the `START_SERVICES.bat` file to run all services
2. Each service will start in a separate Command Prompt window
3. Services will be available at:
   - User Service: http://localhost:5001
   - Queue Service: http://localhost:5002
   - Token Service: http://localhost:5003
   - Notification Service: http://localhost:5004

**Method 2: Manual Startup (All Platforms)**

1. **Start User Service (Port 5001):**
   ```bash
   cd user-service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

2. **Start Queue Service (Port 5002):**
   ```bash
   cd queue-service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   export USER_SERVICE_URL=http://localhost:5001
   export TOKEN_SERVICE_URL=http://localhost:5003
   python app.py
   ```

3. **Start Token Service (Port 5003):**
   ```bash
   cd token-service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   export NOTIFICATION_SERVICE_URL=http://localhost:5004
   python app.py
   ```

4. **Start Notification Service (Port 5004):**
   ```bash
   cd notification-service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

### 4. Verifying the System

After starting all services, verify they are running:

- **Health Checks:**
  - User Service: http://localhost:5001/health
  - Queue Service: http://localhost:5002/health
  - Token Service: http://localhost:5003/health
  - Notification Service: http://localhost:5004/health

All services should return a JSON response with `"status": "healthy"`.

### 5. Testing the Integration

**Test the complete integration flow:**

1. **Create a user** (User Service):
   ```bash
   curl -X POST http://localhost:5001/api/users \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test User",
       "email": "test@example.com",
       "phone": "+94771234567"
     }'
   ```

2. **Create a queue** (Queue Service):
   ```bash
   curl -X POST http://localhost:5002/api/queues \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test Queue",
       "description": "A test queue"
     }'
   ```

3. **Join the queue** (Queue Service) - this triggers the full integration:
   ```bash
   curl -X POST http://localhost:5002/api/queues/join \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "<user_id_from_step_1>",
       "queue_id": "<queue_id_from_step_2>"
     }'
   ```

This should create a token in the Token Service and send a notification to the Notification Service.

### 6. Stopping the Services

To stop each service, press `Ctrl+C` in each terminal/command prompt window where the services are running.

## Troubleshooting

**Common Issues:**

1. **Port Already in Use:**
   - Make sure no other applications are using ports 5001-5004
   - Kill any existing processes on these ports before starting

2. **MongoDB Connection Issues:**
   - Verify your connection string is correct
   - Check that your IP is whitelisted in MongoDB Atlas
   - Ensure the database user has proper permissions

3. **Service Dependencies:**
   - Make sure User and Token services are running before starting Queue service
   - Make sure Notification service is running before starting Token service

4. **Environment Variables:**
   - Ensure all required environment variables are set
   - Check that MONGO_URI is correctly formatted

## API Documentation

Each service includes OpenAPI documentation:
- User Service: [user-service/swagger.yaml](./user-service/swagger.yaml)
- Queue Service: [queue-service/swagger.yaml](./queue-service/swagger.yaml) 
- Token Service: [token-service/swagger.yaml](./token-service/swagger.yaml)
- Notification Service: [notification-service/swagger.yaml](./notification-service/swagger.yaml)

## Next Steps

- Configure your production MongoDB Atlas connection
- Set up proper authentication between services
- Configure logging and monitoring
- Deploy to cloud platform (AWS, Azure, GCP, etc.)

The Smart Queue Management System is now ready to use!