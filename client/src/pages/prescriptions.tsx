import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Upload, FileText, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PrescriptionUploadForm } from "@/components/prescription-upload-form";
import type { PrescriptionWithDetails } from "@shared/schema";
import { apiRequest } from "@/lib/queryClient";

export default function Prescriptions() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewingPrescription, setViewingPrescription] =
    useState<PrescriptionWithDetails | null>(null);

  const { data: prescriptions, isLoading } = useQuery<PrescriptionWithDetails[]>(
    {
      queryKey: ["/api/prescriptions"],
    }
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case "dispensed":
        return "default";
      case "processing":
        return "outline";
      case "pending":
        return "secondary";
      case "cancelled":
        return "destructive";
      default:
        return "outline";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1
            className="text-2xl font-semibold"
            data-testid="title-prescriptions"
          >
            Prescription Management
          </h1>
          <p className="text-sm text-muted-foreground">
            Upload and manage patient prescriptions with AI-powered OCR
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="button-upload-prescription">
              <Upload className="mr-2 h-4 w-4" />
              Upload Prescription
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Upload New Prescription</DialogTitle>
            </DialogHeader>
            <PrescriptionUploadForm onSuccess={() => setDialogOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      ) : prescriptions && prescriptions.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {prescriptions.map((prescription) => (
            <Card
              key={prescription.id}
              data-testid={`prescription-card-${prescription.id}`}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base">
                    {prescription.customer
                      ? `${prescription.customer.firstName} ${prescription.customer.lastName}`
                      : "Walk-in Patient"}
                  </CardTitle>
                  <Badge variant={getStatusColor(prescription.status || "pending")}>
                    {prescription.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {prescription.doctorName && (
                  <div className="text-sm">
                    <span className="text-muted-foreground">Doctor:</span>{" "}
                    <span>{prescription.doctorName}</span>
                  </div>
                )}
                <div className="text-sm">
                  <span className="text-muted-foreground">Date:</span>{" "}
                  <span>{prescription.prescriptionDate}</span>
                </div>
                {prescription.ocrText && (
                  <div className="text-sm">
                    <p className="text-muted-foreground mb-1">OCR Extract:</p>
                    <p className="text-xs line-clamp-3 bg-muted p-2 rounded">
                      {prescription.ocrText}
                    </p>
                  </div>
                )}
                <div className="flex gap-2">
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1"
                        onClick={() => setViewingPrescription(prescription)}
                        data-testid={`button-view-${prescription.id}`}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        View
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                      <DialogHeader>
                        <DialogTitle>Prescription Details</DialogTitle>
                      </DialogHeader>
                      {viewingPrescription && (
                        <div className="space-y-4">
                          {viewingPrescription.imageUrl && (
                            <div>
                              <img
                                src={viewingPrescription.imageUrl}
                                alt="Prescription"
                                className="w-full rounded-md border"
                              />
                            </div>
                          )}
                          <div className="space-y-2">
                            <div>
                              <span className="font-medium">Patient:</span>{" "}
                              {viewingPrescription.customer
                                ? `${viewingPrescription.customer.firstName} ${viewingPrescription.customer.lastName}`
                                : "Walk-in"}
                            </div>
                            {viewingPrescription.doctorName && (
                              <div>
                                <span className="font-medium">Doctor:</span>{" "}
                                {viewingPrescription.doctorName}
                              </div>
                            )}
                            <div>
                              <span className="font-medium">Date:</span>{" "}
                              {viewingPrescription.prescriptionDate}
                            </div>
                            {viewingPrescription.ocrText && (
                              <div>
                                <span className="font-medium">OCR Text:</span>
                                <p className="text-sm bg-muted p-3 rounded mt-1 whitespace-pre-wrap">
                                  {viewingPrescription.ocrText}
                                </p>
                              </div>
                            )}
                            {viewingPrescription.notes && (
                              <div>
                                <span className="font-medium">Notes:</span>
                                <p className="text-sm mt-1">
                                  {viewingPrescription.notes}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </DialogContent>
                  </Dialog>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-12">
          <div className="text-center">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-4 text-muted-foreground">No prescriptions found</p>
          </div>
        </Card>
      )}
    </div>
  );
}
