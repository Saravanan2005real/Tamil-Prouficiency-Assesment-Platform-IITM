# Backend-Frontend Connection Guide

## ✅ Connection Status

The backend and frontend are now properly configured to connect.

## 🚀 Quick Start

### Step 1: Start Backend Server
```bash
cd Backend
python app.py
```
Or double-click: `START_BACKEND.bat`

**Backend runs on:** `http://127.0.0.1:5000`

### Step 2: Start Frontend Server
```bash
python -m http.server 8000
```
Or double-click: `START_FRONTEND.bat`

**Frontend runs on:** `http://localhost:8000`

### Step 3: Open in Browser
Navigate to: **`http://localhost:8000`**

⚠️ **IMPORTANT:** Do NOT open the HTML file directly (file://). Always use `http://localhost:8000`

## 🔌 API Endpoints

### Backend Endpoints (Port 5000):
- `GET /api/test` - Test connection
- `GET /api/start-test/<level>` - Start test for a level
- `GET /questions/<audio_id>` - Get questions by audio ID
- `GET /audio/<audio_id>` - Get audio file by ID
- `POST /api/upload-audio` - Upload audio (host mode)
- `GET /api/transcript` - Get transcript (host mode)
- `POST /evaluate` - Evaluate answers

### Frontend Configuration:
- All API calls use: `http://127.0.0.1:5000`
- CORS is enabled on backend
- Connection test runs automatically on page load

## ✅ Verification

1. **Backend Status**: Check the "Backend Status" section at the bottom of the page
   - Should show: `✅ API working` (green)
   - If red: Backend server is not running

2. **Console Check**: Press F12 → Console tab
   - Should see: No CORS errors
   - Connection test should succeed

## 🐛 Troubleshooting

### "Cannot connect to backend"
1. Check if backend is running: `netstat -ano | findstr :5000`
2. Restart backend: `START_BACKEND.bat`
3. Check browser console (F12) for errors

### CORS Errors
- Make sure you're using `http://localhost:8000` (not file://)
- Backend CORS is configured to allow all origins

### Audio/Questions Not Loading
- Check if audio file exists in `Backend/uploads/audio/`
- Check if questions file exists in `Backend/data/questions/`
- Verify audio_id matches between files

## 📝 Notes

- Backend must be running before frontend can connect
- Both servers can run simultaneously
- Backend runs on port 5000, Frontend on port 8000
- All API endpoints are prefixed with `/api/` except `/audio/` and `/questions/`
