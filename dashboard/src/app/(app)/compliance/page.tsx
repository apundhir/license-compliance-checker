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
import { useQuery, useMutation } from "@tanstack/react-query";
import { getScans, assessRegulatory, downloadCompliancePack } from "@/lib/api";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Shield,
  Loader2,
  AlertCircle,
  Download,
  CheckCircle,
  XCircle,
  AlertTriangle,
  MinusCircle,
  Bot,
} from "lucide-react";

interface Obligation {
  article: string;
  title: string;
  description: string;
  status: string;
  evidence: string[];
  gaps: string[];
}

interface Assessment {
  framework: string;
  component_name: string;
  component_type: string;
  risk_classification: string | null;
  obligations: Obligation[];
  overall_status: string;
  recommendations: string[];
  assessed_at: string;
}

interface RegulatoryReport {
  title: string;
  framework: string;
  generated_at: string;
  assessments: Assessment[];
  summary: {
    total_ai_components: number;
    compliant: number;
    partial: number;
    non_compliant: number;
    compliance_percentage: number;
  };
}

function getStatusColor(status: string): string {
  switch (status) {
    case "compliant":
    case "met":
      return "text-green-600";
    case "partial":
      return "text-amber-500";
    case "non_compliant":
    case "not_met":
      return "text-red-600";
    case "not_applicable":
      return "text-muted-foreground";
    default:
      return "text-muted-foreground";
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case "compliant":
    case "met":
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    case "partial":
      return <AlertTriangle className="h-4 w-4 text-amber-500" />;
    case "non_compliant":
    case "not_met":
      return <XCircle className="h-4 w-4 text-red-600" />;
    case "not_applicable":
      return <MinusCircle className="h-4 w-4 text-muted-foreground" />;
    default:
      return <MinusCircle className="h-4 w-4 text-muted-foreground" />;
  }
}

function getStatusBadgeVariant(
  status: string
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "compliant":
    case "met":
      return "default";
    case "partial":
      return "secondary";
    case "non_compliant":
    case "not_met":
      return "destructive";
    default:
      return "outline";
  }
}

function getScoreColor(percentage: number): string {
  if (percentage >= 80) return "text-green-600";
  if (percentage >= 50) return "text-amber-500";
  return "text-red-600";
}

function getScoreBgColor(percentage: number): string {
  if (percentage >= 80) return "bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-900";
  if (percentage >= 50) return "bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-900";
  return "bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-900";
}

function formatRiskClassification(risk: string | null): string {
  if (!risk) return "Unknown";
  return risk
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatStatus(status: string): string {
  return status
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function CompliancePage() {
  const [selectedScanId, setSelectedScanId] = useState<string>("");
  const [report, setReport] = useState<RegulatoryReport | null>(null);

  // Fetch available scans
  const { data: scans, isLoading: scansLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: getScans,
  });

  // Run assessment mutation
  const assessMutation = useMutation({
    mutationFn: (scanId: string) => assessRegulatory(scanId),
    onSuccess: (data) => {
      setReport(data as RegulatoryReport);
    },
  });

  // Download compliance pack mutation
  const downloadMutation = useMutation({
    mutationFn: async (scanId: string) => {
      const blob = await downloadCompliancePack(scanId);
      // Trigger browser download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `eu-ai-act-compliance-pack-${scanId.slice(0, 8)}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });

  const handleRunAssessment = () => {
    if (selectedScanId) {
      setReport(null);
      assessMutation.mutate(selectedScanId);
    }
  };

  const handleExportPack = () => {
    if (selectedScanId) {
      downloadMutation.mutate(selectedScanId);
    }
  };

  const completedScans = scans?.filter((s) => s.status === "completed") ?? [];

  return (
    <ContentLayout title="EU AI Act Compliance">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              EU AI Act Compliance
            </h2>
            <p className="text-muted-foreground mt-2">
              Assess your AI models against EU AI Act Article 53 GPAI provider
              obligations and export compliance documentation.
            </p>
          </div>
        </div>

        {/* Scan Selection & Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Run Assessment
            </CardTitle>
            <CardDescription>
              Select a completed scan to assess its AI models against EU AI Act
              requirements
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-end">
              <div className="w-full sm:w-96">
                <label className="text-sm font-medium mb-2 block">
                  Select Scan
                </label>
                {scansLoading ? (
                  <div className="flex items-center gap-2 h-9 px-3 border rounded-md">
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      Loading scans...
                    </span>
                  </div>
                ) : completedScans.length === 0 ? (
                  <div className="flex items-center gap-2 h-9 px-3 border rounded-md">
                    <AlertCircle className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      No completed scans available
                    </span>
                  </div>
                ) : (
                  <Select
                    value={selectedScanId}
                    onValueChange={setSelectedScanId}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a scan..." />
                    </SelectTrigger>
                    <SelectContent>
                      {completedScans.map((scan) => (
                        <SelectItem key={scan.id} value={scan.id}>
                          {scan.project} ({scan.id.slice(0, 8)}...) -{" "}
                          {new Date(scan.generatedAt).toLocaleDateString()}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={handleRunAssessment}
                  disabled={
                    !selectedScanId ||
                    assessMutation.isPending
                  }
                >
                  {assessMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Assessing...
                    </>
                  ) : (
                    <>
                      <Shield className="mr-2 h-4 w-4" />
                      Run Assessment
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleExportPack}
                  disabled={
                    !selectedScanId ||
                    downloadMutation.isPending
                  }
                >
                  {downloadMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Exporting...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Export Compliance Pack
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Error display */}
            {assessMutation.isError && (
              <div className="mt-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm flex items-center gap-2">
                <XCircle className="h-4 w-4 flex-shrink-0" />
                <span>
                  Assessment failed:{" "}
                  {(assessMutation.error as any)?.response?.data?.detail ||
                    (assessMutation.error as Error)?.message ||
                    "Unknown error"}
                </span>
              </div>
            )}

            {downloadMutation.isError && (
              <div className="mt-4 p-3 rounded-md bg-destructive/10 text-destructive text-sm flex items-center gap-2">
                <XCircle className="h-4 w-4 flex-shrink-0" />
                <span>
                  Export failed:{" "}
                  {(downloadMutation.error as Error)?.message || "Unknown error"}
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results */}
        {report && (
          <>
            {/* No AI models message */}
            {report.summary.total_ai_components === 0 ? (
              <Card>
                <CardContent className="py-12">
                  <div className="flex flex-col items-center justify-center space-y-3">
                    <Bot className="h-12 w-12 text-muted-foreground" />
                    <p className="text-lg font-medium">No AI Models Found</p>
                    <p className="text-sm text-muted-foreground text-center max-w-md">
                      This scan did not detect any AI models or datasets. EU AI
                      Act assessment only applies to AI/ML components. Try
                      scanning a repository that contains Hugging Face models,
                      MLflow artifacts, or other AI model files.
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Overall Compliance Score */}
                <Card
                  className={`border ${getScoreBgColor(report.summary.compliance_percentage)}`}
                >
                  <CardContent className="py-8">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                      <div className="text-center md:text-left">
                        <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
                          Overall Compliance Score
                        </p>
                        <div
                          className={`text-6xl font-bold mt-2 ${getScoreColor(report.summary.compliance_percentage)}`}
                        >
                          {report.summary.compliance_percentage}%
                        </div>
                        <p className="text-sm text-muted-foreground mt-2">
                          EU AI Act Article 53 GPAI Obligations
                        </p>
                      </div>
                      <div className="grid grid-cols-3 gap-6 text-center">
                        <div>
                          <div className="text-2xl font-bold text-green-600">
                            {report.summary.compliant}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            Compliant
                          </p>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-amber-500">
                            {report.summary.partial}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            Partial
                          </p>
                        </div>
                        <div>
                          <div className="text-2xl font-bold text-red-600">
                            {report.summary.non_compliant}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            Non-Compliant
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Per-Model Assessment Cards */}
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold">
                    Per-Model Assessments
                  </h3>
                  {report.assessments.map((assessment, idx) => (
                    <Card key={`${assessment.component_name}-${idx}`}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Bot className="h-5 w-5 text-primary" />
                            <div>
                              <CardTitle className="text-lg">
                                {assessment.component_name}
                              </CardTitle>
                              <CardDescription className="flex items-center gap-2 mt-1">
                                <span>{assessment.component_type}</span>
                                <span className="text-muted-foreground">|</span>
                                <span>
                                  Risk:{" "}
                                  {formatRiskClassification(
                                    assessment.risk_classification
                                  )}
                                </span>
                              </CardDescription>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(assessment.overall_status)}
                            <Badge
                              variant={getStatusBadgeVariant(
                                assessment.overall_status
                              )}
                            >
                              {formatStatus(assessment.overall_status)}
                            </Badge>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {/* Obligation Status Table */}
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="w-[120px]">
                                Article
                              </TableHead>
                              <TableHead>Obligation</TableHead>
                              <TableHead className="w-[110px]">
                                Status
                              </TableHead>
                              <TableHead>Evidence</TableHead>
                              <TableHead>Gaps</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {assessment.obligations.map((obligation) => (
                              <TableRow key={obligation.article}>
                                <TableCell className="font-mono text-xs">
                                  {obligation.article}
                                </TableCell>
                                <TableCell className="font-medium text-sm">
                                  {obligation.title}
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-1.5">
                                    {getStatusIcon(obligation.status)}
                                    <span
                                      className={`text-xs font-medium ${getStatusColor(obligation.status)}`}
                                    >
                                      {formatStatus(obligation.status)}
                                    </span>
                                  </div>
                                </TableCell>
                                <TableCell className="text-xs text-muted-foreground max-w-[200px]">
                                  {obligation.evidence.length > 0 ? (
                                    <ul className="list-disc list-inside space-y-0.5">
                                      {obligation.evidence.map(
                                        (ev, evIdx) => (
                                          <li key={evIdx}>{ev}</li>
                                        )
                                      )}
                                    </ul>
                                  ) : (
                                    <span className="italic">None</span>
                                  )}
                                </TableCell>
                                <TableCell className="text-xs text-muted-foreground max-w-[200px]">
                                  {obligation.gaps.length > 0 ? (
                                    <ul className="list-disc list-inside space-y-0.5">
                                      {obligation.gaps.map(
                                        (gap, gapIdx) => (
                                          <li
                                            key={gapIdx}
                                            className="text-amber-600 dark:text-amber-400"
                                          >
                                            {gap}
                                          </li>
                                        )
                                      )}
                                    </ul>
                                  ) : (
                                    <span className="italic">None</span>
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>

                        {/* Recommendations */}
                        {assessment.recommendations.length > 0 && (
                          <div className="pt-2 border-t">
                            <p className="text-sm font-medium mb-2">
                              Recommendations
                            </p>
                            <ul className="space-y-1.5">
                              {assessment.recommendations.map(
                                (rec, recIdx) => (
                                  <li
                                    key={recIdx}
                                    className="text-xs text-muted-foreground flex items-start gap-2"
                                  >
                                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                                    <span>{rec}</span>
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </>
        )}

        {/* Information Card */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-5 w-5 text-primary" />
              About EU AI Act Compliance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              The EU AI Act (Regulation (EU) 2024/1689) establishes obligations
              for providers of General Purpose AI (GPAI) models under Article
              53. This tool assesses your AI models against these requirements:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>
                <strong>Art. 53(1)(a) — Technical Documentation:</strong>{" "}
                Maintain up-to-date technical documentation including training
                and testing processes
              </li>
              <li>
                <strong>Art. 53(1)(b) — Downstream Provider Info:</strong>{" "}
                Provide information for downstream AI system providers to
                understand capabilities and limitations
              </li>
              <li>
                <strong>Art. 53(1)(c) — Copyright Policy:</strong> Implement a
                policy to comply with EU copyright law, including rights
                reservations
              </li>
              <li>
                <strong>Art. 53(1)(d) — Training Data Summary:</strong> Publish
                a sufficiently detailed summary of training data content
              </li>
              <li>
                <strong>Art. 53(2) — Systemic Risk:</strong> Additional
                obligations for models with systemic risk including evaluations,
                incident tracking, and cybersecurity
              </li>
            </ul>
            <p className="pt-2">
              The <strong>Export Compliance Pack</strong> generates a ZIP archive
              containing the JSON assessment report, a human-readable Markdown
              report, and scan metadata for your compliance records.
            </p>
          </CardContent>
        </Card>
      </div>
    </ContentLayout>
  );
}
