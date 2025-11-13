import { sql, relations } from "drizzle-orm";
import {
  pgTable,
  varchar,
  text,
  integer,
  decimal,
  timestamp,
  pgEnum,
  boolean,
  date,
  jsonb,
} from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Enums
export const drugFormEnum = pgEnum("drug_form", [
  "tablet",
  "capsule",
  "syrup",
  "injection",
  "cream",
  "ointment",
  "drops",
  "inhaler",
  "powder",
  "other",
]);

export const strengthUnitEnum = pgEnum("strength_unit", [
  "mg",
  "g",
  "ml",
  "mcg",
  "iu",
  "percentage",
]);

export const paymentMethodEnum = pgEnum("payment_method", [
  "cash",
  "card",
  "insurance",
  "mobile_payment",
]);

export const prescriptionStatusEnum = pgEnum("prescription_status", [
  "pending",
  "processing",
  "dispensed",
  "cancelled",
]);

export const batchStatusEnum = pgEnum("batch_status", [
  "active",
  "low_stock",
  "expired",
  "recalled",
]);

// Categories table
export const categories = pgTable("categories", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: varchar("name", { length: 255 }).notNull().unique(),
  description: text("description"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Suppliers table
export const suppliers = pgTable("suppliers", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: varchar("name", { length: 255 }).notNull(),
  contactPerson: varchar("contact_person", { length: 255 }),
  email: varchar("email", { length: 255 }),
  phone: varchar("phone", { length: 50 }),
  address: text("address"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Drugs table
export const drugs = pgTable("drugs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: varchar("name", { length: 255 }).notNull(),
  genericName: varchar("generic_name", { length: 255 }),
  manufacturer: varchar("manufacturer", { length: 255 }),
  form: drugFormEnum("form").notNull(),
  strength: decimal("strength", { precision: 10, scale: 2 }),
  strengthUnit: strengthUnitEnum("strength_unit"),
  categoryId: varchar("category_id").references(() => categories.id),
  supplierId: varchar("supplier_id").references(() => suppliers.id),
  description: text("description"),
  usageInstructions: text("usage_instructions"),
  sideEffects: text("side_effects"),
  contraindications: text("contraindications"),
  price: decimal("price", { precision: 10, scale: 2 }).notNull(),
  reorderLevel: integer("reorder_level").default(10),
  barcode: varchar("barcode", { length: 100 }),
  imageUrl: varchar("image_url", { length: 500 }),
  createdAt: timestamp("created_at").defaultNow(),
});

// Inventory batches table
export const inventoryBatches = pgTable("inventory_batches", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  drugId: varchar("drug_id")
    .references(() => drugs.id)
    .notNull(),
  lotNumber: varchar("lot_number", { length: 100 }).notNull(),
  quantityOnHand: integer("quantity_on_hand").notNull().default(0),
  expiryDate: date("expiry_date").notNull(),
  purchaseDate: date("purchase_date"),
  costPrice: decimal("cost_price", { precision: 10, scale: 2 }),
  status: batchStatusEnum("status").default("active"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Customers table
export const customers = pgTable("customers", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  firstName: varchar("first_name", { length: 255 }).notNull(),
  lastName: varchar("last_name", { length: 255 }).notNull(),
  email: varchar("email", { length: 255 }),
  phone: varchar("phone", { length: 50 }),
  address: text("address"),
  dateOfBirth: date("date_of_birth"),
  allergies: text("allergies"),
  medicalConditions: text("medical_conditions"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Prescriptions table
export const prescriptions = pgTable("prescriptions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  customerId: varchar("customer_id").references(() => customers.id),
  doctorName: varchar("doctor_name", { length: 255 }),
  doctorLicense: varchar("doctor_license", { length: 100 }),
  prescriptionDate: date("prescription_date").notNull(),
  imageUrl: varchar("image_url", { length: 500 }),
  ocrText: text("ocr_text"),
  status: prescriptionStatusEnum("status").default("pending"),
  notes: text("notes"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Prescription items table
export const prescriptionItems = pgTable("prescription_items", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  prescriptionId: varchar("prescription_id")
    .references(() => prescriptions.id)
    .notNull(),
  drugId: varchar("drug_id").references(() => drugs.id),
  quantity: integer("quantity").notNull(),
  dosage: varchar("dosage", { length: 255 }),
  frequency: varchar("frequency", { length: 255 }),
  duration: varchar("duration", { length: 255 }),
  dispensed: boolean("dispensed").default(false),
});

// Sales orders table
export const salesOrders = pgTable("sales_orders", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  customerId: varchar("customer_id").references(() => customers.id),
  prescriptionId: varchar("prescription_id").references(() => prescriptions.id),
  saleDate: timestamp("sale_date").defaultNow(),
  subtotal: decimal("subtotal", { precision: 10, scale: 2 }).notNull(),
  tax: decimal("tax", { precision: 10, scale: 2 }).default("0"),
  discount: decimal("discount", { precision: 10, scale: 2 }).default("0"),
  total: decimal("total", { precision: 10, scale: 2 }).notNull(),
  paymentMethod: paymentMethodEnum("payment_method").notNull(),
  notes: text("notes"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Sales line items table
export const salesLineItems = pgTable("sales_line_items", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  salesOrderId: varchar("sales_order_id")
    .references(() => salesOrders.id)
    .notNull(),
  drugId: varchar("drug_id")
    .references(() => drugs.id)
    .notNull(),
  batchId: varchar("batch_id").references(() => inventoryBatches.id),
  quantity: integer("quantity").notNull(),
  unitPrice: decimal("unit_price", { precision: 10, scale: 2 }).notNull(),
  lineTotal: decimal("line_total", { precision: 10, scale: 2 }).notNull(),
});

// AI Chat sessions table
export const aiChatSessions = pgTable("ai_chat_sessions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  title: varchar("title", { length: 255 }).default("New Conversation"),
  createdAt: timestamp("created_at").defaultNow(),
});

// AI Chat messages table
export const aiChatMessages = pgTable("ai_chat_messages", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  sessionId: varchar("session_id")
    .references(() => aiChatSessions.id)
    .notNull(),
  role: varchar("role", { length: 50 }).notNull(), // 'user' or 'assistant'
  content: text("content").notNull(),
  timestamp: timestamp("timestamp").defaultNow(),
});

// Purchase orders table
export const purchaseOrders = pgTable("purchase_orders", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  supplierId: varchar("supplier_id")
    .references(() => suppliers.id)
    .notNull(),
  orderDate: date("order_date").notNull(),
  expectedDelivery: date("expected_delivery"),
  status: varchar("status", { length: 50 }).default("pending"), // pending, received, cancelled
  totalAmount: decimal("total_amount", { precision: 10, scale: 2 }),
  notes: text("notes"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Purchase order items table
export const purchaseOrderItems = pgTable("purchase_order_items", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  purchaseOrderId: varchar("purchase_order_id")
    .references(() => purchaseOrders.id)
    .notNull(),
  drugId: varchar("drug_id")
    .references(() => drugs.id)
    .notNull(),
  quantity: integer("quantity").notNull(),
  unitCost: decimal("unit_cost", { precision: 10, scale: 2 }).notNull(),
  lineTotal: decimal("line_total", { precision: 10, scale: 2 }).notNull(),
});

// Demand forecasts table
export const demandForecasts = pgTable("demand_forecasts", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  drugId: varchar("drug_id")
    .references(() => drugs.id)
    .notNull(),
  forecastDate: date("forecast_date").notNull(),
  forecastedUnits: integer("forecasted_units").notNull(),
  confidenceLevel: decimal("confidence_level", { precision: 5, scale: 2 }),
  model: varchar("model", { length: 100 }).default("simple_average"),
  horizon: integer("horizon").default(30), // days
  historicalData: jsonb("historical_data"),
  createdAt: timestamp("created_at").defaultNow(),
});

// Relations
export const categoriesRelations = relations(categories, ({ many }) => ({
  drugs: many(drugs),
}));

export const suppliersRelations = relations(suppliers, ({ many }) => ({
  drugs: many(drugs),
  purchaseOrders: many(purchaseOrders),
}));

export const drugsRelations = relations(drugs, ({ one, many }) => ({
  category: one(categories, {
    fields: [drugs.categoryId],
    references: [categories.id],
  }),
  supplier: one(suppliers, {
    fields: [drugs.supplierId],
    references: [suppliers.id],
  }),
  inventoryBatches: many(inventoryBatches),
  prescriptionItems: many(prescriptionItems),
  salesLineItems: many(salesLineItems),
  purchaseOrderItems: many(purchaseOrderItems),
  forecasts: many(demandForecasts),
}));

export const inventoryBatchesRelations = relations(
  inventoryBatches,
  ({ one, many }) => ({
    drug: one(drugs, {
      fields: [inventoryBatches.drugId],
      references: [drugs.id],
    }),
    salesLineItems: many(salesLineItems),
  }),
);

export const customersRelations = relations(customers, ({ many }) => ({
  prescriptions: many(prescriptions),
  salesOrders: many(salesOrders),
}));

export const prescriptionsRelations = relations(
  prescriptions,
  ({ one, many }) => ({
    customer: one(customers, {
      fields: [prescriptions.customerId],
      references: [customers.id],
    }),
    items: many(prescriptionItems),
    salesOrders: many(salesOrders),
  }),
);

export const prescriptionItemsRelations = relations(
  prescriptionItems,
  ({ one }) => ({
    prescription: one(prescriptions, {
      fields: [prescriptionItems.prescriptionId],
      references: [prescriptions.id],
    }),
    drug: one(drugs, {
      fields: [prescriptionItems.drugId],
      references: [drugs.id],
    }),
  }),
);

export const salesOrdersRelations = relations(salesOrders, ({ one, many }) => ({
  customer: one(customers, {
    fields: [salesOrders.customerId],
    references: [customers.id],
  }),
  prescription: one(prescriptions, {
    fields: [salesOrders.prescriptionId],
    references: [prescriptions.id],
  }),
  lineItems: many(salesLineItems),
}));

export const salesLineItemsRelations = relations(salesLineItems, ({ one }) => ({
  salesOrder: one(salesOrders, {
    fields: [salesLineItems.salesOrderId],
    references: [salesOrders.id],
  }),
  drug: one(drugs, {
    fields: [salesLineItems.drugId],
    references: [drugs.id],
  }),
  batch: one(inventoryBatches, {
    fields: [salesLineItems.batchId],
    references: [inventoryBatches.id],
  }),
}));

export const aiChatSessionsRelations = relations(
  aiChatSessions,
  ({ many }) => ({
    messages: many(aiChatMessages),
  }),
);

export const aiChatMessagesRelations = relations(aiChatMessages, ({ one }) => ({
  session: one(aiChatSessions, {
    fields: [aiChatMessages.sessionId],
    references: [aiChatSessions.id],
  }),
}));

export const purchaseOrdersRelations = relations(
  purchaseOrders,
  ({ one, many }) => ({
    supplier: one(suppliers, {
      fields: [purchaseOrders.supplierId],
      references: [suppliers.id],
    }),
    items: many(purchaseOrderItems),
  }),
);

export const purchaseOrderItemsRelations = relations(
  purchaseOrderItems,
  ({ one }) => ({
    purchaseOrder: one(purchaseOrders, {
      fields: [purchaseOrderItems.purchaseOrderId],
      references: [purchaseOrders.id],
    }),
    drug: one(drugs, {
      fields: [purchaseOrderItems.drugId],
      references: [drugs.id],
    }),
  }),
);

export const demandForecastsRelations = relations(
  demandForecasts,
  ({ one }) => ({
    drug: one(drugs, {
      fields: [demandForecasts.drugId],
      references: [drugs.id],
    }),
  }),
);

// Insert and Select schemas
export const insertCategorySchema = createInsertSchema(categories).omit({
  id: true,
  createdAt: true,
});
export const insertSupplierSchema = createInsertSchema(suppliers).omit({
  id: true,
  createdAt: true,
});
export const insertDrugSchema = createInsertSchema(drugs).omit({
  id: true,
  createdAt: true,
});
export const insertInventoryBatchSchema = createInsertSchema(
  inventoryBatches,
).omit({ id: true, createdAt: true });
export const insertCustomerSchema = createInsertSchema(customers).omit({
  id: true,
  createdAt: true,
});
export const insertPrescriptionSchema = createInsertSchema(prescriptions).omit({
  id: true,
  createdAt: true,
});
export const insertPrescriptionItemSchema = createInsertSchema(
  prescriptionItems,
).omit({ id: true });
export const insertSalesOrderSchema = createInsertSchema(salesOrders).omit({
  id: true,
  createdAt: true,
});
export const insertSalesLineItemSchema = createInsertSchema(
  salesLineItems,
).omit({ id: true });
export const insertAiChatSessionSchema = createInsertSchema(
  aiChatSessions,
).omit({ id: true, createdAt: true });
export const insertAiChatMessageSchema = createInsertSchema(
  aiChatMessages,
).omit({ id: true, timestamp: true });
export const insertPurchaseOrderSchema = createInsertSchema(
  purchaseOrders,
).omit({ id: true, createdAt: true });
export const insertPurchaseOrderItemSchema = createInsertSchema(
  purchaseOrderItems,
).omit({ id: true });
export const insertDemandForecastSchema = createInsertSchema(
  demandForecasts,
).omit({ id: true, createdAt: true });

// Types
export type Category = typeof categories.$inferSelect;
export type InsertCategory = z.infer<typeof insertCategorySchema>;
export type Supplier = typeof suppliers.$inferSelect;
export type InsertSupplier = z.infer<typeof insertSupplierSchema>;
export type Drug = typeof drugs.$inferSelect;
export type InsertDrug = z.infer<typeof insertDrugSchema>;
export type InventoryBatch = typeof inventoryBatches.$inferSelect;
export type InsertInventoryBatch = z.infer<typeof insertInventoryBatchSchema>;
export type Customer = typeof customers.$inferSelect;
export type InsertCustomer = z.infer<typeof insertCustomerSchema>;
export type Prescription = typeof prescriptions.$inferSelect;
export type InsertPrescription = z.infer<typeof insertPrescriptionSchema>;
export type PrescriptionItem = typeof prescriptionItems.$inferSelect;
export type InsertPrescriptionItem = z.infer<
  typeof insertPrescriptionItemSchema
>;
export type SalesOrder = typeof salesOrders.$inferSelect;
export type InsertSalesOrder = z.infer<typeof insertSalesOrderSchema>;
export type SalesLineItem = typeof salesLineItems.$inferSelect;
export type InsertSalesLineItem = z.infer<typeof insertSalesLineItemSchema>;
export type AiChatSession = typeof aiChatSessions.$inferSelect;
export type InsertAiChatSession = z.infer<typeof insertAiChatSessionSchema>;
export type AiChatMessage = typeof aiChatMessages.$inferSelect;
export type InsertAiChatMessage = z.infer<typeof insertAiChatMessageSchema>;
export type PurchaseOrder = typeof purchaseOrders.$inferSelect;
export type InsertPurchaseOrder = z.infer<typeof insertPurchaseOrderSchema>;
export type PurchaseOrderItem = typeof purchaseOrderItems.$inferSelect;
export type InsertPurchaseOrderItem = z.infer<
  typeof insertPurchaseOrderItemSchema
>;
export type DemandForecast = typeof demandForecasts.$inferSelect;
export type InsertDemandForecast = z.infer<typeof insertDemandForecastSchema>;

// Composite types for frontend
export type DrugWithDetails = Drug & {
  category?: Category;
  supplier?: Supplier;
  totalStock?: number;
  nearestExpiry?: string;
};

export type SalesOrderWithDetails = SalesOrder & {
  customer?: Customer;
  lineItems?: (SalesLineItem & { drug?: Drug })[];
};

export type PrescriptionWithDetails = Prescription & {
  customer?: Customer;
  items?: (PrescriptionItem & { drug?: Drug })[];
};
