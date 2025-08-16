import can
import time
import random

VCAN_CHANNEL = 'vcan0'
RESPONSE_ID = 0x7E8
REQUEST_ID = 0x7DF


# ECU state variables
seed = None
last_key = None
seed_sent_time = 0
current_session = 0x01

# Start VCAN
bus = can.interface.Bus(channel=VCAN_CHANNEL, interface='socketcan')
print(f"ECU started on {VCAN_CHANNEL}")

# Generate random seed
def generate_seed():
    last_key = None
    return random.randint(0, 0xFFFF)  

# Compute key
def compute_key(seed_val):
    return (seed_val + 1) & 0xFFFF

# ecu reset function
def reset_ecu_state():
    global seed, last_key, failed_attempts, locked_until
    seed = None
    last_key = None
    failed_attempts = 0
    locked_until = 0
    print("ECU security state reset")

while True:
    msg = bus.recv()
    if not msg:
        continue

    data = list(msg.data)
    sid = data[0]

    # Session Control (0x10)
    if sid == 0x10:
        new_session = data[1]
        if current_session != new_session:
            print(f"session changes from {hex(current_session)} to {hex(new_session)}")
            current_session = new_session
            reset_ecu_state()
        print("Diagnostic session started")
        bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x50, 0x03], is_extended_id=False))

    # Security Access (0x27)
    elif sid == 0x27:
        subfn = data[1]
        # Request Seed
        if subfn in [1, 3, 5]:
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
            if last_key == key_recv :
                print("Repeated key detected, rejecting")
                bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x22], is_extended_id=False))
                continue

            # Correct key
            expected_key = compute_key(seed)
            if key_recv == expected_key:
                print(f"Correct key for seed {seed:04X}")
                bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x67, subfn], is_extended_id=False))
                failed_attempts = 0
                locked_until = 0
                last_key = key_recv

            else:
                print('wrong keyy')
                bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x35], is_extended_id=False))

        else:
            print("Invalid subfunction")
            bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, 0x27, 0x12], is_extended_id=False))
