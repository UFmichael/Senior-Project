# User Documentation

## Table of Contents
1. [User Guides and Manuals](#user-guides-and-manuals)
2. [Workflow](#workflow)
3. [Screenshots](#screenshots)
4. [Training Materials](#training-materials)
5. [FAQs](#faqs)

---

## 1. User Guides and Manuals

### 1.1 Getting Started Guide

#### System Requirements
- **Backend:**
  - Python 3.11
  - PostgreSQL database
  - RTMP streaming server (for video input)
  
- **Frontend:**
  - Node.js 18+
  - pnpm package manager
  - Modern web browser (Chrome, Firefox, Safari, Edge)

#### Installation Steps

**Backend Setup:**
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your database credentials and settings

# Apply database migrations
alembic upgrade head

# Start the backend server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend Setup:**
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pnpm install

# Start the development server
pnpm start

# Or build for production
pnpm build
```

#### Initial Configuration
1. Set up PostgreSQL database and update `.env` file with connection details
2. Configure RTMP server endpoint in environment settings
3. Place YOLO model weights in `backend/weights/` directory
4. Update frontend environment files (`environment.ts`, `environment.prod.ts`) with backend API URL

---

### 1.2 User Guide: Core Features

#### Authentication
**Sign Up:**
1. Navigate to the application home page
2. Click "Sign Up" button
3. Enter username and password
4. Submit form to create account

**Login:**
1. Enter your username and password
2. Click "Login"
3. You'll be redirected to the dashboard upon successful authentication

**Logout:**
- Click the logout button in the navigation menu

#### Dashboard
The dashboard provides an overview of:
- Active video streams
- Real-time threat detection status
- Recent alerts
- System statistics

**Key Features:**
- View live stream status
- Start/stop video stream monitoring
- Quick access to alerts and analytics
- Customizable color themes

#### Stream Management
**Starting a Stream:**
1. Navigate to Dashboard
2. Click "Start Stream" button
3. Enter stream ID (e.g., "1" for `rtmp://127.0.0.1:1935/live/1`)
4. System begins processing video and detecting threats

**Stopping a Stream:**
1. Click "Stop Stream" button for the active stream
2. Confirm the action
3. Stream processing halts and resources are released

#### Alert Log
**Viewing Alerts:**
1. Navigate to "Alert Log" from the main menu
2. View list of detected threats with:
   - Timestamp
   - Threat level (LOW, MEDIUM, HIGH)
   - Threat status (MONITORING, ACTIVE, CLEARED)
   - Detected weapons
   - Facial emotions (if detected)
   - Confidence scores

**Filtering Alerts:**
- Filter by date range
- Filter by threat level
- Search by specific criteria

#### Analytics
**Accessing Analytics:**
1. Click "Analytics" in the navigation menu
2. View visualizations including:
   - Threat trends over time
   - Distribution by threat level
   - Detection accuracy metrics
   - System performance statistics

**Customization:**
- Adjust time ranges
- Export data for reporting
- Configure chart types

---

### 1.3 Backend API Reference

#### Base URL
```
http://localhost:8000
```

#### Authentication Endpoints

**POST /auth/signup**
- **Description:** Create a new user account
- **Request Body:**
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **Response:** User object with JWT token

**POST /auth/login**
- **Description:** Authenticate user and receive token
- **Request Body:**
  ```json
  {
    "username": "string",
    "password": "string"
  }
  ```
- **Response:**
  ```json
  {
    "access_token": "string",
    "token_type": "bearer"
  }
  ```

#### Stream Endpoints

**POST /stream/{stream_id}/start**
- **Description:** Start video stream processing
- **Headers:** `Authorization: Bearer <token>`
- **Path Parameters:** `stream_id` (string)
- **Response:**
  ```json
  {
    "status": "success",
    "message": "Stream handler for '1' started."
  }
  ```

**POST /stream/{stream_id}/stop**
- **Description:** Stop video stream processing
- **Headers:** `Authorization: Bearer <token>`
- **Path Parameters:** `stream_id` (string)
- **Response:**
  ```json
  {
    "status": "success",
    "message": "Stream handler for '1' stopped."
  }
  ```

**WebSocket /stream/{stream_id}/ws**
- **Description:** WebSocket connection for receiving processed frames
- **Connection:** Binary frames with JSON metadata
- **Messages:**
  - Client → Server: `{"type": "ping", "timestamp": <time>}`
  - Server → Client: `{"type": "pong", "timestamp": <time>}`
  - Server → Client: Frame metadata + binary JPEG data

#### User Endpoints

**GET /user/me**
- **Description:** Get current authenticated user
- **Headers:** `Authorization: Bearer <token>`
- **Response:** User object

#### YOLO Detection Endpoints

**POST /yolo/predict**
- **Description:** Detect objects in an image
- **Request:** Multipart form data with image file
- **Response:** Detection results with bounding boxes and confidence scores

---

## 2. Workflow

### 2.1 Typical User Workflow

```
┌─────────────┐
│ User Login  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   Dashboard     │
│  - View Status  │
└──────┬──────────┘
       │
       ▼
┌──────────────────┐
│  Start Stream    │
│  - Enter ID      │
│  - Begin Monitor │
└──────┬───────────┘
       │
       ▼
┌────────────────────────┐
│  Real-time Detection   │
│  - YOLO person detect  │
│  - Weapon detection    │
│  - Face emotion detect │
└──────┬─────────────────┘
       │
       ▼
┌──────────────────┐
│  Threat Logging  │
│  - Save to DB    │
│  - Display Alert │
└──────┬───────────┘
       │
       ▼
┌────────────────────┐
│  Review Analytics  │
│  - View trends     │
│  - Generate reports│
└────────────────────┘
```

### 2.2 System Data Flow

```
[RTMP Stream] 
    ↓
[Backend Stream Handler]
    ↓
[Frame Processing]
    ├─→ [YOLO Pose Detection] → Person tracking
    ├─→ [YOLO Weapon Detection] → Weapon identification
    └─→ [DeepFace] → Emotion detection
    ↓
[Threat Assessment]
    ↓
[Database Logging] → PostgreSQL
    ↓
[WebSocket Broadcast]
    ↓
[Frontend Display]
    ├─→ Dashboard (live view)
    ├─→ Alert Log (history)
    └─→ Analytics (statistics)
```

### 2.3 Admin Workflow

1. **System Initialization:**
   - Start backend server
   - Start frontend server
   - Verify RTMP server is running
   - Check database connectivity

2. **User Management:**
   - Create admin accounts
   - Review user access logs
   - Manage permissions

3. **Stream Monitoring:**
   - Configure stream endpoints
   - Monitor system performance
   - Review detection accuracy

4. **Alert Management:**
   - Review high-priority threats
   - Export alert reports
   - Archive historical data

---

## 3. Screenshots

### 3.1 Backend Console

**Example Console Output**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete

[1] Processing frame 45
🔴 PERSON THREAT [1]: person_0 is a threat. Reason: Weapon (knife) detected
⚡️ NEW THREAT DETECTED: person_0. Logging to database...
✅ Successfully logged Threat ID: 123e4567-e89b-12d3-a456-426614174000

[WebSocket] Stream 1 stats: sent=120, dropped=0, slow_clients=0/1
✅ Threat cleared for person_0.
```

---

## 4. Training Materials

### 4.1 Quick Start Tutorial (5 minutes)

**Objective:** Get your first stream running and detect a threat

**Steps:**
1. **Login** to the application
2. **Navigate** to Dashboard
3. **Click** "Start Stream" button
4. **Enter** stream ID: `1`
5. **Wait** for "Stream started successfully" message
6. **Observe** real-time detection in the video feed
7. **Check** Alert Log for any detected threats
8. **Click** "Stop Stream" when done

**Expected Outcome:** You should see live video processing with bounding boxes around detected people and any weapons.

## 5. FAQs

### 5.1 Common Questions

**Q: How do I reset my password?**
A: Currently, password reset must be done through direct database access. Contact your administrator to reset your password. (Feature planned for future release)

**Q: What do the different threat levels mean?**
A: 
- **LOW:** No weapons detected, neutral emotions
- **MEDIUM:** Potential threat indicators (certain emotions without weapons)
- **HIGH:** Weapons detected (knife, pistol, etc.)

**Q: How do I add or remove a user?**
A: Users can sign up through the registration page. To remove users, an administrator must access the database directly and delete the user record from the `Users` table.

**Q: What video formats are supported?**
A: The system accepts RTMP streams. Ensure your video source is configured to stream to `rtmp://127.0.0.1:1935/live/{stream_id}`

**Q: How accurate is the threat detection?**
A: 
- Weapon detection: ~85-90% accuracy
- Person detection: ~95% accuracy
- Emotion detection: ~70% accuracy (varies with lighting)

**Q: Can I run multiple streams simultaneously?**
A: Yes, but performance depends on your hardware. Each stream requires significant CPU/GPU resources. Monitor system performance when running 3+ streams.

**Q: How long is alert data stored?**
A: All alerts are stored indefinitely in the PostgreSQL database. Implement data retention policies as needed.

**Q: Can I customize the detection sensitivity?**
A: Detection thresholds are configured in the backend code. Contact your developer to adjust confidence thresholds in `entities/yolo/model.py` and `entities/stream_handler/combined_model.py`.
