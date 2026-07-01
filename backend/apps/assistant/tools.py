"""
Tool definitions and executor for the AI chat assistant.

Each entry in TOOL_DEFINITIONS is a JSON schema passed to the Anthropic API.
The matching private function calls the existing selector layer directly —
tenant isolation is structural (every selector takes `user`).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from apps.inventory.models import Stock
from apps.inventory import selectors as inventory_selectors
from apps.orders import selectors as order_selectors

# ---------------------------------------------------------------------------
# Tool definitions (JSON schema sent to Anthropic)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "get_overall_financials",
        "description": (
            "Returns overall revenue, COGS, gross profit, gross margin %, and current "
            "inventory value. Pass date_from / date_to (YYYY-MM-DD) to scope by "
            "movement date; omit both for all-time figures."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "format": "date",
                    "description": "Inclusive start date (YYYY-MM-DD)",
                },
                "date_to": {
                    "type": "string",
                    "format": "date",
                    "description": "Inclusive end date (YYYY-MM-DD)",
                },
            },
        },
    },
    {
        "name": "get_products_with_financials",
        "description": (
            "Returns per-product revenue, COGS, gross profit, margin %, markup on cost, "
            "quantity sold, and quantity purchased. Supports optional date range, text "
            "search, margin band filter, activity filter, and sort ordering. "
            "Returns up to `limit` products (default 20, max 50)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "format": "date"},
                "date_to": {"type": "string", "format": "date"},
                "search": {
                    "type": "string",
                    "description": "Filter by product name or SKU (case-insensitive)",
                },
                "margin_band": {
                    "type": "string",
                    "enum": ["negative", "low", "medium", "high"],
                    "description": "negative = loss; low < 20%; medium 20–40%; high >= 40%",
                },
                "activity": {
                    "type": "string",
                    "enum": ["all", "movement", "stale"],
                    "description": (
                        "all = every product; movement = had receipts or sales in period; "
                        "stale = no activity in period"
                    ),
                },
                "ordering": {
                    "type": "string",
                    "description": (
                        "Sort field. Prefix '-' for descending. "
                        "Options: revenue, cogs, profit, margin, qty_sold, qty_purchased, created_at"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Max products to return (default 20)",
                },
            },
        },
    },
    {
        "name": "get_stock_levels",
        "description": (
            "Returns current stock batches with lot code, best-before date, "
            "current quantity, unit cost, and inventory value (current_qty × unit_cost). "
            "Pass product_id (UUID) to focus on a single product; "
            "pass in_stock=true to exclude depleted batches. Returns up to 50 batches."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Filter to a single product by UUID",
                },
                "in_stock": {
                    "type": "boolean",
                    "description": "If true, exclude batches where current_quantity <= 0",
                },
            },
        },
    },
    {
        "name": "list_purchase_orders",
        "description": (
            "Returns purchase orders with their line items (product, quantity, unit cost, "
            "lot code, best-before). Optionally filter by status. Returns up to 30 orders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["DRAFT", "CONFIRMED", "CANCELLED"],
                    "description": "Filter by order status",
                },
            },
        },
    },
    {
        "name": "list_sales_orders",
        "description": (
            "Returns sales orders with their line items (product, quantity, unit price). "
            "Optionally filter by status. Returns up to 30 orders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["DRAFT", "CONFIRMED", "CANCELLED"],
                    "description": "Filter by order status",
                },
            },
        },
    },
    {
        "name": "list_stock_movements",
        "description": (
            "Returns the stock movement audit trail — receipts, sales, returns, and "
            "adjustments. Supports date range, reason filter, product filter, and text "
            "search (product name/SKU, lot code, order title). Returns up to `limit` rows "
            "(default 50, max 100)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "format": "date"},
                "date_to": {"type": "string", "format": "date"},
                "reasons": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["RECEIPT", "SALE", "RETURN", "ADJUSTMENT"],
                    },
                    "description": "Filter to specific movement reasons",
                },
                "product_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Filter to movements for a specific product",
                },
                "search": {
                    "type": "string",
                    "description": "Search product name/SKU, lot code, or order title",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Max rows to return (default 50)",
                },
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _dec(value) -> str | None:
    """Stringify Decimal for JSON serialisation. None passthrough."""
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# Executors (one per tool)
# ---------------------------------------------------------------------------

def _get_overall_financials(user, inp: dict) -> dict:
    result = inventory_selectors.get_overall_financials(
        user,
        date_from=_parse_date(inp.get("date_from")),
        date_to=_parse_date(inp.get("date_to")),
    )
    return {k: _dec(v) for k, v in result.items()}


def _get_products_with_financials(user, inp: dict) -> list[dict]:
    limit = min(int(inp.get("limit", 20)), 50)
    qs = inventory_selectors.get_products_with_financials(
        user,
        date_from=_parse_date(inp.get("date_from")),
        date_to=_parse_date(inp.get("date_to")),
        search=inp.get("search"),
        margin_band=inp.get("margin_band"),
        activity=inp.get("activity", "all"),
        ordering=inp.get("ordering", "-created_at"),
    )
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "sku": p.sku,
            "unit_of_measure": p.unit_of_measure,
            "revenue": _dec(p.revenue),
            "cogs": _dec(p.cogs),
            "profit": _dec(p.profit),
            "margin": _dec(p.margin),
            "markup_on_cost": _dec(p.markup_on_cost),
            "qty_sold": _dec(p.qty_sold),
            "qty_purchased": _dec(p.qty_purchased),
        }
        for p in qs[:limit]
    ]


def _get_stock_levels(user, inp: dict) -> list[dict]:
    qs = (
        Stock.objects.filter(user=user)
        .select_related("product")
        .order_by("product__name", "created_at")
    )
    if inp.get("product_id"):
        qs = qs.filter(product_id=inp["product_id"])
    if inp.get("in_stock"):
        qs = qs.filter(current_quantity__gt=0)

    rows = []
    for batch in qs[:50]:
        unit_cost = batch.unit_cost or Decimal("0")
        rows.append({
            "id": str(batch.id),
            "product_name": batch.product.name,
            "product_sku": batch.product.sku,
            "unit_of_measure": batch.product.unit_of_measure,
            "lot_code": batch.lot_code or None,
            "best_before": batch.best_before.isoformat() if batch.best_before else None,
            "initial_quantity": _dec(batch.initial_quantity),
            "current_quantity": _dec(batch.current_quantity),
            "unit_cost": _dec(unit_cost),
            "inventory_value": _dec(batch.current_quantity * unit_cost),
        })
    return rows


def _list_purchase_orders(user, inp: dict) -> list[dict]:
    qs = order_selectors.get_purchase_orders_for_user(user)
    if inp.get("status"):
        qs = qs.filter(status=inp["status"])

    rows = []
    for order in qs[:30]:
        order_items = list(order.items.all())
        total_cost = sum(
            item.quantity * item.unit_cost
            for item in order_items
            if item.quantity is not None and item.unit_cost is not None
        )
        rows.append({
            "id": order.id,
            "title": order.title,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "total_cost": _dec(total_cost),
            "items": [
                {
                    "product_name": item.product.name,
                    "product_sku": item.product.sku,
                    "quantity": _dec(item.quantity),
                    "unit_cost": _dec(item.unit_cost),
                    "lot_code": item.lot_code or None,
                    "best_before": item.best_before.isoformat() if item.best_before else None,
                }
                for item in order_items
            ],
        })
    return rows


def _list_sales_orders(user, inp: dict) -> list[dict]:
    qs = order_selectors.get_sales_orders_for_user(user)
    if inp.get("status"):
        qs = qs.filter(status=inp["status"])

    rows = []
    for order in qs[:30]:
        order_items = list(order.items.all())
        total_revenue = sum(
            item.quantity * item.unit_price
            for item in order_items
            if item.quantity is not None and item.unit_price is not None
        )
        rows.append({
            "id": order.id,
            "title": order.title,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "total_revenue": _dec(total_revenue),
            "items": [
                {
                    "product_name": item.product.name,
                    "product_sku": item.product.sku,
                    "quantity": _dec(item.quantity),
                    "unit_price": _dec(item.unit_price),
                }
                for item in order_items
            ],
        })
    return rows


def _list_stock_movements(user, inp: dict) -> list[dict]:
    limit = min(int(inp.get("limit", 50)), 100)
    qs = inventory_selectors.list_stock_movements(
        user,
        reasons=inp.get("reasons"),
        product_id=inp.get("product_id"),
        date_from=_parse_date(inp.get("date_from")),
        date_to=_parse_date(inp.get("date_to")),
        search=inp.get("search"),
    )
    rows = []
    for movement in qs[:limit]:
        so_item = movement.sales_order_item
        po_item = movement.purchase_order_item
        rows.append({
            "id": str(movement.id),
            "created_at": movement.created_at.isoformat(),
            "reason": movement.reason,
            "delta": _dec(movement.delta),
            "product_name": movement.stock_batch.product.name,
            "product_sku": movement.stock_batch.product.sku,
            "unit_of_measure": movement.stock_batch.product.unit_of_measure,
            "lot_code": movement.stock_batch.lot_code or None,
            "sales_order": (
                {
                    "id": so_item.order.id,
                    "title": so_item.order.title,
                    "status": so_item.order.status,
                }
                if so_item else None
            ),
            "purchase_order": (
                {
                    "id": po_item.order.id,
                    "title": po_item.order.title,
                    "status": po_item.order.status,
                }
                if po_item else None
            ),
        })
    return rows


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_EXECUTORS = {
    "get_overall_financials": _get_overall_financials,
    "get_products_with_financials": _get_products_with_financials,
    "get_stock_levels": _get_stock_levels,
    "list_purchase_orders": _list_purchase_orders,
    "list_sales_orders": _list_sales_orders,
    "list_stock_movements": _list_stock_movements,
}


def execute_tool(name: str, tool_input: dict, *, user) -> dict | list:
    executor = _EXECUTORS.get(name)
    if executor is None:
        raise ValueError(f"Unknown tool: {name!r}")
    return executor(user, tool_input)
