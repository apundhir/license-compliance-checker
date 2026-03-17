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
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Bot,
  Loader2,
  AlertCircle,
  AlertTriangle,
  Shield,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  Database,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Leaf,
  Info,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AIModel {
  name: string;
  version: string;
  license: string;
  project: string;
  scanId: string;
  scanDate: string;
  metadata?: any;
  policyStatus?: string | null;
}

type LicenseCategory = "all" | "permissive" | "restricted" | "rail" | "unknown";
type EuRiskLevel = "all" | "low" | "review" | "assessment";

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
  "unlicense",
  "wtfpl",
  "0bsd",
  "artistic-2.0",
  "zlib",
];

const RAIL_LICENSES = [
  "openrail",
  "openrail-m",
  "openrail++",
  "bigscience-bloom-rail",
  "bigscience-openrail-m",
  "creativeml-openrail-m",
  "rail",
];

const RESTRICTED_LICENSES = [
  "llama-2",
  "llama-3",
  "llama-3.1",
  "deepmind-gemma",
  "anthropic-claude",
  "openai-gpt",
  "cohere",
  "ai21-jurassic",
  "gpl-2.0",
  "gpl-3.0",
  "agpl-3.0",
  "cc-by-nc",
  "cc-by-nc-sa",
  "cc-by-nc-nd",
];

function classifyLicense(license: string): "permissive" | "restricted" | "rail" | "unknown" {
  if (!license || license === "UNKNOWN") return "unknown";
  const lower = license.toLowerCase();
  if (RAIL_LICENSES.some((r) => lower.includes(r))) return "rail";
  if (RESTRICTED_LICENSES.some((r) => lower.includes(r))) return "restricted";
  if (PERMISSIVE_LICENSES.some((p) => lower.includes(p))) return "permissive";
  // Check for common permissive patterns
  if (lower.includes("apache") || lower.includes("mit") || lower.includes("bsd")) return "permissive";
  if (lower.includes("rail")) return "rail";
  if (lower.includes("gpl") || lower.includes("proprietary") || lower.includes("nc")) return "restricted";
  return "unknown";
}

// ---------------------------------------------------------------------------
// Helper: EU AI Act risk level
// ---------------------------------------------------------------------------

interface EuAiActInfo {
  level: "low" | "review" | "assessment";
  label: string;
  article: string;
}

function getEuAiActRisk(license: string): EuAiActInfo {
  const category = classifyLicense(license);
  switch (category) {
    case "permissive":
      return {
        level: "low",
        label: "EU AI Act — Low Risk",
        article: "Permissive open-source license",
      };
    case "rail":
      return {
        level: "review",
        label: "EU AI Act Art. 53 — Review Required",
        article: "RAIL license with use-based restrictions requires compliance review",
      };
    case "restricted":
      return {
        level: "review",
        label: "EU AI Act Art. 53 — Review Required",
        article: "Restricted license requires compliance review under EU AI Act",
      };
    case "unknown":
    default:
      return {
        level: "assessment",
        label: "EU AI Act — Assessment Needed",
        article: "License not identified; full assessment required",
      };
  }
}

// ---------------------------------------------------------------------------
// Helper: format use restriction labels
// ---------------------------------------------------------------------------

const RESTRICTION_LABELS: Record<string, string> = {
  "no-harm": "Cannot be used for: causing harm to individuals or groups",
  "no-illegal-activity": "Cannot be used for: illegal activities",
  "no-personal-data-exploitation": "Cannot be used for: exploiting personal data without consent",
  "no-discrimination": "Cannot be used for: discrimination or social scoring",
  "no-misinformation": "Cannot be used for: generating misinformation or disinformation",
  "no-impersonation": "Cannot be used for: impersonating real persons",
  "no-automated-legal-advice": "Cannot be used for: automated legal, medical, or financial advice without disclosure",
  "no-deception": "Cannot be used for: deception or fraud",
  "behavioral-restrictions": "Behavioral use restrictions apply",
  "enhanced-monitoring": "Enhanced monitoring requirements apply",
  "user-threshold-700m": "Commercial use restricted above 700M monthly active users",
  "no-llama-improvement": "Cannot be used to improve competing LLMs",
  "acceptable-use-policy": "Subject to acceptable use policy",
  "api-only": "API access only — no model distribution",
  "no-distribution": "Model weights cannot be redistributed",
  "usage-policies": "Subject to provider usage policies",
  "attribution-required": "Attribution is required in all use cases",
};

function formatRestriction(restriction: string): string {
  return RESTRICTION_LABELS[restriction] || restriction;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function EuAiActBadge({ license }: { license: string }) {
  const info = getEuAiActRisk(license);
  const colorClasses = {
    low: "bg-green-100 text-green-800 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800",
    review: "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800",
    assessment: "bg-red-100 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800",
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
      title={info.article}
    >
      {icons[info.level]}
      {info.label}
    </Badge>
  );
}

function PolicyStatusBadge({ status }: { status?: string | null }) {
  if (!status) {
    return (
      <Badge variant="secondary" className="text-[10px]">
        Not evaluated
      </Badge>
    );
  }
  const lower = status.toLowerCase();
  if (lower === "pass") {
    return (
      <Badge
        variant="outline"
        className="bg-green-100 text-green-800 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800 text-[10px]"
      >
        <CheckCircle2 className="h-3 w-3 mr-1" />
        PASS
      </Badge>
    );
  }
  if (lower === "warning") {
    return (
      <Badge
        variant="outline"
        className="bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800 text-[10px]"
      >
        <AlertTriangle className="h-3 w-3 mr-1" />
        WARNING
      </Badge>
    );
  }
  if (lower === "violation") {
    return (
      <Badge
        variant="outline"
        className="bg-red-100 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800 text-[10px]"
      >
        <XCircle className="h-3 w-3 mr-1" />
        VIOLATION
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="text-[10px]">
      {status}
    </Badge>
  );
}

function UseRestrictionsPanel({ metadata }: { metadata?: any }) {
  const [open, setOpen] = useState(false);

  const restrictions: string[] = metadata?.use_restrictions || [];

  if (restrictions.length === 0) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
        <CheckCircle2 className="h-3.5 w-3.5" />
        No restrictions identified
      </div>
    );
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 transition-colors">
          {open ? (
            <ChevronDown className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
          <AlertTriangle className="h-3.5 w-3.5" />
          <span className="font-medium">
            {restrictions.length} use restriction{restrictions.length !== 1 ? "s" : ""}
          </span>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ul className="mt-2 space-y-1 pl-5">
          {restrictions.map((r, i) => (
            <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
              <span className="text-amber-500 mt-0.5 shrink-0">-</span>
              {formatRestriction(r)}
            </li>
          ))}
        </ul>
      </CollapsibleContent>
    </Collapsible>
  );
}

function TrainingDataSection({ metadata }: { metadata?: any }) {
  const datasets: string[] = metadata?.datasets || [];
  const sources: string[] = metadata?.training_data_sources || [];
  const description: string | undefined = metadata?.training_data_description;

  const hasData = datasets.length > 0 || sources.length > 0 || description;

  if (!hasData) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
        <AlertTriangle className="h-3.5 w-3.5" />
        Training data not documented
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-medium text-foreground">
        <Database className="h-3.5 w-3.5 text-primary" />
        Training Data
      </div>
      {datasets.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {datasets.map((ds, i) => (
            <Badge key={i} variant="secondary" className="text-[10px]">
              {ds}
            </Badge>
          ))}
        </div>
      )}
      {sources.length > 0 && (
        <ul className="space-y-0.5 pl-4">
          {sources.map((src, i) => (
            <li key={i} className="text-xs text-muted-foreground">
              {src.startsWith("http") ? (
                <a
                  href={src}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-foreground inline-flex items-center gap-1"
                >
                  {src.length > 60 ? src.slice(0, 60) + "..." : src}
                  <ExternalLink className="h-2.5 w-2.5" />
                </a>
              ) : (
                src
              )}
            </li>
          ))}
        </ul>
      )}
      {description && (
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
          {description}
        </p>
      )}
    </div>
  );
}

function ModelDetailDialog({
  model,
  open,
  onOpenChange,
}: {
  model: AIModel | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!model) return null;

  const meta = model.metadata || {};
  const euInfo = getEuAiActRisk(model.license);
  const restrictions: string[] = meta.use_restrictions || [];
  const datasets: string[] = meta.datasets || [];
  const sources: string[] = meta.training_data_sources || [];
  const description: string | undefined = meta.training_data_description;
  const limitations: string | undefined = meta.limitations;
  const intendedUses: string | undefined = meta.intended_uses;
  const outOfScopeUses: string | undefined = meta.out_of_scope_uses;
  const evaluationMetrics: Record<string, string> = meta.evaluation_metrics || {};
  const environmentalImpact: Record<string, string> = meta.environmental_impact || {};

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            {model.name}
          </DialogTitle>
          <DialogDescription>
            Version {model.version} &middot; Project: {model.project}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 pt-2">
          {/* Model Info */}
          <div className="grid grid-cols-2 gap-3">
            {meta.model_type && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">Model Type</span>
                <p className="text-sm">{meta.model_type}</p>
              </div>
            )}
            {meta.architecture && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">Architecture</span>
                <p className="text-sm">{meta.architecture}</p>
              </div>
            )}
            {(meta.framework || meta.library_name) && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">Framework</span>
                <p className="text-sm">{meta.framework || meta.library_name}</p>
              </div>
            )}
            {meta.pipeline_tag && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">Pipeline</span>
                <p className="text-sm">{meta.pipeline_tag}</p>
              </div>
            )}
            {meta.language && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">Language</span>
                <p className="text-sm">{meta.language}</p>
              </div>
            )}
          </div>

          {/* License & EU AI Act */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold flex items-center gap-1.5">
              <Shield className="h-4 w-4 text-primary" />
              License & Compliance
            </h4>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{model.license}</Badge>
              <EuAiActBadge license={model.license} />
              <PolicyStatusBadge status={model.policyStatus} />
            </div>
            <p className="text-xs text-muted-foreground">{euInfo.article}</p>
          </div>

          {/* RAIL Restrictions */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Use Restrictions
            </h4>
            {restrictions.length > 0 ? (
              <ul className="space-y-1.5">
                {restrictions.map((r, i) => (
                  <li
                    key={i}
                    className="text-sm text-muted-foreground flex items-start gap-2"
                  >
                    <XCircle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                    {formatRestriction(r)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" />
                No restrictions identified
              </p>
            )}
          </div>

          {/* Training Data */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold flex items-center gap-1.5">
              <Database className="h-4 w-4 text-primary" />
              Training Data
            </h4>
            {datasets.length > 0 || sources.length > 0 || description ? (
              <div className="space-y-2">
                {datasets.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {datasets.map((ds, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {ds}
                      </Badge>
                    ))}
                  </div>
                )}
                {sources.length > 0 && (
                  <ul className="space-y-1 pl-1">
                    {sources.map((src, i) => (
                      <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
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
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {description}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5" />
                Training data not documented
              </p>
            )}
          </div>

          {/* Intended Uses */}
          {intendedUses && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <Info className="h-4 w-4 text-primary" />
                Intended Uses
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                {intendedUses}
              </p>
            </div>
          )}

          {/* Out of Scope Uses */}
          {outOfScopeUses && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <XCircle className="h-4 w-4 text-red-500" />
                Out-of-Scope Uses
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                {outOfScopeUses}
              </p>
            </div>
          )}

          {/* Limitations */}
          {limitations && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <AlertCircle className="h-4 w-4 text-amber-500" />
                Limitations
              </h4>
              <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                {limitations}
              </p>
            </div>
          )}

          {/* Evaluation Metrics */}
          {Object.keys(evaluationMetrics).length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold">Evaluation Metrics</h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(evaluationMetrics).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-md border px-3 py-1.5 text-sm"
                  >
                    <span className="text-muted-foreground">{key}</span>
                    <span className="font-medium">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Environmental Impact */}
          {Object.keys(environmentalImpact).length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold flex items-center gap-1.5">
                <Leaf className="h-4 w-4 text-green-600" />
                Environmental Impact
              </h4>
              <div className="space-y-1">
                {Object.entries(environmentalImpact).map(([key, value]) => (
                  <div key={key} className="flex items-start gap-2 text-sm">
                    <span className="text-muted-foreground capitalize min-w-[100px]">
                      {key.replace(/_/g, " ")}:
                    </span>
                    <span>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end pt-2">
            <Button variant="outline" size="sm" asChild>
              <Link href={`/scans/${model.scanId}`}>
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
// Filter bar component
// ---------------------------------------------------------------------------

function FilterBar({
  searchQuery,
  onSearchChange,
  licenseFilter,
  onLicenseFilterChange,
  euRiskFilter,
  onEuRiskFilterChange,
  activeFilterCount,
}: {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  licenseFilter: LicenseCategory;
  onLicenseFilterChange: (value: LicenseCategory) => void;
  euRiskFilter: EuRiskLevel;
  onEuRiskFilterChange: (value: EuRiskLevel) => void;
  activeFilterCount: number;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="relative flex-1 max-w-sm">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search models..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9"
        />
      </div>
      <Select value={licenseFilter} onValueChange={(v) => onLicenseFilterChange(v as LicenseCategory)}>
        <SelectTrigger className="w-[170px]">
          <SelectValue placeholder="License type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Licenses</SelectItem>
          <SelectItem value="permissive">Permissive</SelectItem>
          <SelectItem value="restricted">Restricted</SelectItem>
          <SelectItem value="rail">RAIL</SelectItem>
          <SelectItem value="unknown">Unknown</SelectItem>
        </SelectContent>
      </Select>
      <Select value={euRiskFilter} onValueChange={(v) => onEuRiskFilterChange(v as EuRiskLevel)}>
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="EU AI Act risk" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Risk Levels</SelectItem>
          <SelectItem value="low">Low Risk</SelectItem>
          <SelectItem value="review">Review Required</SelectItem>
          <SelectItem value="assessment">Assessment Needed</SelectItem>
        </SelectContent>
      </Select>
      {activeFilterCount > 0 && (
        <Badge variant="secondary" className="flex items-center gap-1 text-xs">
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

export default function AIModelsPage() {
  // Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [licenseFilter, setLicenseFilter] = useState<LicenseCategory>("all");
  const [euRiskFilter, setEuRiskFilter] = useState<EuRiskLevel>("all");

  // Detail dialog state
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

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
      if (!scanDetail?.report?.findings) return;

      const findings = scanDetail.report.findings || [];

      findings.forEach((finding: any) => {
        if (finding?.component?.type === "ai_model") {
          const meta = finding.component.metadata || {};
          const policyStatus =
            typeof meta.policy === "object" && meta.policy !== null
              ? meta.policy.status
              : null;

          allModels.push({
            name: finding.component.name || "unknown",
            version: finding.component.version || "unknown",
            license: finding.resolved_license || "UNKNOWN",
            project: scanDetail.summary?.project || "unknown",
            scanId: scanDetail.summary?.id || "",
            scanDate:
              scanDetail.summary?.generatedAt || new Date().toISOString(),
            metadata: meta,
            policyStatus,
          });
        }
      });
    });

    return allModels;
  }, [scanDetails]);

  // Filtered models
  const filteredModels = useMemo(() => {
    return aiModels.filter((model) => {
      // Search filter
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (
          !model.name.toLowerCase().includes(q) &&
          !model.project.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      // License type filter
      if (licenseFilter !== "all") {
        if (classifyLicense(model.license) !== licenseFilter) return false;
      }
      // EU risk filter
      if (euRiskFilter !== "all") {
        if (getEuAiActRisk(model.license).level !== euRiskFilter) return false;
      }
      return true;
    });
  }, [aiModels, searchQuery, licenseFilter, euRiskFilter]);

  // Active filter count
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (searchQuery) count++;
    if (licenseFilter !== "all") count++;
    if (euRiskFilter !== "all") count++;
    return count;
  }, [searchQuery, licenseFilter, euRiskFilter]);

  // Calculate statistics (based on all models, not filtered)
  const stats = useMemo(() => {
    const totalModels = aiModels.length;
    const uniqueModels = new Set(aiModels.map((m) => m.name)).size;
    const licensedModels = aiModels.filter(
      (m) => m.license !== "UNKNOWN"
    ).length;
    const projectsUsingModels = new Set(aiModels.map((m) => m.project)).size;
    const railModels = aiModels.filter(
      (m) => classifyLicense(m.license) === "rail"
    ).length;
    const restrictedModels = aiModels.filter(
      (m) => classifyLicense(m.license) === "restricted"
    ).length;

    return {
      totalModels,
      uniqueModels,
      licensedModels,
      projectsUsingModels,
      railModels,
      restrictedModels,
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
              Track AI/ML models detected in your projects with RAIL restriction analysis, EU AI Act compliance flags, and training data transparency.
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
                  <span className="text-sm text-muted-foreground">
                    Loading...
                  </span>
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
                  <span className="text-sm text-muted-foreground">
                    Loading...
                  </span>
                </div>
              ) : (
                <>
                  <div className="text-2xl font-bold">
                    {stats.uniqueModels}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Distinct model names
                  </p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                RAIL / Restricted
              </CardTitle>
              <AlertTriangle className="h-4 w-4 text-amber-500" />
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
                    {stats.railModels + stats.restrictedModels}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {stats.railModels} RAIL, {stats.restrictedModels} restricted
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
                  <span className="text-sm text-muted-foreground">
                    Loading...
                  </span>
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
          <CardContent className="space-y-4">
            {/* Filter Bar */}
            {!isLoading && aiModels.length > 0 && (
              <FilterBar
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                licenseFilter={licenseFilter}
                onLicenseFilterChange={setLicenseFilter}
                euRiskFilter={euRiskFilter}
                onEuRiskFilterChange={setEuRiskFilter}
                activeFilterCount={activeFilterCount}
              />
            )}

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
            ) : filteredModels.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <Search className="h-12 w-12 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  No models match the current filters. Try adjusting your search criteria.
                </p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Model Name</TableHead>
                      <TableHead>Version</TableHead>
                      <TableHead>License</TableHead>
                      <TableHead>EU AI Act</TableHead>
                      <TableHead>Policy</TableHead>
                      <TableHead>Restrictions</TableHead>
                      <TableHead>Training Data</TableHead>
                      <TableHead>Project</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredModels.map((model, index) => (
                      <TableRow
                        key={`${model.scanId}-${model.name}-${index}`}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => {
                          setSelectedModel(model);
                          setDialogOpen(true);
                        }}
                      >
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <Bot className="h-4 w-4 text-primary shrink-0" />
                            <span className="truncate max-w-[180px]">
                              {model.name}
                            </span>
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
                        <TableCell>
                          <EuAiActBadge license={model.license} />
                        </TableCell>
                        <TableCell>
                          <PolicyStatusBadge status={model.policyStatus} />
                        </TableCell>
                        <TableCell>
                          <UseRestrictionsPanel metadata={model.metadata} />
                        </TableCell>
                        <TableCell>
                          <TrainingDataSection metadata={model.metadata} />
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {model.project}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            asChild
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Link href={`/scans/${model.scanId}`}>
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
            {!isLoading && aiModels.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Showing {filteredModels.length} of {aiModels.length} model{aiModels.length !== 1 ? "s" : ""}
              </p>
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
                <strong>Llama Licenses:</strong> Handles Meta&apos;s Llama 2 and Llama 3 commercial use thresholds
              </li>
              <li>
                <strong>EU AI Act Compliance:</strong> Flags models requiring review under EU AI Act Article 53 based on license type
              </li>
              <li>
                <strong>Training Data Transparency:</strong> Extracts and displays training data sources from model cards
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

      {/* Model Detail Dialog */}
      <ModelDetailDialog
        model={selectedModel}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </ContentLayout>
  );
}
