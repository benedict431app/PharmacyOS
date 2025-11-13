import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { insertDrugSchema, type DrugWithDetails, type Category, type Supplier } from "@shared/schema";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface DrugFormProps {
  drug?: DrugWithDetails | null;
  onSuccess?: () => void;
}

export function DrugForm({ drug, onSuccess }: DrugFormProps) {
  const { toast } = useToast();

  const { data: categories } = useQuery<Category[]>({
    queryKey: ["/api/categories"],
  });

  const { data: suppliers } = useQuery<Supplier[]>({
    queryKey: ["/api/suppliers"],
  });

  const form = useForm({
    resolver: zodResolver(insertDrugSchema),
    defaultValues: {
      name: drug?.name || "",
      genericName: drug?.genericName || "",
      manufacturer: drug?.manufacturer || "",
      form: drug?.form || "tablet",
      strength: drug?.strength || "",
      strengthUnit: drug?.strengthUnit || "mg",
      categoryId: drug?.categoryId || "",
      supplierId: drug?.supplierId || "",
      description: drug?.description || "",
      usageInstructions: drug?.usageInstructions || "",
      sideEffects: drug?.sideEffects || "",
      contraindications: drug?.contraindications || "",
      price: drug?.price || "",
      reorderLevel: drug?.reorderLevel || 10,
      barcode: drug?.barcode || "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: any) => {
      if (drug) {
        return apiRequest("PATCH", `/api/drugs/${drug.id}`, data);
      }
      return apiRequest("POST", "/api/drugs", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/drugs"] });
      toast({
        title: drug ? "Drug updated successfully" : "Drug added successfully",
      });
      onSuccess?.();
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Drug Name *</FormLabel>
                <FormControl>
                  <Input {...field} data-testid="input-drug-name" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="genericName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Generic Name</FormLabel>
                <FormControl>
                  <Input {...field} value={field.value || ""} data-testid="input-generic-name" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="manufacturer"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Manufacturer</FormLabel>
                <FormControl>
                  <Input {...field} value={field.value || ""} data-testid="input-manufacturer" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="form"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Form *</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl>
                    <SelectTrigger data-testid="select-form">
                      <SelectValue placeholder="Select form" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="tablet">Tablet</SelectItem>
                    <SelectItem value="capsule">Capsule</SelectItem>
                    <SelectItem value="syrup">Syrup</SelectItem>
                    <SelectItem value="injection">Injection</SelectItem>
                    <SelectItem value="cream">Cream</SelectItem>
                    <SelectItem value="ointment">Ointment</SelectItem>
                    <SelectItem value="drops">Drops</SelectItem>
                    <SelectItem value="inhaler">Inhaler</SelectItem>
                    <SelectItem value="powder">Powder</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="strength"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Strength</FormLabel>
                <FormControl>
                  <Input {...field} value={field.value || ""} data-testid="input-strength" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="strengthUnit"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Strength Unit</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value || "mg"}>
                  <FormControl>
                    <SelectTrigger data-testid="select-strength-unit">
                      <SelectValue placeholder="Select unit" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="mg">mg</SelectItem>
                    <SelectItem value="g">g</SelectItem>
                    <SelectItem value="ml">ml</SelectItem>
                    <SelectItem value="mcg">mcg</SelectItem>
                    <SelectItem value="iu">IU</SelectItem>
                    <SelectItem value="percentage">%</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="categoryId"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Category</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value || ""}>
                  <FormControl>
                    <SelectTrigger data-testid="select-category">
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {categories?.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="supplierId"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Supplier</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value || ""}>
                  <FormControl>
                    <SelectTrigger data-testid="select-supplier">
                      <SelectValue placeholder="Select supplier" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {suppliers?.map((sup) => (
                      <SelectItem key={sup.id} value={sup.id}>
                        {sup.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="price"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Price *</FormLabel>
                <FormControl>
                  <Input {...field} type="number" step="0.01" data-testid="input-price" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="reorderLevel"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Reorder Level</FormLabel>
                <FormControl>
                  <Input {...field} type="number" data-testid="input-reorder-level" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="barcode"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Barcode</FormLabel>
                <FormControl>
                  <Input {...field} value={field.value || ""} data-testid="input-barcode" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea {...field} value={field.value || ""} data-testid="input-description" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="usageInstructions"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Usage Instructions</FormLabel>
              <FormControl>
                <Textarea {...field} value={field.value || ""} data-testid="input-usage" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="sideEffects"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Side Effects</FormLabel>
              <FormControl>
                <Textarea {...field} value={field.value || ""} data-testid="input-side-effects" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-3">
          <Button
            type="submit"
            disabled={mutation.isPending}
            data-testid="button-submit-drug"
          >
            {mutation.isPending ? "Saving..." : drug ? "Update Drug" : "Add Drug"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
