import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';

interface AgentStatus {
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  progress: number;
  duration?: number;
}

interface SeoFinding {
  file: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  issue: string;
  autofix: string | null;
}

interface SeoFix {
  file: string;
  fix: string;
  detail: string;
}

interface SeoReport {
  audit_status: string;
  files_scanned: number;
  score: number;
  findings: SeoFinding[];
  auto_fixes_applied: SeoFix[];
  report_path: string | null;
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
  { id: 'seo', name: 'SEO Auditor', icon: '📊' },
];

export default function ProgressDashboard({ projectId, onComplete }: ProgressDashboardProps) {
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus>>({});
  const [logs, setLogs] = useState<string[]>([]);
  const [overallProgress, setOverallProgress] = useState(0);
  const [cmsUrl, setCmsUrl] = useState<string | null>(null);
  const [panelUrl, setPanelUrl] = useState<string | null>(null);
  const [seoReport, setSeoReport] = useState<SeoReport | null>(null);

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

      if (!data.agent && data.status === 'completed') {
        const urls = data.result?.urls;
        if (urls) {
          setCmsUrl(urls.cms);
          setPanelUrl(urls.panel);
        }
        const seo = data.result?.seo;
        if (seo && seo.audit_status === 'completed') {
          setSeoReport(seo as SeoReport);
        }
        setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ✅ Build completed!`]);
        if (urls?.cms) {
          setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] 🌐 CMS URL: ${urls.cms}`]);
          setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] 🔐 Admin Panel: ${urls.panel}`]);
        }
        eventSource.close();
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
      case 'skipped':
        return 'Skipped';
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

      {/* SEO Report */}
      {seoReport && <SeoReportCard report={seoReport} />}

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

function SeoReportCard({ report }: { report: SeoReport }) {
  const [showFixes, setShowFixes] = useState(true);
  const [showFindings, setShowFindings] = useState(true);

  const score = report.score;
  const scoreColor =
    score >= 90 ? 'text-green-600 dark:text-green-400'
    : score >= 70 ? 'text-yellow-600 dark:text-yellow-400'
    : 'text-red-600 dark:text-red-400';
  const scoreBg =
    score >= 90 ? 'border-green-500 bg-green-50 dark:bg-green-950'
    : score >= 70 ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950'
    : 'border-red-500 bg-red-50 dark:bg-red-950';

  // Group findings by severity, preserving insertion order: critical, high, medium, low
  const sevOrder: Array<SeoFinding['severity']> = ['critical', 'high', 'medium', 'low'];
  const grouped: Record<string, SeoFinding[]> = {};
  for (const sev of sevOrder) grouped[sev] = [];
  for (const f of report.findings) grouped[f.severity]?.push(f);

  const sevColor = (sev: SeoFinding['severity']) =>
    sev === 'critical' ? 'destructive'
    : sev === 'high' ? 'destructive'
    : sev === 'medium' ? 'secondary'
    : 'outline';

  return (
    <Card className={scoreBg}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            📊 SEO Audit Report
          </CardTitle>
          <div className="text-right">
            <div className={`text-3xl font-bold ${scoreColor}`}>{score}/100</div>
            <div className="text-xs text-muted-foreground">{report.files_scanned} files scanned</div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2 text-sm">
          <Badge variant="default">{report.findings.length} findings</Badge>
          <Badge variant="default">{report.auto_fixes_applied.length} auto-fixed</Badge>
          {sevOrder.map(sev =>
            grouped[sev].length > 0 ? (
              <Badge key={sev} variant={sevColor(sev)}>
                {grouped[sev].length} {sev}
              </Badge>
            ) : null
          )}
        </div>

        {report.report_path && (
          <div className="text-xs text-muted-foreground">
            Full report: <code className="font-mono">{report.report_path}</code>
          </div>
        )}

        {/* Auto-fixes */}
        {report.auto_fixes_applied.length > 0 && (
          <div>
            <button
              onClick={() => setShowFixes(!showFixes)}
              className="flex items-center gap-2 font-semibold text-sm hover:opacity-70"
            >
              {showFixes ? '▼' : '▶'} Auto-fixes Applied ({report.auto_fixes_applied.length})
            </button>
            {showFixes && (
              <div className="mt-2 space-y-1 max-h-48 overflow-y-auto bg-background/50 rounded-md border p-2">
                {report.auto_fixes_applied.map((fix, i) => (
                  <div key={i} className="text-xs font-mono">
                    <span className="text-muted-foreground">{fix.file}</span>
                    {' — '}
                    <span className="font-semibold">{fix.fix}</span>
                    {fix.detail && <span className="text-muted-foreground">: {fix.detail}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Findings */}
        {report.findings.length > 0 && (
          <div>
            <button
              onClick={() => setShowFindings(!showFindings)}
              className="flex items-center gap-2 font-semibold text-sm hover:opacity-70"
            >
              {showFindings ? '▼' : '▶'} Findings ({report.findings.length})
            </button>
            {showFindings && (
              <div className="mt-2 space-y-3 max-h-96 overflow-y-auto bg-background/50 rounded-md border p-2">
                {sevOrder.map(sev => {
                  const items = grouped[sev];
                  if (items.length === 0) return null;
                  return (
                    <div key={sev}>
                      <div className="text-xs font-semibold uppercase tracking-wide mb-1">
                        {sev} ({items.length})
                      </div>
                      <div className="space-y-1">
                        {items.map((f, i) => (
                          <div key={i} className="text-xs font-mono">
                            <span className="text-muted-foreground">{f.file}</span>
                            {' '}
                            <span className="text-muted-foreground">[{f.category}]</span>
                            {' '}
                            {f.issue}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
