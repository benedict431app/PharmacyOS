import { Badge } from "@/components/ui/badge";

interface StockBadgeProps {
  stock: number;
  reorderLevel: number;
}

export function StockBadge({ stock, reorderLevel }: StockBadgeProps) {
  if (stock === 0) {
    return (
      <Badge variant="destructive" className="text-xs">
        Out of Stock
      </Badge>
    );
  }

  if (stock <= reorderLevel) {
    return (
      <Badge
        variant="outline"
        className="text-xs border-warning text-warning bg-warning/10"
      >
        Low Stock
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className="text-xs border-green-600 text-green-600 dark:border-green-400 dark:text-green-400 bg-green-50 dark:bg-green-950/30"
    >
      In Stock
    </Badge>
  );
}
