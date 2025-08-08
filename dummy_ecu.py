import can
import time
import random

VCAN_CHANNEL = 'vcan0'
RESPONSE_ID = 0x7E8
REQUEST_ID = 0x7DF

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_TIME = 30
SESSION_TIMEOUT = 5 

# ECU state variables
seed = None
last_key = None
failed_attempts = 0
locked_until = 0
locked = False
seed_sent_time = 0
repeated_key = False
last_seed = None

# Start VCAN
bus = can.interface.Bus(channel=VCAN_CHANNEL, interface='socketcan')
print(f"ECU started on {VCAN_CHANNEL}")

# Generate random seed
def generate_seed():
    if not locked:
       last_key = None
       return random.randint(0, 0xFFFF)  

# Compute key
def compute_key(seed_val):
    return (seed_val + 1) & 0xFFFF

while True:
    msg = bus.recv()
    if not msg:
        continue

    data = list(msg.data)
    sid = data[0]

    # Session Control (0x10)
    if sid == 0x10 and data[1] == 0x03:
        print("Diagnostic session started")
        bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x50, 0x03], is_extended_id=False))

    # ECU Reset (0x11)
    elif sid == 0x11:
        print("ECU Reset command received")
        bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x51], is_extended_id=False))
        seed = None
        last_key = None
        failed_attempts = 0
        locked_until = 0

    # Security Access (0x27)
    elif sid == 0x27:
        subfn = data[1]

        # Check lockout
        if time.time() < locked_until:
            print("ECU locked due to failed attempts")
            bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x36], is_extended_id=False))
            continue

        # Request Seed
        if subfn in [1, 3, 5]:
            locked = False
            seed = generate_seed()
            last_key = None
            seed_sent_time = time.time()
            seed_high = (seed >> 8) & 0xFF
            seed_low = seed & 0xFF
            print(f"Generated seed for subfunction {hex(subfn)}: {seed:04X}")
            bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x67, subfn, seed_high, seed_low], is_extended_id=False))

        # Send Key
        elif subfn in [2, 4, 6]:
            if seed is None:
                print("No seed requested before key")
                bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x24], is_extended_id=False))
                continue

            key_recv = (data[2] << 8) | data[3]

            # Repeated key
            if last_key == key_recv or last_seed == seed:
                repeated_key = True
                print("Repeated key detected, rejecting")
                bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x22], is_extended_id=False))
                continue
            else:
                repeated_key = False

            # Timeout check
            if time.time() - seed_sent_time > SESSION_TIMEOUT:
                print("Key received after timeout, rejecting")
                bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x37], is_extended_id=False))
                continue

            expected_key = compute_key(seed)
            if key_recv == expected_key:
                print(f"Correct key for seed {seed:04X}")
                bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x67, subfn], is_extended_id=False))
                failed_attempts = 0
                last_seed = seed
                last_key = key_recv
                locked_until = 0

            else:
                print('wrong keyy')
                failed_attempts += 1
                print(f"Wrong key! Attempts: {failed_attempts}")
                if failed_attempts >= MAX_FAILED_ATTEMPTS:
                    locked_until = time.time() + LOCKOUT_TIME
                    locked = True
                    print(f"ECU locked for {LOCKOUT_TIME} seconds")
                bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x35], is_extended_id=False))

        else:
            print("Invalid subfunction")
            bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x12], is_extended_id=False))
