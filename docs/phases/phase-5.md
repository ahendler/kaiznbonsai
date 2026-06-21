# Phase 5: Inventory Management UI

## Objective

Build the application shell and the inventory management interface. By the end of this phase, an authenticated user can view, create, edit, and delete products, and manage their stock batches — all communicating with the Phase 4 API.

## 1. Application Shell

The shell is the persistent layout that wraps all authenticated content. It is rendered once and does not unmount between page navigations.

### Header (top bar)

- **Left:** KaiznBonsai brand icon/logo. Clicking it navigates to the root (`/`).
- **Centre:** Empty in Phase 5.
- **Right:**
  - Bell icon — inert in Phase 5, scaffolded for future notifications.
  - User avatar/initials button — opens an account actions menu: Profile, Logout.
- **Burger menu icon (left of logo):** Toggles the navigation drawer.

### Navigation Drawer (burger menu)

Opens from the left side of the screen as an overlay. Contains:

- **Products** — navigates to `/inventory/products`.
- **History** — placeholder link, wired up in Phase 6.
- **Settings** — placeholder link for account preferences.

The currently active route is visually highlighted in the drawer.

### JPT Panel (AI Assistant trigger)

A vertically centred floating button fixed to the **left edge** of the viewport. Clicking it opens a left-side drawer.

- In Phase 5, the drawer contains only a placeholder: a chat-bubble illustration and a "Coming soon" message.
- The JPT button is always visible regardless of which section is active.
- Full functionality is implemented in Phase 12.

### Main Content Area

The central region rendered between the header and the viewport bottom. Renders a different view based on the active route:

- `/` → Dashboard placeholder (a clean empty state with the KaiznBonsai logo).
- `/inventory/products` → Product Management View (see Section 2).

---

## 2. Product Management View (`/inventory/products`)

### Page Header

- Section title: "Products"
- Primary action: "+ Add Product" button, opens the Product Form Modal.

### Product Table

A sortable data table displaying all products owned by the user. Columns:

- **Name**
- **SKU**
- **Unit of Measure**
- **Total Stock** — the database-annotated aggregate. Displays a red **"Out of Stock"** badge when `total_stock == 0`.
- **Created**
- **Actions** — Edit (opens Product Form Modal pre-filled), View Stock (opens Stock Drawer), Delete (opens Delete Confirmation Modal).

**Loading state:** Skeleton rows while TanStack Query is fetching.
**Empty state:** Illustration + "Add your first product" CTA when the list is empty.
**Search/filter bar:** Filter visible rows by name or SKU (client-side on the fetched list).
**Pagination:** Infinite scrolling implemented via a "Load More" intersection observer (see Section 8).

---

## 3. Product Form Modal (Create & Edit)

A Mantine `Modal` with a controlled form. Validation is handled entirely via **Mantine Form's built-in validation** to minimize dependencies while ensuring UX. 

**Form definition:**

```ts
const form = useForm({
  initialValues: {
    name: "",
    sku: "",
    unit_of_measure: "UNIT",
    description: "",
  },
  validate: {
    name: isNotEmpty("Name is a required field."),
    sku: isNotEmpty("SKU is a required field."),
    unit_of_measure: isNotEmpty("Unit of measure is a required field."),
  },
});
```

Fields:

- `name` — required text input.
- `description` — optional textarea.
- `sku` — required text input. Shows inline error if the API returns a duplicate-SKU validation error.
- `unit_of_measure` — required `Select` from the fixed choices (KG, G, L, ML, UNIT).

On submit:

- **Create:** `POST /api/v1/inventory/products/` → on success, invalidates `['products']` query, closes modal, shows success toast.
- **Edit:** `PATCH /api/v1/inventory/products/<id>/` → on success, same invalidation.

Error feedback is displayed at the field level. Mantine native errors surface before the API is called; API errors (e.g. duplicate SKU) are mapped back into the form's error state using `form.setErrors()` after the request.

---

## 4. Delete Confirmation Modal

Triggered from the product table's Delete action. The modal behaviour depends on the product's `total_stock` value (already available in the list query):

| State              | Modal behaviour                                                                                                             |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `total_stock > 0`  | Shows a warning: "This product has active stock batches. Remove all stock before deleting." Confirm button is **disabled**. |
| `total_stock == 0` | Shows a standard "Are you sure?" confirmation. Confirm button sends `DELETE /products/<id>/`.                               |

On successful delete, invalidates `['products']` cache and shows success toast.

---

## 5. Stock Drawer (per Product)

Opens from the Product row's "View Stock" action as a Mantine `Drawer` from the right side. Shows context for the selected product (name, SKU) in the drawer header.

### Batch List

A table of all `Stock` batches for this product. Columns:

- **Lot Code**
- **Best Before**
- **Initial Qty**
- **Current Qty**
- **Unit Cost**
- **Actions:** Edit (inline quantity correction), Delete.

**Empty state:** "No stock batches yet" + "Add Batch" CTA.

### Add Batch Form

A collapsible section at the top of the drawer. Fields:

- `lot_code` — optional text input.
- `best_before` — optional date picker.
- `initial_quantity` — required decimal input (also sets `current_quantity` on first submit).
- `unit_cost` — required decimal input.

On submit: `POST /api/v1/inventory/stocks/` → invalidates `['stocks', productId]` and `['products']` (so `total_stock` updates in the table behind the drawer).

### Edit Batch

A compact inline edit form (PATCH) to correct batch details (lot code, initial quantity, cost, dates).
- Validation (Frontend & Backend): `initial_quantity` cannot be edited if the batch is partially or fully consumed (`current_quantity < initial_quantity`). `current_quantity` is read-only.

### Delete Batch

Sends `DELETE /api/v1/inventory/stocks/<id>/`. Shows a confirmation step.
- Validation (Frontend & Backend): Deletion is completely blocked in the UI, and rejected by the API (`409 Conflict`), if the batch has been consumed (`current_quantity < initial_quantity`).
On success, invalidates both `['stocks', productId]` and `['products']`.

---

## 6. Notifications

All mutating operations (create, update, delete) provide feedback via **Mantine `notifications`**:

- **Success:** Green toast with a contextual message (e.g. "Product created", "Batch deleted").
- **Error:** Red toast with the first error message from the API response.

---

## 7. TanStack Query Key Strategy

| Key                        | Scope                                                  |
| -------------------------- | ------------------------------------------------------ |
| `['products', 'infinite']` | All products for the user, managed via infinite scroll |
| `['product', id]`          | Single product detail                                  |
| `['stocks', productId]`    | All stock batches for a specific product               |

Mutations always invalidate the relevant keys so the UI reflects the latest server state without a full page reload. By using `useInfiniteQuery`, cache invalidation will seamlessly refetch the active pages.

---

## 8. Server-side Cursor Pagination & Infinite Scroll

**Backend:** We configure DRF `CursorPagination` with an `ordering` (e.g. `-created_at`) instead of standard offset/limit pagination. This avoids OFFSET performance penalties on large datasets and is the modern standard for feeds. The API response:

```json
{
  "next": "http://api/products/?cursor=cj1...",
  "previous": null,
  "results": [...]
}
```

**Frontend:** Instead of standard `Pagination` components, the frontend uses TanStack's `useInfiniteQuery`. A hidden div at the bottom of the table uses an `IntersectionObserver` (via Mantine Hooks `useIntersection`) to automatically call `fetchNextPage()` when the user scrolls near the bottom.

This provides a premium "infinite scroll" UX that is optimized for data-heavy views.

---

## 9. Validation Strategy

We use **Mantine Form's built-in validation functions** (`isNotEmpty`, `matches`) to achieve robust client-side validation with zero extra dependencies, minimizing our bundle size and complexity.

API errors are mapped back into the form state (`form.setErrors()`), so field-level errors from both client constraints and server constraints (like SKU uniqueness) are displayed in the exact same location.

---

## 10. Acceptance Criteria

- [ ] Application shell renders correctly: header, nav drawer, JPT button placeholder.
- [ ] Navigation from burger menu routes to `/inventory/products`.
- [ ] Product table fetches and displays products with `total_stock`.
- [ ] Table implements infinite scrolling with `CursorPagination` and `useInfiniteQuery`.
- [ ] Skeleton loader renders while products are being initially fetched.
- [ ] Empty state renders when no products exist.
- [ ] Product form validates client-side using Mantine's native `isNotEmpty` before submitting.
- [ ] Product create form submits and table refreshes.
- [ ] Product edit form pre-fills with existing data and submits a PATCH.
- [ ] API field errors (e.g. duplicate SKU) are mapped back into the form state.
- [ ] Delete modal shows warning and disabled confirm when `total_stock > 0`.
- [ ] Delete modal sends DELETE and removes the product when `total_stock == 0`.
- [ ] Stock drawer opens and lists all batches for a product.
- [ ] Add batch form uses native validation before submitting.
- [ ] Add batch form submits and the drawer list + product `total_stock` both refresh.
- [ ] Edit batch inline form supports all fields except current quantity.
- [ ] Edit batch disables initial quantity edit if consumed.
- [ ] Delete batch removes the row and updates `total_stock` in the background table.
- [ ] Delete batch action is hidden/blocked if the batch is consumed.
- [ ] All mutations show success or error toasts.
- [ ] JPT drawer button opens a left-side drawer with a placeholder UI.
