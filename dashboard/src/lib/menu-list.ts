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

import {
  Shield,
  ScanSearch,
  FileText,
  BarChart3,
  Settings,
  FileWarning,
  Bot,
  Package,
  LayoutGrid,
  LucideIcon
} from "lucide-react";

type Submenu = {
  href: string;
  label: string;
  active?: boolean;
};

type Menu = {
  href: string;
  label: string;
  active?: boolean;
  icon: LucideIcon;
  submenus?: Submenu[];
};

type Group = {
  groupLabel: string;
  menus: Menu[];
};

export function getMenuList(pathname: string): Group[] {
  return [
    {
      groupLabel: "",
      menus: [
        {
          href: "/dashboard",
          label: "Dashboard",
          icon: LayoutGrid,
          submenus: []
        }
      ]
    },
    {
      groupLabel: "Compliance",
      menus: [
        {
          href: "/scans",
          label: "Scans",
          icon: ScanSearch,
          submenus: []
        },
        {
          href: "/policies",
          label: "Policies",
          icon: Shield,
          submenus: []
        },
        {
          href: "/violations",
          label: "Violations",
          icon: FileWarning,
          submenus: []
        }
      ]
    },
    {
      groupLabel: "AI/ML Detection",
      menus: [
        {
          href: "/ai-models",
          label: "AI Models",
          icon: Bot,
          submenus: []
        },
        {
          href: "/datasets",
          label: "Datasets",
          icon: Package,
          submenus: []
        },
        {
          href: "/compliance",
          label: "EU AI Act",
          icon: Shield,
          submenus: []
        }
      ]
    },
    {
      groupLabel: "Reports",
      menus: [
        {
          href: "/sbom",
          label: "SBOM",
          icon: FileText,
          submenus: []
        },
        {
          href: "/analytics",
          label: "Analytics",
          icon: BarChart3,
          submenus: []
        }
      ]
    },
    {
      groupLabel: "Settings",
      menus: [
        {
          href: "/settings",
          label: "Settings",
          icon: Settings,
          submenus: []
        }
      ]
    }
  ];
}
