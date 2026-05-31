import uuid
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, Optional

# ==========================================
# 1. Enums and Exceptions
# ==========================================

class Role(Enum):
    ADMIN = auto()
    MANAGER = auto()
    VIEWER = auto()

class TransactionType(Enum):
    ADD = auto()
    REMOVE = auto()
    TRANSFER = auto()
    RETURN = auto()
    DAMAGE = auto()

class Category(Enum):
    ELECTRONICS = auto()
    CLOTHING = auto()
    GROCERY = auto()

class InventoryError(Exception):
    """Base class for inventory exceptions."""
    pass

class UnauthorizedAccessError(InventoryError):
    pass

class InsufficientStockError(InventoryError):
    pass

class ProductNotFoundError(InventoryError):
    pass

# ==========================================
# 2. Core Entities
# ==========================================

@dataclass(slots=True)
class User:
    user_id: str
    name: str
    role: Role

@dataclass(slots=True)
class Product:
    sku: str
    name: str
    price: float
    category: Category
    threshold: int  # Minimum stock level before alert triggers

@dataclass(slots=True)
class TransactionRecord:
    transaction_id: str
    timestamp: datetime
    type: TransactionType
    sku: str
    quantity: int
    user_id: str
    from_warehouse_id: Optional[str] = None
    to_warehouse_id: Optional[str] = None

# ==========================================
# 3. Interfaces (Protocols) & Subsystems
# ==========================================

class AlertObserver(Protocol):
    def on_low_stock(self, product: Product, warehouse_id: str, current_stock: int) -> None:
        ...

class ReplenishmentStrategy(Protocol):
    def calculate_restock_amount(self, product: Product, current_stock: int) -> int:
        ...

class EmailAlertSystem:
    """Concrete implementation of AlertObserver."""
    def on_low_stock(self, product: Product, warehouse_id: str, current_stock: int) -> None:
        print(f"🚨 ALERT: Low stock for {product.name} (SKU: {product.sku}) in Warehouse {warehouse_id}. "
              f"Current stock: {current_stock}, Threshold: {product.threshold}.")

class StandardReplenishment:
    """Concrete strategy for restocking."""
    def calculate_restock_amount(self, product: Product, current_stock: int) -> int:
        # Standard logic: order twice the threshold amount if below threshold
        return max(0, (product.threshold * 2) - current_stock)

class AuditTrail:
    """Manages the history of all inventory movements."""
    def __init__(self) -> None:
        self._logs: list[TransactionRecord] = []

    def record(self, txn: TransactionRecord) -> None:
        self._logs.append(txn)
        print(f"📝 AUDIT: {txn.type.name} | SKU: {txn.sku} | Qty: {txn.quantity} | By: {txn.user_id}")

    def get_history(self) -> list[TransactionRecord]:
        return self._logs

# ==========================================
# 4. Warehouse & Inventory Management
# ==========================================

class Warehouse:
    def __init__(self, warehouse_id: str, location: str):
        self.warehouse_id = warehouse_id
        self.location = location
        # Mapping of SKU -> Quantity
        self._inventory: dict[str, int] = {}

    def get_stock(self, sku: str) -> int:
        return self._inventory.get(sku, 0)

    def add_stock(self, sku: str, quantity: int) -> None:
        self._inventory[sku] = self.get_stock(sku) + quantity

    def remove_stock(self, sku: str, quantity: int) -> None:
        current_stock = self.get_stock(sku)
        if current_stock < quantity:
            raise InsufficientStockError(f"Cannot remove {quantity}. Only {current_stock} available.")
        self._inventory[sku] -= quantity

class InventoryManager:
    """Facade for managing the entire inventory system."""
    
    def __init__(self, audit_trail: AuditTrail):
        self.products: dict[str, Product] = {}
        self.warehouses: dict[str, Warehouse] = {}
        self.audit_trail = audit_trail
        self.alert_observers: list[AlertObserver] = []
        
    def add_observer(self, observer: AlertObserver) -> None:
        self.alert_observers.append(observer)

    def register_product(self, product: Product) -> None:
        self.products[product.sku] = product

    def add_warehouse(self, warehouse: Warehouse) -> None:
        self.warehouses[warehouse.warehouse_id] = warehouse

    def _check_permission(self, user: User, required_roles: list[Role]) -> None:
        if user.role not in required_roles:
            raise UnauthorizedAccessError(f"User {user.name} lacks permissions.")

    def _check_thresholds(self, sku: str, warehouse_id: str) -> None:
        product = self.products.get(sku)
        warehouse = self.warehouses.get(warehouse_id)
        if not product or not warehouse:
            return
            
        current_stock = warehouse.get_stock(sku)
        if current_stock <= product.threshold:
            for observer in self.alert_observers:
                observer.on_low_stock(product, warehouse_id, current_stock)

    def receive_stock(self, user: User, sku: str, warehouse_id: str, quantity: int, is_return: bool = False) -> None:
        self._check_permission(user, [Role.ADMIN, Role.MANAGER])
        if sku not in self.products:
            raise ProductNotFoundError(f"SKU {sku} not found.")
            
        warehouse = self.warehouses[warehouse_id]
        warehouse.add_stock(sku, quantity)
        
        txn_type = TransactionType.RETURN if is_return else TransactionType.ADD
        txn = TransactionRecord(
            transaction_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            type=txn_type,
            sku=sku,
            quantity=quantity,
            user_id=user.user_id,
            to_warehouse_id=warehouse_id
        )
        self.audit_trail.record(txn)

    def ship_stock(self, user: User, sku: str, warehouse_id: str, quantity: int, is_damage: bool = False) -> None:
        self._check_permission(user, [Role.ADMIN, Role.MANAGER])
        warehouse = self.warehouses[warehouse_id]
        
        warehouse.remove_stock(sku, quantity)
        
        txn_type = TransactionType.DAMAGE if is_damage else TransactionType.REMOVE
        txn = TransactionRecord(
            transaction_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            type=txn_type,
            sku=sku,
            quantity=quantity,
            user_id=user.user_id,
            from_warehouse_id=warehouse_id
        )
        self.audit_trail.record(txn)
        self._check_thresholds(sku, warehouse_id)

    def transfer_stock(self, user: User, sku: str, from_w_id: str, to_w_id: str, quantity: int) -> None:
        self._check_permission(user, [Role.ADMIN, Role.MANAGER])
        
        # Atomicity is simulated here. In a real DB, this would be a transaction block.
        self.warehouses[from_w_id].remove_stock(sku, quantity)
        self.warehouses[to_w_id].add_stock(sku, quantity)
        
        txn = TransactionRecord(
            transaction_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            type=TransactionType.TRANSFER,
            sku=sku,
            quantity=quantity,
            user_id=user.user_id,
            from_warehouse_id=from_w_id,
            to_warehouse_id=to_w_id
        )
        self.audit_trail.record(txn)
        self._check_thresholds(sku, from_w_id)

    def search_inventory(self, category: Optional[Category] = None) -> list[dict]:
        """Simple reporting/filtering capability."""
        report = []
        for sku, product in self.products.items():
            if category and product.category != category:
                continue
            total_qty = sum(w.get_stock(sku) for w in self.warehouses.values())
            report.append({
                "SKU": sku,
                "Name": product.name,
                "Category": product.category.name,
                "TotalStock": total_qty
            })
        return report

# ==========================================
# 5. Example Execution Flow
# ==========================================
if __name__ == "__main__":
    # 1. System Setup
    audit_system = AuditTrail()
    inventory_system = InventoryManager(audit_system)
    
    # Register Observers (Alerts)
    email_alerts = EmailAlertSystem()
    inventory_system.add_observer(email_alerts)

    # Setup Users
    admin_user = User(user_id="U1", name="Alice", role=Role.ADMIN)
    viewer_user = User(user_id="U2", name="Bob", role=Role.VIEWER)

    # Setup Warehouses
    ny_warehouse = Warehouse(warehouse_id="WH-NY", location="New York")
    la_warehouse = Warehouse(warehouse_id="WH-LA", location="Los Angeles")
    inventory_system.add_warehouse(ny_warehouse)
    inventory_system.add_warehouse(la_warehouse)

    # Register Products
    laptop = Product(sku="MAC-01", name="MacBook Pro", price=1999.99, category=Category.ELECTRONICS, threshold=10)
    inventory_system.register_product(laptop)

    # 2. Operations
    # Admin receives stock
    inventory_system.receive_stock(admin_user, sku="MAC-01", warehouse_id="WH-NY", quantity=50)
    
    # Admin transfers stock
    inventory_system.transfer_stock(admin_user, sku="MAC-01", from_w_id="WH-NY", to_w_id="WH-LA", quantity=20)
    
    # Shipping orders (simulating stock dropping below threshold)
    print("\n--- Processing Large Order ---")
    inventory_system.ship_stock(admin_user, sku="MAC-01", warehouse_id="WH-NY", quantity=25)
    
    # 3. Handling Edge Cases
    print("\n--- Handling Damaged Return ---")
    inventory_system.receive_stock(admin_user, sku="MAC-01", warehouse_id="WH-LA", quantity=1, is_return=True)
    inventory_system.ship_stock(admin_user, sku="MAC-01", warehouse_id="WH-LA", quantity=1, is_damage=True)

    # 4. Reporting
    print("\n--- Inventory Report ---")
    report = inventory_system.search_inventory(category=Category.ELECTRONICS)
    for row in report:
        print(row)