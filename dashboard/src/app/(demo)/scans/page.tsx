"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getScans, createScan, getPolicies } from "@/lib/api";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ScanSearch,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

export default function ScansPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [projectName, setProjectName] = useState("");
  const [selectedPolicy, setSelectedPolicy] = useState("");
  const queryClient = useQueryClient();

  const { data: scans, isLoading, error } = useQuery({
    queryKey: ["scans"],
    queryFn: getScans,
    retry: 1,
    refetchInterval: 30000,
  });

  const { data: policies, error: policiesError } = useQuery({
    queryKey: ["policies"],
    queryFn: getPolicies,
    retry: 1,
    // Don't show error, just use empty array if policies fail to load
    onError: (error) => {
      console.error("Failed to load policies:", error);
    },
  });

  const createScanMutation = useMutation({
    mutationFn: (data: { repoUrl: string; projectName: string; policy?: string }) => {
      return createScan(data.repoUrl, data.policy, data.projectName);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      setIsDialogOpen(false);
      setRepoUrl("");
      setProjectName("");
      setSelectedPolicy("");
      toast.success("Scan created successfully! The repository will be cloned and scanned.");
    },
    onError: (error: any) => {
      console.error("Scan creation error:", error);

      // Handle different error formats
      let errorMsg = "Failed to create scan";

      if (error.response?.data) {
        const data = error.response.data;

        // Handle Pydantic validation errors (422)
        if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map((err: any) => err.msg).join(", ");
        } else if (typeof data.detail === 'string') {
          errorMsg = data.detail;
        } else if (data.message) {
          errorMsg = data.message;
        }
      }

      toast.error(errorMsg);
    },
  });

  const handleCreateScan = () => {
    if (!repoUrl.trim()) {
      toast.error("Please enter a GitHub repository URL");
      return;
    }

    // Validate GitHub URL format
    const githubUrlPattern = /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+/;
    if (!githubUrlPattern.test(repoUrl)) {
      toast.error("Please enter a valid GitHub repository URL");
      return;
    }

    // Extract project name from URL if not provided
    let finalProjectName = projectName.trim();
    if (!finalProjectName) {
      const match = repoUrl.match(/github\.com\/([\w-]+)\/([\w.-]+)/);
      if (match) {
        finalProjectName = match[2].replace(/\.git$/, "");
      }
    }

    // Note: Currently scans /workspace, GitHub cloning to be implemented in backend
    createScanMutation.mutate({
      repoUrl: repoUrl.trim(),
      projectName: finalProjectName,
      policy: selectedPolicy === "none" ? undefined : selectedPolicy,
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return (
          <Badge variant="default" className="bg-green-500">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            Completed
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="destructive">
            <XCircle className="mr-1 h-3 w-3" />
            Failed
          </Badge>
        );
      case "running":
        return (
          <Badge variant="secondary">
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            Running
          </Badge>
        );
      default:
        return (
          <Badge variant="outline">
            <Clock className="mr-1 h-3 w-3" />
            {status}
          </Badge>
        );
    }
  };

  return (
    <ContentLayout title="Scans">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Scan History</h2>
            <p className="text-muted-foreground mt-2">
              View and manage all compliance scans across your projects
            </p>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <ScanSearch className="mr-2 h-4 w-4" />
                New Scan
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px]">
              <DialogHeader>
                <DialogTitle>Scan GitHub Repository</DialogTitle>
                <DialogDescription>
                  Enter a GitHub repository URL to clone and scan for license compliance issues.
                  The repository will be automatically cloned, scanned, and cleaned up.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="repoUrl">GitHub Repository URL *</Label>
                  <Input
                    id="repoUrl"
                    placeholder="https://github.com/username/repository"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    disabled={createScanMutation.isPending}
                  />
                  <p className="text-xs text-muted-foreground">
                    Enter the full GitHub repository URL (e.g., https://github.com/torvalds/linux)
                  </p>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="projectName">Project Name (Optional)</Label>
                  <Input
                    id="projectName"
                    placeholder="my-project"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    disabled={createScanMutation.isPending}
                  />
                  <p className="text-xs text-muted-foreground">
                    Optional: Custom project name (defaults to repository name)
                  </p>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="policy">Compliance Policy (Optional)</Label>
                  <Select
                    value={selectedPolicy}
                    onValueChange={setSelectedPolicy}
                    disabled={createScanMutation.isPending}
                  >
                    <SelectTrigger id="policy">
                      <SelectValue placeholder="Select a policy" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No Policy</SelectItem>
                      {policies?.map((policy: any) => (
                        <SelectItem key={policy.name} value={policy.name}>
                          {policy.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Optional: Evaluate against a specific compliance policy
                  </p>
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsDialogOpen(false)}
                  disabled={createScanMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateScan}
                  disabled={createScanMutation.isPending}
                >
                  {createScanMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <ScanSearch className="mr-2 h-4 w-4" />
                      Create Scan
                    </>
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Recent Scans</CardTitle>
            <CardDescription>
              All automated and manual scans with their compliance status
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <AlertCircle className="h-12 w-12 text-destructive" />
                <p className="text-sm text-muted-foreground">
                  Failed to load scans. Make sure the backend API is running.
                </p>
              </div>
            ) : !scans || scans.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <ScanSearch className="h-12 w-12 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  No scans found. Create your first scan to get started.
                </p>
                <Button onClick={() => setIsDialogOpen(true)}>
                  <ScanSearch className="mr-2 h-4 w-4" />
                  Create First Scan
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Scan ID</TableHead>
                    <TableHead>Project</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Violations</TableHead>
                    <TableHead>Warnings</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scans.map((scan: any) => (
                    <TableRow key={scan.id}>
                      <TableCell className="font-mono text-xs">
                        {scan.id.substring(0, 8)}
                      </TableCell>
                      <TableCell className="font-medium">
                        {scan.project || "Unknown"}
                      </TableCell>
                      <TableCell>{getStatusBadge(scan.status)}</TableCell>
                      <TableCell>
                        <span className="text-destructive font-medium">
                          {scan.violations || 0}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="text-yellow-500 font-medium">
                          {scan.warnings || 0}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(scan.generatedAt).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm" asChild>
                          <Link href={`/scans/${scan.id}`}>View Details</Link>
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
