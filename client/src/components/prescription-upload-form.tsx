import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Upload, Loader2 } from "lucide-react";
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
import { insertPrescriptionSchema, type Customer } from "@shared/schema";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface PrescriptionUploadFormProps {
  onSuccess?: () => void;
}

export function PrescriptionUploadForm({
  onSuccess,
}: PrescriptionUploadFormProps) {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isOcrProcessing, setIsOcrProcessing] = useState(false);
  const { toast } = useToast();

  const { data: customers } = useQuery<Customer[]>({
    queryKey: ["/api/customers"],
  });

  const form = useForm({
    resolver: zodResolver(insertPrescriptionSchema),
    defaultValues: {
      customerId: "",
      doctorName: "",
      doctorLicense: "",
      prescriptionDate: new Date().toISOString().split("T")[0],
      notes: "",
    },
  });

  const mutation = useMutation({
    mutationFn: async (data: any) => {
      // First upload the image if present
      if (imageFile) {
        const formData = new FormData();
        formData.append("image", imageFile);
        formData.append("prescriptionData", JSON.stringify(data));

        const response = await fetch("/api/prescriptions/upload", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const error = await response.text();
          throw new Error(error || "Upload failed");
        }

        return response.json();
      } else {
        return apiRequest("POST", "/api/prescriptions", data);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/prescriptions"] });
      toast({ title: "Prescription uploaded successfully" });
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

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
        className="space-y-4"
      >
        <div className="border-2 border-dashed rounded-lg p-6 text-center">
          <input
            type="file"
            accept="image/*"
            onChange={handleImageChange}
            className="hidden"
            id="prescription-image"
            data-testid="input-prescription-image"
          />
          {imagePreview ? (
            <div className="space-y-3">
              <img
                src={imagePreview}
                alt="Preview"
                className="max-h-64 mx-auto rounded"
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setImageFile(null);
                  setImagePreview(null);
                }}
              >
                Change Image
              </Button>
            </div>
          ) : (
            <label
              htmlFor="prescription-image"
              className="cursor-pointer block"
            >
              <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-2 text-sm text-muted-foreground">
                Click to upload prescription image
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                AI will extract text automatically
              </p>
            </label>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="customerId"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Customer</FormLabel>
                <Select
                  onValueChange={field.onChange}
                  defaultValue={field.value || ""}
                >
                  <FormControl>
                    <SelectTrigger data-testid="select-customer">
                      <SelectValue placeholder="Select customer" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {customers?.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id}>
                        {customer.firstName} {customer.lastName}
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
            name="prescriptionDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Prescription Date *</FormLabel>
                <FormControl>
                  <Input {...field} type="date" data-testid="input-date" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="doctorName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Doctor Name</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    value={field.value || ""}
                    data-testid="input-doctor-name"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="doctorLicense"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Doctor License</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    value={field.value || ""}
                    data-testid="input-doctor-license"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Notes</FormLabel>
              <FormControl>
                <Textarea
                  {...field}
                  value={field.value || ""}
                  placeholder="Additional notes..."
                  data-testid="input-notes"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-3">
          <Button
            type="submit"
            disabled={mutation.isPending || isOcrProcessing}
            data-testid="button-submit-prescription"
          >
            {mutation.isPending || isOcrProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isOcrProcessing ? "Processing OCR..." : "Uploading..."}
              </>
            ) : (
              "Upload Prescription"
            )}
          </Button>
        </div>
      </form>
    </Form>
  );
}
