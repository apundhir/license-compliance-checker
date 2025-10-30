"use client";

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
  Loader2,
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Package,
  FileText,
  Clock,
} from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";

interface ScanDetail {
  summary: {
    id: string;
    project: string;
    status: string;
    violations: number;
    warnings: number;
    generatedAt: string;
    durationSeconds: number;
    reportUrl: string;
  };
  report: {
    findings: Array<{
      component: {
        name: string;
        version?: string;
        type?: string;
      };
      resolved_license?: string;
      status?: string;
    }>;
    summary: {
      componentCount: number;
      violations: number;
      warnings: number;
      licenseDistribution: Array<{
        license: string;
        count: number;
      }>;
    };
  };
}

async function getScanDetail(id: string): Promise<ScanDetail> {
  const response = await api.get(`/scans/${id}`);
  return response.data;
}

function getStatusBadge(status: string) {
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
      return <Badge variant="outline">{status}</Badge>;
  }
}

export default function ScanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const scanId = params.id as string;

  const { data: scan, isLoading, error } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => getScanDetail(scanId),
    retry: 1,
  });

  if (isLoading) {
    return (
      <ContentLayout title="Scan Details">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </ContentLayout>
    );
  }

  if (error || !scan) {
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

  const { summary, report } = scan;

  return (
    <ContentLayout title="Scan Details">
      <div className="space-y-6">
        {/* Back Button */}
        <Button variant="outline" onClick={() => router.push("/scans")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Scans
        </Button>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-4">
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
              <div className="text-2xl font-bold">{report?.summary?.componentCount || 0}</div>
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
                {summary.durationSeconds < 60
                  ? `${summary.durationSeconds.toFixed(1)}s`
                  : `${(summary.durationSeconds / 60).toFixed(1)}m`}
              </div>
              <p className="text-xs text-muted-foreground">Scan time</p>
            </CardContent>
          </Card>
        </div>

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
                <p className="text-sm">
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
        {report?.summary?.licenseDistribution && report.summary.licenseDistribution.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>License Distribution</CardTitle>
              <CardDescription>
                Breakdown of licenses found in {report.summary.componentCount} components
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
                    const percentage = (
                      (item.count / report.summary.componentCount) *
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
        {report?.findings && report.findings.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Component Findings</CardTitle>
              <CardDescription>
                Detailed license information for each component (showing first 50)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Component</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>License</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Issues</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.findings.slice(0, 50).map((finding: any, index: number) => {
                    const resolverErrors = finding.component?.metadata?.resolver_errors || [];
                    const hasErrors = resolverErrors.length > 0;
                    const version = finding.component?.version;
                    const versionSource = finding.component?.metadata?.version_source;

                    return (
                      <TableRow key={index}>
                        <TableCell className="font-medium">
                          {finding.component?.name || "Unknown"}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {version || "N/A"}
                          {versionSource && version !== "*" && (
                            <span className="text-xs text-blue-500 ml-1" title={`Version ${versionSource}`}>
                              (assumed)
                            </span>
                          )}
                        </TableCell>
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
              {report.findings.length > 50 && (
                <p className="text-sm text-muted-foreground mt-4 text-center">
                  Showing 50 of {report.findings.length} components
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </ContentLayout>
  );
}
