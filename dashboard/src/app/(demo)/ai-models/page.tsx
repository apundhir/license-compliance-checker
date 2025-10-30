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
import { Bot, Loader2, AlertCircle, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

interface AIModel {
  name: string;
  version: string;
  license: string;
  project: string;
  scanId: string;
  scanDate: string;
  metadata?: any;
}

export default function AIModelsPage() {
  // Fetch all scans
  const { data: scans, isLoading: scansLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: getScans,
  });

  // Fetch all scan details to extract AI models
  const { data: scanDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ["all-scans-details"],
    queryFn: async () => {
      if (!scans || scans.length === 0) return [];
      const details = await Promise.all(scans.map((scan) => getScan(scan.id)));
      return details;
    },
    enabled: !!scans && scans.length > 0,
  });

  // Extract all AI models from scan results
  const aiModels: AIModel[] = useMemo(() => {
    if (!scanDetails) return [];

    const allModels: AIModel[] = [];

    scanDetails.forEach((scanDetail) => {
      const findings = scanDetail.report.findings || [];

      findings.forEach((finding: any) => {
        // Filter for AI_MODEL component type
        if (finding.component.type === "ai_model") {
          allModels.push({
            name: finding.component.name,
            version: finding.component.version || "unknown",
            license: finding.resolved_license || "UNKNOWN",
            project: scanDetail.summary.project,
            scanId: scanDetail.summary.id,
            scanDate: scanDetail.summary.generatedAt,
            metadata: finding.component.metadata,
          });
        }
      });
    });

    return allModels;
  }, [scanDetails]);

  // Calculate statistics
  const stats = useMemo(() => {
    const totalModels = aiModels.length;
    const uniqueModels = new Set(aiModels.map((m) => m.name)).size;
    const licensedModels = aiModels.filter((m) => m.license !== "UNKNOWN").length;
    const projectsUsingModels = new Set(aiModels.map((m) => m.project)).size;

    return {
      totalModels,
      uniqueModels,
      licensedModels,
      projectsUsingModels,
    };
  }, [aiModels]);

  const isLoading = scansLoading || detailsLoading;

  return (
    <ContentLayout title="AI Models">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">AI Models</h2>
            <p className="text-muted-foreground mt-2">
              Track AI/ML models detected in your projects. Models are identified from Hugging Face, MLflow, and other model registries with specialized license handling for RAIL, Llama, and other AI-specific licenses.
            </p>
          </div>
        </div>

        {/* Statistics Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Models
              </CardTitle>
              <Bot className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Loading...</span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">{stats.totalModels}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Across all scans
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Unique Models
              </CardTitle>
              <Bot className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Loading...</span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">{stats.uniqueModels}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Distinct model names
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Licensed</CardTitle>
              <AlertCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Loading...</span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">{stats.licensedModels}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    With known licenses
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Projects</CardTitle>
              <Bot className="h-4 w-4 text-primary" />
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
                    {stats.projectsUsingModels}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Using AI models
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* AI Models Table */}
        <Card>
          <CardHeader>
            <CardTitle>Detected AI Models</CardTitle>
            <CardDescription>
              AI/ML models discovered in your repositories including Hugging Face models, Llama, and other model registry downloads
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : aiModels.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <Bot className="h-12 w-12 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  No AI models detected yet. Scan repositories containing Hugging Face models, MLflow artifacts, or other AI model files.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Model Name</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>License</TableHead>
                    <TableHead>Project</TableHead>
                    <TableHead>Detected</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {aiModels.map((model, index) => (
                    <TableRow key={`${model.scanId}-${model.name}-${index}`}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <Bot className="h-4 w-4 text-primary" />
                          {model.name}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {model.version}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            model.license === "UNKNOWN"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {model.license}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {model.project}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(model.scanDate).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/scans/${model.scanId}`}>
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

        {/* Information Card */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-5 w-5 text-primary" />
              About AI Model Detection
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              The License Compliance Checker automatically detects AI/ML models in your repositories and extracts their license information:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>
                <strong>Hugging Face Models:</strong> Detects models from Hugging Face Hub with model cards and license metadata
              </li>
              <li>
                <strong>RAIL Licenses:</strong> Identifies Responsible AI License variants with use restrictions
              </li>
              <li>
                <strong>Llama Licenses:</strong> Handles Meta's Llama 2 and Llama 3 commercial use thresholds
              </li>
              <li>
                <strong>Model Registry Support:</strong> Scans MLflow, local model files, and other AI artifacts
              </li>
            </ul>
            <p className="pt-2">
              Use the AI-specific policies (ai-ml-permissive, ai-ml-research) to enforce compliance rules tailored for AI/ML workloads.
            </p>
          </CardContent>
        </Card>
      </div>
    </ContentLayout>
  );
}
