import { useQuery } from "@tanstack/react-query";
import {
  Package,
  DollarSign,
  AlertTriangle,
  TrendingUp,
  Calendar,
} from "lucide-react";
import { StatsCard } from "@/components/stats-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Line, LineChart, XAxis, YAxis, CartesianGrid } from "recharts";

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["/api/analytics/dashboard-stats"],
  });

  const { data: salesTrend, isLoading: trendLoading } = useQuery({
    queryKey: ["/api/analytics/sales-trend"],
  });

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ["/api/alerts"],
  });

  if (statsLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold" data-testid="title-dashboard">
          Dashboard
        </h1>
        <p className="text-sm text-muted-foreground">
          Overview of your pharmacy operations
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Drugs"
          value={stats?.totalDrugs || 0}
          icon={Package}
          testId="stat-total-drugs"
        />
        <StatsCard
          title="Today's Sales"
          value={`$${stats?.todaySales?.toFixed(2) || "0.00"}`}
          icon={DollarSign}
          trend={stats?.salesTrend}
          trendUp={stats?.salesTrendUp}
          testId="stat-today-sales"
        />
        <StatsCard
          title="Low Stock Items"
          value={stats?.lowStockCount || 0}
          icon={AlertTriangle}
          testId="stat-low-stock"
        />
        <StatsCard
          title="Expiring Soon"
          value={stats?.expiringSoon || 0}
          icon={Calendar}
          testId="stat-expiring-soon"
        />
      </div>

      {!alertsLoading && alerts && alerts.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Alerts</h2>
          <div className="space-y-2">
            {alerts.slice(0, 3).map((alert: any) => (
              <Alert
                key={alert.id}
                variant={alert.severity === "critical" ? "destructive" : "default"}
                data-testid={`alert-${alert.id}`}
              >
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>{alert.title}</AlertTitle>
                <AlertDescription>{alert.message}</AlertDescription>
              </Alert>
            ))}
          </div>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Sales Trend (Last 7 Days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {trendLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : salesTrend && salesTrend.length > 0 ? (
            <ChartContainer
              config={{
                sales: {
                  label: "Sales",
                  color: "hsl(var(--chart-1))",
                },
              }}
              className="h-64"
            >
              <LineChart data={salesTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Line
                  type="monotone"
                  dataKey="sales"
                  stroke="var(--color-sales)"
                  strokeWidth={2}
                />
              </LineChart>
            </ChartContainer>
          ) : (
            <div className="flex h-64 items-center justify-center text-muted-foreground">
              No sales data available
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
