import can
import time

REQUEST_ID = 0x7DF
RESPONSE_ID = 0x7E8

# connection
bus = can.interface.Bus(channel='vcan0', interface='socketcan')

# function to send and receive data from ecu
def send_and_wait(data, timeout=1):
    msg = can.Message(arbitration_id=REQUEST_ID, data=data, is_extended_id=False)
    bus.send(msg)
    print(f"➡ Sent: {data}")

    start = time.time()
    while time.time() - start < timeout:
        resp = bus.recv()
        if resp and resp.arbitration_id == RESPONSE_ID:
            print(f"⬅ Response: {list(resp.data)}")
            return list(resp.data)
    print(" No response")
    return None



#  Diagnostic Session
resp = send_and_wait([0x10, 0x03])
if not resp or resp[0] != 0x50:
    print("Failed to start session")
    exit()

# Request Seed 
def request_seed():
    resp = send_and_wait([0x27, 0x01])
    if not resp or resp[0] != 0x67:
       print("Failed to get seed")
       exit()

    return (resp[2] << 8) | resp[3]
    print(f"Received Seed: {seed:04X}")

# session timeout test 
seed = request_seed()
time.sleep(5)
key = (seed + 1) & 0xFFFF
key_high = (key >> 8) & 0xFF
key_low = key & 0xFF
resp = send_and_wait([0x27, 0x02, key_high, key_low])
if resp and resp[0] ==  0x7F:
    print("Rejected the key as expected", )
else:
    print("key accepted after timeout!!!" ,hex(resp[0]))

# Sending  Correct Key
seed = request_seed()
key = (seed + 1) & 0xFFFF
key_high = (key >> 8) & 0xFF
key_low = key & 0xFF
resp = send_and_wait([0x27, 0x02, key_high, key_low])
if resp and resp[0] == 0x67:
    print("Correct key accepted")
else:
    print("correct key rejected!!!")

# Trying to Re-Sending Same Key
resp = send_and_wait([0x27, 0x02, key_high, key_low])
if resp and resp[0] == 0x7F:
    print("Repeated key correctly rejected")
else:
    print("Repeated key was accepted (security flaw)",hex(resp[0]))

# sending Wrong Keys Until Lockout
for i in range(5):
    wrong_key = (key + i + 5) & 0xFFFF
    wh = (wrong_key >> 8) & 0xFF
    wl = wrong_key & 0xFF
    resp = send_and_wait([0x27, 0x02, wh, wl])
    time.sleep(0.5)

# Requesting Seed While Locked (Should Fail)
resp = send_and_wait([0x27, 0x01])
if resp and resp[0] == 0x7F:
    print("ECU locked as expected")
else:
    print("ECU did not lock after failed attempts" , hex(resp[0]))

# Resetting ecu
resp = send_and_wait([0x11])
if resp and resp[0] == 0x51:
    print("ECU resetted as expected")
else:
    print("ECU did  not resetted" , hex(resp[0]))

# Trying to Re-Sending Same Key after resetting ecu
resp = send_and_wait([0x27, 0x02, key_high, key_low])
if resp and resp[0] == 0x7F:
    print("Repeated key correctly rejected after resetting")
else:
    print("Repeated key was accepted (security flaw)",hex(resp[0]))

print("Test complete")
bus.shutdown()
