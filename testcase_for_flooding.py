import can
import time

VCAN_CHANNEL = "vcan0"
REQUEST_ID = 0x7DF

bus = can.interface.Bus(channel=VCAN_CHANNEL, interface="socketcan")

def flood(sid, count, delay):
    print(f"\n Flooding SID {hex(sid)} with {count} messages, delay={delay}s")
    for _ in range(count):
        bus.send(can.Message(arbitration_id=REQUEST_ID, data=[sid, 0x01], is_extended_id=False))
        time.sleep(delay)

# Small reset flood — lock 0x11 only
flood(0x11, 12, 0.01)
# time.sleep(2)

# sending other request while reset request is locked
flood(0x10,2,0.01)

# Big reset flood — lock ALL comms (0x28)
flood(0x11, 30, 0.01)
# time.sleep(2)

# Try comm control after lock
flood(0x28, 3, 0.01)
time.sleep(10)

# Trying after ecu unlocked
flood(0x28,3,0.01)


print("Test complete")
bus.shutdown()