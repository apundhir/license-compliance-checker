"use client";

import { useQuery } from "@tanstack/react-query";
import { getPolicy } from "@/lib/api";
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
  Shield,
  Loader2,
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function PolicyDetailPage() {
  const params = useParams();
  const policyName = params.name as string;

  const { data: policy, isLoading, error } = useQuery({
    queryKey: ["policy", policyName],
    queryFn: () => getPolicy(policyName),
    retry: 1,
  });

  return (
    <ContentLayout title="Policy Details">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" asChild>
            <Link href="/policies">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Policies
            </Link>
          </Button>
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
                Failed to load policy details. Policy may not exist or backend API is unavailable.
              </p>
            </CardContent>
          </Card>
        ) : !policy ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 space-y-3">
              <Shield className="h-12 w-12 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Policy not found.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {/* Policy Overview */}
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <Shield className="h-10 w-10 text-primary" />
                    <div>
                      <CardTitle className="text-2xl">{policy.name}</CardTitle>
                      <CardDescription className="mt-1">
                        {policy.description}
                      </CardDescription>
                    </div>
                  </div>
                  <Badge
                    variant={policy.status === "active" ? "default" : "secondary"}
                  >
                    {policy.status || "active"}
                  </Badge>
                </div>
              </CardHeader>
              {policy.disclaimer && (
                <CardContent>
                  <div className="rounded-lg bg-muted p-4">
                    <div className="flex gap-2">
                      <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-sm">Disclaimer</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          {policy.disclaimer}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>

            {/* Contexts */}
            {policy.contexts && policy.contexts.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-xl font-semibold">Policy Contexts</h3>
                <p className="text-sm text-muted-foreground">
                  Different license rules for different usage scenarios
                </p>

                {policy.contexts.map((context: any) => (
                  <Card key={context.name}>
                    <CardHeader>
                      <CardTitle className="text-lg capitalize">
                        {context.name}
                      </CardTitle>
                      {context.description && (
                        <CardDescription>{context.description}</CardDescription>
                      )}
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Allowed Licenses */}
                      {context.allow && context.allow.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <CheckCircle className="h-5 w-5 text-green-600" />
                            <h4 className="font-medium">Allowed Licenses</h4>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {context.allow.map((license: string) => (
                              <Badge
                                key={license}
                                variant="outline"
                                className="bg-green-50 text-green-700 border-green-200"
                              >
                                {license}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Denied Licenses */}
                      {context.deny && context.deny.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <XCircle className="h-5 w-5 text-red-600" />
                            <h4 className="font-medium">Denied Licenses</h4>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {context.deny.map((license: string) => (
                              <Badge
                                key={license}
                                variant="outline"
                                className="bg-red-50 text-red-700 border-red-200"
                              >
                                {license}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Review Licenses */}
                      {context.review && context.review.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <AlertTriangle className="h-5 w-5 text-yellow-600" />
                            <h4 className="font-medium">Requires Review</h4>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {context.review.map((license: string) => (
                              <Badge
                                key={license}
                                variant="outline"
                                className="bg-yellow-50 text-yellow-700 border-yellow-200"
                              >
                                {license}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Dual License Preference */}
                      {context.dualLicensePreference && (
                        <div>
                          <h4 className="font-medium mb-2">
                            Dual License Strategy
                          </h4>
                          <Badge variant="secondary">
                            {context.dualLicensePreference}
                          </Badge>
                        </div>
                      )}

                      {/* Overrides */}
                      {context.overrides &&
                        Object.keys(context.overrides).length > 0 && (
                          <div>
                            <h4 className="font-medium mb-2">
                              Component Overrides
                            </h4>
                            <div className="space-y-2">
                              {Object.entries(context.overrides).map(
                                ([component, override]: [string, any]) => (
                                  <div
                                    key={component}
                                    className="rounded-lg bg-muted p-3"
                                  >
                                    <p className="font-mono text-sm font-medium">
                                      {component}
                                    </p>
                                    {override.decision && (
                                      <p className="text-sm text-muted-foreground mt-1">
                                        Decision: {override.decision}
                                      </p>
                                    )}
                                    {override.reason && (
                                      <p className="text-sm text-muted-foreground mt-1">
                                        Reason: {override.reason}
                                      </p>
                                    )}
                                  </div>
                                )
                              )}
                            </div>
                          </div>
                        )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </ContentLayout>
  );
}
