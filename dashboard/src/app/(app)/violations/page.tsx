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

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getScans, getScan } from "@/lib/api";
import { ContentLayout } from "@/components/admin-panel/content-layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { FileWarning, XCircle, Loader2, AlertCircle, Package, GitBranch, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Violation {
  component: string;
  version: string;
  license: string;
  project: string;
  scanId: string;
  scanDate: string;
  policyName: string;
  isDirect?: boolean;
  dependencyDepth?: number;
  parentPackages?: string[];
}

interface CompatibilityIssue {
  severity: string;
  issue_type: string;
  description: string;
  components: string[];
  licenses: string[];
  recommendation: string;
}

interface CompatIssueWithContext extends CompatibilityIssue {
  project: string;
  scanId: string;
  scanDate: string;
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
// Main page
// ---------------------------------------------------------------------------

export default function ViolationsPage() {
  const [activeTab, setActiveTab] = useState<"violations" | "compatibility">("violations");

  // Fetch all scans
  const { data: scans, isLoading: scansLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: getScans,
  });

  // Fetch details for scans with violations
  const scansWithViolations = useMemo(() => {
    return scans?.filter((scan) => scan.violations && scan.violations > 0) || [];
  }, [scans]);

  // Fetch scan details for scans with violations
  const { data: scanDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ["scan-violations", scansWithViolations.map((s) => s.id)],
    queryFn: async () => {
      const details = await Promise.all(
        scansWithViolations.map((scan) => getScan(scan.id))
      );
      return details;
    },
    enabled: scansWithViolations.length > 0,
  });

  // Fetch all scan details (for compatibility data from any scan, not just those with violations)
  const allScanIds = useMemo(() => scans?.map((s) => s.id) || [], [scans]);
  const { data: allScanDetails, isLoading: allDetailsLoading } = useQuery({
    queryKey: ["scan-all-details", allScanIds],
    queryFn: async () => {
      const details = await Promise.all(
        (scans || []).map((scan) => getScan(scan.id))
      );
      return details;
    },
    enabled: (scans?.length || 0) > 0,
  });

  // Extract all violations from scan details
  const violations: Violation[] = useMemo(() => {
    if (!scanDetails) return [];

    const allViolations: Violation[] = [];

    scanDetails.forEach((scanDetail) => {
      const findings = scanDetail.report.findings || [];
      const policyName = scanDetail.report.policyEvaluation?.policy_name || "Unknown";

      findings.forEach((finding: any) => {
        if (finding.status === "violation") {
          allViolations.push({
            component: finding.component.name,
            version: finding.component.version || "unknown",
            license: finding.resolved_license || "UNKNOWN",
            project: scanDetail.summary.project,
            scanId: scanDetail.summary.id,
            scanDate: scanDetail.summary.generatedAt,
            policyName: policyName,
            isDirect: finding.component.metadata?.is_direct,
            dependencyDepth: finding.component.metadata?.dependency_depth,
            parentPackages: finding.component.metadata?.parent_packages,
          });
        }
      });
    });

    return allViolations;
  }, [scanDetails]);

  // Extract compatibility issues from all scan details
  const compatIssues: CompatIssueWithContext[] = useMemo(() => {
    if (!allScanDetails) return [];

    const issues: CompatIssueWithContext[] = [];

    allScanDetails.forEach((scanDetail: any) => {
      const compatibility =
        scanDetail.report?.compatibility ?? scanDetail.compatibility;
      if (!compatibility?.issues || !Array.isArray(compatibility.issues)) return;

      compatibility.issues.forEach((issue: CompatibilityIssue) => {
        issues.push({
          ...issue,
          project: scanDetail.summary.project,
          scanId: scanDetail.summary.id,
          scanDate: scanDetail.summary.generatedAt,
        });
      });
    });

    // Sort by severity
    issues.sort(
      (a, b) => (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99)
    );

    return issues;
  }, [allScanDetails]);

  // Calculate statistics
  const stats = useMemo(() => {
    const totalViolations = violations.length;
    const affectedProjects = new Set(violations.map((v) => v.project)).size;
    const deniedLicenses = new Set(violations.map((v) => v.license)).size;

    return {
      totalViolations,
      affectedProjects,
      deniedLicenses,
    };
  }, [violations]);

  // Compatibility stats
  const compatStats = useMemo(() => {
    const total = compatIssues.length;
    const critical = compatIssues.filter((i) => i.severity === "critical").length;
    const high = compatIssues.filter((i) => i.severity === "high").length;
    const projectsAffected = new Set(compatIssues.map((i) => i.project)).size;
    return { total, critical, high, projectsAffected };
  }, [compatIssues]);

  // Check if any violation has depth metadata
  const hasDepthMetadata = useMemo(() => {
    return violations.some((v) => v.isDirect !== undefined);
  }, [violations]);

  const hasCompatData = compatIssues.length > 0;
  const isLoading = scansLoading || detailsLoading;
  const isCompatLoading = scansLoading || allDetailsLoading;

  return (
    <ContentLayout title="Violations">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              License Violations
            </h2>
            <p className="text-muted-foreground mt-2">
              Track all license compliance violations and compatibility issues across your projects.
            </p>
          </div>
        </div>

        {/* Tab switcher — only show if compatibility data exists */}
        {(hasCompatData || isCompatLoading) && (
          <div className="flex border-b">
            <button
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "violations"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setActiveTab("violations")}
            >
              <XCircle className="inline-block mr-1.5 h-4 w-4" />
              Policy Violations
              {!isLoading && violations.length > 0 && (
                <Badge variant="destructive" className="ml-2 text-xs">
                  {violations.length}
                </Badge>
              )}
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "compatibility"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setActiveTab("compatibility")}
            >
              <ShieldAlert className="inline-block mr-1.5 h-4 w-4" />
              Compatibility Issues
              {!isCompatLoading && compatIssues.length > 0 && (
                <Badge
                  variant="outline"
                  className={`ml-2 text-xs ${
                    compatStats.critical > 0
                      ? "bg-[#C0392B]/10 text-[#C0392B] border-[#C0392B]/30"
                      : compatStats.high > 0
                        ? "bg-[#B7770D]/10 text-[#B7770D] border-[#B7770D]/30"
                        : ""
                  }`}
                >
                  {compatIssues.length}
                </Badge>
              )}
            </button>
          </div>
        )}

        {/* ============================================================= */}
        {/* Policy Violations tab                                         */}
        {/* ============================================================= */}
        {activeTab === "violations" && (
          <>
            {/* Statistics Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Total Violations
                  </CardTitle>
                  <XCircle className="h-4 w-4 text-destructive" />
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <div className="flex items-center space-x-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Loading...</span>
                    </div>
                  ) : (
                    <>
                      <div className="text-2xl font-bold text-destructive">
                        {stats.totalViolations}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Components with denied licenses
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Affected Projects
                  </CardTitle>
                  <AlertCircle className="h-4 w-4 text-destructive" />
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <div className="flex items-center space-x-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Loading...</span>
                    </div>
                  ) : (
                    <>
                      <div className="text-2xl font-bold">
                        {stats.affectedProjects}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Projects with violations
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Denied Licenses
                  </CardTitle>
                  <FileWarning className="h-4 w-4 text-destructive" />
                </CardHeader>
                <CardContent>
                  {isLoading ? (
                    <div className="flex items-center space-x-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Loading...</span>
                    </div>
                  ) : (
                    <>
                      <div className="text-2xl font-bold">
                        {stats.deniedLicenses}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Unique denied license types
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Violations Table */}
            <Card>
              <CardHeader>
                <CardTitle>All Violations</CardTitle>
                <CardDescription>
                  Complete list of components using licenses that are denied by your policies
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : violations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 space-y-3">
                    <FileWarning className="h-12 w-12 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      No violations found. Your projects are compliant!
                    </p>
                  </div>
                ) : (
                  <TooltipProvider>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Component</TableHead>
                          <TableHead>Version</TableHead>
                          {hasDepthMetadata && <TableHead>Depth</TableHead>}
                          <TableHead>License</TableHead>
                          <TableHead>Project</TableHead>
                          <TableHead>Policy</TableHead>
                          <TableHead>Scan Date</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {violations.map((violation, index) => (
                          <TableRow key={`${violation.scanId}-${violation.component}-${index}`}>
                            <TableCell className="font-medium">
                              {violation.component}
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {violation.version}
                            </TableCell>
                            {hasDepthMetadata && (
                              <TableCell>
                                {violation.isDirect === true ? (
                                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                    <Package className="mr-1 h-3 w-3" />
                                    Direct
                                  </Badge>
                                ) : violation.isDirect === false ? (
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Badge variant="secondary" className="cursor-default">
                                        <GitBranch className="mr-1 h-3 w-3" />
                                        Transitive{violation.dependencyDepth !== undefined && violation.dependencyDepth > 0 ? ` (${violation.dependencyDepth})` : ""}
                                      </Badge>
                                    </TooltipTrigger>
                                    {violation.parentPackages && violation.parentPackages.length > 0 && (
                                      <TooltipContent side="top" className="max-w-[300px]">
                                        <p className="font-medium mb-1">Required by:</p>
                                        <p>{violation.parentPackages.join(", ")}</p>
                                      </TooltipContent>
                                    )}
                                  </Tooltip>
                                ) : (
                                  <span className="text-xs text-muted-foreground">—</span>
                                )}
                              </TableCell>
                            )}
                            <TableCell>
                              <Badge variant="destructive">{violation.license}</Badge>
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {violation.project}
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {violation.policyName}
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {new Date(violation.scanDate).toLocaleDateString()}
                            </TableCell>
                            <TableCell className="text-right">
                              <Button variant="ghost" size="sm" asChild>
                                <Link href={`/scans/${violation.scanId}`}>
                                  View Scan
                                </Link>
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TooltipProvider>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {/* ============================================================= */}
        {/* Compatibility Issues tab                                      */}
        {/* ============================================================= */}
        {activeTab === "compatibility" && (
          <>
            {/* Compatibility Statistics */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Total Issues
                  </CardTitle>
                  <ShieldAlert className="h-4 w-4 text-[#B7770D]" />
                </CardHeader>
                <CardContent>
                  {isCompatLoading ? (
                    <div className="flex items-center space-x-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Loading...</span>
                    </div>
                  ) : (
                    <>
                      <div className="text-2xl font-bold">
                        {compatStats.total}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {compatStats.critical > 0 && (
                          <span className="text-[#C0392B] font-medium">{compatStats.critical} critical</span>
                        )}
                        {compatStats.critical > 0 && compatStats.high > 0 && ", "}
                        {compatStats.high > 0 && (
                          <span className="text-[#B7770D] font-medium">{compatStats.high} high</span>
                        )}
                        {(compatStats.critical === 0 && compatStats.high === 0) && "Compatibility issues across scans"}
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Affected Projects
                  </CardTitle>
                  <AlertCircle className="h-4 w-4 text-[#B7770D]" />
                </CardHeader>
                <CardContent>
                  {isCompatLoading ? (
                    <div className="flex items-center space-x-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Loading...</span>
                    </div>
                  ) : (
                    <>
                      <div className="text-2xl font-bold">
                        {compatStats.projectsAffected}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Projects with compatibility issues
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Critical + High
                  </CardTitle>
                  <XCircle className="h-4 w-4 text-[#C0392B]" />
                </CardHeader>
                <CardContent>
                  {isCompatLoading ? (
                    <div className="flex items-center space-x-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Loading...</span>
                    </div>
                  ) : (
                    <>
                      <div className="text-2xl font-bold text-[#C0392B]">
                        {compatStats.critical + compatStats.high}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Issues requiring immediate attention
                      </p>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Compatibility Issues List */}
            <Card>
              <CardHeader>
                <CardTitle>All Compatibility Issues</CardTitle>
                <CardDescription>
                  License compatibility issues detected across all scans, sorted by severity
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isCompatLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : compatIssues.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 space-y-3">
                    <ShieldAlert className="h-12 w-12 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      No compatibility issues found. All licenses are compatible.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {compatIssues.map((issue, index) => {
                      const colors = SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.low;
                      return (
                        <Card key={`compat-${index}`} className={`${colors.border} border`}>
                          <CardContent className="pt-4 pb-4 space-y-3">
                            {/* Header row */}
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <div className="flex items-center gap-2 flex-wrap">
                                {getSeverityBadge(issue.severity)}
                                <Badge variant="outline" className="capitalize">
                                  {formatIssueType(issue.issue_type)}
                                </Badge>
                                <span className="text-sm text-muted-foreground">
                                  in <span className="font-medium text-foreground">{issue.project}</span>
                                </span>
                              </div>
                              <Button variant="ghost" size="sm" asChild>
                                <Link href={`/scans/${issue.scanId}`}>
                                  View Scan
                                </Link>
                              </Button>
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
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </ContentLayout>
  );
}
