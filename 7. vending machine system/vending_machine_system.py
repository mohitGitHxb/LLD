from __future__ import annotations
import uuid
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Optional

# ==========================================
# 1. Enums and Exceptions
# ==========================================

class ProductCategory(Enum):
    BEVERAGE = auto()
    SNACK = auto()
    CANDY = auto()

class Coin(Enum):
    """Represented in cents to avoid floating-point precision issues."""
    NICKEL = 5
    DIME = 10
    QUARTER = 25
    DOLLAR_COIN = 100

class VendingMachineError(Exception): pass
class OutOfStockError(VendingMachineError): pass
class InsufficientFundsError(VendingMachineError): pass
class InvalidActionError(VendingMachineError): pass

# ==========================================
# 2. Core Entities
# ==========================================

@dataclass(slots=True)
class Product:
    sku: str
    name: str
    price_cents: int
    category: ProductCategory

@dataclass(slots=True)
class AuditLog:
    log_id: str
    timestamp: datetime
    action: str
    details: str

# ==========================================
# 3. Subsystems: Inventory & Audit
# ==========================================

class AuditTrail:
    def __init__(self) -> None:
        self._logs: list[AuditLog] = []

    def record(self, action: str, details: str) -> None:
        log = AuditLog(
            log_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=action,
            details=details
        )
        self._logs.append(log)
        print(f"📝 [AUDIT] {log.timestamp.strftime('%H:%M:%S')} | {action} | {details}")

class InventoryManager:
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.stock: dict[str, int] = {}

    def add_product(self, product: Product, quantity: int) -> None:
        self.products[product.sku] = product
        self.stock[product.sku] = self.stock.get(product.sku, 0) + quantity

    def get_product(self, sku: str) -> Product:
        if sku not in self.products:
            raise VendingMachineError(f"Product {sku} does not exist.")
        return self.products[sku]

    def get_stock(self, sku: str) -> int:
        return self.stock.get(sku, 0)

    def reduce_stock(self, sku: str) -> None:
        if self.get_stock(sku) <= 0:
            raise OutOfStockError(f"SKU {sku} is out of stock.")
        self.stock[sku] -= 1

# ==========================================
# 4. State Pattern Implementation
# ==========================================

class State(Protocol):
    """The State interface encapsulating all state-specific behaviors."""
    def select_item(self, sku: str) -> None: ...
    def insert_coin(self, coin: Coin) -> None: ...
    def dispense(self) -> None: ...
    def cancel(self) -> None: ...

class IdleState:
    def __init__(self, machine: VendingMachine):
        self.machine = machine

    def select_item(self, sku: str) -> None:
        if self.machine.inventory.get_stock(sku) <= 0:
            print(f"❌ Item {sku} is out of stock.")
            return
            
        product = self.machine.inventory.get_product(sku)
        self.machine.selected_product = product
        self.machine.audit.record("ITEM_SELECTED", f"User selected {product.name} (Price: {product.price_cents}¢)")
        self.machine.set_state(self.machine.item_selected_state)

    def insert_coin(self, coin: Coin) -> None:
        print("⚠️ Please select an item first before inserting coins.")

    def dispense(self) -> None:
        print("⚠️ No item selected.")

    def cancel(self) -> None:
        print("⚠️ Nothing to cancel.")


class ItemSelectedState:
    def __init__(self, machine: VendingMachine):
        self.machine = machine

    def select_item(self, sku: str) -> None:
        assert self.machine.selected_product is not None, "Selected product should not be None in ItemSelectedState."
        print(f"⚠️ You have already selected {self.machine.selected_product.name}. Please cancel to select another.")

    def insert_coin(self, coin: Coin) -> None:
        self.machine.current_balance += coin.value
        print(f"🪙 Inserted {coin.name} ({coin.value}¢). Current Balance: {self.machine.current_balance}¢")
        assert self.machine.selected_product is not None, "Selected product should not be None in ItemSelectedState."
        # Auto-transition to dispensing if fully paid
        if self.machine.current_balance >= self.machine.selected_product.price_cents:
            print("✅ Payment complete. Ready to dispense.")
            self.machine.set_state(self.machine.dispensing_state)
            self.machine.dispense()  # Auto-dispense for seamless UX

    def dispense(self) -> None:
        assert self.machine.selected_product is not None, "Selected product should not be None in ItemSelectedState."
        shortfall = self.machine.selected_product.price_cents - self.machine.current_balance
        print(f"⚠️ Insufficient funds. Please insert {shortfall}¢ more.")

    def cancel(self) -> None:
        self.machine.refund()
        self.machine.selected_product = None
        self.machine.audit.record("TRANSACTION_CANCELLED", "User cancelled. Refunded balance.")
        self.machine.set_state(self.machine.idle_state)


class DispensingState:
    def __init__(self, machine: VendingMachine):
        self.machine = machine

    def select_item(self, sku: str) -> None:
        print("⚠️ Currently dispensing. Please wait.")

    def insert_coin(self, coin: Coin) -> None:
        print("⚠️ Currently dispensing. Cannot accept coins right now.")

    def dispense(self) -> None:
        product = self.machine.selected_product
        assert product is not None, "Selected product should not be None in DispensingState."
        # Deduct inventory
        self.machine.inventory.reduce_stock(product.sku)
        
        # Calculate change
        change = self.machine.current_balance - product.price_cents
        
        print(f"🎉 Dispensing {product.name}...")
        self.machine.audit.record("DISPENSE_SUCCESS", f"Dispensed {product.name}")
        
        if change > 0:
            print(f"💵 Returning change: {change}¢")
            self.machine.audit.record("CHANGE_RETURNED", f"Returned {change}¢")

        # Reset machine state
        self.machine.current_balance = 0
        self.machine.selected_product = None
        self.machine.set_state(self.machine.idle_state)

    def cancel(self) -> None:
        print("⚠️ Cannot cancel. Product is already dispensing.")


class MaintenanceState:
    def __init__(self, machine: VendingMachine):
        self.machine = machine

    def select_item(self, sku: str) -> None:
        print("🛠️ Machine is currently under maintenance.")

    def insert_coin(self, coin: Coin) -> None:
        print("🛠️ Machine is currently under maintenance. Returning coin.")

    def dispense(self) -> None:
        print("🛠️ Machine is currently under maintenance.")

    def cancel(self) -> None:
        print("🛠️ Machine is currently under maintenance.")

# ==========================================
# 5. The Context (Vending Machine)
# ==========================================

class VendingMachine:
    def __init__(self):
        self.inventory = InventoryManager()
        self.audit = AuditTrail()
        
        # Initialize States
        self.idle_state = IdleState(self)
        self.item_selected_state = ItemSelectedState(self)
        self.dispensing_state = DispensingState(self)
        self.maintenance_state = MaintenanceState(self)
        
        # Set Initial State
        self._current_state: State = self.idle_state
        
        # Transaction Context Variables
        self.selected_product: Optional[Product] = None
        self.current_balance: int = 0

    def set_state(self, state: State) -> None:
        self._current_state = state

    def toggle_maintenance(self, activate: bool) -> None:
        if activate:
            if self.current_balance > 0:
                self.refund()
            self.set_state(self.maintenance_state)
            self.audit.record("MAINTENANCE_MODE", "Machine entered maintenance mode.")
        else:
            self.set_state(self.idle_state)
            self.audit.record("MAINTENANCE_MODE", "Machine returned to service.")

    def refund(self) -> None:
        if self.current_balance > 0:
            print(f"💵 Refunding current balance: {self.current_balance}¢")
            self.current_balance = 0

    # Pass-through methods to the current state
    def select_item(self, sku: str) -> None:
        self._current_state.select_item(sku)

    def insert_coin(self, coin: Coin) -> None:
        self._current_state.insert_coin(coin)

    def dispense(self) -> None:
        self._current_state.dispense()

    def cancel(self) -> None:
        self._current_state.cancel()


# ==========================================
# 6. Example Execution Flow
# ==========================================
if __name__ == "__main__":
    # 1. Setup Machine & Inventory
    machine = VendingMachine()
    
    cola = Product(sku="A1", name="Cola", price_cents=150, category=ProductCategory.BEVERAGE)
    chips = Product(sku="B1", name="Potato Chips", price_cents=85, category=ProductCategory.SNACK)
    
    machine.inventory.add_product(cola, quantity=5)
    machine.inventory.add_product(chips, quantity=1)  # Only 1 in stock

    # 2. Standard Purchase Flow (Perfect Path)
    print("\n--- Purchase: Chips ---")
    machine.select_item("B1")
    machine.insert_coin(Coin.QUARTER) # 25¢
    machine.insert_coin(Coin.QUARTER) # 50¢
    machine.insert_coin(Coin.QUARTER) # 75¢
    machine.insert_coin(Coin.DIME)    # 85¢ (Triggers auto-dispense)

    # 3. Handling Out of Stock
    print("\n--- Out of Stock Test ---")
    machine.select_item("B1")  # Should fail, we bought the only one

    # 4. Purchase with Change & Manual Cancelation
    print("\n--- Purchase: Cola with Cancel ---")
    machine.select_item("A1")
    machine.insert_coin(Coin.DOLLAR_COIN) # 100¢
    machine.cancel() # Changed my mind
    
    print("\n--- Purchase: Cola with Change ---")
    machine.select_item("A1")
    machine.insert_coin(Coin.DOLLAR_COIN) # 100¢
    machine.insert_coin(Coin.DOLLAR_COIN) # 200¢ (Price is 150¢, returns 50¢ change)

    # 5. Maintenance Mode
    print("\n--- Maintenance Test ---")
    machine.toggle_maintenance(True)
    machine.select_item("A1")