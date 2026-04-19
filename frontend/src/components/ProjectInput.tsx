import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Checkbox } from './ui/checkbox';
import { Alert, AlertDescription } from './ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

interface DiscoveredProject {
  name: string;
  path: string;
  type: string;
  has_package_json: boolean;
  has_src: boolean;
}

interface ProjectInputProps {
  onBuildStart: (projectId: string) => void;
}

export default function ProjectInput({ onBuildStart }: ProjectInputProps) {
  const [projectPath, setProjectPath] = useState('');
  const [projectName, setProjectName] = useState('');
  const [autoApply, setAutoApply] = useState(true);
  const [enableValidation, setEnableValidation] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [discoveredProjects, setDiscoveredProjects] = useState<DiscoveredProject[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [useDropdown, setUseDropdown] = useState(true);

  // Fetch discovered projects on mount
  useEffect(() => {
    const fetchProjects = async () => {
      setLoadingProjects(true);
      try {
        const response = await fetch('http://localhost:8001/api/projects/scan?base_path=/root');
        if (response.ok) {
          const data = await response.json();
          setDiscoveredProjects(data.projects || []);
        }
      } catch (err) {
        console.error('Failed to fetch projects:', err);
      } finally {
        setLoadingProjects(false);
      }
    };

    fetchProjects();
  }, []);

  const handleProjectSelect = (value: string) => {
    const selected = discoveredProjects.find(p => p.path === value);
    if (selected) {
      setProjectPath(selected.path);
      setProjectName(selected.name);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8001/api/projects/build', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          path: projectPath,
          name: projectName,
          auto_apply: autoApply,
          enable_validation: enableValidation,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start build process');
      }

      const data = await response.json();
      onBuildStart(data.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create CMS Project</CardTitle>
        <CardDescription>
          Select a frontend project to analyze and generate a Kirby CMS for
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Toggle between dropdown and manual input */}
          <div className="flex items-center space-x-2 text-sm">
            <Button
              type="button"
              variant={useDropdown ? "default" : "outline"}
              size="sm"
              onClick={() => setUseDropdown(true)}
            >
              📁 Browse Projects
            </Button>
            <Button
              type="button"
              variant={!useDropdown ? "default" : "outline"}
              size="sm"
              onClick={() => setUseDropdown(false)}
            >
              ✏️ Manual Entry
            </Button>
          </div>

          {/* Project Selection */}
          {useDropdown ? (
            <div className="space-y-2">
              <Label htmlFor="project-select">Select Project</Label>
              {loadingProjects ? (
                <div className="text-sm text-muted-foreground">🔍 Scanning projects...</div>
              ) : discoveredProjects.length > 0 ? (
                <Select onValueChange={handleProjectSelect} value={projectPath}>
                  <SelectTrigger id="project-select">
                    <SelectValue placeholder="Choose a project from /root" />
                  </SelectTrigger>
                  <SelectContent>
                    {discoveredProjects.map((project) => (
                      <SelectItem key={project.path} value={project.path}>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{project.name}</span>
                          <span className="text-xs text-muted-foreground">({project.type})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Alert>
                  <AlertDescription>
                    No frontend projects found in /root. Switch to manual entry to specify a custom path.
                  </AlertDescription>
                </Alert>
              )}
              {projectPath && (
                <p className="text-xs text-muted-foreground">
                  Selected: {projectPath}
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="path">Project Path</Label>
              <Input
                id="path"
                type="text"
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                placeholder="Enter full path (e.g., /root/small-group-soccer-training)"
                required
              />
              <p className="text-xs text-muted-foreground">
                Enter the absolute path to your frontend project directory
              </p>
            </div>
          )}

          {/* Project Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Project Name</Label>
            <Input
              id="name"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Give your project a friendly name"
              required
            />
          </div>

          {/* Options */}
          <div className="space-y-3">
            <Label>Options</Label>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="auto-apply"
                checked={autoApply}
                onCheckedChange={setAutoApply}
              />
              <label
                htmlFor="auto-apply"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Auto-apply changes
              </label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="validation"
                checked={enableValidation}
                onCheckedChange={setEnableValidation}
              />
              <label
                htmlFor="validation"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Enable self-validation
              </label>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Submit Button */}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? '⏳ Starting...' : '🚀 Build CMS'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
