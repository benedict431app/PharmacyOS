import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Users,
  FileText,
  Bot,
  Building2,
  TrendingUp,
  AlertCircle,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Link, useLocation } from "wouter";

const menuItems = [
  {
    title: "Dashboard",
    url: "/",
    icon: LayoutDashboard,
    testId: "nav-dashboard",
  },
  {
    title: "Inventory",
    url: "/inventory",
    icon: Package,
    testId: "nav-inventory",
  },
  {
    title: "Sales & POS",
    url: "/sales",
    icon: ShoppingCart,
    testId: "nav-sales",
  },
  {
    title: "Customers",
    url: "/customers",
    icon: Users,
    testId: "nav-customers",
  },
  {
    title: "Prescriptions",
    url: "/prescriptions",
    icon: FileText,
    testId: "nav-prescriptions",
  },
  {
    title: "AI Assistant",
    url: "/ai-assistant",
    icon: Bot,
    testId: "nav-ai",
  },
  {
    title: "Suppliers",
    url: "/suppliers",
    icon: Building2,
    testId: "nav-suppliers",
  },
  {
    title: "Analytics",
    url: "/analytics",
    icon: TrendingUp,
    testId: "nav-analytics",
  },
  {
    title: "Alerts",
    url: "/alerts",
    icon: AlertCircle,
    testId: "nav-alerts",
  },
];

export function AppSidebar() {
  const [location] = useLocation();

  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>PharmaCare</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={location === item.url}
                    data-testid={item.testId}
                  >
                    <Link href={item.url}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
