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
