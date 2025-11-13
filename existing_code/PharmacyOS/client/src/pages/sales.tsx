import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { ShoppingCart, Plus, Minus, Trash2, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import type { DrugWithDetails, Customer } from "@shared/schema";
import { Separator } from "@/components/ui/separator";

interface CartItem {
  drug: DrugWithDetails;
  quantity: number;
}

export default function Sales() {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [search, setSearch] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<string>("cash");
  const { toast } = useToast();

  const { data: drugs } = useQuery<DrugWithDetails[]>({
    queryKey: ["/api/drugs"],
  });

  const { data: customers } = useQuery<Customer[]>({
    queryKey: ["/api/customers"],
  });

  const checkoutMutation = useMutation({
    mutationFn: (data: any) => apiRequest("POST", "/api/sales", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/sales"] });
      queryClient.invalidateQueries({ queryKey: ["/api/analytics/dashboard-stats"] });
      toast({ title: "Sale completed successfully" });
      setCart([]);
      setCustomerId("");
      setPaymentMethod("cash");
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const filteredDrugs = drugs?.filter(
    (drug) =>
      drug.name.toLowerCase().includes(search.toLowerCase()) &&
      !cart.find((item) => item.drug.id === drug.id)
  );

  const addToCart = (drug: DrugWithDetails) => {
    setCart([...cart, { drug, quantity: 1 }]);
  };

  const updateQuantity = (drugId: string, delta: number) => {
    setCart(
      cart
        .map((item) =>
          item.drug.id === drugId
            ? { ...item, quantity: Math.max(1, item.quantity + delta) }
            : item
        )
    );
  };

  const removeFromCart = (drugId: string) => {
    setCart(cart.filter((item) => item.drug.id !== drugId));
  };

  const subtotal = cart.reduce(
    (sum, item) => sum + parseFloat(item.drug.price) * item.quantity,
    0
  );
  const tax = subtotal * 0.1;
  const total = subtotal + tax;

  const handleCheckout = () => {
    if (cart.length === 0) {
      toast({
        title: "Cart is empty",
        description: "Please add items to cart before checkout",
        variant: "destructive",
      });
      return;
    }

    const saleData = {
      customerId: customerId || null,
      subtotal: subtotal.toFixed(2),
      tax: tax.toFixed(2),
      total: total.toFixed(2),
      paymentMethod,
      lineItems: cart.map((item) => ({
        drugId: item.drug.id,
        quantity: item.quantity,
        unitPrice: item.drug.price,
        lineTotal: (parseFloat(item.drug.price) * item.quantity).toFixed(2),
      })),
    };

    checkoutMutation.mutate(saleData);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold" data-testid="title-sales">
          Sales & Point of Sale
        </h1>
        <p className="text-sm text-muted-foreground">
          Process sales and manage transactions
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Product Search</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search drugs to add to cart..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="input-search-products"
                />
              </div>
              {search && filteredDrugs && filteredDrugs.length > 0 && (
                <div className="mt-4 max-h-64 overflow-y-auto space-y-2">
                  {filteredDrugs.slice(0, 5).map((drug) => (
                    <div
                      key={drug.id}
                      className="flex items-center justify-between p-3 border rounded-md hover-elevate"
                      data-testid={`product-${drug.id}`}
                    >
                      <div>
                        <p className="font-medium">{drug.name}</p>
                        <p className="text-sm text-muted-foreground">
                          ${parseFloat(drug.price).toFixed(2)}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => addToCart(drug)}
                        data-testid={`button-add-${drug.id}`}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Add
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShoppingCart className="h-5 w-5" />
                Cart ({cart.length} items)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {cart.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  Cart is empty. Search and add products to cart.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Product</TableHead>
                      <TableHead>Price</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>Total</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cart.map((item) => (
                      <TableRow
                        key={item.drug.id}
                        data-testid={`cart-item-${item.drug.id}`}
                      >
                        <TableCell className="font-medium">
                          {item.drug.name}
                        </TableCell>
                        <TableCell className="font-mono">
                          ${parseFloat(item.drug.price).toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Button
                              size="icon"
                              variant="outline"
                              className="h-7 w-7"
                              onClick={() => updateQuantity(item.drug.id, -1)}
                              data-testid={`button-decrease-${item.drug.id}`}
                            >
                              <Minus className="h-3 w-3" />
                            </Button>
                            <span
                              className="font-mono w-8 text-center"
                              data-testid={`quantity-${item.drug.id}`}
                            >
                              {item.quantity}
                            </span>
                            <Button
                              size="icon"
                              variant="outline"
                              className="h-7 w-7"
                              onClick={() => updateQuantity(item.drug.id, 1)}
                              data-testid={`button-increase-${item.drug.id}`}
                            >
                              <Plus className="h-3 w-3" />
                            </Button>
                          </div>
                        </TableCell>
                        <TableCell className="font-mono">
                          ${(parseFloat(item.drug.price) * item.quantity).toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => removeFromCart(item.drug.id)}
                            data-testid={`button-remove-${item.drug.id}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Checkout</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Customer (Optional)
                </label>
                <Select value={customerId} onValueChange={setCustomerId}>
                  <SelectTrigger data-testid="select-customer">
                    <SelectValue placeholder="Select customer" />
                  </SelectTrigger>
                  <SelectContent>
                    {customers?.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id}>
                        {customer.firstName} {customer.lastName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">
                  Payment Method *
                </label>
                <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                  <SelectTrigger data-testid="select-payment">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cash">Cash</SelectItem>
                    <SelectItem value="card">Card</SelectItem>
                    <SelectItem value="insurance">Insurance</SelectItem>
                    <SelectItem value="mobile_payment">Mobile Payment</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">Subtotal:</span>
                  <span className="font-mono" data-testid="text-subtotal">
                    ${subtotal.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Tax (10%):</span>
                  <span className="font-mono" data-testid="text-tax">
                    ${tax.toFixed(2)}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between text-lg font-semibold">
                  <span>Total:</span>
                  <span className="font-mono" data-testid="text-total">
                    ${total.toFixed(2)}
                  </span>
                </div>
              </div>

              <Button
                className="w-full"
                onClick={handleCheckout}
                disabled={cart.length === 0 || checkoutMutation.isPending}
                data-testid="button-checkout"
              >
                {checkoutMutation.isPending ? "Processing..." : "Complete Sale"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
