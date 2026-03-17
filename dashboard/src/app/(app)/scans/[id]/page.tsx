// Copyright 2025 Ajay Pundhir
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

"use client";

import { useState, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { ContentLayout } from "@/components/admin-panel/content-layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Loader2,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Package,
  FileText,
  Clock,
  ShieldAlert,
  Download,
  GitBranch,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CompatibilityIssue {
  severity: string;
  issue_type: string;
  description: string;
  components: string[];
  licenses: string[];
  recommendation: string;
}

interface CompatibilityReport {
  project_license: string | null;
  context: string | null;
  issues: CompatibilityIssue[];
  compatible: boolean;
  summary: Record<string, number>;
}

interface ScanDetail {
  summary: {
    id: string;
    project: string;
    status: string;
    violations: number;
    warnings: number;
    generatedAt: string;
    durationSeconds?: number;
    reportUrl: string;
  };
  report?: {
    findings?: Array<{
      component: {
        name: string;
        version?: string;
        type?: string;
        metadata?: any;
      };
      resolved_license?: string;
      status?: string;
    }>;
    summary?: {
      componentCount?: number;
      component_count?: number;
      violations: number;
      warnings: number;
      licenseDistribution?: Array<{
        license: string;
        count: number;
      }>;
      context?: {
        vulnerabilities?: number;
        [key: string]: any;
      };
    };
    compatibility?: CompatibilityReport;
  };
  compatibility?: CompatibilityReport;
}

async function getScanDetail(id: string): Promise<ScanDetail> {
  const response = await api.get(`/scans/${id}`);
  return response.data;
}

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  critical: { bg: "bg-[#C0392B]/10", text: "text-[#C0392B]", border: "border-[#C0392B]/30" },
  high: { bg: "bg-[#B7770D]/10", text: "text-[#B7770D]", border: "border-[#B7770D]/30" },
  medium: { bg: "bg-[#3498DB]/10", text: "text-[#3498DB]", border: "border-[#3498DB]/30" },
  low: { bg: "bg-[#7F8C8D]/10", text: "text-[#7F8C8D]", border: "border-[#7F8C8D]/30" },
};

function getSeverityBadge(severity: string) {
  const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS.low;
  return (
    <Badge
      variant="outline"
      className={`${colors.bg} ${colors.text} ${colors.border} capitalize`}
    >
      {severity}
    </Badge>
  );
}

/** Convert snake_case issue_type to a readable label. */
function formatIssueType(issueType: string): string {
  const labels: Record<string, string> = {
    copyleft_contamination: "Copyleft Contamination",
    agpl_saas: "AGPL in SaaS",
    sspl_saas: "SSPL in SaaS",
    copyleft_version_conflict: "Copyleft Version Conflict",
    license_conflict: "License Conflict",
    weak_copyleft_boundary: "Weak Copyleft Boundary",
    unknown_license: "Unknown License",
  };
  return labels[issueType] || issueType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Status badge (unchanged)
// ---------------------------------------------------------------------------

function getStatusBadge(status: any) {
  if (typeof status !== "string") {
    return <Badge variant="outline">Unknown</Badge>;
  }
  switch (status?.toLowerCase()) {
    case "pass":
      return (
        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
          <CheckCircle2 className="mr-1 h-3 w-3" />
          Pass
        </Badge>
      );
    case "violation":
      return (
        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
          <XCircle className="mr-1 h-3 w-3" />
          Violation
        </Badge>
      );
    case "warning":
      return (
        <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
          <AlertTriangle className="mr-1 h-3 w-3" />
          Warning
        </Badge>
      );
    default:
      return <Badge variant="outline">{status || "Unknown"}</Badge>;
  }
}

// ---------------------------------------------------------------------------
// Compatibility banner component
// ---------------------------------------------------------------------------

function CompatibilityBanner({
  compatibility,
  onViewDetails,
}: {
  compatibility: CompatibilityReport;
  onViewDetails: () => void;
}) {
  const { summary, compatible } = compatibility;
  const criticalCount = summary.critical || 0;
  const highCount = summary.high || 0;
  const mediumCount = summary.medium || 0;
  const lowCount = summary.low || 0;
  const totalCount = criticalCount + highCount + mediumCount + lowCount;

  if (compatible && totalCount === 0) {
    return (
      <Alert className="border-green-200 bg-green-50">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <AlertTitle className="text-green-800">No Compatibility Issues</AlertTitle>
        <AlertDescription className="text-green-700">
          All dependencies are compatible with your project license.
        </AlertDescription>
      </Alert>
    );
  }

  // Determine banner color based on highest severity present
  const isCritical = criticalCount > 0;
  const bannerBorder = isCritical ? "border-[#C0392B]/40" : "border-[#B7770D]/40";
  const bannerBg = isCritical ? "bg-[#C0392B]/5" : "bg-[#B7770D]/5";
  const iconColor = isCritical ? "text-[#C0392B]" : "text-[#B7770D]";
  const titleColor = isCritical ? "text-[#C0392B]" : "text-[#B7770D]";

  const parts: string[] = [];
  if (criticalCount > 0) parts.push(`${criticalCount} critical`);
  if (highCount > 0) parts.push(`${highCount} high`);
  if (mediumCount > 0) parts.push(`${mediumCount} medium`);
  if (lowCount > 0) parts.push(`${lowCount} low`);

  return (
    <Alert className={`${bannerBorder} ${bannerBg}`}>
      <ShieldAlert className={`h-4 w-4 ${iconColor}`} />
      <AlertTitle className={titleColor}>License Compatibility Issues Detected</AlertTitle>
      <AlertDescription className="flex items-center justify-between">
        <span className="text-muted-foreground">
          {parts.join(", ")} {totalCount === 1 ? "issue" : "issues"} found
        </span>
        <Button variant="ghost" size="sm" onClick={onViewDetails} className={titleColor}>
          View details
          <ChevronDown className="ml-1 h-3 w-3" />
        </Button>
      </AlertDescription>
    </Alert>
  );
}

// ---------------------------------------------------------------------------
// Compatibility issues section component
// ---------------------------------------------------------------------------

function CompatibilityIssuesSection({
  compatibility,
  sectionRef,
}: {
  compatibility: CompatibilityReport;
  sectionRef: React.RefObject<HTMLDivElement | null>;
}) {
  const [isOpen, setIsOpen] = useState(true);

  const sortedIssues = useMemo(() => {
    return [...compatibility.issues].sort(
      (a, b) => (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99)
    );
  }, [compatibility.issues]);

  if (sortedIssues.length === 0) return null;

  // Group by severity
  const grouped = useMemo(() => {
    const groups: Record<string, CompatibilityIssue[]> = {};
    for (const issue of sortedIssues) {
      if (!groups[issue.severity]) groups[issue.severity] = [];
      groups[issue.severity].push(issue);
    }
    return groups;
  }, [sortedIssues]);

  const severityKeys = Object.keys(grouped).sort(
    (a, b) => (SEVERITY_ORDER[a] ?? 99) - (SEVERITY_ORDER[b] ?? 99)
  );

  return (
    <div ref={sectionRef}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <Card>
          <CardHeader>
            <CollapsibleTrigger asChild>
              <button className="flex w-full items-center justify-between text-left">
                <div className="space-y-1">
                  <CardTitle className="flex items-center gap-2">
                    <ShieldAlert className="h-5 w-5" />
                    License Compatibility Issues
                    <Badge variant="secondary" className="ml-2">
                      {sortedIssues.length}
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    Potential license conflicts and compatibility concerns
                    {compatibility.project_license && (
                      <> for project licensed under <span className="font-medium">{compatibility.project_license}</span></>
                    )}
                  </CardDescription>
                </div>
                {isOpen ? (
                  <ChevronDown className="h-5 w-5 text-muted-foreground shrink-0" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0" />
                )}
              </button>
            </CollapsibleTrigger>
          </CardHeader>
          <CollapsibleContent>
            <CardContent className="space-y-6">
              {severityKeys.map((severity) => (
                <div key={severity} className="space-y-3">
                  <div className="flex items-center gap-2">
                    {getSeverityBadge(severity)}
                    <span className="text-sm text-muted-foreground">
                      {grouped[severity].length} {grouped[severity].length === 1 ? "issue" : "issues"}
                    </span>
                  </div>
                  <div className="space-y-3 pl-2">
                    {grouped[severity].map((issue, idx) => {
                      const colors = SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.low;
                      return (
                        <Card key={`${severity}-${idx}`} className={`${colors.border} border`}>
                          <CardContent className="pt-4 pb-4 space-y-3">
                            {/* Header: severity + issue type */}
                            <div className="flex items-center gap-2 flex-wrap">
                              {getSeverityBadge(issue.severity)}
                              <Badge variant="outline" className="capitalize">
                                {formatIssueType(issue.issue_type)}
                              </Badge>
                            </div>

                            {/* Description */}
                            <p className="text-sm leading-relaxed">{issue.description}</p>

                            {/* Components and licenses */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                              <div>
                                <span className="font-medium text-muted-foreground">Affected components:</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {issue.components.map((comp) => (
                                    <Badge key={comp} variant="secondary" className="font-mono text-xs">
                                      {comp}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                              <div>
                                <span className="font-medium text-muted-foreground">Licenses involved:</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {issue.licenses.map((lic) => (
                                    <Badge key={lic} variant="outline" className="font-mono text-xs">
                                      {lic}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            </div>

                            {/* Recommendation */}
                            <div className="rounded-md bg-muted/50 p-3 text-sm">
                              <span className="font-medium">Recommendation: </span>
                              {issue.recommendation}
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </div>
              ))}
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function ScanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const scanId = params.id as string;
  const compatibilitySectionRef = useRef<HTMLDivElement>(null);

  const { data: scan, isLoading, error } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => getScanDetail(scanId),
    retry: 1,
  });

  const status =
    scan?.summary?.status && typeof scan.summary.status === "string"
      ? scan.summary.status.toLowerCase()
      : "unknown";
  const isRunning = (status === "running" || status === "queued") && !!scan;

  // Poll progress if scan is running
  const { data: progress } = useQuery({
    queryKey: ["scan-progress", scanId],
    queryFn: () => api.get(`/scans/${scanId}/progress`).then((res) => res.data),
    enabled: isRunning,
    refetchInterval: 1000,
  });

  // Depth filter state
  const [depthFilter, setDepthFilter] = useState<"all" | "direct" | "transitive">("all");

  // Resolve compatibility data (may come from report.compatibility or top-level)
  const compatibility: CompatibilityReport | undefined = useMemo(() => {
    if (!scan) return undefined;
    return scan.report?.compatibility ?? scan.compatibility ?? undefined;
  }, [scan]);

  // Build a set of component names that appear in compatibility issues
  const componentsWithCompatIssues: Set<string> = useMemo(() => {
    if (!compatibility?.issues) return new Set();
    const names = new Set<string>();
    for (const issue of compatibility.issues) {
      for (const comp of issue.components) {
        names.add(comp);
      }
    }
    return names;
  }, [compatibility]);

  // Compute dependency depth stats from findings
  const depthStats = useMemo(() => {
    const findings = scan?.report?.findings;
    if (!findings || !Array.isArray(findings)) return { direct: 0, transitive: 0 };
    let direct = 0;
    let transitive = 0;
    findings.forEach((f: any) => {
      if (!f?.component) return;
      const isDirect = f.component.metadata?.is_direct;
      if (isDirect === true) {
        direct++;
      } else if (isDirect === false) {
        transitive++;
      } else {
        // No depth info available — count as direct by default
        direct++;
      }
    });
    return { direct, transitive };
  }, [scan?.report?.findings]);

  // Filter findings by depth
  const filteredFindings = useMemo(() => {
    const findings = scan?.report?.findings;
    if (!findings || !Array.isArray(findings)) return [];
    if (depthFilter === "all") return findings;
    return findings.filter((f: any) => {
      if (!f?.component) return false;
      const isDirect = f.component.metadata?.is_direct;
      if (depthFilter === "direct") {
        // Include if explicitly direct, or if no metadata (backwards compat)
        return isDirect === true || isDirect === undefined || isDirect === null;
      }
      // transitive
      return isDirect === false;
    });
  }, [scan?.report?.findings, depthFilter]);

  // Check if any finding has depth metadata
  const hasDepthMetadata = useMemo(() => {
    const findings = scan?.report?.findings;
    if (!findings || !Array.isArray(findings)) return false;
    return findings.some((f: any) => f?.component?.metadata?.is_direct !== undefined);
  }, [scan?.report?.findings]);

  const scrollToCompatibility = () => {
    compatibilitySectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (isLoading) {
    return (
      <ContentLayout title="Scan Details">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </ContentLayout>
    );
  }

  if (error || !scan || !scan.summary) {
    return (
      <ContentLayout title="Scan Details">
        <div className="flex flex-col items-center justify-center py-12 space-y-3">
          <AlertCircle className="h-12 w-12 text-destructive" />
          <p className="text-sm text-muted-foreground">
            Failed to load scan details. The scan may not exist or there was an error.
          </p>
          <Button variant="outline" onClick={() => router.push("/scans")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Scans
          </Button>
        </div>
      </ContentLayout>
    );
  }

  if (isRunning) {
    return (
      <ContentLayout title="Scan In Progress">
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={() => router.push("/scans")}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Scans
            </Button>
          </div>

          <Card className="w-full max-w-2xl mx-auto mt-8">
            <CardHeader>
              <CardTitle>Scan in Progress</CardTitle>
              <CardDescription>
                Please wait while we analyze your repository...
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium capitalize text-primary">
                    {progress?.current_stage?.replace(/_/g, " ") || scan.summary.status}
                  </span>
                  <span className="text-muted-foreground">
                    {progress?.progress_percent || 0}%
                  </span>
                </div>
                <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-500 ease-in-out"
                    style={{ width: `${progress?.progress_percent || 0}%` }}
                  />
                </div>
              </div>

              <div className="space-y-3 text-sm border rounded-lg p-4 bg-muted/50">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span>{progress?.message || "Processing..."}</span>
                </div>

                {progress?.components_found !== undefined && progress.components_found > 0 && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Package className="h-4 w-4" />
                    <span>
                      {progress.components_resolved || 0} of {progress.components_found} components processed
                    </span>
                  </div>
                )}

                {progress?.elapsed_seconds !== undefined && (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>Elapsed: {progress.elapsed_seconds}s</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </ContentLayout>
    );
  }

  const { summary, report } = scan;

  return (
    <ContentLayout title="Scan Details">
      <div className="space-y-6">
        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => router.push("/scans")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Scans
          </Button>
          {summary.warnings > 0 && (
            <Button
              variant="default"
              onClick={() => router.push(`/scans/${scanId}/warnings`)}
              className="bg-yellow-600 hover:bg-yellow-700"
            >
              <AlertTriangle className="mr-2 h-4 w-4" />
              View {summary.warnings} Warning{summary.warnings !== 1 ? "s" : ""}
            </Button>
          )}
          <Button
            variant="outline"
            onClick={async () => {
              try {
                const response = await api.get(`/scans/${scanId}/attribution`, {
                  responseType: "blob",
                });
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement("a");
                link.href = url;
                link.setAttribute("download", `NOTICE-${scan.summary.project || scanId}.txt`);
                document.body.appendChild(link);
                link.click();
                link.parentNode?.removeChild(link);
                window.URL.revokeObjectURL(url);
              } catch (error) {
                console.error("Download failed:", error);
                alert("Failed to download NOTICE file. Please try again.");
              }
            }}
          >
            <Download className="mr-2 h-4 w-4" />
            Download NOTICE
          </Button>
        </div>

        {/* Compatibility Issues Banner */}
        {compatibility && (
          <CompatibilityBanner
            compatibility={compatibility}
            onViewDetails={scrollToCompatibility}
          />
        )}

        {/* Summary Cards */}
        <div className={`grid gap-4 ${hasDepthMetadata ? "md:grid-cols-5" : "md:grid-cols-4"}`}>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Status</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{getStatusBadge(summary.status)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Components</CardTitle>
              <Package className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{report?.summary?.componentCount || report?.summary?.component_count || 0}</div>
              <p className="text-xs text-muted-foreground">Total scanned</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Violations</CardTitle>
              <XCircle className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-destructive">
                {summary.violations || 0}
              </div>
              <p className="text-xs text-muted-foreground">License issues</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Duration</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(summary.durationSeconds || 0) < 60
                  ? `${(summary.durationSeconds || 0).toFixed(1)}s`
                  : `${((summary.durationSeconds || 0) / 60).toFixed(1)}m`}
              </div>
              <p className="text-xs text-muted-foreground">Scan time</p>
            </CardContent>
          </Card>

          {hasDepthMetadata && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Dependencies</CardTitle>
                <GitBranch className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-green-600">{depthStats.direct}</span>
                  <span className="text-xs text-muted-foreground">Direct</span>
                  <span className="text-muted-foreground">|</span>
                  <span className="text-lg font-bold text-muted-foreground">{depthStats.transitive}</span>
                  <span className="text-xs text-muted-foreground">Transitive</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">Dependency breakdown</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Compatibility Issues Section (collapsible, detailed) */}
        {compatibility && compatibility.issues.length > 0 && (
          <CompatibilityIssuesSection
            compatibility={compatibility}
            sectionRef={compatibilitySectionRef}
          />
        )}

        {/* Security Vulnerabilities */}
        {scan.summary.violations >= 0 && ( /* Always show if verified, logic can be refined */
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="space-y-1">
                <CardTitle>Security Vulnerabilities</CardTitle>
                <CardDescription>
                  Known vulnerabilities detected via OSV
                </CardDescription>
              </div>
              <ShieldAlert className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {report?.summary?.context?.vulnerabilities !== undefined ? (
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-destructive">{report.summary.context.vulnerabilities}</span>
                  <span className="text-sm text-muted-foreground">issues found</span>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Vulnerability scan was not enabled for this run.</p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Project Information */}
        <Card>
          <CardHeader>
            <CardTitle>Project Information</CardTitle>
            <CardDescription>Details about the scanned project</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Project Name</p>
                <p className="text-lg font-semibold">{summary.project}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Scan ID</p>
                <p className="text-sm font-mono">{summary.id}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Generated At</p>
                <p className="text-sm" suppressHydrationWarning>
                  {new Date(summary.generatedAt).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Warnings</p>
                <p className="text-sm text-yellow-600 font-semibold">
                  {summary.warnings || 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* License Distribution */}
        {report?.summary?.licenseDistribution && Array.isArray(report.summary.licenseDistribution) && report.summary.licenseDistribution.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>License Distribution</CardTitle>
              <CardDescription>
                Breakdown of licenses found in {report.summary?.componentCount || 0} components
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>License</TableHead>
                    <TableHead className="text-right">Count</TableHead>
                    <TableHead className="text-right">Percentage</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.summary.licenseDistribution.slice(0, 10).map((item: any, index: number) => {
                    const componentCount = report.summary?.componentCount || report.summary?.component_count || 1;
                    const percentage = (
                      (item.count / componentCount) *
                      100
                    ).toFixed(1);
                    return (
                      <TableRow key={index}>
                        <TableCell className="font-mono text-sm">
                          {item.license || "UNKNOWN"}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {item.count}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {percentage}%
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
              {report.summary.licenseDistribution.length > 10 && (
                <p className="text-sm text-muted-foreground mt-4 text-center">
                  Showing top 10 of {report.summary.licenseDistribution.length} licenses
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Component Findings */}
        {report?.findings && Array.isArray(report.findings) && report.findings.length > 0 && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Component Findings</CardTitle>
                  <CardDescription>
                    Detailed license information for each component
                    {depthFilter !== "all" && (
                      <span className="ml-1">
                        — showing {filteredFindings.length} of {report.findings.length}
                      </span>
                    )}
                    {depthFilter === "all" && filteredFindings.length > 50 && (
                      <span className="ml-1">(showing first 50)</span>
                    )}
                  </CardDescription>
                </div>
                {hasDepthMetadata && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground whitespace-nowrap">Filter:</span>
                    <Select value={depthFilter} onValueChange={(val) => setDepthFilter(val as "all" | "direct" | "transitive")}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Dependencies</SelectItem>
                        <SelectItem value="direct">Direct Only</SelectItem>
                        <SelectItem value="transitive">Transitive Only</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <TooltipProvider>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Component</TableHead>
                      <TableHead>Version</TableHead>
                      {hasDepthMetadata && <TableHead>Depth</TableHead>}
                      <TableHead>License</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Issues</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredFindings.slice(0, 50).map((finding: any, index: number) => {
                      if (!finding || !finding.component) return null;
                      const resolverErrors = finding.component?.metadata?.resolver_errors || [];
                      const hasErrors = resolverErrors.length > 0;
                      const version = finding.component?.version;
                      const versionSource = finding.component?.metadata?.version_source;
                      const isDirect = finding.component?.metadata?.is_direct;
                      const depthValue = finding.component?.metadata?.dependency_depth;
                      const parentPackages: string[] = finding.component?.metadata?.parent_packages || [];
                      const componentName = finding.component?.name || "Unknown";
                      const hasCompatIssue = componentsWithCompatIssues.has(componentName);

                      return (
                        <TableRow key={index}>
                          <TableCell className="font-medium">
                            <div className="flex items-center gap-1.5">
                              {componentName}
                              {hasCompatIssue && (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <button
                                      onClick={scrollToCompatibility}
                                      className="inline-flex items-center"
                                    >
                                      <ShieldAlert className="h-4 w-4 text-[#B7770D] shrink-0" />
                                    </button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>This component has compatibility issues</p>
                                  </TooltipContent>
                                </Tooltip>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {version || "N/A"}
                            {versionSource && version !== "*" && (
                              <span className="text-xs text-blue-500 ml-1" title={`Version ${versionSource}`}>
                                (assumed)
                              </span>
                            )}
                          </TableCell>
                          {hasDepthMetadata && (
                            <TableCell>
                              {isDirect === true ? (
                                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                  <Package className="mr-1 h-3 w-3" />
                                  Direct
                                </Badge>
                              ) : isDirect === false ? (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Badge variant="secondary" className="cursor-default">
                                      <GitBranch className="mr-1 h-3 w-3" />
                                      Transitive{depthValue !== undefined && depthValue > 0 ? ` (${depthValue})` : ""}
                                    </Badge>
                                  </TooltipTrigger>
                                  {parentPackages.length > 0 && (
                                    <TooltipContent side="top" className="max-w-[300px]">
                                      <p className="font-medium mb-1">Required by:</p>
                                      <p>{parentPackages.join(", ")}</p>
                                    </TooltipContent>
                                  )}
                                </Tooltip>
                              ) : (
                                <span className="text-xs text-muted-foreground">—</span>
                              )}
                            </TableCell>
                          )}
                          <TableCell className="font-mono text-sm">
                            {finding.resolved_license || "UNKNOWN"}
                          </TableCell>
                          <TableCell>
                            {finding.status && getStatusBadge(finding.status)}
                          </TableCell>
                          <TableCell>
                            {hasErrors && (
                              <div className="flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                                <details className="cursor-pointer">
                                  <summary className="text-xs text-yellow-600">
                                    {resolverErrors.length} error(s)
                                  </summary>
                                  <div className="mt-2 text-xs space-y-1">
                                    {resolverErrors.map((err: any, i: number) => (
                                      <div key={i} className="text-muted-foreground">
                                        <strong>{err.resolver}:</strong> {err.error}
                                      </div>
                                    ))}
                                  </div>
                                </details>
                              </div>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TooltipProvider>
              {filteredFindings.length > 50 && (
                <p className="text-sm text-muted-foreground mt-4 text-center">
                  Showing 50 of {filteredFindings.length} components
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </ContentLayout>
  );
}
