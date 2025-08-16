import can
import time

REQUEST_ID = 0x7DF
RESPONSE_ID = 0x7E8

bus = can.interface.Bus(channel='vcan0', interface='socketcan')

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
    print("No response")
    return None

def seed_request():
    resp = send_and_wait([0x27, 0x01])
    if not resp or resp[0] != 0x67:
        print("Failed to get seed")
        exit()

    seed_val = (resp[2] << 8) | resp[3]
    print(f"Received Seed: {seed_val:04X}")
    return seed_val

sessions = [0x01, 0x02, 0x03]

for session in sessions:
    print(f"Testing session {hex(session)}")

    # Change session
    resp = send_and_wait([0x10, session])
    if not resp or resp[0] != 0x50:
        print("Failed to start session")
        exit()
    print("Session change response:", resp)

    # Request seed and send wrong key
    seed = seed_request()
    wrong_key = (seed + 2) & 0xFFFF 
    key_high = (wrong_key >> 8) & 0xFF
    key_low = wrong_key & 0xFF

    resp = send_and_wait([0x27, 0x02, key_high, key_low])
    if resp and resp[0] == 0x7F:
        print("Wrong key rejected as expected -- TEST PASS")
    else:
        print("Wrong key accepted -- TEST FAIL")

    #Requesting seed and sending crct key
    seed = seed_request()
    key = (seed + 1) & 0xFFFF 
    key_high = (key >> 8) & 0xFF
    key_low = key & 0xFF

    resp = send_and_wait([0x27, 0x02, key_high, key_low])
    if resp and resp[0] == 0x67:
        print(" correct key accepted as expected -- TEST PASS")
    else:
        print("correct key rejected -- TEST FAIL")

    # Trying to Re-Sending Same Key
    resp = send_and_wait([0x27, 0x02, key_high, key_low])
    if resp and resp[0] == 0x7F:
        print("Repeated key correctly rejected -- TEST PASS")
    else:
        print("Repeated key was accepted (security flaw)",hex(resp[0]))

    time.sleep(2)