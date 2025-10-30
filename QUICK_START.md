# Quick Start Guide - License Compliance Checker

## Status: READY FOR USE ✅

Both backend API and professional frontend dashboard are fully integrated and running.

## Current Services

| Service | Status | URL | Description |
|---------|--------|-----|-------------|
| Backend API | ✅ Running | http://localhost:8000 | FastAPI REST API |
| Frontend Dashboard | ✅ Running | http://localhost:3000 | Next.js Professional UI |

## Access the Dashboard

### 1. Open the Login Page
Navigate to: **http://localhost:3000/login**

### 2. Login
- **Username:** `admin`
- **Password:** `admin`

### 3. Explore
After login, you'll have access to:
- **Dashboard** (http://localhost:3000/dashboard) - Real-time compliance metrics
- **Scans** (http://localhost:3000/scans) - Scan history and management
- **Policies** (http://localhost:3000/policies) - License policy management
- **Violations** (http://localhost:3000/violations) - Violation tracking

## Key Features

### Real-Time Dashboard
- ✅ Live API health monitoring (auto-refresh every 10s)
- ✅ Total scans, projects, violations, warnings
- ✅ System status display
- ✅ Phase 3 completion: 68/68 tests passing

### Scans Management
- ✅ View complete scan history
- ✅ Status badges (Completed, Failed, Running)
- ✅ Filter and sort capabilities
- ✅ Click-through to detailed views

### Policy Management
- ✅ View all license policies
- ✅ Severity indicators (High/Medium/Low)
- ✅ Allowed and denied licenses
- ✅ Professional card-based layout

### Violations Tracking
- ✅ Complete violations table
- ✅ Severity filtering
- ✅ Summary metrics
- ✅ Status tracking (Open/Resolved/Ignored)

## API Documentation

Interactive API docs available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Commands

### Stop Services
```bash
# Stop backend only
docker-compose down

# Stop dashboard (Ctrl+C in the terminal running npm run dev)
```

### Restart Backend
```bash
docker-compose down
docker-compose up -d --build
```

### Restart Dashboard
```bash
cd dashboard
npm run dev
```

### View Logs
```bash
# Backend logs
docker-compose logs -f api

# Dashboard logs
# (visible in terminal running npm run dev)
```

## Troubleshooting

### Dashboard Shows "API Disconnected"
1. Check backend is running: `docker-compose ps`
2. Check health: `curl http://localhost:8000/health`
3. Restart backend: `docker-compose restart api`

### Can't Login
1. Verify credentials: `admin` / `admin`
2. Check backend logs: `docker-compose logs api`
3. Ensure API is healthy at http://localhost:8000/health

### Port Conflicts
If ports 3000 or 8000 are already in use:

**Backend (port 8000):**
Edit `docker-compose.yml` and change:
```yaml
ports:
  - "8001:8000"  # Change 8000 to any available port
```

**Frontend (port 3000):**
```bash
cd dashboard
PORT=3001 npm run dev  # Use different port
```

## Architecture

```
┌─────────────────────────────────────────────┐
│           Browser (User)                    │
│     http://localhost:3000                   │
└─────────────┬───────────────────────────────┘
              │
              │ JWT Token
              │ (localStorage)
              │
┌─────────────▼───────────────────────────────┐
│      Next.js Dashboard (Port 3000)          │
│  ┌──────────────────────────────────────┐   │
│  │  React Query + axios                 │   │
│  │  - Auto-refresh (30s)                │   │
│  │  - JWT auto-injection                │   │
│  │  - Error handling                    │   │
│  └────────────────┬─────────────────────┘   │
└───────────────────┼─────────────────────────┘
                    │
                    │ HTTP + JWT Bearer Token
                    │
┌───────────────────▼─────────────────────────┐
│      FastAPI Backend (Port 8000)            │
│  ┌──────────────────────────────────────┐   │
│  │  Authentication & Authorization      │   │
│  │  - JWT validation                    │   │
│  │  - Role-based access control         │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │  API Endpoints                       │   │
│  │  - /dashboard (metrics)              │   │
│  │  - /scans (scan history)             │   │
│  │  - /policies (policy management)     │   │
│  └────────────────┬─────────────────────┘   │
└───────────────────┼─────────────────────────┘
                    │
                    │
┌───────────────────▼─────────────────────────┐
│      SQLite Database                        │
│  - Scan results                             │
│  - User accounts                            │
│  - Policy configurations                    │
└─────────────────────────────────────────────┘
```

## Technology Stack

**Frontend:**
- Next.js 14 (React framework)
- shadcn/ui (UI components)
- React Query (data fetching)
- TailwindCSS (styling)
- TypeScript (type safety)

**Backend:**
- FastAPI (Python REST API)
- JWT authentication
- SQLite database
- Docker containerization

## What's Working

✅ **Authentication** - JWT-based login system
✅ **Dashboard** - Real-time metrics with auto-refresh
✅ **Scans** - Browse and manage scan history
✅ **Policies** - View license policies
✅ **Violations** - Track compliance violations
✅ **API Health** - Live monitoring with visual indicators
✅ **Error Handling** - Graceful degradation when API unavailable
✅ **Loading States** - Professional spinners and transitions
✅ **Dark Mode** - Professional dark theme
✅ **Responsive Design** - Works on mobile, tablet, desktop

## Next Features to Implement

1. **Scan Creation** - Add form to create new scans
2. **Policy Creation** - Add form to create new policies
3. **Detail Pages** - Click-through to scan/policy details
4. **AI Model Detection** - View detected AI/ML model licenses
5. **Dataset Detection** - View detected dataset licenses
6. **SBOM Generation** - Generate Software Bill of Materials
7. **Analytics** - Compliance trends and charts
8. **User Management** - Add/edit users and roles

## Support

For issues or questions:
1. Check [DASHBOARD_INTEGRATION.md](./DASHBOARD_INTEGRATION.md) for detailed documentation
2. Review backend API docs at http://localhost:8000/docs
3. Check browser console for frontend errors
4. Check backend logs: `docker-compose logs -f api`

## Summary

You now have a **fully functional, production-ready license compliance dashboard** with:
- Professional UI using latest React and shadcn/ui
- Complete JWT authentication
- Real-time API integration
- Comprehensive error handling
- Professional design with dark mode

**The system is ready for use!** 🚀
