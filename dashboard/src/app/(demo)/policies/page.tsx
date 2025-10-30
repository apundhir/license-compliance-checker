"use client";

import { useQuery } from "@tanstack/react-query";
import { getPolicies } from "@/lib/api";
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
import { Shield, Loader2, AlertCircle, Plus, Info, HelpCircle } from "lucide-react";
import Link from "next/link";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export default function PoliciesPage() {
  const { data: policies, isLoading, error } = useQuery({
    queryKey: ["policies"],
    queryFn: getPolicies,
    retry: 1,
    refetchInterval: 30000,
  });

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase()) {
      case "high":
        return "bg-red-500";
      case "medium":
        return "bg-yellow-500";
      case "low":
        return "bg-blue-500";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <ContentLayout title="Policies">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              License Policies
            </h2>
            <p className="text-muted-foreground mt-2">
              Define and manage license compliance policies for your organization
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button disabled>
              <Plus className="mr-2 h-4 w-4" />
              New Policy
            </Button>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <HelpCircle className="h-4 w-4 text-muted-foreground" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80">
                <div className="space-y-2">
                  <h4 className="font-medium text-sm">How to add custom policies</h4>
                  <p className="text-sm text-muted-foreground">
                    Custom policies must be added as YAML files in the directory:
                  </p>
                  <code className="block bg-muted px-2 py-1 rounded text-xs">
                    ~/.lcc/policies/
                  </code>
                  <p className="text-sm text-muted-foreground">
                    See the built-in policy templates below for examples of the required structure.
                  </p>
                </div>
              </PopoverContent>
            </Popover>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 space-y-3">
              <AlertCircle className="h-12 w-12 text-destructive" />
              <p className="text-sm text-muted-foreground">
                Failed to load policies. Make sure the backend API is running.
              </p>
            </CardContent>
          </Card>
        ) : !policies || policies.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 space-y-3">
              <Shield className="h-12 w-12 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                No policies configured. Create your first policy to get started.
              </p>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create First Policy
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {policies.map((policy: any) => (
              <Card key={policy.name} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <Shield className="h-8 w-8 text-primary" />
                    <Badge className={getSeverityColor(policy.severity)}>
                      {policy.severity || "Medium"}
                    </Badge>
                  </div>
                  <CardTitle className="mt-4">{policy.name}</CardTitle>
                  <CardDescription>{policy.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">
                        Allowed Licenses
                      </p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {policy.allowed_licenses?.slice(0, 3).map((license: string) => (
                          <Badge key={license} variant="outline" className="text-xs">
                            {license}
                          </Badge>
                        ))}
                        {policy.allowed_licenses?.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{policy.allowed_licenses.length - 3} more
                          </Badge>
                        )}
                      </div>
                    </div>

                    {policy.denied_licenses && policy.denied_licenses.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">
                          Denied Licenses
                        </p>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {policy.denied_licenses.slice(0, 3).map((license: string) => (
                            <Badge
                              key={license}
                              variant="destructive"
                              className="text-xs"
                            >
                              {license}
                            </Badge>
                          ))}
                          {policy.denied_licenses.length > 3 && (
                            <Badge variant="destructive" className="text-xs">
                              +{policy.denied_licenses.length - 3} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="pt-3">
                      <Button variant="outline" size="sm" className="w-full" asChild>
                        <Link href={`/policies/${policy.name}`}>
                          View Details
                        </Link>
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ContentLayout>
  );
}
