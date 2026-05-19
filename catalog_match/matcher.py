import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .data import Order, Product


WORD_RE = re.compile(
    r"#\d+-\d+|m\d+(?:-\d+(?:\.\d+)?)?|"
    r"\d+/\d+(?:-\d+)?|\d+(?:-\d+/\d+)?(?:mm|ft|in)?|[a-z]+"
)
THREAD_RE = re.compile(r"(m\d+)-(\d+(?:\.\d+)?)|(#\d+-\d+)|(\d+/\d+)-(\d+)")
METRIC_DIAMETER_RE = re.compile(r"\bm\d+\b")
NUMBERED_DIAMETER_RE = re.compile(r"\b#\d+")
FRACTION_DIAMETER_RE = re.compile(r"\b\d+/\d+")
LENGTH_AFTER_X_RE = re.compile(
    r"\bx\s*(\d+(?:-\d+/\d+)?|\d+/\d+)(?:\s*(mm|millimeter|millimeters|ft|foot|feet|in|inch|inches))?"
)
UNIT_LENGTH_RE = re.compile(r"\b(\d+(?:-\d+/\d+)?|\d+/\d+)\s*(mm|millimeter|millimeters|ft|foot|feet|in|inch|inches)\b")

MATERIALS = {"steel", "brass", "alloy", "stainless", "316", "18-8", "a2"}
FINISHES = {"zinc", "plain", "black", "oxide", "yellow", "hdg", "galvanized"}
SOFT_HISTORY_WORDS = {"same", "again", "last", "previous", "reorder"}

PHRASE_REPLACEMENTS: Sequence[Tuple[re.Pattern, str]] = (
    (re.compile(r"\bshcs\b"), "socket head cap screw"),
    (re.compile(r"\bbhcs\b"), "button socket cap screw"),
    (re.compile(r"\bhhb\b"), "hex head bolt"),
    (re.compile(r"\bhcs\b"), "hex cap screw"),
    (re.compile(r"\bhx\s+hd\b"), "hex head"),
    (re.compile(r"\bhx\b"), "hex"),
    (re.compile(r"\bhd\b"), "head"),
    (re.compile(r"\bsoc\b"), "socket"),
    (re.compile(r"\bscr\b"), "screw"),
    (re.compile(r"\bbtn\b"), "button"),
    (re.compile(r"\bwshr\b"), "washer"),
    (re.compile(r"\bmach\b"), "machine"),
    (re.compile(r"\bphil\b"), "phillips"),
    (re.compile(r"\bzn\b|\bzc\b"), "zinc"),
    (re.compile(r"\byel\b"), "yellow"),
    (re.compile(r"\bpln\b"), "plain"),
    (re.compile(r"\bss\b"), "stainless steel"),
    (re.compile(r"\bhot dip galvanized\b"), "hdg galvanized"),
)


@dataclass(frozen=True)
class ProductIndex:
    product: Product
    normalized: str
    tokens: Counter
    token_set: Set[str]
    product_type: str
    diameter: str
    thread: str
    length: str
    materials: Set[str]
    finishes: Set[str]
    vector: Dict[str, float] = field(default_factory=dict)
    norm: float = 1.0


@dataclass(frozen=True)
class CustomerProfile:
    customer_id: str
    customer_name: str
    order_count: int
    skus: Counter
    product_types: Counter
    diameters: Counter
    threads: Counter
    materials: Counter
    finishes: Counter


def normalize_text(value: str) -> str:
    text = value.lower()
    text = text.replace('"', " in ")
    text = text.replace("'", " ft ")
    text = re.sub(r"(\d)\s*x\s*(\d|#|m)", r"\1 x \2", text)
    text = re.sub(r"([a-z])(\d)", r"\1\2", text)
    for pattern, replacement in PHRASE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    text = text.replace("full thread rod", "threaded rod full thread rod")
    text = text.replace("thread rod", "threaded rod")
    text = text.replace("hex head bolt", "hex cap screw hex head bolt")
    text = re.sub(r"\bmillimeters?\b", "mm", text)
    text = re.sub(r"\bfeet\b|\bfoot\b", "ft", text)
    text = re.sub(r"\binches\b|\binch\b", "in", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens_for(value: str) -> Counter:
    normalized = normalize_text(value)
    tokens = WORD_RE.findall(normalized)
    joined: List[str] = []
    for index in range(len(tokens) - 1):
        joined.append(tokens[index] + "_" + tokens[index + 1])
    for index in range(len(tokens) - 2):
        joined.append(tokens[index] + "_" + tokens[index + 1] + "_" + tokens[index + 2])
    return Counter(tokens + joined)


def product_type_for(text: str) -> str:
    if "hex nut" in text:
        return "hex nut"
    if "lock washer" in text:
        return "lock washer"
    if "flat washer" in text:
        return "flat washer"
    if "washer" in text:
        return "washer"
    if "threaded rod" in text or "full thread rod" in text:
        return "threaded rod"
    if "lag screw" in text:
        return "lag screw"
    if "tap bolt" in text:
        return "tap bolt"
    if "button socket cap screw" in text or "button head cap screw" in text:
        return "button socket cap screw"
    if "socket head cap screw" in text:
        return "socket head cap screw"
    if "phillips pan machine screw" in text or "pan machine screw" in text:
        return "phillips pan machine screw"
    if "hex cap screw" in text or "hex head bolt" in text:
        return "hex cap screw"
    if "screw" in text:
        return "screw"
    if "bolt" in text:
        return "bolt"
    return ""


def _thread(text: str) -> str:
    match = THREAD_RE.search(text)
    if not match:
        return ""
    if match.group(1) and match.group(2):
        return f"{match.group(1)}-{match.group(2)}"
    if match.group(3):
        return match.group(3)
    return f"{match.group(4)}-{match.group(5)}"


def _diameter(text: str) -> str:
    thread = _thread(text)
    if thread:
        if thread.startswith("m"):
            return thread.split("-", 1)[0]
        if thread.startswith("#"):
            return thread.split("-", 1)[0]
        return thread.split("-", 1)[0]
    for pattern in (METRIC_DIAMETER_RE, NUMBERED_DIAMETER_RE, FRACTION_DIAMETER_RE):
        match = pattern.search(text)
        if match:
            return match.group(0)
    return ""


def _canonical_length(value: str, unit: Optional[str]) -> str:
    unit = unit or "in"
    if unit in {"inch", "inches"}:
        unit = "in"
    if unit in {"foot", "feet"}:
        unit = "ft"
    if unit in {"millimeter", "millimeters"}:
        unit = "mm"
    return f"{value}{unit}"


def _length(text: str, diameter: str) -> str:
    match = LENGTH_AFTER_X_RE.search(text)
    if match:
        return _canonical_length(match.group(1), match.group(2))
    matches = UNIT_LENGTH_RE.findall(text)
    for value, unit in matches:
        candidate = _canonical_length(value, unit)
        if not diameter or not candidate.startswith(diameter):
            return candidate
    return ""


def _attributes(tokens: Iterable[str], allowed: Set[str]) -> Set[str]:
    return {token for token in tokens if token in allowed}


def _index_product(product: Product) -> ProductIndex:
    normalized = normalize_text(product.description)
    tokens = tokens_for(product.description)
    token_set = set(tokens)
    diameter = _diameter(normalized)
    return ProductIndex(
        product=product,
        normalized=normalized,
        tokens=tokens,
        token_set=token_set,
        product_type=product_type_for(normalized),
        diameter=diameter,
        thread=_thread(normalized),
        length=_length(normalized, diameter),
        materials=_attributes(token_set, MATERIALS),
        finishes=_attributes(token_set, FINISHES),
    )


def _cosine(a: Dict[str, float], a_norm: float, b: Dict[str, float], b_norm: float) -> float:
    if not a_norm or not b_norm:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(token, 0.0) for token, weight in a.items()) / (a_norm * b_norm)


class CatalogMatcher:
    def __init__(self, products: Sequence[Product], orders: Sequence[Order]):
        self.products = [_index_product(product) for product in products if product.active]
        self.product_by_sku = {item.product.sku: item for item in self.products}
        self.idf = self._build_idf(self.products)
        self.products = [self._with_vector(item) for item in self.products]
        self.orders = list(orders)
        self.customers = self._build_customers()

    @staticmethod
    def _build_idf(products: Sequence[ProductIndex]) -> Dict[str, float]:
        df: Counter = Counter()
        for item in products:
            df.update(item.token_set)
        total = max(len(products), 1)
        return {
            token: math.log((1 + total) / (1 + count)) + 1.0
            for token, count in df.items()
        }

    def _vector(self, tokens: Counter) -> Tuple[Dict[str, float], float]:
        vector = {
            token: count * self.idf.get(token, 1.0)
            for token, count in tokens.items()
        }
        norm = math.sqrt(sum(weight * weight for weight in vector.values()))
        return vector, norm

    def _with_vector(self, item: ProductIndex) -> ProductIndex:
        vector, norm = self._vector(item.tokens)
        return ProductIndex(
            product=item.product,
            normalized=item.normalized,
            tokens=item.tokens,
            token_set=item.token_set,
            product_type=item.product_type,
            diameter=item.diameter,
            thread=item.thread,
            length=item.length,
            materials=item.materials,
            finishes=item.finishes,
            vector=vector,
            norm=norm,
        )

    def _build_customers(self) -> Dict[str, CustomerProfile]:
        grouped: Dict[str, List[Order]] = defaultdict(list)
        for order in self.orders:
            grouped[order.customer_id].append(order)

        profiles: Dict[str, CustomerProfile] = {}
        today = date.today()
        for customer_id, orders in grouped.items():
            skus: Counter = Counter()
            product_types: Counter = Counter()
            diameters: Counter = Counter()
            threads: Counter = Counter()
            materials: Counter = Counter()
            finishes: Counter = Counter()
            customer_name = orders[0].customer_name

            for order in orders:
                item = self.product_by_sku.get(order.sku) or _index_product(
                    Product("", order.sku, order.description, True)
                )
                try:
                    ordered_on = date.fromisoformat(order.order_date)
                    days_old = max((today - ordered_on).days, 0)
                except ValueError:
                    days_old = 365
                recency = 1.0 / (1.0 + days_old / 180.0)
                quantity_weight = 1.0 + min(order.quantity, 2000) / 2000.0
                weight = recency * quantity_weight
                skus[item.product.sku] += weight
                if item.product_type:
                    product_types[item.product_type] += weight
                if item.diameter:
                    diameters[item.diameter] += weight
                if item.thread:
                    threads[item.thread] += weight
                materials.update({token: weight for token in item.materials})
                finishes.update({token: weight for token in item.finishes})

            profiles[customer_id] = CustomerProfile(
                customer_id=customer_id,
                customer_name=customer_name,
                order_count=len(orders),
                skus=skus,
                product_types=product_types,
                diameters=diameters,
                threads=threads,
                materials=materials,
                finishes=finishes,
            )
        return profiles

    def customer_options(self) -> List[Dict]:
        return [
            {
                "customer_id": profile.customer_id,
                "customer_name": profile.customer_name,
                "order_count": profile.order_count,
            }
            for profile in sorted(self.customers.values(), key=lambda item: item.customer_id)
        ]

    def match(self, query: str, customer_id: Optional[str] = None, limit: int = 3) -> Dict:
        query_tokens = tokens_for(query)
        query_vector, query_norm = self._vector(query_tokens)
        query_normalized = normalize_text(query)
        query_type = product_type_for(query_normalized)
        query_diameter = _diameter(query_normalized)
        query_thread = _thread(query_normalized)
        query_length = _length(query_normalized, query_diameter)
        query_materials = _attributes(query_tokens, MATERIALS)
        query_finishes = _attributes(query_tokens, FINISHES)
        profile = self.customers.get(customer_id or "")
        history_weight = self._history_weight(query_tokens, profile)

        scored = []
        for item in self.products:
            base, reasons = self._base_score(
                item,
                query_vector,
                query_norm,
                query_type,
                query_diameter,
                query_thread,
                query_length,
                query_materials,
                query_finishes,
            )
            personal, personal_reasons = self._personal_score(item, profile)
            final = (base * (1.0 - history_weight)) + (personal * history_weight)
            reasons.extend(personal_reasons)
            scored.append((final, base, personal, reasons, item))

        scored.sort(key=lambda row: row[0], reverse=True)
        matches = []
        for final, base, personal, reasons, item in scored[:limit]:
            matches.append(
                {
                    "catalog_id": item.product.catalog_id,
                    "sku": item.product.sku,
                    "description": item.product.description,
                    "confidence": round(max(1.0, min(final * 100.0, 99.0)), 1),
                    "base_score": round(base, 4),
                    "history_score": round(personal, 4),
                    "reasons": reasons[:5],
                }
            )

        return {
            "query": query,
            "customer": self._customer_payload(profile),
            "history_weight": round(history_weight, 2),
            "matches": matches,
        }

    def _base_score(
        self,
        item: ProductIndex,
        query_vector: Dict[str, float],
        query_norm: float,
        query_type: str,
        query_diameter: str,
        query_thread: str,
        query_length: str,
        query_materials: Set[str],
        query_finishes: Set[str],
    ) -> Tuple[float, List[str]]:
        lexical = _cosine(query_vector, query_norm, item.vector, item.norm)
        score = 0.52 * lexical
        reasons = [f"text similarity {round(lexical * 100)}%"]

        if query_type:
            if item.product_type == query_type or (query_type == "washer" and "washer" in item.product_type):
                score += 0.2
                reasons.append(f"product type: {item.product_type}")
            elif item.product_type:
                score -= 0.16

        if query_diameter:
            if item.diameter == query_diameter:
                score += 0.16
                reasons.append(f"diameter: {item.diameter}")
            else:
                score -= 0.12
        if query_thread:
            if item.thread == query_thread:
                score += 0.1
                reasons.append(f"thread: {item.thread}")
            else:
                score -= 0.06
        if query_length:
            if item.length == query_length:
                score += 0.16
                reasons.append(f"length: {item.length}")
            else:
                score -= 0.08

        attr_hits = sorted((query_materials & item.materials) | (query_finishes & item.finishes))
        if attr_hits:
            score += min(len(attr_hits) * 0.035, 0.12)
            reasons.append("attributes: " + ", ".join(attr_hits))

        return max(0.0, min(score, 1.0)), reasons

    @staticmethod
    def _counter_ratio(counter: Counter, key: str) -> float:
        if not key or not counter:
            return 0.0
        max_value = max(counter.values()) or 1.0
        return float(counter.get(key, 0.0)) / float(max_value)

    def _personal_score(self, item: ProductIndex, profile: Optional[CustomerProfile]) -> Tuple[float, List[str]]:
        if not profile:
            return 0.0, []

        score = 0.0
        reasons: List[str] = []
        sku_ratio = self._counter_ratio(profile.skus, item.product.sku)
        if sku_ratio:
            score += 0.5 * sku_ratio
            reasons.append("customer bought this SKU before")

        type_ratio = self._counter_ratio(profile.product_types, item.product_type)
        if type_ratio:
            score += 0.22 * type_ratio
            reasons.append("customer often buys this product type")

        diameter_ratio = self._counter_ratio(profile.diameters, item.diameter)
        if diameter_ratio:
            score += 0.12 * diameter_ratio
            reasons.append("customer history favors this size")

        material_ratio = max((self._counter_ratio(profile.materials, token) for token in item.materials), default=0.0)
        finish_ratio = max((self._counter_ratio(profile.finishes, token) for token in item.finishes), default=0.0)
        if material_ratio or finish_ratio:
            score += 0.08 * max(material_ratio, finish_ratio)
            reasons.append("customer history favors similar materials/finishes")

        return min(score, 1.0), reasons

    @staticmethod
    def _history_weight(query_tokens: Counter, profile: Optional[CustomerProfile]) -> float:
        if not profile:
            return 0.0
        token_set = set(query_tokens)
        if token_set & SOFT_HISTORY_WORDS:
            return 0.42
        if len([token for token in token_set if "_" not in token]) <= 3:
            return 0.28
        return 0.16

    @staticmethod
    def _customer_payload(profile: Optional[CustomerProfile]) -> Optional[Dict]:
        if not profile:
            return None
        return {
            "customer_id": profile.customer_id,
            "customer_name": profile.customer_name,
            "order_count": profile.order_count,
        }

