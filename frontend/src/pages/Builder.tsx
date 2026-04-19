import { useState } from 'react';
import ProjectInput from '../components/ProjectInput';
import ProgressDashboard from '../components/ProgressDashboard';
import { Button } from '../components/ui/button';

export default function Builder() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);

  const handleBuildStart = (id: string) => {
    setProjectId(id);
    setIsBuilding(true);
  };

  const handleBuildComplete = () => {
    setIsBuilding(false);
  };

  const handleReset = () => {
    setProjectId(null);
    setIsBuilding(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20">
      <div className="container mx-auto px-6 py-12 max-w-6xl">
        {/* Header */}
        <header className="mb-12 text-center">
          <div className="mb-4">
            <span className="text-6xl">🏗️</span>
          </div>
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            Autonomous CMS Builder
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            AI-powered multi-agent system that analyzes your frontend projects and automatically generates Kirby CMS configurations
          </p>
        </header>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          {!projectId ? (
            <ProjectInput onBuildStart={handleBuildStart} />
          ) : (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-semibold">Building CMS...</h2>
                <Button variant="outline" onClick={handleReset}>
                  New Project
                </Button>
              </div>
              <ProgressDashboard
                projectId={projectId}
                onComplete={handleBuildComplete}
              />
            </div>
          )}
        </div>

        {/* Footer Info */}
        {!projectId && (
          <div className="mt-16 pt-8 border-t text-center">
            <p className="text-sm text-muted-foreground">
              Powered by AI • Multi-Agent Architecture • Self-Validating
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
