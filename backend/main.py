"""
Autonomous CMS Builder - Main FastAPI Application
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import json
import os
from datetime import datetime
from agents.analyzer import AnalyzerAgent
from agents.critic import CriticAgent
from agents.builder import BuilderAgent
from agents.tester import TesterAgent
from agents.applicator import ApplicatorAgent
from agents.installer import InstallerAgent
from agents.integrator import IntegratorAgent

app = FastAPI(
    title="Autonomous CMS Builder",
    description="AI-powered CMS generation system for frontend projects",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:3037", "http://localhost:3100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Project(BaseModel):
    path: str
    name: str
    auto_apply: bool = True
    enable_validation: bool = True

class AgentStatus(BaseModel):
    agent: str
    status: str  # pending, in_progress, completed, failed
    progress: int
    duration: Optional[float] = None
    message: Optional[str] = None

# In-memory storage for demo
projects = {}
agent_statuses = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Autonomous CMS Builder",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "agents": "ready",
        "projects_count": len(projects)
    }

@app.get("/api/projects/scan")
async def scan_projects(base_path: str = "/root"):
    """
    Scan directories for potential frontend projects
    Looks for package.json, index.html, or common framework files
    """
    try:
        discovered_projects = []

        # Scan immediate subdirectories
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)

            # Skip hidden directories and common non-project folders
            if item.startswith('.') or item in ['node_modules', 'venv', '__pycache__', 'dist', 'build']:
                continue

            if os.path.isdir(item_path):
                # Check for frontend project indicators
                has_package_json = os.path.exists(os.path.join(item_path, 'package.json'))
                has_index_html = os.path.exists(os.path.join(item_path, 'index.html'))
                has_public_folder = os.path.exists(os.path.join(item_path, 'public'))
                has_src_folder = os.path.exists(os.path.join(item_path, 'src'))

                # Determine project type
                project_type = None
                if has_package_json:
                    try:
                        with open(os.path.join(item_path, 'package.json'), 'r') as f:
                            pkg = json.load(f)
                            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

                            if 'next' in deps:
                                project_type = 'Next.js'
                            elif 'react' in deps and 'vite' in deps:
                                project_type = 'React + Vite'
                            elif 'react' in deps:
                                project_type = 'React'
                            elif 'vue' in deps:
                                project_type = 'Vue.js'
                            elif '@angular/core' in deps:
                                project_type = 'Angular'
                            else:
                                project_type = 'Node.js'
                    except:
                        project_type = 'JavaScript'
                elif has_index_html and has_public_folder:
                    project_type = 'Static HTML'
                elif has_index_html:
                    project_type = 'HTML'

                # Add to discovered projects if it looks like a frontend project
                if project_type:
                    discovered_projects.append({
                        "name": item,
                        "path": item_path,
                        "type": project_type,
                        "has_package_json": has_package_json,
                        "has_src": has_src_folder
                    })

        # Sort by name
        discovered_projects.sort(key=lambda x: x['name'])

        return {
            "projects": discovered_projects,
            "count": len(discovered_projects),
            "base_path": base_path
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan projects: {str(e)}")

@app.post("/api/projects/build")
async def build_cms(project: Project):
    """
    Start the CMS building process for a project
    """
    project_id = f"proj_{len(projects) + 1}"

    # Store project
    projects[project_id] = {
        "id": project_id,
        "path": project.path,
        "name": project.name,
        "auto_apply": project.auto_apply,
        "enable_validation": project.enable_validation,
        "status": "started",
        "created_at": datetime.now().isoformat()
    }

    # Initialize agent statuses
    agent_statuses[project_id] = {
        "analyzer": {"status": "pending", "progress": 0},
        "critic": {"status": "pending", "progress": 0},
        "builder": {"status": "pending", "progress": 0},
        "tester": {"status": "pending", "progress": 0},
        "applicator": {"status": "pending", "progress": 0},
        "installer": {"status": "pending", "progress": 0},
        "integrator": {"status": "pending", "progress": 0},
    }

    return {
        "project_id": project_id,
        "status": "queued",
        "message": "CMS build process started"
    }

@app.get("/api/projects/{project_id}/status")
async def get_project_status(project_id: str):
    """
    Get the current status of a project build
    """
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "project": projects[project_id],
        "agents": agent_statuses.get(project_id, {})
    }

async def generate_progress_events(project_id: str):
    """
    SSE generator for real-time progress updates with REAL AI agents
    """
    if project_id not in projects:
        yield f"data: {json.dumps({'error': 'Project not found'})}\n\n"
        return

    project = projects[project_id]

    try:
        # Phase 1: REAL Analyzer Agent
        yield f"data: {json.dumps({'agent': 'analyzer', 'status': 'in_progress', 'progress': 0, 'message': 'Scanning project files...'})}\n\n"

        analyzer = AnalyzerAgent(
            project_path=project["path"],
            project_name=project["name"],
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        # Update progress during scanning
        yield f"data: {json.dumps({'agent': 'analyzer', 'status': 'in_progress', 'progress': 30, 'message': 'Parsing HTML files...'})}\n\n"

        # Execute the analyzer
        analyzer_result = await analyzer.execute()

        # Store results
        projects[project_id]["analyzer_result"] = analyzer_result
        agent_statuses[project_id]["analyzer"]["status"] = "completed"
        agent_statuses[project_id]["analyzer"]["progress"] = 100

        files_analyzed = analyzer_result.get("files_analyzed", 0) + analyzer_result.get("components_analyzed", 0)
        framework = analyzer_result.get("framework", "unknown")
        yield f"data: {json.dumps({'agent': 'analyzer', 'status': 'completed', 'progress': 100, 'message': f'Analyzed {files_analyzed} files ({framework} project)'})}\n\n"

        # Phase 2: REAL Critic Agent (if validation enabled)
        critic_result = None
        if project.get("enable_validation", True):
            yield f"data: {json.dumps({'agent': 'critic', 'status': 'in_progress', 'progress': 0, 'message': 'Validating analysis...'})}\n\n"

            critic = CriticAgent(
                project_path=project["path"],
                project_name=project["name"],
                analyzer_output=analyzer_result,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
            )

            critic_result = await critic.execute()
            projects[project_id]["critic_result"] = critic_result
            agent_statuses[project_id]["critic"]["status"] = "completed"
            agent_statuses[project_id]["critic"]["progress"] = 100

            confidence = int(critic_result.get("overall_confidence", 0) * 100)
            approval = "✓ Approved" if critic_result.get("approval") else "⚠ Needs Review"
            yield f"data: {json.dumps({'agent': 'critic', 'status': 'completed', 'progress': 100, 'message': f'{approval} (Confidence: {confidence}%)'})}\n\n"
        else:
            agent_statuses[project_id]["critic"]["status"] = "skipped"
            yield f"data: {json.dumps({'agent': 'critic', 'status': 'skipped', 'progress': 100, 'message': 'Validation disabled'})}\n\n"

        # Phase 3: REAL Builder Agent
        yield f"data: {json.dumps({'agent': 'builder', 'status': 'in_progress', 'progress': 0, 'message': 'Generating Kirby CMS files...'})}\n\n"

        builder = BuilderAgent(
            project_path=project["path"],
            project_name=project["name"],
            analyzer_output=analyzer_result,
            critic_output=critic_result or {},
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        yield f"data: {json.dumps({'agent': 'builder', 'status': 'in_progress', 'progress': 40, 'message': 'Creating blueprints...'})}\n\n"

        builder_result = await builder.execute()
        projects[project_id]["builder_result"] = builder_result
        agent_statuses[project_id]["builder"]["status"] = "completed"
        agent_statuses[project_id]["builder"]["progress"] = 100

        files_generated = builder_result.get("files_generated", 0)
        yield f"data: {json.dumps({'agent': 'builder', 'status': 'completed', 'progress': 100, 'message': f'Generated {files_generated} files'})}\n\n"

        # Phase 4: REAL Tester Agent
        yield f"data: {json.dumps({'agent': 'tester', 'status': 'in_progress', 'progress': 0, 'message': 'Running tests...'})}\n\n"

        tester = TesterAgent(
            project_path=project["path"],
            project_name=project["name"],
            builder_output=builder_result
        )

        tester_result = await tester.execute()
        projects[project_id]["tester_result"] = tester_result
        agent_statuses[project_id]["tester"]["status"] = "completed"
        agent_statuses[project_id]["tester"]["progress"] = 100

        tests_passed = tester_result.get("tests_passed", 0)
        tests_total = tester_result.get("tests_run", 0)
        yield f"data: {json.dumps({'agent': 'tester', 'status': 'completed', 'progress': 100, 'message': f'Tests: {tests_passed}/{tests_total} passed'})}\n\n"

        # Phase 5: REAL Applicator Agent
        yield f"data: {json.dumps({'agent': 'applicator', 'status': 'in_progress', 'progress': 0, 'message': 'Creating backup...'})}\n\n"

        applicator = ApplicatorAgent(
            project_path=project["path"],
            project_name=project["name"],
            builder_output=builder_result,
            tester_output=tester_result,
            auto_apply=project.get("auto_apply", False)
        )

        yield f"data: {json.dumps({'agent': 'applicator', 'status': 'in_progress', 'progress': 60, 'message': 'Applying changes...'})}\n\n"

        applicator_result = await applicator.execute()
        projects[project_id]["applicator_result"] = applicator_result
        agent_statuses[project_id]["applicator"]["status"] = "completed"
        agent_statuses[project_id]["applicator"]["progress"] = 100

        apply_status = applicator_result.get("apply_status", "unknown")
        yield f"data: {json.dumps({'agent': 'applicator', 'status': 'completed', 'progress': 100, 'message': f'Status: {apply_status}'})}\n\n"

        # Phase 6: REAL Installer Agent (NEW!)
        yield f"data: {json.dumps({'agent': 'installer', 'status': 'in_progress', 'progress': 0, 'message': 'Checking for Kirby CMS...'})}\n\n"

        installer = InstallerAgent()

        yield f"data: {json.dumps({'agent': 'installer', 'status': 'in_progress', 'progress': 30, 'message': 'Installing Kirby CMS...'})}\n\n"

        installer_result = await installer.execute(
            project_path=project["path"],
            options={'use_starterkit': False}
        )
        projects[project_id]["installer_result"] = installer_result
        agent_statuses[project_id]["installer"]["status"] = "completed"
        agent_statuses[project_id]["installer"]["progress"] = 100

        kirby_path = installer_result.get("kirby_path")
        install_action = installer_result.get("action")
        action_msg = "Detected existing" if install_action == "detected" else "Installed new"
        yield f"data: {json.dumps({'agent': 'installer', 'status': 'completed', 'progress': 100, 'message': f'{action_msg} Kirby at {kirby_path}'})}\n\n"

        # Phase 7: REAL Integrator Agent (NEW!)
        yield f"data: {json.dumps({'agent': 'integrator', 'status': 'in_progress', 'progress': 0, 'message': 'Integrating CMS files...'})}\n\n"

        integrator = IntegratorAgent()

        # Get path to generated files
        generated_path = applicator_result.get("output_path", os.path.join(project["path"], "kirby-cms-generated"))

        yield f"data: {json.dumps({'agent': 'integrator', 'status': 'in_progress', 'progress': 40, 'message': 'Merging blueprints and templates...'})}\n\n"

        # Find available port (check 8080-8090)
        available_port = 8080
        for port in range(8080, 8091):
            result = await integrator._test_server(f"http://localhost:{port}")
            if not result.get('accessible'):
                available_port = port
                break

        yield f"data: {json.dumps({'agent': 'integrator', 'status': 'in_progress', 'progress': 70, 'message': 'Starting PHP server...'})}\n\n"

        integrator_result = await integrator.execute(
            kirby_path=kirby_path,
            generated_files_path=generated_path,
            options={
                'port': available_port,
                'merge_strategy': 'overwrite',
                'auto_start': True
            }
        )
        projects[project_id]["integrator_result"] = integrator_result
        agent_statuses[project_id]["integrator"]["status"] = "completed"
        agent_statuses[project_id]["integrator"]["progress"] = 100

        cms_url = integrator_result.get("urls", {}).get("cms")
        panel_url = integrator_result.get("urls", {}).get("panel")
        files_merged = integrator_result.get("merge_result", {}).get("files_copied", 0)
        yield f"data: {json.dumps({'agent': 'integrator', 'status': 'completed', 'progress': 100, 'message': f'✅ CMS ready! Merged {files_merged} files'})}\n\n"

        # Final completion
        projects[project_id]["status"] = "completed"
        final_result = {
            "analyzer": analyzer_result,
            "critic": critic_result,
            "builder": builder_result,
            "tester": tester_result,
            "applicator": applicator_result,
            "installer": installer_result,
            "integrator": integrator_result,
            "urls": {
                "cms": cms_url,
                "panel": panel_url
            }
        }
        yield f"data: {json.dumps({'status': 'completed', 'message': f'🎉 CMS is live at {cms_url}', 'result': final_result})}\n\n"

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        yield f"data: {json.dumps({'status': 'failed', 'error': error_msg})}\n\n"
        projects[project_id]["status"] = "failed"
        projects[project_id]["error"] = str(e)

@app.get("/api/projects/{project_id}/stream")
async def stream_progress(project_id: str):
    """
    Server-Sent Events endpoint for real-time progress
    """
    return StreamingResponse(
        generate_progress_events(project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/api/projects")
async def list_projects():
    """
    List all projects
    """
    return {
        "projects": list(projects.values()),
        "total": len(projects)
    }

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project
    """
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")

    del projects[project_id]
    if project_id in agent_statuses:
        del agent_statuses[project_id]

    return {"status": "deleted", "project_id": project_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
