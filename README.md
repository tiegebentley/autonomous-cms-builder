# 🏗️ Autonomous CMS Builder

An AI-powered system that analyzes frontend projects and automatically generates a comprehensive Kirby CMS integration with self-validation.

## 🎯 What It Does

1. **Analyzes** your entire frontend project (React, Next.js, Vite, or static HTML)
2. **Validates** its own analysis for accuracy using a Critic Agent
3. **Generates** complete Kirby CMS blueprints and templates
4. **Tests** everything to ensure it works
5. **Applies** changes to your project automatically (with rollback on failure)
6. **Verifies** end-to-end functionality

## 🤖 Multi-Agent Architecture

```
Orchestrator
    ├── Analyzer Agent  → Scans & maps your project
    ├── Critic Agent    → Validates the analysis
    ├── Builder Agent   → Generates Kirby CMS
    ├── Tester Agent    → Tests everything
    └── Applicator Agent → Applies changes safely
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Installation

1. **Backend Setup:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys
```

2. **Frontend Setup:**
```bash
cd frontend
npm install
```

### Running the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## 📖 Usage

### Basic Workflow

1. **Enter Project Path:**
   - Provide the absolute path to your frontend project
   - Example: `/root/small-group-soccer-training-2026-02-21-34l4t/`

2. **Configure Options:**
   - ☑️ Auto-apply changes (recommended)
   - ☑️ Enable self-validation (recommended)

3. **Click "Build CMS":**
   - Watch real-time progress as agents work
   - See logs streaming live
   - Wait for completion (typically 3-5 minutes)

4. **Access Your CMS:**
   - Navigate to your project's Kirby panel
   - Manage all content through the UI
   - Changes sync automatically to your frontend

### Interface Preview

```
┌──────────────────────────────────────┐
│  📁 /root/small-group-soccer...      │
│  📝 Project Name: ___________        │
│  ☑️  Auto-apply changes              │
│  ☑️  Enable self-validation          │
│  🚀 [Build CMS]                      │
├──────────────────────────────────────┤
│  Progress: 60%                       │
│  ✅ Analyzer  - Complete (32s)       │
│  ✅ Critic    - Complete (18s)       │
│  ⏳ Builder   - In Progress... 47%   │
│  ⏸️  Tester    - Waiting              │
│  ⏸️  Applicator - Waiting             │
└──────────────────────────────────────┘
```

## 🛠️ Tech Stack

- **Frontend:** React + Vite + TypeScript + Tailwind CSS + shadcn/ui
- **Backend:** Python + FastAPI + uvicorn
- **AI:** Claude Sonnet 4.5 (via Anthropic SDK)
- **Agents:** Pydantic AI
- **CMS:** Kirby 3.10+
- **Database:** Supabase (PostgreSQL + pgvector)
- **Task Queue:** Celery + Redis (for production)

## 📁 Project Structure

```
autonomous-cms-builder/
├── frontend/                 # React interface
│   ├── src/
│   │   ├── components/
│   │   │   ├── ProjectInput.tsx
│   │   │   └── ProgressDashboard.tsx
│   │   ├── pages/
│   │   │   └── Builder.tsx
│   │   └── lib/
│   │       └── utils.ts
│   └── package.json
│
├── backend/                  # FastAPI + Agents
│   ├── main.py              # FastAPI app with SSE
│   ├── agents/              # Agent implementations (TODO)
│   ├── tools/               # Parser & generator tools (TODO)
│   └── requirements.txt
│
├── kirby-base/              # Base Kirby template
│
└── README.md                # This file
```

## 🔄 Current Status

### ✅ Phase 1: Core Infrastructure (COMPLETE)

- [x] Project directory structure
- [x] Backend FastAPI setup with SSE
- [x] Frontend React + Vite + Tailwind
- [x] Real-time progress UI
- [x] Basic routing and API
- [x] Server-Sent Events for live updates

### 🚧 Next Steps (TODO)

**Phase 2: Analyzer Agent**
- [ ] Framework detection (React/Next.js/Vite/static)
- [ ] AST parsing for JSX/TSX files
- [ ] Content extraction
- [ ] Pattern detection

**Phase 3: Critic Agent**
- [ ] Analysis validation
- [ ] Completeness checking
- [ ] Confidence scoring

**Phase 4: Builder Agent**
- [ ] Blueprint generation
- [ ] Template generation
- [ ] Content migration

**Phase 5: Tester Agent**
- [ ] Syntax validation
- [ ] Integration testing
- [ ] API testing

**Phase 6: Applicator Agent**
- [ ] Backup system
- [ ] Integration engine
- [ ] Rollback mechanism

**Phase 7: Kirby Integration**
- [ ] Copy base Kirby template
- [ ] Configure for multi-project support
- [ ] Set up project registry

## 🧪 Testing

```bash
# Backend health check
curl http://localhost:8001/api/health

# Create test project
curl -X POST http://localhost:8001/api/projects/build \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/root/test-project",
    "name": "Test Project",
    "auto_apply": true,
    "enable_validation": true
  }'

# Watch SSE stream
curl -N http://localhost:8001/api/projects/proj_1/stream
```

## 📝 API Reference

### `POST /api/projects/build`
Start CMS build process for a project.

**Request:**
```json
{
  "path": "/absolute/path/to/project",
  "name": "Project Name",
  "auto_apply": true,
  "enable_validation": true
}
```

**Response:**
```json
{
  "project_id": "proj_1",
  "status": "queued",
  "message": "CMS build process started"
}
```

### `GET /api/projects/{project_id}/status`
Get current status of a build.

### `GET /api/projects/{project_id}/stream`
Server-Sent Events endpoint for real-time progress.

### `GET /api/projects`
List all projects.

### `DELETE /api/projects/{project_id}`
Delete a project.

## 🎯 Supported Projects

Currently designed to analyze:

- **React** (with Vite, CRA, or custom setup)
- **Next.js** (Pages Router and App Router)
- **Static HTML/CSS/JS** sites
- **Vite** projects

## 🔐 Security Notes

- Always backup your projects before using auto-apply
- Review generated CMS configurations before deploying to production
- Use environment variables for sensitive data
- Enable validation for safer operations

## 📚 Resources

- [Kirby CMS Documentation](https://getkirby.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic AI](https://ai.pydantic.dev/)
- [Anthropic API](https://docs.anthropic.com/)

## 🤝 Contributing

This is currently a personal project. Contributions welcome once core functionality is complete.

## 📄 License

MIT License - See LICENSE file for details

## 🙋 Support

For issues or questions:
1. Check the logs in the Progress Dashboard
2. Review API responses for error details
3. Check `.env` configuration

---

**Built with ❤️ using Claude Code and AI agents**
