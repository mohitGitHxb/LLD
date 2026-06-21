import uuid
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Protocol, Optional
""" 
The Car Rental System introduces the complex dimension of time-based inventory management. Unlike a standard e-commerce or warehouse system where an item is simply "in stock" or "out of stock," a rental vehicle can be available today, booked for next week, and available again the week after.

To solve this efficiently, we must focus on Interval Overlap detection for conflict prevention, alongside robust state management for the vehicles.

Design Patterns Used
Strategy Pattern: For calculating rental costs. Prices might be standard, or they might surge based on demand or vehicle type (Dynamic Pricing).

State Pattern (via Enums): To manage the strict lifecycle of a vehicle (Available -> Booked -> In Use -> Maintenance) and a reservation (Pending -> Confirmed -> Completed).

Facade Pattern: A CarRentalSystem orchestrator that abstracts the complexity of the InventoryManager, ReservationManager, and PaymentGateway from the client.

Dependency Inversion: Interacting with payment gateways and pricing models via Protocols, making the system loosely coupled and highly testable.
"""
# ==========================================
# 1. Enums and Exceptions
# ==========================================

class VehicleType(Enum):
    ECONOMY = auto()
    COMPACT = auto()
    SUV = auto()
    LUXURY = auto()

class VehicleStatus(Enum):
    AVAILABLE = auto()
    MAINTENANCE = auto()
    RETIRED = auto()

class ReservationStatus(Enum):
    PENDING = auto()
    CONFIRMED = auto()
    ACTIVE = auto()      # Customer has picked up the car
    COMPLETED = auto()   # Customer returned the car
    CANCELLED = auto()

class CarRentalError(Exception): pass
class VehicleNotAvailableError(CarRentalError): pass
class InvalidReservationError(CarRentalError): pass
class PaymentFailedError(CarRentalError): pass

# ==========================================
# 2. Core Entities
# ==========================================

@dataclass(slots=True, kw_only=True)
class User:
    user_id: str
    name: str
    email: str
    driver_license: str

@dataclass(slots=True, kw_only=True)
class Vehicle:
    vehicle_id: str
    license_plate: str
    make: str
    model: str
    year: int
    v_type: VehicleType
    base_daily_rate: float
    status: VehicleStatus = VehicleStatus.AVAILABLE
    store_id: str

@dataclass(slots=True, kw_only=True)
class Store:
    store_id: str
    name: str
    location: str
    vehicles: dict[str, Vehicle] = field(default_factory=dict)

@dataclass(slots=True, kw_only=True)
class Reservation:
    reservation_id: str
    user_id: str
    vehicle_id: str
    store_id: str
    start_time: datetime
    end_time: datetime
    status: ReservationStatus = ReservationStatus.PENDING
    total_cost: float = 0.0

# ==========================================
# 3. Interfaces (Protocols) & Strategies
# ==========================================

class PricingStrategy(Protocol):
    def calculate_price(self, vehicle: Vehicle, start: datetime, end: datetime) -> float:
        ...

class PaymentProcessor(Protocol):
    def process_payment(self, user_id: str, amount: float) -> bool:
        ...

class DynamicPricing:
    """Calculates price factoring in vehicle type multipliers."""
    def calculate_price(self, vehicle: Vehicle, start: datetime, end: datetime) -> float:
        days = max(1, (end - start).days)
        
        # Multipliers based on vehicle type
        multipliers = {
            VehicleType.ECONOMY: 1.0,
            VehicleType.COMPACT: 1.2,
            VehicleType.SUV: 1.8,
            VehicleType.LUXURY: 2.5
        }
        multiplier = multipliers.get(vehicle.v_type, 1.0)
        return vehicle.base_daily_rate * days * multiplier

class StripePaymentGateway:
    """Mock implementation of a payment processor."""
    def process_payment(self, user_id: str, amount: float) -> bool:
        print(f"💳 Processing payment of ${amount:.2f} for user {user_id} via Stripe...")
        return True  # Assume success

# ==========================================
# 4. Managers (Subsystems)
# ==========================================

class InventoryManager:
    def __init__(self) -> None:
        self.stores: dict[str, Store] = {}
        # Quick lookup for vehicles globally
        self.vehicles: dict[str, Vehicle] = {}

    def add_store(self, store: Store) -> None:
        self.stores[store.store_id] = store

    def add_vehicle(self, vehicle: Vehicle) -> None:
        if vehicle.store_id not in self.stores:
            raise CarRentalError(f"Store {vehicle.store_id} does not exist.")
        self.stores[vehicle.store_id].vehicles[vehicle.vehicle_id] = vehicle
        self.vehicles[vehicle.vehicle_id] = vehicle

    def get_vehicles_by_store(self, store_id: str) -> list[Vehicle]:
        return list(self.stores.get(store_id, Store(store_id="", name="", location="")).vehicles.values())

class ReservationManager:
    def __init__(self) -> None:
        self.reservations: dict[str, Reservation] = {}

    def _is_overlap(self, r1_start: datetime, r1_end: datetime, r2_start: datetime, r2_end: datetime) -> bool:
        """Check if two time intervals overlap."""
        return max(r1_start, r2_start) < min(r1_end, r2_end)

    def is_vehicle_available(self, vehicle_id: str, start: datetime, end: datetime) -> bool:
        for res in self.reservations.values():
            if res.vehicle_id == vehicle_id and res.status in {ReservationStatus.CONFIRMED, ReservationStatus.ACTIVE}:
                if self._is_overlap(start, end, res.start_time, res.end_time):
                    return False
        return True

    def create_reservation(self, res: Reservation) -> None:
        self.reservations[res.reservation_id] = res

    def get_user_reservations(self, user_id: str) -> list[Reservation]:
        return [res for res in self.reservations.values() if res.user_id == user_id]

# ==========================================
# 5. The Facade (Orchestrator)
# ==========================================

class CarRentalSystem:
    def __init__(self, inventory: InventoryManager, reservations: ReservationManager, 
                 pricing: PricingStrategy, payment: PaymentProcessor):
        self.inventory = inventory
        self.reservations = reservations
        self.pricing = pricing
        self.payment = payment
        self.users: dict[str, User] = {}

    def register_user(self, user: User) -> None:
        self.users[user.user_id] = user

    def search_vehicles(self, store_id: str, start_time: datetime, end_time: datetime, v_type: Optional[VehicleType] = None) -> list[Vehicle]:
        """Search for available vehicles at a store for a given time range."""
        available_vehicles = []
        all_store_vehicles = self.inventory.get_vehicles_by_store(store_id)

        for vehicle in all_store_vehicles:
            if vehicle.status != VehicleStatus.AVAILABLE:
                continue
            if v_type and vehicle.v_type != v_type:
                continue
            if self.reservations.is_vehicle_available(vehicle.vehicle_id, start_time, end_time):
                available_vehicles.append(vehicle)

        return available_vehicles

    def book_vehicle(self, user_id: str, vehicle_id: str, start_time: datetime, end_time: datetime) -> Reservation:
        if not self.reservations.is_vehicle_available(vehicle_id, start_time, end_time):
            raise VehicleNotAvailableError(f"Vehicle {vehicle_id} is not available for the selected dates.")

        vehicle = self.inventory.vehicles[vehicle_id]
        
        # Calculate cost via Strategy
        total_cost = self.pricing.calculate_price(vehicle, start_time, end_time)

        # Process Payment
        if not self.payment.process_payment(user_id, total_cost):
            raise PaymentFailedError("Payment processing failed.")

        # Create Reservation
        res = Reservation(
            reservation_id=str(uuid.uuid4()),
            user_id=user_id,
            vehicle_id=vehicle_id,
            store_id=vehicle.store_id,
            start_time=start_time,
            end_time=end_time,
            status=ReservationStatus.CONFIRMED,
            total_cost=total_cost
        )
        self.reservations.create_reservation(res)
        print(f"✅ Booking Confirmed! ID: {res.reservation_id} | Total: ${total_cost:.2f}")
        return res

    def cancel_reservation(self, reservation_id: str) -> None:
        res = self.reservations.reservations.get(reservation_id)
        if not res:
            raise InvalidReservationError("Reservation not found.")
        if res.status in {ReservationStatus.COMPLETED, ReservationStatus.CANCELLED, ReservationStatus.ACTIVE}:
            raise InvalidReservationError("Cannot cancel an active or completed reservation.")
        
        res.status = ReservationStatus.CANCELLED
        print(f"🚫 Reservation {reservation_id} has been cancelled.")

# ==========================================
# 6. Example Execution Flow
# ==========================================
if __name__ == "__main__":
    # 1. System Setup
    inventory_manager = InventoryManager()
    reservation_manager = ReservationManager()
    pricing_strategy = DynamicPricing()
    payment_processor = StripePaymentGateway()

    rental_system = CarRentalSystem(
        inventory=inventory_manager, 
        reservations=reservation_manager, 
        pricing=pricing_strategy, 
        payment=payment_processor
    )

    # 2. Seed Data
    store_sfo = Store(store_id="SFO-01", name="SFO Airport Rent-A-Car", location="San Francisco")
    inventory_manager.add_store(store_sfo)

    tesla = Vehicle(
        vehicle_id="V-100", license_plate="XYZ-123", make="Tesla", model="Model 3", 
        year=2023, v_type=VehicleType.LUXURY, base_daily_rate=50.0, store_id="SFO-01"
    )
    honda = Vehicle(
        vehicle_id="V-101", license_plate="ABC-987", make="Honda", model="Civic", 
        year=2022, v_type=VehicleType.ECONOMY, base_daily_rate=30.0, store_id="SFO-01"
    )
    inventory_manager.add_vehicle(tesla)
    inventory_manager.add_vehicle(honda)

    john = User(user_id="U-001", name="John Doe", email="john@example.com", driver_license="DL12345")
    rental_system.register_user(john)

    # 3. Operations
    start_date = datetime.now(timezone.utc) + timedelta(days=2)
    end_date = start_date + timedelta(days=5)

    print("--- Searching for Luxury Vehicles ---")
    available_cars = rental_system.search_vehicles("SFO-01", start_date, end_date, v_type=VehicleType.LUXURY)
    for car in available_cars:
        print(f"Found: {car.make} {car.model} (ID: {car.vehicle_id})")

    print("\n--- Booking the Vehicle ---")
    if available_cars:
        booking = rental_system.book_vehicle("U-001", available_cars[0].vehicle_id, start_date, end_date)

    print("\n--- Attempting to Book the Same Vehicle for Overlapping Dates ---")
    try:
        # Trying to book the exact same dates
        rental_system.book_vehicle("U-001", "V-100", start_date + timedelta(days=1), end_date + timedelta(days=1))
    except CarRentalError as e:
        print(f"❌ Conflict Detected: {e}")