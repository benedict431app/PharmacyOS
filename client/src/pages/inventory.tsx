import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Plus, Search, Edit, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card } from "@/components/ui/card";
import { StockBadge } from "@/components/stock-badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { DrugForm } from "@/components/drug-form";
import { Skeleton } from "@/components/ui/skeleton";
import type { DrugWithDetails } from "@shared/schema";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

export default function Inventory() {
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDrug, setEditingDrug] = useState<DrugWithDetails | null>(null);
  const { toast } = useToast();

  const { data: drugs, isLoading } = useQuery<DrugWithDetails[]>({
    queryKey: ["/api/drugs"],
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiRequest("DELETE", `/api/drugs/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/drugs"] });
      toast({ title: "Drug deleted successfully" });
    },
  });

  const filteredDrugs = drugs?.filter((drug) =>
    drug.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleEdit = (drug: DrugWithDetails) => {
    setEditingDrug(drug);
    setDialogOpen(true);
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
    setEditingDrug(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold" data-testid="title-inventory">
            Inventory Management
          </h1>
          <p className="text-sm text-muted-foreground">
            Manage your drug inventory and stock levels
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="button-add-drug">
              <Plus className="mr-2 h-4 w-4" />
              Add Drug
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingDrug ? "Edit Drug" : "Add New Drug"}
              </DialogTitle>
            </DialogHeader>
            <DrugForm drug={editingDrug} onSuccess={handleDialogClose} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search drugs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="input-search-drugs"
          />
        </div>
      </div>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Generic Name</TableHead>
              <TableHead>Form</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Stock</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 8 }).map((_, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : filteredDrugs && filteredDrugs.length > 0 ? (
              filteredDrugs.map((drug) => (
                <TableRow key={drug.id} data-testid={`drug-row-${drug.id}`}>
                  <TableCell className="font-medium">{drug.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {drug.genericName || "-"}
                  </TableCell>
                  <TableCell className="capitalize">{drug.form}</TableCell>
                  <TableCell>{drug.category?.name || "-"}</TableCell>
                  <TableCell className="font-mono">
                    {drug.totalStock || 0}
                  </TableCell>
                  <TableCell className="font-mono">
                    ${parseFloat(drug.price).toFixed(2)}
                  </TableCell>
                  <TableCell>
                    <StockBadge
                      stock={drug.totalStock || 0}
                      reorderLevel={drug.reorderLevel || 10}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(drug)}
                        data-testid={`button-edit-${drug.id}`}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteMutation.mutate(drug.id)}
                        data-testid={`button-delete-${drug.id}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  <p className="text-muted-foreground">No drugs found</p>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
