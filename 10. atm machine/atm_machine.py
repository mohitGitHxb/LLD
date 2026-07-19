from __future__ import annotations
import uuid
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Optional, Dict

# ==========================================
# 1. Enums and Exceptions
# ==========================================

class Denomination(Enum):
    """Explicitly assigned integer values for sorting and math operations."""
    HUNDRED = 100
    FIFTY = 50
    TWENTY = 20
    TEN = 10

class ATMError(Exception): pass
class AuthenticationError(ATMError): pass
class InsufficientFundsError(ATMError): pass
class InsufficientATMCashError(ATMError): pass
class InvalidStateActionError(ATMError): pass

# ==========================================
# 2. Core Entities
# ==========================================

@dataclass(slots=True, kw_only=True)
class Card:
    card_number: str
    pin_hash: str  # Security: Never store plain text PINs
    account_id: str

@dataclass(slots=True, kw_only=True)
class BankAccount:
    account_id: str
    balance: float

@dataclass(slots=True, kw_only=True)
class TransactionLog:
    transaction_id: str
    timestamp: datetime
    account_id: str
    action: str
    amount: float = 0.0
    status: str

# ==========================================
# 3. Subsystems: Bank, Dispenser, Logger
# ==========================================

class TransactionLogger:
    def __init__(self) -> None:
        self._logs: list[TransactionLog] = []

    def log(self, account_id: str, action: str, status: str, amount: float = 0.0) -> None:
        record = TransactionLog(
            transaction_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            account_id=account_id,
            action=action,
            amount=amount,
            status=status
        )
        self._logs.append(record)
        print(f"📝 [AUDIT] {record.action} | Status: {record.status} | Account: {account_id}")

class BankService:
    """Mock external banking system."""
    def __init__(self):
        self.accounts: dict[str, BankAccount] = {}

    def authenticate_card(self, card: Card, entered_pin: str) -> bool:
        # In a real system, we'd hash the entered_pin and compare
        # Here we do a simple string match for demonstration
        return card.pin_hash == entered_pin

    def get_balance(self, account_id: str) -> float:
        return self.accounts[account_id].balance

    def debit_account(self, account_id: str, amount: float) -> None:
        account = self.accounts.get(account_id)
        if not account or account.balance < amount:
            raise InsufficientFundsError("Insufficient funds in bank account.")
        account.balance -= amount

class CashDispenser:
    """Manages physical cash inventory and dispensing logic."""
    def __init__(self):
        # Maps Denomination to Count
        self.inventory: Dict[Denomination, int] = {
            Denomination.HUNDRED: 0,
            Denomination.FIFTY: 0,
            Denomination.TWENTY: 0,
            Denomination.TEN: 0
        }

    def load_cash(self, denomination: Denomination, count: int) -> None:
        self.inventory[denomination] += count

    def get_total_cash(self) -> int:
        return sum(d.value * count for d, count in self.inventory.items())

    def can_dispense(self, amount: int) -> bool:
        try:
            self._calculate_dispense_breakdown(amount)
            return True
        except InsufficientATMCashError:
            return False

    def _calculate_dispense_breakdown(self, amount: int) -> Dict[Denomination, int]:
        """Greedy algorithm to find the bill breakdown. Dry run only."""
        if amount % 10 != 0:
            raise InsufficientATMCashError("Amount must be a multiple of 10.")
            
        remaining = amount
        breakdown: Dict[Denomination, int] = {}
        
        # Sort denominations highest to lowest
        for denom in sorted(Denomination, key=lambda x: x.value, reverse=True):
            available_notes = self.inventory[denom]
            notes_needed = remaining // denom.value
            notes_to_dispense = min(available_notes, notes_needed)
            
            if notes_to_dispense > 0:
                breakdown[denom] = notes_to_dispense
                remaining -= notes_to_dispense * denom.value
                
        if remaining > 0:
            raise InsufficientATMCashError("ATM cannot dispense this exact amount with current denominations.")
            
        return breakdown

    def dispense(self, amount: int) -> None:
        breakdown = self._calculate_dispense_breakdown(amount)
        # Deduct from actual inventory
        print(f"💵 Dispensing ${amount}...")
        for denom, count in breakdown.items():
            self.inventory[denom] -= count
            print(f"   -> {count}x ${denom.value} bills")

# ==========================================
# 4. State Pattern Implementation
# ==========================================

class ATMState(Protocol):
    def insert_card(self, card: Card) -> None: ...
    def eject_card(self) -> None: ...
    def enter_pin(self, pin: str) -> None: ...
    def check_balance(self) -> None: ...
    def withdraw_cash(self, amount: int) -> None: ...

class IdleState:
    def __init__(self, atm: ATM):
        self.atm = atm

    def insert_card(self, card: Card) -> None:
        print(f"💳 Card inserted: {card.card_number}")
        self.atm.current_card = card
        self.atm.set_state(self.atm.has_card_state)

    def eject_card(self) -> None:
        print("⚠️ No card to eject.")

    def enter_pin(self, pin: str) -> None:
        print("⚠️ Please insert a card first.")

    def check_balance(self) -> None:
        print("⚠️ Please insert a card first.")

    def withdraw_cash(self, amount: int) -> None:
        print("⚠️ Please insert a card first.")


class HasCardState:
    def __init__(self, atm: ATM):
        self.atm = atm

    def insert_card(self, card: Card) -> None:
        print("⚠️ A card is already inserted.")

    def eject_card(self) -> None:
        print("💳 Ejecting card...")
        self.atm.current_card = None
        self.atm.set_state(self.atm.idle_state)

    def enter_pin(self, pin: str) -> None:
        if not self.atm.current_card:
            return
            
        is_valid = self.atm.bank_service.authenticate_card(self.atm.current_card, pin)
        if is_valid:
            print("✅ PIN accepted. Authentication successful.")
            self.atm.set_state(self.atm.authenticated_state)
        else:
            print("❌ Invalid PIN.")
            self.atm.logger.log(self.atm.current_card.account_id, "AUTH", "FAILED")
            self.eject_card()

    def check_balance(self) -> None:
        print("⚠️ Please enter your PIN first.")

    def withdraw_cash(self, amount: int) -> None:
        print("⚠️ Please enter your PIN first.")


class AuthenticatedState:
    def __init__(self, atm: ATM):
        self.atm = atm

    def insert_card(self, card: Card) -> None:
        print("⚠️ A card is already inserted.")

    def eject_card(self) -> None:
        print("💳 Transaction complete. Ejecting card...")
        self.atm.current_card = None
        self.atm.set_state(self.atm.idle_state)

    def enter_pin(self, pin: str) -> None:
        print("⚠️ You are already authenticated.")

    def check_balance(self) -> None:
        if not self.atm.current_card:
            print("⚠️ No card inserted.")
            return
        account_id = self.atm.current_card.account_id
        balance = self.atm.bank_service.get_balance(account_id)
        print(f"💰 Current Balance for Account {account_id}: ${balance:.2f}")
        self.atm.logger.log(account_id, "CHECK_BALANCE", "SUCCESS")
        self.eject_card()  # End session after operation

    def withdraw_cash(self, amount: int) -> None:
        if not self.atm.current_card:
            print("⚠️ No card inserted.")
            return
        account_id = self.atm.current_card.account_id
        
        # 1. Check ATM physical cash availability
        if not self.atm.dispenser.can_dispense(amount):
            print("❌ ATM cannot dispense this exact amount.")
            self.atm.logger.log(account_id, "WITHDRAW", "FAILED_ATM_EMPTY", amount)
            self.eject_card()
            return
            
        # 2. Check Bank Account balance
        if self.atm.bank_service.get_balance(account_id) < amount:
            print("❌ Insufficient funds in bank account.")
            self.atm.logger.log(account_id, "WITHDRAW", "FAILED_INSUFFICIENT_FUNDS", amount)
            self.eject_card()
            return

        # 3. Execute Transaction
        try:
            self.atm.bank_service.debit_account(account_id, amount)
            self.atm.dispenser.dispense(amount)
            self.atm.logger.log(account_id, "WITHDRAW", "SUCCESS", amount)
            print("✅ Please take your cash.")
        except Exception as e:
            print(f"❌ System error during transaction: {e}")
            self.atm.logger.log(account_id, "WITHDRAW", "SYSTEM_ERROR", amount)
            
        self.eject_card()


class MaintenanceState:
    def __init__(self, atm: ATM):
        self.atm = atm

    def insert_card(self, card: Card) -> None:
        print("🛠️ ATM is out of service for maintenance.")

    def eject_card(self) -> None: pass
    def enter_pin(self, pin: str) -> None: pass
    def check_balance(self) -> None: pass
    def withdraw_cash(self, amount: int) -> None: pass

# ==========================================
# 5. The Context (ATM Machine)
# ==========================================

class ATM:
    def __init__(self, bank_service: BankService):
        self.bank_service = bank_service
        self.dispenser = CashDispenser()
        self.logger = TransactionLogger()
        
        # Initialize States
        self.idle_state = IdleState(self)
        self.has_card_state = HasCardState(self)
        self.authenticated_state = AuthenticatedState(self)
        self.maintenance_state = MaintenanceState(self)
        
        # Initial Configuration
        self._current_state: ATMState = self.idle_state
        self.current_card: Optional[Card] = None

    def set_state(self, state: ATMState) -> None:
        self._current_state = state

    def toggle_maintenance(self, activate: bool) -> None:
        if activate:
            if self.current_card:
                self._current_state.eject_card()
            self.set_state(self.maintenance_state)
            print("🛠️ ATM placed into Maintenance Mode.")
        else:
            self.set_state(self.idle_state)
            print("✅ ATM is back in service.")

    # Context Pass-throughs
    def insert_card(self, card: Card) -> None:
        self._current_state.insert_card(card)

    def eject_card(self) -> None:
        self._current_state.eject_card()

    def enter_pin(self, pin: str) -> None:
        self._current_state.enter_pin(pin)

    def check_balance(self) -> None:
        self._current_state.check_balance()

    def withdraw_cash(self, amount: int) -> None:
        self._current_state.withdraw_cash(amount)

# ==========================================
# 6. Example Execution Flow
# ==========================================
if __name__ == "__main__":
    # 1. Setup Backend Services
    bank = BankService()
    
    # Register a user account and card
    alice_account_id = "ACC-12345"
    bank.accounts[alice_account_id] = BankAccount(account_id=alice_account_id, balance=500.0)
    alice_card = Card(card_number="1111-2222-3333-4444", pin_hash="1234", account_id=alice_account_id)

    # 2. Setup ATM and Load Cash
    atm = ATM(bank_service=bank)
    atm.dispenser.load_cash(Denomination.HUNDRED, 5) # $500
    atm.dispenser.load_cash(Denomination.TWENTY, 10) # $200

    print("\n--- Scenario 1: Successful Withdrawal ---")
    atm.insert_card(alice_card)
    atm.enter_pin("1234")
    atm.withdraw_cash(140)  # Should dispense 1x$100, 2x$20

    print("\n--- Scenario 2: Incorrect PIN ---")
    atm.insert_card(alice_card)
    atm.enter_pin("9999")   # Will reject and eject

    print("\n--- Scenario 3: ATM Cannot Make Exact Denomination ---")
    atm.insert_card(alice_card)
    atm.enter_pin("1234")
    atm.withdraw_cash(50)   # We only have $100s and $20s loaded!

    print("\n--- Scenario 4: Check Balance ---")
    atm.insert_card(alice_card)
    atm.enter_pin("1234")
    atm.check_balance()     # Original 500 - 140 withdrawn = 360

    print("\n--- Scenario 5: Maintenance Mode ---")
    atm.toggle_maintenance(True)
    atm.insert_card(alice_card) # Should block usage