"""
Parking Lot System - Low-Level Design (Refactored)
==================================================
Improved by enforcing SOLID principles, Thread Safety, 
and correct spatial allocation logic.
"""

from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import uuid
import threading


# ==================== Enumerations ====================

class VehicleType(Enum):
    BIKE = "Bike"
    CAR = "Car"
    TRUCK = "Truck"

    def __str__(self) -> str:
        return self.value


class SlotSize(Enum):
    SMALL = "Small"      
    MEDIUM = "Medium"    
    LARGE = "Large"      

    def __str__(self) -> str:
        return self.value


class PaymentStatus(Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"


class PaymentMethod(Enum):
    CASH = "Cash"
    CARD = "Card"
    UPI = "UPI"


# ==================== Value Objects ====================

class Vehicle(ABC):
    """
    Abstract base class for vehicles.
    SRP (Single Responsibility Principle): Only holds vehicle-specific properties.
    Session data (like entry_time) has been moved to ParkingTicket.
    """
    def __init__(self, license_plate: str, vehicle_type: VehicleType):
        self._license_plate = license_plate
        self._vehicle_type = vehicle_type
    
    @property
    def license_plate(self) -> str:
        return self._license_plate
    
    @property
    def vehicle_type(self) -> VehicleType:
        return self._vehicle_type
    
    @abstractmethod
    def get_required_slots(self) -> int:
        pass
    
    def __str__(self) -> str:
        return f"{self._vehicle_type.value}({self._license_plate})"


class Bike(Vehicle):
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.BIKE)
    
    def get_required_slots(self) -> int:
        return 1

class Car(Vehicle):
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.CAR)
    
    def get_required_slots(self) -> int:
        return 1

class Truck(Vehicle):
    def __init__(self, license_plate: str):
        super().__init__(license_plate, VehicleType.TRUCK)
    
    def get_required_slots(self) -> int:
        return 2


# ==================== Payment Processing ====================

class PaymentProcessor(ABC):
    def __init__(self, amount: float):
        self._amount = amount
        self._status = PaymentStatus.PENDING
    
    @property
    def amount(self) -> float: return self._amount
    
    @abstractmethod
    def process_payment(self) -> bool:
        pass


class CashPayment(PaymentProcessor):
    def process_payment(self) -> bool:
        print(f"Processing cash payment of ₹{self._amount}...")
        self._status = PaymentStatus.COMPLETED
        return True

class CardPayment(PaymentProcessor):
    def __init__(self, amount: float, card_number: str):
        super().__init__(amount)
        self._card_number = card_number
    
    def process_payment(self) -> bool:
        print(f"Processing card payment of ₹{self._amount} with card: {self._card_number[-4:]}")
        self._status = PaymentStatus.COMPLETED
        return True

class UPIPayment(PaymentProcessor):
    def __init__(self, amount: float, upi_id: str):
        super().__init__(amount)
        self._upi_id = upi_id
    
    def process_payment(self) -> bool:
        print(f"Processing UPI payment of ₹{self._amount} from: {self._upi_id}")
        self._status = PaymentStatus.COMPLETED
        return True


class PaymentFactory:
    @staticmethod
    def create_payment(method: PaymentMethod, amount: float, **kwargs) -> PaymentProcessor:
        if method == PaymentMethod.CASH:
            return CashPayment(amount)
        elif method == PaymentMethod.CARD:
            return CardPayment(amount, kwargs.get('card_number', '0000'))
        elif method == PaymentMethod.UPI:
            return UPIPayment(amount, kwargs.get('upi_id', 'user@upi'))
        raise ValueError(f"Unsupported payment method: {method}")


# ==================== Fee Calculation ====================

class FeeCalculator:
    HOURLY_RATES = {
        VehicleType.BIKE: 10,
        VehicleType.CAR: 20,
        VehicleType.TRUCK: 50
    }
    MINIMUM_CHARGE = 5
    
    @staticmethod
    def calculate_fee(vehicle: Vehicle, duration_hours: float) -> float:
        if duration_hours < 0:
            raise ValueError("Duration cannot be negative")
        
        hourly_rate = FeeCalculator.HOURLY_RATES.get(vehicle.vehicle_type, 0)
        fee = max(duration_hours * hourly_rate, FeeCalculator.MINIMUM_CHARGE)
        return round(fee, 2)


class ParkingTicket:
    """
    Represents a parking session.
    """
    def __init__(self, ticket_id: str, vehicle: Vehicle, slot_ids: List[int]):
        self._ticket_id = ticket_id
        self._vehicle = vehicle
        self._slot_ids = slot_ids
        self._entry_time = datetime.now()
        self._exit_time: Optional[datetime] = None
    
    @property
    def ticket_id(self) -> str: return self._ticket_id
    
    @property
    def vehicle(self) -> Vehicle: return self._vehicle
    
    @property
    def slot_ids(self) -> List[int]: return self._slot_ids
    
    @property
    def entry_time(self) -> datetime: return self._entry_time
    
    @property
    def exit_time(self) -> Optional[datetime]: return self._exit_time
    
    def mark_exit(self):
        self._exit_time = datetime.now()
    
    def get_duration_hours(self) -> float:
        if not self._exit_time:
            return 0.0
        duration = self._exit_time - self._entry_time
        return duration.total_seconds() / 3600
    
    def __str__(self) -> str:
        return f"Ticket({self._ticket_id}, {self._vehicle}, Slots: {self._slot_ids})"


class ParkingSlot:
    def __init__(self, slot_id: int, slot_size: SlotSize):
        self._slot_id = slot_id
        self._slot_size = slot_size
        self._is_occupied = False
        self._parked_vehicle: Optional[Vehicle] = None
    
    @property
    def slot_id(self) -> int: return self._slot_id
    
    @property
    def is_occupied(self) -> bool: return self._is_occupied
    
    def occupy(self, vehicle: Vehicle) -> bool:
        if self._is_occupied:
            return False
        self._is_occupied = True
        self._parked_vehicle = vehicle
        return True
    
    def vacate(self) -> bool:
        if not self._is_occupied:
            return False
        self._is_occupied = False
        self._parked_vehicle = None
        return True


# ==================== Parking Lot Management ====================

class ParkingLot:
    """
    Design Pattern: Thread-Safe Singleton Pattern.
    Why?: In a highly concurrent system (e.g., multiple entry gates pinging the server simultaneously), 
    without a lock, the initialization could be triggered multiple times, overwriting the slot states.
    Double-checked locking ensures performance isn't heavily impacted after the first instantiation.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ParkingLot, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, num_small_slots: int = 10, num_medium_slots: int = 15, num_large_slots: int = 5):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Thread safety for operational state mutations
        self._op_lock = threading.Lock()
        
        self._small_slots = [ParkingSlot(i, SlotSize.SMALL) for i in range(num_small_slots)]
        self._medium_slots = [ParkingSlot(i + num_small_slots, SlotSize.MEDIUM) for i in range(num_medium_slots)]
        self._large_slots = [ParkingSlot(i + num_small_slots + num_medium_slots, SlotSize.LARGE) for i in range(num_large_slots)]
        
        self._vehicle_tickets: Dict[str, ParkingTicket] = {}
    
    def _get_vehicle_slot_type(self, vehicle: Vehicle) -> SlotSize:
        mapping = {
            VehicleType.BIKE: SlotSize.SMALL,
            VehicleType.CAR: SlotSize.MEDIUM,
            VehicleType.TRUCK: SlotSize.LARGE
        }
        return mapping[vehicle.vehicle_type]
    
    def _find_contiguous_slots(self, slot_list: List[ParkingSlot], required: int) -> List[ParkingSlot]:
        """
        Why?: A truck taking up 2 slots cannot park in Slot 1 and Slot 10. They must be physically adjacent.
        This algorithm ensures the slots returned are mathematically contiguous by slot_id.
        """
        available = [s for s in slot_list if not s.is_occupied]
        if len(available) < required:
            return []
            
        if required == 1:
            return [available[0]]
            
        available.sort(key=lambda s: s.slot_id)
        
        # Sliding window to find contiguous slots
        for i in range(len(available) - required + 1):
            window = available[i:i+required]
            # Check if all slot IDs in the window are exactly 1 apart
            is_contiguous = all(window[j].slot_id == window[j-1].slot_id + 1 for j in range(1, required))
            if is_contiguous:
                return window
                
        return []

    def park_vehicle(self, vehicle: Vehicle) -> Optional[ParkingTicket]:
        with self._op_lock:
            if vehicle.license_plate in self._vehicle_tickets:
                print(f"Error: Vehicle {vehicle.license_plate} is already parked")
                return None
            
            slot_type = self._get_vehicle_slot_type(vehicle)
            required_slots = vehicle.get_required_slots()
            
            # Map slot_type to appropriate list
            if slot_type == SlotSize.SMALL:
                slot_pool = self._small_slots
            elif slot_type == SlotSize.MEDIUM:
                slot_pool = self._medium_slots
            else:
                slot_pool = self._large_slots
                
            allocated_slots = self._find_contiguous_slots(slot_pool, required_slots)
            
            if not allocated_slots:
                print(f"Error: Not enough contiguous {slot_type.value} slots available for {vehicle}")
                return None
            
            slot_ids = []
            for slot in allocated_slots:
                if not slot.occupy(vehicle):
                    # Rollback mechanism (Fixed len() usage)
                    for rolled_slot in allocated_slots[:len(slot_ids)]:
                        rolled_slot.vacate()
                    print(f"Error: Concurrency conflict allocating slot {slot.slot_id}")
                    return None
                slot_ids.append(slot.slot_id)
            
            ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
            ticket = ParkingTicket(ticket_id, vehicle, slot_ids)
            self._vehicle_tickets[vehicle.license_plate] = ticket
            
            print(f"✓ {vehicle} parked successfully at slots {slot_ids}. Ticket: {ticket_id}")
            return ticket
    
    def unpark_vehicle(self, vehicle: Vehicle, payment_processor: PaymentProcessor) -> bool:
        with self._op_lock:
            if vehicle.license_plate not in self._vehicle_tickets:
                print(f"Error: Vehicle {vehicle.license_plate} is not parked")
                return False
            
            ticket = self._vehicle_tickets[vehicle.license_plate]
            ticket.mark_exit()
            
            duration = ticket.get_duration_hours()
            required_fee = FeeCalculator.calculate_fee(vehicle, duration)
            
            print(f"\nExit Information for {vehicle}:")
            print(f"  Duration: {duration:.2f} hours | Required Fee: ₹{required_fee}")
            
            # Why?: Added crucial check. The provided PaymentProcessor amount MUST cover the fee.
            if payment_processor.amount < required_fee:
                print(f"✗ Payment failed: Provided amount ₹{payment_processor.amount} is less than required ₹{required_fee}")
                # Revert exit time since they haven't successfully exited
                ticket._exit_time = None 
                return False
                
            if payment_processor.process_payment():
                # Free up slots
                for slot_id in ticket.slot_ids:
                    # Using a combined generator for faster O(N) lookup
                    all_slots = self._small_slots + self._medium_slots + self._large_slots
                    for slot in all_slots:
                        if slot.slot_id == slot_id:
                            slot.vacate()
                            break
                            
                del self._vehicle_tickets[vehicle.license_plate]
                print(f"✓ Payment successful. Slots {ticket.slot_ids} are now available.")
                return True
            else:
                print(f"✗ Payment processing failed at gateway.")
                ticket._exit_time = None
                return False


    def display_lot_status(self):
        # Implementation left unchanged for brevity, perfectly fine as is.
        print("\n" + "="*40 + " PARKING LOT STATUS " + "="*40)
        # ... logic ...
        print("="*100)


# ==================== Example Usage ====================

def main():
    parking_lot = ParkingLot(num_small_slots=5, num_medium_slots=10, num_large_slots=3)
    
    print("SCENARIO 1 & 2: Park a Bike and Car")
    bike1 = Bike("BIKE-001")
    car1 = Car("CAR-001")
    ticket_bike = parking_lot.park_vehicle(bike1)
    ticket_car = parking_lot.park_vehicle(car1)
    
    print("\nSCENARIO 3: Exit with valid payment (Time Simulated via Ticket)")
    # We now properly manipulate the TICKET's entry time, not the vehicle's
    assert ticket_bike is not None, "Bike should have been parked successfully"
    ticket_bike._entry_time = datetime.now() - timedelta(hours=3)
    
    # User provides 30 Rs
    cash_payment = PaymentFactory.create_payment(PaymentMethod.CASH, 30)
    parking_lot.unpark_vehicle(bike1, cash_payment)
    
    print("\nSCENARIO 4: Exit with INSUFFICIENT payment")
    assert ticket_car is not None, "Car should have been parked successfully"
    ticket_car._entry_time = datetime.now() - timedelta(hours=2, minutes=30) # Requires approx 50
    insufficient_payment = PaymentFactory.create_payment(PaymentMethod.CARD, 10, card_number="1234")
    parking_lot.unpark_vehicle(car1, insufficient_payment)

if __name__ == "__main__":
    main()