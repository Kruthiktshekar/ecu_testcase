import can
import time

VCAN_CHANNEL = "vcan0"
RESPONSE_ID = 0x7E8

# Flood detection
RESET_FLOOD_THRESHOLD = 10    
RESET_FLOOD_INTERVAL = 1      
RESET_LOCKOUT_TIME = 2         

COMM_LOCK_THRESHOLD = 20       
COMM_LOCKOUT_TIME = 4       

# State
reset_times = []
reset_lock_until = 0
comm_lock_until = 0

bus = can.interface.Bus(channel=VCAN_CHANNEL, interface="socketcan")
print(f"ECU started on {VCAN_CHANNEL}")

def send_positive(sid):
    bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[sid + 0x40], is_extended_id=False))

def send_negative(sid, nrc):
    bus.send(can.Message(arbitration_id=RESPONSE_ID, data=[0x7F, sid, nrc], is_extended_id=False))

while True:
    msg = bus.recv()
    if not msg:
        continue

    data = list(msg.data)
    if len(data) < 1:
        continue

    sid = data[0]
    now = time.time()

    # Communication control block if globally locked
    if sid == 0x28 and now < comm_lock_until:
        print(f"All communication locked until {comm_lock_until:.2f}")
        send_negative(sid, 0x21)  
        continue

    # ECU Reset flood detection
    if sid == 0x11:
        
        reset_times = [t for t in reset_times if now - t <= RESET_FLOOD_INTERVAL]
        reset_times.append(now)

         # Trigger full comms lock if massive flood
        if len(reset_times) > COMM_LOCK_THRESHOLD:
            comm_lock_until = now + COMM_LOCKOUT_TIME
            print(f"Massive flood — Disabling ALL comms for {COMM_LOCKOUT_TIME}s")
            send_negative(sid, 0x21)
            continue

        # Lock 0x11 only
        if now < reset_lock_until:
            print(f"Reset requests locked until {reset_lock_until:.2f}")
            send_negative(sid, 0x21)
            continue

        # Trigger reset lock
        if len(reset_times) == RESET_FLOOD_THRESHOLD:
            reset_lock_until = now + RESET_LOCKOUT_TIME
            print(f"Flood detected for 0x11 — Locking reset for {RESET_LOCKOUT_TIME}s")
            send_negative(sid, 0x21)
            continue


        # Otherwise, accept request
        print(f"Processing Reset request: {data}")
        send_positive(sid)
        continue

    # Handle normal requests
    if sid == 0x10:
        print(f"Diagnostic Session Control: {data}")
        send_positive(sid)

    elif sid == 0x28:
        print(f"Communication Control: {data}")
        send_positive(sid)
