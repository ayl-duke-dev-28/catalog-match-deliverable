import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@dataclass(frozen=True)
class Product:
    catalog_id: str
    sku: str
    description: str
    active: bool


@dataclass(frozen=True)
class Order:
    customer_id: str
    customer_name: str
    order_date: str
    sku: str
    description: str
    quantity: int


def _clean_header(value: str) -> str:
    cleaned = CONTROL_RE.sub("", ANSI_RE.sub("", value or "")).strip()
    for expected in ("catalog_id", "customer_id", "customer_name", "order_date"):
        if cleaned.endswith(expected):
            return expected
    return cleaned


def _rows(path: Path) -> Iterable[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            return
        clean_names = [_clean_header(name) for name in reader.fieldnames]
        for raw in reader:
            yield {
                clean_names[index]: value.strip()
                for index, value in enumerate(raw.values())
            }


def load_catalog(path: Path) -> List[Product]:
    products: List[Product] = []
    for row in _rows(path):
        products.append(
            Product(
                catalog_id=row["catalog_id"],
                sku=row["sku"],
                description=row["catalog_description"],
                active=row.get("active", "Y").upper() == "Y",
            )
        )
    return products


def load_orders(path: Path) -> List[Order]:
    orders: List[Order] = []
    for row in _rows(path):
        try:
            quantity = int(row.get("quantity", "0") or "0")
        except ValueError:
            quantity = 0
        orders.append(
            Order(
                customer_id=row["customer_id"],
                customer_name=row["customer_name"],
                order_date=row["order_date"],
                sku=row["sku"],
                description=row["catalog_description"],
                quantity=quantity,
            )
        )
    return orders
