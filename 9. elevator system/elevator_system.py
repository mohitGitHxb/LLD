import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Protocol, Optional

# ==========================================
# 1. Enums and Exceptions
# ==========================================

class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0

class ElevatorState(Enum):
    NORMAL = 1
    EMERGENCY = 2
    MAINTENANCE = 3

class DoorState(Enum):
    OPEN = 1
    CLOSED = 0
    OBSTRUCTED = -1

class ElevatorError(Exception): pass
class OverloadError(ElevatorError): pass
class EmergencyStopError(ElevatorError): pass

# ==========================================
# 2. Core Entities
# ==========================================

@dataclass(slots=True, kw_only=True)
class ExternalRequest:
    floor: int
    direction: Direction

@dataclass(slots=True, kw_only=True)
class Elevator:
    elevator_id: str
    max_capacity_kg: float
    current_weight: float = 0.0
    current_floor: int = 0
    direction: Direction = Direction.IDLE
    state: ElevatorState = ElevatorState.NORMAL
    door_state: DoorState = DoorState.CLOSED
    
    # Using sets to avoid duplicate stops
    _up_stops: set[int] = field(default_factory=set)
    _down_stops: set[int] = field(default_factory=set)

    def add_weight(self, weight: float) -> None:
        if self.current_weight + weight > self.max_capacity_kg:
            print(f"⚠️ Elevator {self.elevator_id}: Overload detected! Cannot close doors.")
            self.door_state = DoorState.OPEN
            raise OverloadError("Weight exceeds maximum capacity.")
        self.current_weight += weight

    def trigger_emergency(self) -> None:
        self.state = ElevatorState.EMERGENCY
        self.direction = Direction.IDLE
        self._up_stops.clear()
        self._down_stops.clear()
        print(f"🚨 EMERGENCY TRIGGERED on Elevator {self.elevator_id}! Halting immediately.")

    def obstruct_door(self) -> None:
        self.door_state = DoorState.OBSTRUCTED
        print(f"⚠️ Elevator {self.elevator_id}: Door obstructed. Re-opening.")

    def clear_obstruction(self) -> None:
        self.door_state = DoorState.OPEN
        print(f"✅ Elevator {self.elevator_id}: Obstruction cleared.")

    def add_internal_request(self, target_floor: int) -> None:
        if self.state != ElevatorState.NORMAL:
            print(f"❌ Elevator {self.elevator_id} is out of service.")
            return

        if target_floor > self.current_floor:
            self._up_stops.add(target_floor)
        elif target_floor < self.current_floor:
            self._down_stops.add(target_floor)
        
        self._update_direction()
        print(f"🔘 Elevator {self.elevator_id}: Button pressed for Floor {target_floor}.")

    def add_external_request(self, target_floor: int, direction: Direction) -> None:
        if direction == Direction.UP or target_floor > self.current_floor:
            self._up_stops.add(target_floor)
        else:
            self._down_stops.add(target_floor)
        self._update_direction()

    def _update_direction(self) -> None:
        if self.direction == Direction.IDLE:
            if self._up_stops:
                self.direction = Direction.UP
            elif self._down_stops:
                self.direction = Direction.DOWN

    def move(self) -> None:
        if self.state != ElevatorState.NORMAL:
            return
        if self.door_state == DoorState.OBSTRUCTED:
            print(f"⚠️ Elevator {self.elevator_id} cannot move. Doors are obstructed.")
            return

        self.door_state = DoorState.CLOSED

        if self.direction == Direction.UP:
            if self._up_stops:
                next_stop = min(self._up_stops)
                self.current_floor = next_stop
                self._up_stops.remove(next_stop)
                self._open_doors()
            elif self._down_stops:
                self.direction = Direction.DOWN
            else:
                self.direction = Direction.IDLE

        elif self.direction == Direction.DOWN:
            if self._down_stops:
                next_stop = max(self._down_stops)
                self.current_floor = next_stop
                self._down_stops.remove(next_stop)
                self._open_doors()
            elif self._up_stops:
                self.direction = Direction.UP
            else:
                self.direction = Direction.IDLE

    def _open_doors(self) -> None:
        self.door_state = DoorState.OPEN
        print(f"🔔 Elevator {self.elevator_id} arrived at Floor {self.current_floor}. Doors OPEN.")
        # Simulating time for passengers to enter/exit
        self.door_state = DoorState.CLOSED


# ==========================================
# 3. Dispatching Strategy (Routing)
# ==========================================

class DispatchStrategy(Protocol):
    def assign_elevator(self, elevators: list[Elevator], request: ExternalRequest) -> Optional[Elevator]:
        ...

class NearestElevatorStrategy:
    """Assigns the closest elevator that is moving in the correct direction or is idle."""
    
    def assign_elevator(self, elevators: list[Elevator], request: ExternalRequest) -> Optional[Elevator]:
        best_elevator = None
        min_distance = float('inf')

        for el in elevators:
            if el.state != ElevatorState.NORMAL:
                continue
            
            distance = abs(el.current_floor - request.floor)
            
            # Eligibility check
            is_idle = el.direction == Direction.IDLE
            moving_towards_and_same_dir = (
                (el.direction == Direction.UP and request.direction == Direction.UP and el.current_floor <= request.floor) or
                (el.direction == Direction.DOWN and request.direction == Direction.DOWN and el.current_floor >= request.floor)
            )

            if is_idle or moving_towards_and_same_dir:
                if distance < min_distance:
                    min_distance = distance
                    best_elevator = el

        return best_elevator

# ==========================================
# 4. The Controller (Orchestrator)
# ==========================================

class ElevatorController:
    def __init__(self, dispatch_strategy: DispatchStrategy):
        self.elevators: dict[str, Elevator] = {}
        self.dispatch_strategy = dispatch_strategy

    def add_elevator(self, elevator: Elevator) -> None:
        self.elevators[elevator.elevator_id] = elevator

    def request_elevator(self, floor: int, direction: Direction) -> None:
        print(f"🧍 External Request: Floor {floor}, going {direction.name}.")
        req = ExternalRequest(floor=floor, direction=direction)
        
        # 1. Calculate best elevator
        best_elevator = self.dispatch_strategy.assign_elevator(list(self.elevators.values()), req)
        
        # 2. Assign and notify
        if best_elevator:
            best_elevator.add_external_request(floor, direction)
            print(f"✅ Dispatched Elevator {best_elevator.elevator_id} to Floor {floor}.")
        else:
            print("⏳ All elevators busy or moving away. Request queued (Not implemented in basic version).")

    def simulate_step(self) -> None:
        """Simulates one time unit of movement for all elevators."""
        for el in self.elevators.values():
            if el.direction != Direction.IDLE:
                el.move()

# ==========================================
# 5. Example Execution Flow
# ==========================================
if __name__ == "__main__":
    # 1. System Setup
    controller = ElevatorController(dispatch_strategy=NearestElevatorStrategy())
    
    e1 = Elevator(elevator_id="E1", max_capacity_kg=800.0, current_floor=0)
    e2 = Elevator(elevator_id="E2", max_capacity_kg=800.0, current_floor=5)
    
    controller.add_elevator(e1)
    controller.add_elevator(e2)

    # 2. Operations (External Calls)
    controller.request_elevator(floor=3, direction=Direction.UP)   # E1 is closer (idle at 0)
    controller.request_elevator(floor=7, direction=Direction.DOWN) # E2 is closer (idle at 5)

    print("\n--- Simulating Movement ---")
    controller.simulate_step()  # E1 goes to 3, E2 goes to 7

    # 3. Inside the Elevator
    print("\n--- Passengers Boarding ---")
    # Passenger boards E1 at floor 3, wants to go to 8
    e1.add_internal_request(target_floor=8)
    e1.add_weight(75.0)  # Safe weight
    
    # 4. Safety Features Demo: Overload & Emergency
    print("\n--- Safety Scenarios ---")
    try:
        # Piano + 10 people try to board E2 at floor 7
        e2.add_weight(900.0) 
    except OverloadError:
        pass

    # E1 gets an emergency signal
    e1.trigger_emergency()

    # Move attempt (E1 won't move due to emergency, E2 won't move due to open/overloaded doors)
    print("\n--- Final Movement Attempt ---")
    controller.simulate_step()