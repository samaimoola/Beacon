# StormReady React Migration Guide

Complete rewrite of the StormReady UI from Python/Streamlit to React/Next.js with Ohio State branding.

## Overview

This migration replaces the Streamlit UI with a modern React frontend while preserving all functionality and adding:
- **CometDial components** for interactive controls
- **Ohio State color scheme** (Scarlet #BB0000, Grey, White)
- **Improved performance** and responsiveness
- **Better mobile experience**

## Architecture Changes

### Before (Streamlit)
```
┌─────────────────┐
│   Streamlit     │
│   Python UI     │
│  + Engine API   │
│  (port 8501)    │
└─────────────────┘
```

### After (React + FastAPI)
```
┌──────────────┐    HTTP/REST    ┌────────────────┐
│   React UI   │ ◄─────────────► │  FastAPI       │
│  (port 3000) │                 │  + Engine API  │
│              │                 │  (port 8000)   │
└──────────────┘                 └────────────────┘
```

## What's Preserved

✅ **All engine interfaces** - No changes to `engine/api.py`  
✅ **Notification backend** - Full integration maintained  
✅ **AI concierge** - Accessible via API  
✅ **Data flow** - Same calculations and logic  
✅ **Fallback behavior** - Demo mode when backend unavailable  

## What's New

🆕 **CometDial sliders** - Beautiful circular controls for crew availability  
🆕 **Ohio State branding** - Scarlet and grey color scheme  
🆕 **Modern UI framework** - React + Next.js + Tailwind CSS  
🆕 **REST API** - FastAPI backend for frontend/backend separation  
🆕 **Responsive design** - Better mobile and tablet experience  
🆕 **Performance** - Faster rendering and interactions  

## Setup Instructions

### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

The updated `requirements.txt` includes:
- FastAPI for the REST API
- Uvicorn for the ASGI server
- Existing Streamlit (kept for backup)

### 3. Start the Backend API

```bash
python api_server.py
```

The API will run on `http://localhost:8000`

### 4. Start the React Frontend

```bash
cd frontend
npm run dev
```

The UI will be available at `http://localhost:3000`

## File Structure

```
StormReady/
├── frontend/                 # NEW: React frontend
│   ├── src/
│   │   ├── app/             # Next.js pages
│   │   │   ├── page.tsx     # Main UI
│   │   │   ├── layout.tsx   # Root layout
│   │   │   └── globals.css  # Global styles
│   │   ├── components/      # React components
│   │   │   ├── CometDial.tsx
│   │   │   └── CometDial.css
│   │   └── lib/
│   │       └── api.ts       # API client
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
├── api_server.py            # NEW: FastAPI backend
├── app.py                   # OLD: Streamlit (preserved)
├── ui/                      # OLD: Streamlit components (preserved)
├── engine/                  # UNCHANGED: Core engine
├── concierge/               # UNCHANGED: AI concierge
└── requirements.txt         # UPDATED: Added FastAPI
```

## API Endpoints

The FastAPI backend exposes:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/customers` | GET | Get customer list |
| `/api/damage-scenarios/:id` | GET | Get damage scenarios |
| `/api/evaluate` | POST | Evaluate scenario |
| `/api/notification-preview` | POST | Generate notification |
| `/api/concierge/ask` | POST | Ask AI concierge |
| `/health` | GET | Health check |

## Testing

### Test Backend API
```bash
# Start API
python api_server.py

# In another terminal
curl http://localhost:8000/api/customers
curl http://localhost:8000/health
```

### Test Frontend
```bash
cd frontend
npm run dev
# Open http://localhost:3000
```

### Test Full Stack
1. Start backend: `python api_server.py`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to `http://localhost:3000`
4. Select a household and adjust controls
5. Verify data loads from backend

## Ohio State Branding

### Colors
- **Primary (Scarlet)**: `#BB0000` - Buttons, highlights, dials
- **Secondary (Grey)**: `#666666` - Text, borders
- **Light**: `#F5F5F5` - Background
- **Dark**: `#2C2C2C` - Dark text
- **White**: `#FFFFFF` - Cards, panels

### Usage in Code
```tsx
// Tailwind classes
className="bg-ohio-scarlet text-white"
className="text-ohio-grey"

// Inline styles
style={{ color: '#BB0000' }}

// CometDial props
accent="#BB0000"
ink="#666666"
```

## CometDial Component

Circular dial for crew availability (replaces Streamlit slider):

```tsx
<CometDial
  value={availableCrews}
  min={1}
  max={10}
  step={1}
  unit=" crews"
  label="Available Crews"
  accent="#BB0000"     // Ohio State scarlet
  ink="#666666"        // Grey
  size={200}
  onChange={(value) => setAvailableCrews(value)}
/>
```

Features:
- Touch and mouse support
- Keyboard navigation (arrow keys, Page Up/Down, Home/End)
- Smooth animations
- Accessible (ARIA labels)

## Deployment

### Development
```bash
# Backend
python api_server.py

# Frontend (separate terminal)
cd frontend && npm run dev
```

### Production

#### Option 1: Separate Services
```bash
# Backend
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run build
npm start
```

#### Option 2: Docker Compose
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    command: uvicorn api_server:app --host 0.0.0.0 --port 8000

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

## Migration Checklist

- [x] Create React frontend structure
- [x] Implement CometDial component
- [x] Apply Ohio State color scheme
- [x] Create FastAPI backend
- [x] Implement API endpoints
- [x] Connect frontend to backend
- [x] Preserve all engine interfaces
- [x] Update documentation

## Next Steps

1. **Install dependencies** for both frontend and backend
2. **Test the API** to ensure backend works
3. **Test the UI** to ensure frontend connects
4. **Coordinate with teammate** on backend changes
5. **Deploy** for hackathon demo

## Fallback Plan

The **Streamlit UI is preserved** as a backup:
```bash
streamlit run app.py
```

If the React UI has issues during the demo, you can always fall back to the original Streamlit interface.

## Support

For issues or questions:
1. Check `frontend/README.md` for frontend setup
2. Verify API is running: `curl http://localhost:8000/health`
3. Check browser console for frontend errors
4. Review `api_server.py` logs for backend errors

Built for AEP HackOHIO 2026 🌩️
