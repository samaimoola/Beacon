# StormReady React UI - Quick Start Guide

Get the new React UI running in 5 minutes!

## Prerequisites

- **Node.js 18+** ([download](https://nodejs.org/))
- **Python 3.8+** (should already be installed)
- Both services will run simultaneously

## Step 1: Install Frontend Dependencies

```bash
cd frontend
npm install
```

This installs:
- React 18
- Next.js 14
- Tailwind CSS
- Motion (for CometDial animations)
- TypeScript

## Step 2: Install Backend Dependencies

```bash
# From project root
pip install -r requirements.txt
```

This adds:
- FastAPI (REST API framework)
- Uvicorn (ASGI server)
- Existing dependencies (boto3, etc.)

## Step 3: Start the Backend

```bash
# From project root
python api_server.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Keep this terminal open!

## Step 4: Start the Frontend

Open a **NEW terminal** and run:

```bash
cd frontend
npm run dev
```

You should see:
```
▲ Next.js 14.2.0
- Local:        http://localhost:3000
```

## Step 5: Open the App

Open your browser to: **http://localhost:3000**

You should see:
- 🌩️ StormReady header in Ohio State scarlet
- Sidebar with scenario controls
- CometDial for crew availability (circular dial)
- Main content area showing risk assessment

## Using the UI

### Sidebar Controls

1. **Household**: Select an anonymized customer
2. **Storm Severity**: Choose Low, Medium, or High
3. **Damage Scenario**: Select type of simulated damage
4. **Crew Availability**: Use the CometDial! 
   - Click and drag the dial
   - Use arrow keys for precise control
   - Shows 1-10 crews available
5. **Access Blocked**: Check if road access is blocked

### CometDial Tips

- **Click & Drag**: Grab the red bead and rotate
- **Keyboard**: Arrow keys for +/- 1, Page Up/Down for +/- 10
- **Touch**: Works great on touch screens
- **Flick**: Flick to spin with momentum

### Main Content

Watch as the results update automatically:
- **Risk Band**: Low / Moderate / High / Critical
- **Restoration Window**: Estimated hours for power restoration
- **Evidence Quality**: Data confidence level
- **Preparation Checklist**: Interactive to-do list
- **Alert Eligibility**: Notification criteria

## Troubleshooting

### Backend Won't Start

**Error**: "Address already in use: port 8000"

**Solution**: Something else is using port 8000
```bash
# Find what's using port 8000
lsof -ti:8000   # macOS/Linux
netstat -ano | findstr :8000   # Windows

# Kill the process or use a different port
python api_server.py --port 8001
```

### Frontend Shows "Backend not connected"

1. Check backend is running: `curl http://localhost:8000/health`
2. Check CORS in `api_server.py`
3. Check browser console (F12) for errors

### CometDial Not Working

1. Make sure `motion` package installed: `cd frontend && npm install`
2. Clear Next.js cache: `rm -rf .next`
3. Restart dev server: `npm run dev`

### "Module not found" Errors

```bash
# Frontend issues
cd frontend
rm -rf node_modules .next
npm install
npm run dev

# Backend issues
pip install --force-reinstall -r requirements.txt
```

## Demo Mode

If the Python backend isn't running, the frontend will show **demo data**:
- Yellow warning banner at top
- Simulated risk assessment
- Static crew and scenario data
- All UI features still work

This is useful for:
- Frontend development
- UI testing without backend
- Demo when backend has issues

## Production Build

For hackathon demo or deployment:

```bash
# Build frontend
cd frontend
npm run build
npm start

# Backend (production mode)
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

## Quick Reference

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | React UI |
| Backend | http://localhost:8000 | Python API |
| API Docs | http://localhost:8000/docs | FastAPI docs |
| Health Check | http://localhost:8000/health | API status |

## Next Steps

- Try different scenarios and watch results update
- Check out the CometDial controls
- Explore the Ohio State color scheme
- Review `REACT_MIGRATION.md` for architecture details
- Read `frontend/README.md` for deployment options

## Getting Help

- **Can't start backend?** Check `api_server.py` is in project root
- **Frontend errors?** Check `frontend/package.json` exists
- **API connection issues?** Verify both services are running
- **Visual bugs?** Clear browser cache (Ctrl+Shift+R)

Built for AEP HackOHIO 2026 🌩️

---

**Ready to demo?** Run both services and open http://localhost:3000
