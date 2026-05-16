"""
Unit / character class: represents the controllable agent on the map.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProductLot:
    qty: float
    origin_market_id: Optional[int] = None


@dataclass
class Unit:
    uid: int
    x: int
    y: int
    max_hp: int = 300
    capacity: int = 30

    # Runtime state
    hp: int = field(init=False)
    # raw_inv: raw harvested resources
    # prod_inv: finished products (by product_id)
    raw_inv: float = field(default=0.0, init=False)
    prod_inv: Dict[int, float] = field(default_factory=dict, init=False)
    prod_lots: Dict[int, List[ProductLot]] = field(default_factory=dict, init=False)

    # Busy system: while busy_ticks > 0 the unit ignores new commands
    busy_ticks: int = field(default=0, init=False)
    busy_action: str = field(default="", init=False)  # tag for what's completing

    state: str = field(default="idle", init=False)

    def __post_init__(self):
        self.hp = self.max_hp
        self.prod_inv = {}
        self.prod_lots = {}

    # ── Inventory helpers ──────────────────────────────────────────────────────
    @property
    def total_goods(self) -> float:
        return self.raw_inv + sum(self.prod_inv.values())

    @property
    def free_capacity(self) -> float:
        return max(0.0, self.capacity - self.total_goods)

    def _sync_product_total(self, pid: int):
        total = sum(lot.qty for lot in self.prod_lots.get(pid, []) if lot.qty > 0)
        if total > 0:
            self.prod_inv[pid] = total
        else:
            self.prod_inv.pop(pid, None)
            self.prod_lots.pop(pid, None)

    def add_product(self, pid: int, qty: float, origin_market_id: Optional[int] = None):
        if qty <= 0:
            return
        lots = self.prod_lots.setdefault(pid, [])
        if lots and lots[-1].origin_market_id == origin_market_id:
            lots[-1].qty += qty
        else:
            lots.append(ProductLot(qty=qty, origin_market_id=origin_market_id))
        self._sync_product_total(pid)

    def take_product(self, pid: int, qty: float) -> float:
        actual = self.take_sellable_product(pid, qty)
        self._sync_product_total(pid)
        return actual

    def sellable_product_qty(self, pid: int, market_id: Optional[int] = None) -> float:
        total = 0.0
        for lot in self.prod_lots.get(pid, []):
            if market_id is None or lot.origin_market_id != market_id:
                total += lot.qty
        return total

    def take_sellable_product(self, pid: int, qty: float, market_id: Optional[int] = None) -> float:
        if qty <= 0:
            return 0.0
        actual = 0.0
        remaining = qty
        new_lots: List[ProductLot] = []
        for lot in self.prod_lots.get(pid, []):
            if remaining <= 0 or (market_id is not None and lot.origin_market_id == market_id):
                if lot.qty > 0:
                    new_lots.append(lot)
                continue

            taken = min(lot.qty, remaining)
            actual += taken
            remaining -= taken
            left = lot.qty - taken
            if left > 0:
                new_lots.append(ProductLot(qty=left, origin_market_id=lot.origin_market_id))

        if new_lots:
            self.prod_lots[pid] = new_lots
        else:
            self.prod_lots.pop(pid, None)
        self._sync_product_total(pid)
        return actual

    def all_products(self) -> Dict[int, float]:
        return {pid: qty for pid, qty in self.prod_inv.items() if qty > 0}

    def clear_products(self):
        self.prod_inv.clear()
        self.prod_lots.clear()
        self.raw_inv = 0.0

    # ── Movement ───────────────────────────────────────────────────────────────
    def move(self, dx: int, dy: int, max_h: int, max_w: int) -> bool:
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < max_h and 0 <= ny < max_w:
            self.x, self.y = nx, ny
            return True
        return False
