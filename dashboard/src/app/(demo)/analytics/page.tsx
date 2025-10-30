"use client";

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
import { Badge } from "@/components/ui/badge";
import { BarChart3, Loader2, TrendingUp, FileText, AlertTriangle, CheckCircle } from "lucide-react";
import { useMemo } from "react";

export default function AnalyticsPage() {
  // Fetch all scans
  const { data: scans, isLoading: scansLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: getScans,
  });

  // Fetch all scan details for analytics
  const { data: scanDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ["all-scans-for-analytics"],
    queryFn: async () => {
      if (!scans || scans.length === 0) return [];
      const details = await Promise.all(scans.map((scan) => getScan(scan.id)));
      return details;
    },
    enabled: !!scans && scans.length > 0,
  });

  // Calculate comprehensive analytics
  const analytics = useMemo(() => {
    if (!scanDetails || scanDetails.length === 0) {
      return {
        totalScans: 0,
        totalComponents: 0,
        totalViolations: 0,
        totalWarnings: 0,
        licensedComponents: 0,
        unlicensedComponents: 0,
        licenseDistribution: [],
        componentTypeDistribution: [],
        topProjects: [],
        recentActivity: [],
        complianceRate: 0,
      };
    }

    let totalComponents = 0;
    let totalViolations = 0;
    let totalWarnings = 0;
    let licensedComponents = 0;
    let unlicensedComponents = 0;

    const licenseCount: Record<string, number> = {};
    const componentTypeCount: Record<string, number> = {};
    const projectScans: Record<string, { scans: number; violations: number; warnings: number }> = {};

    scanDetails.forEach((scanDetail) => {
      const findings = scanDetail.report.findings || [];
      const projectName = scanDetail.summary.project;

      // Initialize project tracking
      if (!projectScans[projectName]) {
        projectScans[projectName] = { scans: 0, violations: 0, warnings: 0 };
      }
      projectScans[projectName].scans++;
      projectScans[projectName].violations += scanDetail.summary.violations || 0;
      projectScans[projectName].warnings += scanDetail.summary.warnings || 0;

      findings.forEach((finding: any) => {
        totalComponents++;

        // Count component types
        const type = finding.component.type || "unknown";
        componentTypeCount[type] = (componentTypeCount[type] || 0) + 1;

        // Count licenses
        const license = finding.resolved_license || "UNKNOWN";
        licenseCount[license] = (licenseCount[license] || 0) + 1;

        if (license !== "UNKNOWN") {
          licensedComponents++;
        } else {
          unlicensedComponents++;
        }

        // Count violations and warnings
        if (finding.status === "violation") {
          totalViolations++;
        } else if (finding.status === "warning") {
          totalWarnings++;
        }
      });
    });

    // Convert to sorted arrays
    const licenseDistribution = Object.entries(licenseCount)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10); // Top 10 licenses

    const componentTypeDistribution = Object.entries(componentTypeCount)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    const topProjects = Object.entries(projectScans)
      .map(([name, data]) => ({ name, ...data }))
      .sort((a, b) => b.scans - a.scans)
      .slice(0, 5); // Top 5 projects

    const recentActivity = scans
      .slice()
      .sort((a, b) => new Date(b.generatedAt).getTime() - new Date(a.generatedAt).getTime())
      .slice(0, 5); // 5 most recent scans

    const complianceRate = totalComponents > 0
      ? Math.round(((totalComponents - totalViolations) / totalComponents) * 100)
      : 100;

    return {
      totalScans: scanDetails.length,
      totalComponents,
      totalViolations,
      totalWarnings,
      licensedComponents,
      unlicensedComponents,
      licenseDistribution,
      componentTypeDistribution,
      topProjects,
      recentActivity,
      complianceRate,
    };
  }, [scanDetails, scans]);

  const isLoading = scansLoading || detailsLoading;

  return (
    <ContentLayout title="Analytics">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Analytics</h2>
            <p className="text-muted-foreground mt-2">
              Comprehensive insights into license compliance across all your projects
            </p>
          </div>
        </div>

        {/* Overview Statistics */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Scans</CardTitle>
              <BarChart3 className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">{analytics.totalScans}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Projects analyzed
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Components
              </CardTitle>
              <FileText className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">{analytics.totalComponents}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Dependencies tracked
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Compliance Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold text-green-600">
                    {analytics.complianceRate}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Components compliant
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Issues</CardTitle>
              <AlertTriangle className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold text-destructive">
                    {analytics.totalViolations}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {analytics.totalWarnings} warnings
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* License Distribution */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Top Licenses</CardTitle>
              <CardDescription>Most common licenses across all scans</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : analytics.licenseDistribution.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No license data available
                </p>
              ) : (
                <div className="space-y-3">
                  {analytics.licenseDistribution.map((item, index) => (
                    <div key={item.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-muted-foreground">
                          #{index + 1}
                        </span>
                        <Badge variant={item.name === "UNKNOWN" ? "secondary" : "outline"}>
                          {item.name}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary"
                            style={{
                              width: `${(item.count / analytics.totalComponents) * 100}%`,
                            }}
                          />
                        </div>
                        <span className="text-sm font-medium min-w-[3rem] text-right">
                          {item.count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Component Types</CardTitle>
              <CardDescription>Distribution by dependency type</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : analytics.componentTypeDistribution.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No component data available
                </p>
              ) : (
                <div className="space-y-3">
                  {analytics.componentTypeDistribution.map((item, index) => (
                    <div key={item.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-muted-foreground">
                          #{index + 1}
                        </span>
                        <Badge variant="outline" className="capitalize">
                          {item.name}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary"
                            style={{
                              width: `${(item.count / analytics.totalComponents) * 100}%`,
                            }}
                          />
                        </div>
                        <span className="text-sm font-medium min-w-[3rem] text-right">
                          {item.count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Project and License Status */}
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Top Projects</CardTitle>
              <CardDescription>Most frequently scanned projects</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : analytics.topProjects.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No project data available
                </p>
              ) : (
                <div className="space-y-4">
                  {analytics.topProjects.map((project) => (
                    <div key={project.name} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{project.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {project.scans} {project.scans === 1 ? "scan" : "scans"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="destructive" className="text-xs">
                          {project.violations} violations
                        </Badge>
                        <Badge variant="secondary" className="text-xs">
                          {project.warnings} warnings
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>License Status</CardTitle>
              <CardDescription>Coverage and identification rate</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="space-y-6">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <span className="text-sm font-medium">Licensed Components</span>
                      </div>
                      <span className="text-sm font-bold">
                        {analytics.licensedComponents}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-600"
                        style={{
                          width: `${analytics.totalComponents > 0 ? (analytics.licensedComponents / analytics.totalComponents) * 100 : 0}%`,
                        }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {analytics.totalComponents > 0
                        ? Math.round((analytics.licensedComponents / analytics.totalComponents) * 100)
                        : 0}% of total components
                    </p>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-yellow-600" />
                        <span className="text-sm font-medium">Unlicensed Components</span>
                      </div>
                      <span className="text-sm font-bold">
                        {analytics.unlicensedComponents}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-yellow-600"
                        style={{
                          width: `${analytics.totalComponents > 0 ? (analytics.unlicensedComponents / analytics.totalComponents) * 100 : 0}%`,
                        }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {analytics.totalComponents > 0
                        ? Math.round((analytics.unlicensedComponents / analytics.totalComponents) * 100)
                        : 0}% of total components
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ContentLayout>
  );
}
