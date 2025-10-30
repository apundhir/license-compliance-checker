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
import { FileWarning, XCircle, Loader2, AlertCircle } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

interface Violation {
  component: string;
  version: string;
  license: string;
  project: string;
  scanId: string;
  scanDate: string;
  policyName: string;
}

export default function ViolationsPage() {
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
          });
        }
      });
    });

    return allViolations;
  }, [scanDetails]);

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

  const isLoading = scansLoading || detailsLoading;

  return (
    <ContentLayout title="Violations">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              License Violations
            </h2>
            <p className="text-muted-foreground mt-2">
              Track all license compliance violations across your projects. Violations occur when components use licenses that are denied by your policy.
            </p>
          </div>
        </div>

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
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Component</TableHead>
                    <TableHead>Version</TableHead>
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
            )}
          </CardContent>
        </Card>
      </div>
    </ContentLayout>
  );
}
