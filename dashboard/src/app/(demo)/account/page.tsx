"use client";

import { useQuery } from "@tanstack/react-query";
import { getUserProfile } from "@/lib/api";
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
import { User, Mail, Shield, Loader2, AlertCircle, Key } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import Link from "next/link";

export default function AccountPage() {
  const { data: profile, isLoading, error } = useQuery({
    queryKey: ["user-profile"],
    queryFn: getUserProfile,
  });

  return (
    <ContentLayout title="Account">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Account</h2>
            <p className="text-muted-foreground mt-2">
              Manage your profile and account settings
            </p>
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
                Failed to load profile. Please try again.
              </p>
            </CardContent>
          </Card>
        ) : profile ? (
          <>
            {/* Profile Information */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-primary" />
                  <CardTitle>Profile Information</CardTitle>
                </div>
                <CardDescription>
                  Your account details and role information
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-muted-foreground">
                        Username
                      </p>
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <p className="text-base font-semibold">
                          {profile.username}
                        </p>
                      </div>
                    </div>
                    <Badge variant={profile.disabled ? "destructive" : "default"}>
                      {profile.disabled ? "Disabled" : "Active"}
                    </Badge>
                  </div>
                </div>

                <Separator />

                {profile.email && (
                  <>
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-muted-foreground">
                        Email Address
                      </p>
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <p className="text-base">{profile.email}</p>
                      </div>
                    </div>
                    <Separator />
                  </>
                )}

                {profile.full_name && (
                  <>
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-muted-foreground">
                        Full Name
                      </p>
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <p className="text-base">{profile.full_name}</p>
                      </div>
                    </div>
                    <Separator />
                  </>
                )}

                <div className="space-y-1">
                  <p className="text-sm font-medium text-muted-foreground">
                    Role
                  </p>
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <Badge
                      variant={profile.role === "admin" ? "default" : "secondary"}
                      className="capitalize"
                    >
                      {profile.role}
                    </Badge>
                  </div>
                  {profile.role === "admin" && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Full access to all features and settings
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Security Settings */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  <CardTitle>Security</CardTitle>
                </div>
                <CardDescription>
                  Manage your password and authentication
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <p className="text-sm font-medium">Password</p>
                  <p className="text-sm text-muted-foreground">
                    Keep your account secure by using a strong password
                  </p>
                  <Button variant="outline" disabled>
                    Change Password
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Use CLI: <code className="bg-muted px-1 py-0.5 rounded">lcc auth change-password</code>
                  </p>
                </div>

                <Separator />

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Key className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">API Keys</p>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Create and manage API keys for programmatic access
                  </p>
                  <Button variant="outline" disabled>
                    Manage API Keys
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Use CLI: <code className="bg-muted px-1 py-0.5 rounded">lcc auth create-key --name "My Key"</code>
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Common tasks and navigation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button variant="outline" className="w-full justify-start" asChild>
                  <Link href="/settings">
                    <Shield className="mr-2 h-4 w-4" />
                    Application Settings
                  </Link>
                </Button>
                <Button variant="outline" className="w-full justify-start" asChild>
                  <Link href="/scans">
                    <User className="mr-2 h-4 w-4" />
                    View My Scans
                  </Link>
                </Button>
                <Button variant="outline" className="w-full justify-start" asChild>
                  <Link href="/policies">
                    <Shield className="mr-2 h-4 w-4" />
                    Manage Policies
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </ContentLayout>
  );
}
