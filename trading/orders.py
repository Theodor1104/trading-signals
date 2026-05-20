"""
Order management
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIAL = "partial"


@dataclass
class Order:
    """Represents a trading order"""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_quantity: float = 0
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    market: str = "stocks"
    notes: str = ""

    def fill(self, price: float, quantity: float = None):
        """Mark order as filled"""
        self.filled_price = price
        self.filled_quantity = quantity or self.quantity
        self.filled_at = datetime.now()

        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIAL

    def cancel(self):
        """Cancel the order"""
        self.status = OrderStatus.CANCELLED

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "market": self.market,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        """Create from dictionary"""
        order = cls(
            symbol=data["symbol"],
            side=OrderSide(data["side"]),
            quantity=data["quantity"],
            order_type=OrderType(data["order_type"]),
            limit_price=data.get("limit_price"),
            stop_price=data.get("stop_price"),
            market=data.get("market", "stocks"),
            notes=data.get("notes", ""),
        )
        order.order_id = data["order_id"]
        order.status = OrderStatus(data["status"])
        order.filled_price = data.get("filled_price")
        order.filled_quantity = data.get("filled_quantity", 0)
        order.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("filled_at"):
            order.filled_at = datetime.fromisoformat(data["filled_at"])
        return order
