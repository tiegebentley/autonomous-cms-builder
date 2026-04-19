import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';

interface AgentStatus {
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  duration?: number;
}

interface ProgressDashboardProps {
  projectId: string;
  onComplete: () => void;
}

const agents = [
  { id: 'analyzer', name: 'Analyzer Agent', icon: '🔍' },
  { id: 'critic', name: 'Critic Agent', icon: '✅' },
  { id: 'builder', name: 'Builder Agent', icon: '🏗️' },
  { id: 'tester', name: 'Tester Agent', icon: '🧪' },
  { id: 'applicator', name: 'Applicator Agent', icon: '💾' },
  { id: 'installer', name: 'Installer Agent', icon: '📦' },
  { id: 'integrator', name: 'Integrator Agent', icon: '🔗' },
];

export default function ProgressDashboard({ projectId, onComplete }: ProgressDashboardProps) {
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus>>({});
  const [logs, setLogs] = useState<string[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);
  const [cmsUrl, setCmsUrl] = useState<string | null>(null);
  const [panelUrl, setPanelUrl] = useState<string | null>(null);

  useEffect(() => {
    // Connect to SSE for real-time updates
    const eventSource = new EventSource(
      `http://localhost:8001/api/projects/${projectId}/stream`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.agent) {
        // Update agent status
        setAgentStatuses((prev) => ({
          ...prev,
          [data.agent]: {
            status: data.status,
            progress: data.progress,
          },
        }));

        // Add log entry
        const timestamp = new Date().toLocaleTimeString();
        const logMessage = `[${timestamp}] ${data.agent}: ${data.status} (${data.progress}%)`;
        setLogs((prev) => [...prev, logMessage]);
      }

      if (data.status === 'completed') {
        const urls = data.result?.urls;
        if (urls) {
          setCmsUrl(urls.cms);
          setPanelUrl(urls.panel);
        }
        setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ✅ Build completed!`]);
        if (urls?.cms) {
          setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] 🌐 CMS URL: ${urls.cms}`]);
          setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] 🔐 Admin Panel: ${urls.panel}`]);
        }
        setTimeout(() => {
          onComplete();
        }, 2000);
      }
    };

    eventSource.onerror = () => {
      console.error('SSE connection error');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [projectId, onComplete]);

  // Calculate overall progress
  useEffect(() => {
    const total = agents.reduce((sum, agent) => {
      return sum + (agentStatuses[agent.id]?.progress || 0);
    }, 0);
    setOverallProgress(Math.round(total / agents.length));
  }, [agentStatuses]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return '✅';
      case 'in_progress':
        return '⏳';
      case 'failed':
        return '❌';
      default:
        return '⏸️';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Complete';
      case 'in_progress':
        return 'In Progress';
      case 'failed':
        return 'Failed';
      default:
        return 'Waiting';
    }
  };

  return (
    <div className="space-y-6">
      {/* Overall Progress */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Overall Progress</CardTitle>
            <span className="text-2xl font-bold">{overallProgress}%</span>
          </div>
        </CardHeader>
        <CardContent>
          <Progress value={overallProgress} className="h-3" />
        </CardContent>
      </Card>

      {/* Agent Statuses */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {agents.map((agent) => {
            const status = agentStatuses[agent.id] || { status: 'pending', progress: 0 };
            return (
              <div key={agent.id} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{agent.icon}</span>
                    <span className="font-medium">{agent.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        status.status === 'completed'
                          ? 'default'
                          : status.status === 'in_progress'
                          ? 'secondary'
                          : 'outline'
                      }
                    >
                      {getStatusText(status.status)}
                    </Badge>
                    <span className="text-sm font-medium min-w-[3ch] text-right">
                      {status.progress}%
                    </span>
                  </div>
                </div>
                <Progress
                  value={status.progress}
                  className="h-2"
                />
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Success Card with URLs */}
      {cmsUrl && (
        <Card className="border-green-500 bg-green-50 dark:bg-green-950">
          <CardHeader>
            <CardTitle className="text-green-700 dark:text-green-400 flex items-center gap-2">
              🎉 CMS is Live!
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div>
                <label className="text-sm font-medium text-green-700 dark:text-green-400">Website URL:</label>
                <a
                  href={cmsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-blue-600 hover:underline font-mono text-sm mt-1"
                >
                  {cmsUrl}
                </a>
              </div>
              <div>
                <label className="text-sm font-medium text-green-700 dark:text-green-400">Admin Panel:</label>
                <a
                  href={panelUrl || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-blue-600 hover:underline font-mono text-sm mt-1"
                >
                  {panelUrl}
                </a>
              </div>
            </div>
            <div className="text-sm text-green-700 dark:text-green-400">
              Click the Admin Panel link to create your account and start managing content!
            </div>
          </CardContent>
        </Card>
      )}

      {/* Logs */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Logs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-muted/50 border rounded-md p-4 h-64 overflow-y-auto font-mono text-sm space-y-1">
            {logs.length === 0 ? (
              <div className="text-muted-foreground">Waiting for activity...</div>
            ) : (
              logs.map((log, index) => (
                <div key={index} className="text-xs">
                  {log}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
