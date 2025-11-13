import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Package, DollarSign } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Bar, BarChart, XAxis, YAxis, CartesianGrid } from "recharts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function Analytics() {
  const { data: topDrugs, isLoading: topLoading } = useQuery({
    queryKey: ["/api/analytics/top-drugs"],
  });

  const { data: categoryAnalytics, isLoading: categoryLoading } = useQuery({
    queryKey: ["/api/analytics/by-category"],
  });

  const { data: revenueData, isLoading: revenueLoading } = useQuery({
    queryKey: ["/api/analytics/revenue"],
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold" data-testid="title-analytics">
          Analytics & Insights
        </h1>
        <p className="text-sm text-muted-foreground">
          Sales trends, forecasts, and performance metrics
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Revenue (30d)
            </CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold" data-testid="metric-revenue">
              {revenueLoading ? (
                <Skeleton className="h-8 w-32" />
              ) : (
                `$${revenueData?.total?.toFixed(2) || "0.00"}`
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Products Sold (30d)
            </CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold" data-testid="metric-products-sold">
              {revenueLoading ? (
                <Skeleton className="h-8 w-32" />
              ) : (
                revenueData?.productsSold || 0
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Avg. Transaction
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold" data-testid="metric-avg-transaction">
              {revenueLoading ? (
                <Skeleton className="h-8 w-32" />
              ) : (
                `$${revenueData?.avgTransaction?.toFixed(2) || "0.00"}`
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Sales by Category</CardTitle>
          </CardHeader>
          <CardContent>
            {categoryLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : categoryAnalytics && categoryAnalytics.length > 0 ? (
              <ChartContainer
                config={{
                  sales: {
                    label: "Sales",
                    color: "hsl(var(--chart-1))",
                  },
                }}
                className="h-64"
              >
                <BarChart data={categoryAnalytics}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" />
                  <YAxis />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="sales" fill="var(--color-sales)" />
                </BarChart>
              </ChartContainer>
            ) : (
              <div className="flex h-64 items-center justify-center text-muted-foreground">
                No category data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Selling Drugs</CardTitle>
          </CardHeader>
          <CardContent>
            {topLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : topDrugs && topDrugs.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Drug</TableHead>
                    <TableHead>Units Sold</TableHead>
                    <TableHead>Revenue</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topDrugs.map((drug: any, idx: number) => (
                    <TableRow key={idx} data-testid={`top-drug-${idx}`}>
                      <TableCell className="font-medium">
                        {drug.drugName}
                      </TableCell>
                      <TableCell className="font-mono">
                        {drug.unitsSold}
                      </TableCell>
                      <TableCell className="font-mono">
                        ${drug.revenue.toFixed(2)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="flex h-64 items-center justify-center text-muted-foreground">
                No sales data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
