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
import { Package, Loader2, AlertCircle, Database } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

interface Dataset {
  name: string;
  version: string;
  license: string;
  project: string;
  scanId: string;
  scanDate: string;
  metadata?: any;
}

export default function DatasetsPage() {
  // Fetch all scans
  const { data: scans, isLoading: scansLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: getScans,
  });

  // Fetch all scan details to extract datasets
  const { data: scanDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ["all-scans-details-datasets"],
    queryFn: async () => {
      if (!scans || scans.length === 0) return [];
      const details = await Promise.all(scans.map((scan) => getScan(scan.id)));
      return details;
    },
    enabled: !!scans && scans.length > 0,
  });

  // Extract all datasets from scan results
  const datasets: Dataset[] = useMemo(() => {
    if (!scanDetails) return [];

    const allDatasets: Dataset[] = [];

    scanDetails.forEach((scanDetail) => {
      const findings = scanDetail.report.findings || [];

      findings.forEach((finding: any) => {
        // Filter for DATASET component type
        if (finding.component.type === "dataset") {
          allDatasets.push({
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

    return allDatasets;
  }, [scanDetails]);

  // Calculate statistics
  const stats = useMemo(() => {
    const totalDatasets = datasets.length;
    const uniqueDatasets = new Set(datasets.map((d) => d.name)).size;
    const licensedDatasets = datasets.filter((d) => d.license !== "UNKNOWN").length;
    const projectsUsingDatasets = new Set(datasets.map((d) => d.project)).size;

    return {
      totalDatasets,
      uniqueDatasets,
      licensedDatasets,
      projectsUsingDatasets,
    };
  }, [datasets]);

  const isLoading = scansLoading || detailsLoading;

  return (
    <ContentLayout title="Datasets">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Datasets</h2>
            <p className="text-muted-foreground mt-2">
              Track AI/ML datasets detected in your projects. Datasets are identified from Hugging Face Datasets, Kaggle, and other data sources with license compliance checking for training data.
            </p>
          </div>
        </div>

        {/* Statistics Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Datasets
              </CardTitle>
              <Database className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Loading...</span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">{stats.totalDatasets}</div>
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
                Unique Datasets
              </CardTitle>
              <Package className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Loading...</span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">{stats.uniqueDatasets}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Distinct dataset names
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
                  <div className="text-2xl font-bold">{stats.licensedDatasets}</div>
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
              <Database className="h-4 w-4 text-primary" />
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
                    {stats.projectsUsingDatasets}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Using datasets
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Datasets Table */}
        <Card>
          <CardHeader>
            <CardTitle>Detected Datasets</CardTitle>
            <CardDescription>
              Training and validation datasets discovered in your repositories including Hugging Face Datasets, Kaggle datasets, and local data files
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : datasets.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <Package className="h-12 w-12 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  No datasets detected yet. Scan repositories containing Hugging Face Datasets, Kaggle data, or other training data files.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Dataset Name</TableHead>
                    <TableHead>Version</TableHead>
                    <TableHead>License</TableHead>
                    <TableHead>Project</TableHead>
                    <TableHead>Detected</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {datasets.map((dataset, index) => (
                    <TableRow key={`${dataset.scanId}-${dataset.name}-${index}`}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <Database className="h-4 w-4 text-primary" />
                          {dataset.name}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {dataset.version}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            dataset.license === "UNKNOWN"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {dataset.license}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {dataset.project}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(dataset.scanDate).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/scans/${dataset.scanId}`}>
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
              About Dataset Detection
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              The License Compliance Checker automatically detects AI/ML datasets in your repositories and verifies their license compliance:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>
                <strong>Hugging Face Datasets:</strong> Detects datasets from Hugging Face Hub with license metadata
              </li>
              <li>
                <strong>Training Data Licenses:</strong> Identifies licenses like CC-BY, CC0, OpenData, and dataset-specific terms
              </li>
              <li>
                <strong>Data Use Restrictions:</strong> Tracks restrictions on commercial use, derivative works, and research-only datasets
              </li>
              <li>
                <strong>Local Dataset Files:</strong> Scans local CSV, JSON, Parquet, and other data files for license information
              </li>
            </ul>
            <p className="pt-2">
              Dataset licenses are critical for AI/ML compliance. Some datasets allow only research use or prohibit commercial applications, which can affect your model's license.
            </p>
          </CardContent>
        </Card>
      </div>
    </ContentLayout>
  );
}
