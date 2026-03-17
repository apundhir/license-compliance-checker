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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Package,
  Loader2,
  AlertCircle,
  AlertTriangle,
  Shield,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  Database,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Dataset {
  name: string;
  version: string;
  license: string;
  project: string;
  scanId: string;
  scanDate: string;
  metadata?: any;
}

type LicenseCategory = "all" | "permissive" | "restricted" | "unknown";

// ---------------------------------------------------------------------------
// Helper: classify license type
// ---------------------------------------------------------------------------

const PERMISSIVE_LICENSES = [
  "apache-2.0",
  "mit",
  "bsd-2-clause",
  "bsd-3-clause",
  "isc",
  "cc0-1.0",
  "cc-by-4.0",
  "cc-by-3.0",
  "cc-by-sa-4.0",
  "unlicense",
  "wtfpl",
  "0bsd",
  "odc-by",
  "odc-odbl",
  "pddl",
  "cdla-permissive-1.0",
  "opendata",
];

const RESTRICTED_LICENSES = [
  "cc-by-nc",
  "cc-by-nc-sa",
  "cc-by-nc-nd",
  "cc-by-nd",
  "gpl-2.0",
  "gpl-3.0",
  "agpl-3.0",
  "cdla-sharing-1.0",
];

function classifyLicense(
  license: string
): "permissive" | "restricted" | "unknown" {
  if (!license || license === "UNKNOWN") return "unknown";
  const lower = license.toLowerCase();
  if (PERMISSIVE_LICENSES.some((p) => lower.includes(p))) return "permissive";
  if (
    lower.includes("apache") ||
    lower.includes("mit") ||
    lower.includes("bsd") ||
    lower.includes("cc0") ||
    lower.includes("cc-by-4") ||
    lower.includes("cc-by-3")
  )
    return "permissive";
  if (RESTRICTED_LICENSES.some((r) => lower.includes(r))) return "restricted";
  if (
    lower.includes("nc") ||
    lower.includes("gpl") ||
    lower.includes("proprietary")
  )
    return "restricted";
  return "unknown";
}

// ---------------------------------------------------------------------------
// Helper: EU AI Act risk for datasets
// ---------------------------------------------------------------------------

interface EuAiActInfo {
  level: "low" | "review" | "assessment";
  label: string;
}

function getEuAiActRisk(license: string): EuAiActInfo {
  const category = classifyLicense(license);
  switch (category) {
    case "permissive":
      return { level: "low", label: "EU AI Act — Low Risk" };
    case "restricted":
      return {
        level: "review",
        label: "EU AI Act Art. 53 — Review Required",
      };
    case "unknown":
    default:
      return { level: "assessment", label: "EU AI Act — Assessment Needed" };
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LicenseRiskBadge({ license }: { license: string }) {
  const category = classifyLicense(license);
  const config = {
    permissive: {
      label: "Permissive",
      classes:
        "bg-green-100 text-green-800 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800",
      icon: <CheckCircle2 className="h-3 w-3 mr-1" />,
    },
    restricted: {
      label: "Restricted",
      classes:
        "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800",
      icon: <AlertTriangle className="h-3 w-3 mr-1" />,
    },
    unknown: {
      label: "Unknown",
      classes:
        "bg-red-100 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800",
      icon: <XCircle className="h-3 w-3 mr-1" />,
    },
  };
  const c = config[category];
  return (
    <Badge variant="outline" className={`text-[10px] leading-tight ${c.classes}`}>
      {c.icon}
      {c.label}
    </Badge>
  );
}

function EuAiActBadge({ license }: { license: string }) {
  const info = getEuAiActRisk(license);
  const colorClasses = {
    low: "bg-green-100 text-green-800 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800",
    review:
      "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800",
    assessment:
      "bg-red-100 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800",
  };
  const icons = {
    low: <CheckCircle2 className="h-3 w-3 mr-1" />,
    review: <AlertTriangle className="h-3 w-3 mr-1" />,
    assessment: <XCircle className="h-3 w-3 mr-1" />,
  };
  return (
    <Badge
      variant="outline"
      className={`text-[10px] leading-tight ${colorClasses[info.level]}`}
    >
      {icons[info.level]}
      {info.label}
    </Badge>
  );
}

function DataSourcesSection({ metadata }: { metadata?: any }) {
  const sources: string[] = metadata?.training_data_sources || metadata?.data_sources || [];
  const description: string | undefined =
    metadata?.training_data_description || metadata?.description;

  if (sources.length === 0 && !description) {
    return (
      <span className="text-xs text-muted-foreground">-</span>
    );
  }

  return (
    <div className="space-y-1">
      {sources.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {sources.slice(0, 3).map((src, i) => (
            <Badge key={i} variant="secondary" className="text-[10px]">
              {src.length > 30 ? src.slice(0, 30) + "..." : src}
            </Badge>
          ))}
          {sources.length > 3 && (
            <Badge variant="secondary" className="text-[10px]">
              +{sources.length - 3} more
            </Badge>
          )}
        </div>
      )}
      {description && !sources.length && (
        <p className="text-xs text-muted-foreground line-clamp-2">
          {description}
        </p>
      )}
    </div>
  );
}

function DatasetDetailDialog({
  dataset,
  open,
  onOpenChange,
}: {
  dataset: Dataset | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!dataset) return null;

  const meta = dataset.metadata || {};
  const sources: string[] =
    meta.training_data_sources || meta.data_sources || [];
  const description: string | undefined =
    meta.training_data_description || meta.description;
  const tags: string[] = meta.tags || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            {dataset.name}
          </DialogTitle>
          <DialogDescription>
            Version {dataset.version} &middot; Project: {dataset.project}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 pt-2">
          {/* License & Compliance */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold flex items-center gap-1.5">
              <Shield className="h-4 w-4 text-primary" />
              License & Compliance
            </h4>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{dataset.license}</Badge>
              <LicenseRiskBadge license={dataset.license} />
              <EuAiActBadge license={dataset.license} />
            </div>
          </div>

          {/* Data Sources */}
          {(sources.length > 0 || description) && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <Database className="h-4 w-4 text-primary" />
                Data Sources
              </h4>
              {sources.length > 0 && (
                <ul className="space-y-1 pl-1">
                  {sources.map((src, i) => (
                    <li
                      key={i}
                      className="text-sm text-muted-foreground flex items-start gap-2"
                    >
                      <span className="text-primary mt-0.5 shrink-0">-</span>
                      {src.startsWith("http") ? (
                        <a
                          href={src}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="underline hover:text-foreground inline-flex items-center gap-1"
                        >
                          {src.length > 70 ? src.slice(0, 70) + "..." : src}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        src
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {description && (
                <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                  {description}
                </p>
              )}
            </div>
          )}

          {/* Tags */}
          {tags.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold">Tags</h4>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((tag, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-3">
            {meta.language && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">
                  Language
                </span>
                <p className="text-sm">{meta.language}</p>
              </div>
            )}
            {meta.size && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">
                  Size
                </span>
                <p className="text-sm">{meta.size}</p>
              </div>
            )}
            {meta.format && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">
                  Format
                </span>
                <p className="text-sm">{meta.format}</p>
              </div>
            )}
            {meta.task && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">
                  Task
                </span>
                <p className="text-sm">{meta.task}</p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end pt-2">
            <Button variant="outline" size="sm" asChild>
              <Link href={`/scans/${dataset.scanId}`}>
                <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                View Full Scan
              </Link>
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Filter bar
// ---------------------------------------------------------------------------

function FilterBar({
  searchQuery,
  onSearchChange,
  licenseFilter,
  onLicenseFilterChange,
  activeFilterCount,
}: {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  licenseFilter: LicenseCategory;
  onLicenseFilterChange: (value: LicenseCategory) => void;
  activeFilterCount: number;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="relative flex-1 max-w-sm">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search datasets..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9"
        />
      </div>
      <Select
        value={licenseFilter}
        onValueChange={(v) => onLicenseFilterChange(v as LicenseCategory)}
      >
        <SelectTrigger className="w-[170px]">
          <SelectValue placeholder="License type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Licenses</SelectItem>
          <SelectItem value="permissive">Permissive</SelectItem>
          <SelectItem value="restricted">Restricted</SelectItem>
          <SelectItem value="unknown">Unknown</SelectItem>
        </SelectContent>
      </Select>
      {activeFilterCount > 0 && (
        <Badge
          variant="secondary"
          className="flex items-center gap-1 text-xs"
        >
          <Filter className="h-3 w-3" />
          {activeFilterCount} active filter{activeFilterCount !== 1 ? "s" : ""}
        </Badge>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DatasetsPage() {
  // Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [licenseFilter, setLicenseFilter] = useState<LicenseCategory>("all");

  // Detail dialog state
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

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
      if (!scanDetail?.report?.findings) return;

      const findings = scanDetail.report.findings || [];

      findings.forEach((finding: any) => {
        if (finding?.component?.type === "dataset") {
          allDatasets.push({
            name: finding.component.name || "unknown",
            version: finding.component.version || "unknown",
            license: finding.resolved_license || "UNKNOWN",
            project: scanDetail.summary?.project || "unknown",
            scanId: scanDetail.summary?.id || "",
            scanDate:
              scanDetail.summary?.generatedAt || new Date().toISOString(),
            metadata: finding.component.metadata,
          });
        }
      });
    });

    return allDatasets;
  }, [scanDetails]);

  // Filtered datasets
  const filteredDatasets = useMemo(() => {
    return datasets.filter((dataset) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (
          !dataset.name.toLowerCase().includes(q) &&
          !dataset.project.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      if (licenseFilter !== "all") {
        if (classifyLicense(dataset.license) !== licenseFilter) return false;
      }
      return true;
    });
  }, [datasets, searchQuery, licenseFilter]);

  // Active filter count
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (searchQuery) count++;
    if (licenseFilter !== "all") count++;
    return count;
  }, [searchQuery, licenseFilter]);

  // Calculate statistics
  const stats = useMemo(() => {
    const totalDatasets = datasets.length;
    const uniqueDatasets = new Set(datasets.map((d) => d.name)).size;
    const licensedDatasets = datasets.filter(
      (d) => d.license !== "UNKNOWN"
    ).length;
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
              Track AI/ML datasets detected in your projects with license risk assessment and EU AI Act compliance flags for training data.
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
                  <span className="text-sm text-muted-foreground">
                    Loading...
                  </span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">
                    {stats.totalDatasets}
                  </div>
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
                  <span className="text-sm text-muted-foreground">
                    Loading...
                  </span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">
                    {stats.uniqueDatasets}
                  </div>
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
                  <span className="text-sm text-muted-foreground">
                    Loading...
                  </span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">
                    {stats.licensedDatasets}
                  </div>
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
                  <span className="text-sm text-muted-foreground">
                    Loading...
                  </span>
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
          <CardContent className="space-y-4">
            {/* Filter Bar */}
            {!isLoading && datasets.length > 0 && (
              <FilterBar
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                licenseFilter={licenseFilter}
                onLicenseFilterChange={setLicenseFilter}
                activeFilterCount={activeFilterCount}
              />
            )}

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
            ) : filteredDatasets.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <Search className="h-12 w-12 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  No datasets match the current filters. Try adjusting your search criteria.
                </p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Dataset Name</TableHead>
                      <TableHead>Version</TableHead>
                      <TableHead>License</TableHead>
                      <TableHead>Risk</TableHead>
                      <TableHead>EU AI Act</TableHead>
                      <TableHead>Data Sources</TableHead>
                      <TableHead>Project</TableHead>
                      <TableHead>Detected</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredDatasets.map((dataset, index) => (
                      <TableRow
                        key={`${dataset.scanId}-${dataset.name}-${index}`}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => {
                          setSelectedDataset(dataset);
                          setDialogOpen(true);
                        }}
                      >
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <Database className="h-4 w-4 text-primary shrink-0" />
                            <span className="truncate max-w-[180px]">
                              {dataset.name}
                            </span>
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
                        <TableCell>
                          <LicenseRiskBadge license={dataset.license} />
                        </TableCell>
                        <TableCell>
                          <EuAiActBadge license={dataset.license} />
                        </TableCell>
                        <TableCell>
                          <DataSourcesSection metadata={dataset.metadata} />
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {dataset.project}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(dataset.scanDate).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            asChild
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Link href={`/scans/${dataset.scanId}`}>
                              View Scan
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Results count */}
            {!isLoading && datasets.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Showing {filteredDatasets.length} of {datasets.length} dataset{datasets.length !== 1 ? "s" : ""}
              </p>
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
                <strong>EU AI Act Compliance:</strong> Flags datasets requiring review under EU AI Act transparency requirements
              </li>
              <li>
                <strong>Local Dataset Files:</strong> Scans local CSV, JSON, Parquet, and other data files for license information
              </li>
            </ul>
            <p className="pt-2">
              Dataset licenses are critical for AI/ML compliance. Some datasets allow only research use or prohibit commercial applications, which can affect your model&apos;s license.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Dataset Detail Dialog */}
      <DatasetDetailDialog
        dataset={selectedDataset}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </ContentLayout>
  );
}
