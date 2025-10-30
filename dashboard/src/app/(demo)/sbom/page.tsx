"use client";

import { useQuery } from "@tanstack/react-query";
import { getScans } from "@/lib/api";
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
import { FileText, Loader2, AlertCircle, Download, Terminal, Copy, CheckCircle } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function SBOMPage() {
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);

  const { data: scans, isLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: getScans,
  });

  const copyCommand = (command: string, id: string) => {
    navigator.clipboard.writeText(command);
    setCopiedCommand(id);
    setTimeout(() => setCopiedCommand(null), 2000);
  };

  return (
    <ContentLayout title="SBOM">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              Software Bill of Materials (SBOM)
            </h2>
            <p className="text-muted-foreground mt-2">
              Generate standardized SBOMs for your scans in CycloneDX or SPDX formats
            </p>
          </div>
        </div>

        {/* Information Card */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Terminal className="h-5 w-5 text-primary" />
              SBOM Generation via CLI
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <p className="text-muted-foreground">
              SBOM generation is currently available through the command-line interface. The web UI integration is planned for a future release.
            </p>

            <div className="space-y-3">
              <div>
                <p className="font-medium mb-2">Generate CycloneDX SBOM (JSON):</p>
                <div className="relative">
                  <pre className="bg-muted p-3 rounded-md text-xs overflow-x-auto">
                    lcc sbom --scan-id &lt;SCAN_ID&gt; --format cyclonedx --output sbom.json
                  </pre>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 h-6 w-6"
                    onClick={() => copyCommand("lcc sbom --scan-id <SCAN_ID> --format cyclonedx --output sbom.json", "cyclonedx")}
                  >
                    {copiedCommand === "cyclonedx" ? (
                      <CheckCircle className="h-3 w-3 text-green-600" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              </div>

              <div>
                <p className="font-medium mb-2">Generate SPDX SBOM (JSON):</p>
                <div className="relative">
                  <pre className="bg-muted p-3 rounded-md text-xs overflow-x-auto">
                    lcc sbom --scan-id &lt;SCAN_ID&gt; --format spdx --output sbom.spdx.json
                  </pre>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 h-6 w-6"
                    onClick={() => copyCommand("lcc sbom --scan-id <SCAN_ID> --format spdx --output sbom.spdx.json", "spdx")}
                  >
                    {copiedCommand === "spdx" ? (
                      <CheckCircle className="h-3 w-3 text-green-600" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              </div>

              <div>
                <p className="font-medium mb-2">Generate SPDX SBOM (Tag-Value format):</p>
                <div className="relative">
                  <pre className="bg-muted p-3 rounded-md text-xs overflow-x-auto">
                    lcc sbom --scan-id &lt;SCAN_ID&gt; --format spdx --output-format tag-value --output sbom.spdx
                  </pre>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 h-6 w-6"
                    onClick={() => copyCommand("lcc sbom --scan-id <SCAN_ID> --format spdx --output-format tag-value --output sbom.spdx", "spdx-tag")}
                  >
                    {copiedCommand === "spdx-tag" ? (
                      <CheckCircle className="h-3 w-3 text-green-600" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t">
              <p className="font-medium mb-2">Available Options:</p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-2">
                <li><code className="bg-muted px-1 py-0.5 rounded">--format</code>: Choose <code className="bg-muted px-1 py-0.5 rounded">cyclonedx</code> or <code className="bg-muted px-1 py-0.5 rounded">spdx</code></li>
                <li><code className="bg-muted px-1 py-0.5 rounded">--output-format</code>: Choose <code className="bg-muted px-1 py-0.5 rounded">json</code>, <code className="bg-muted px-1 py-0.5 rounded">xml</code>, <code className="bg-muted px-1 py-0.5 rounded">yaml</code>, or <code className="bg-muted px-1 py-0.5 rounded">tag-value</code></li>
                <li><code className="bg-muted px-1 py-0.5 rounded">--project-name</code>: Specify project name</li>
                <li><code className="bg-muted px-1 py-0.5 rounded">--project-version</code>: Specify project version</li>
                <li><code className="bg-muted px-1 py-0.5 rounded">--author</code>: Specify document author</li>
                <li><code className="bg-muted px-1 py-0.5 rounded">--supplier</code>: Specify component supplier</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Available Scans */}
        <Card>
          <CardHeader>
            <CardTitle>Available Scans for SBOM Generation</CardTitle>
            <CardDescription>
              Copy the scan ID from the table below and use it in the CLI commands above
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : !scans || scans.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <FileText className="h-12 w-12 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  No scans available. Create a scan first to generate SBOMs.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Scan ID</TableHead>
                    <TableHead>Project</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scans.map((scan) => (
                    <TableRow key={scan.id}>
                      <TableCell className="font-mono text-xs">
                        <div className="flex items-center gap-2">
                          {scan.id}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => copyCommand(scan.id, scan.id)}
                          >
                            {copiedCommand === scan.id ? (
                              <CheckCircle className="h-3 w-3 text-green-600" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">{scan.project}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            scan.status === "completed"
                              ? "default"
                              : scan.status === "failed"
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {scan.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(scan.generatedAt).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/scans/${scan.id}`}>View Scan</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* What is SBOM Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-5 w-5 text-primary" />
              About Software Bill of Materials (SBOM)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              A Software Bill of Materials (SBOM) is a formal, structured list of all components, libraries, and modules in a software application.
            </p>
            <div className="space-y-2">
              <p className="font-medium text-foreground">Why SBOMs Matter:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>
                  <strong>Security:</strong> Identify vulnerable components quickly during security incidents
                </li>
                <li>
                  <strong>Compliance:</strong> Meet regulatory requirements (e.g., Executive Order 14028, NTIA guidelines)
                </li>
                <li>
                  <strong>License Management:</strong> Track open source licenses and ensure compliance
                </li>
                <li>
                  <strong>Supply Chain:</strong> Provide transparency about software composition
                </li>
              </ul>
            </div>
            <div className="space-y-2 pt-2">
              <p className="font-medium text-foreground">Supported Formats:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>
                  <strong>CycloneDX:</strong> Modern SBOM standard optimized for security use cases, supports multiple output formats
                </li>
                <li>
                  <strong>SPDX:</strong> ISO/IEC standard (ISO/IEC 5962:2021) for software package data exchange
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </ContentLayout>
  );
}
