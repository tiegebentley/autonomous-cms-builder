# 🚀 Getting Started

## Current Status

✅ **Phase 1 Complete** - Core infrastructure is ready!

The foundation is built and running:
- ✅ Backend API with FastAPI + SSE
- ✅ Frontend interface with React + Vite + Tailwind
- ✅ Real-time progress dashboard
- ✅ Project management endpoints

## 🏃 Running Right Now

**Backend:** http://localhost:8001
- API: http://localhost:8001/docs (FastAPI auto-docs)
- Health: http://localhost:8001/api/health

**Frontend:** http://localhost:3099
- Open in browser to see the UI

## 🧪 Try It Out

### Option 1: Web Interface
1. Open http://localhost:3099
2. Enter a project path (e.g., `/root/small-group-soccer-training-2026-02-21-34l4t/`)
3. Enter a project name
4. Click "Build CMS"
5. Watch the agents work in real-time!

### Option 2: API Testing
```bash
# Create a test build
curl -X POST http://localhost:8001/api/projects/build \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/root/test-project",
    "name": "Test Project",
    "auto_apply": true,
    "enable_validation": true
  }'

# Get the project_id from response, then watch progress
curl -N http://localhost:8001/api/projects/proj_1/stream
```

## 📊 What You'll See

The current demo shows:
- ✅ Analyzer Agent - simulated analysis
- ✅ Critic Agent - simulated validation
- ✅ Builder Agent - simulated CMS generation
- ✅ Tester Agent - simulated testing
- ✅ Applicator Agent - simulated deployment

**Note:** These are currently simulated workflows. The next phases will implement the actual AI agents.

## 🔄 Next Development Steps

### Phase 2: Analyzer Agent (Planned)
Build the actual frontend analyzer that:
- Detects framework (React/Next.js/Vite/static)
- Parses JSX/TSX files with AST
- Extracts content patterns
- Maps component relationships
- Identifies data structures

### Phase 3: Critic Agent (Planned)
Implement self-validation that:
- Reviews analyzer output
- Checks for missing components
- Validates accuracy
- Scores confidence
- Flags ambiguities

### Phase 4-6: Builder, Tester, Applicator (Planned)
Complete the full pipeline.

## 🛠️ Development Commands

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend
npm run dev

# Install new Python packages
cd backend
source venv/bin/activate
pip install <package-name>
pip freeze > requirements.txt

# Install new frontend packages
cd frontend
npm install <package-name>
```

## 📝 Project Structure

```
/root/autonomous-cms-builder/
├── backend/
│   ├── main.py           # ✅ FastAPI app with SSE
│   ├── agents/           # 🚧 TODO: Implement agents
│   ├── tools/            # 🚧 TODO: Parsers & generators
│   └── requirements.txt  # ✅ Dependencies installed
│
├── frontend/
│   ├── src/
│   │   ├── components/   # ✅ ProjectInput, ProgressDashboard
│   │   ├── pages/        # ✅ Builder page
│   │   └── lib/          # ✅ Utils
│   └── package.json      # ✅ Dependencies installed
│
├── kirby-base/           # 📁 Empty (TODO: Copy from /root/microsite)
├── README.md             # ✅ Full documentation
└── GETTING_STARTED.md    # ✅ This file
```

## 💡 Tips

1. **Check logs** - Both servers log to console
2. **API docs** - Visit http://localhost:8001/docs for interactive API testing
3. **Hot reload** - Both frontend and backend support hot reload
4. **Port conflicts** - Backend uses 8001, Frontend uses 3099 (configurable)

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if port 8001 is in use
lsof -i :8001

# Kill existing process
pkill -f "uvicorn main:app"

# Restart
cd backend && source venv/bin/activate && uvicorn main:app --port 8001
```

### Frontend won't start
```bash
# Check if port 3099 is in use
lsof -i :3099

# Try different port
npm run dev -- --port 3100
```

### Dependencies issues
```bash
# Backend
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## 🎯 Ready to Build More?

The infrastructure is solid. Next steps:
1. Implement the Analyzer Agent (Phase 2)
2. Test with a real project
3. Iterate and improve

---

**Happy Building! 🏗️**
