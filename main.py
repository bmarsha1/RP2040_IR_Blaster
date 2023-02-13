import rp2
from machine import Pin
import time
import network
import uasyncio as asyncio

NEC_WAVE_IRQ = 5
NEC_WAVE_PERIODS = 21
NEC_SQUARE_FREQ = 152000

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def nec_square():
    NEC_WAVE_IRQ = 5
    NEC_WAVE_PERIODS = 21
    wrap_target()
    set(x, NEC_WAVE_PERIODS - 1)
    wait(1, irq, NEC_WAVE_IRQ)
    label("squarewave")
    set(pins, 1)
    set(pins, 0) [1]
    jmp(x_dec, "squarewave")
    wrap()

COMMAND_INIT_WAVES = 16
NEC_DATA_FREQ = 3571

@rp2.asm_pio()
def nec_data():
    NEC_WAVE_IRQ = 5
    COMMAND_INIT_WAVES = 16
    wrap_target()
    pull()
    
    #9ms wave
    set(x, COMMAND_INIT_WAVES - 1)
    label("command_init")
    irq(NEC_WAVE_IRQ)
    jmp(x_dec, "command_init")

    #4.5ms pause
    nop() [15]

    irq(NEC_WAVE_IRQ) [1]
    label("bitloop")
    out(x, 1)
    jmp(not_x, "zero")
    nop() [3]
    label("zero")
    irq(NEC_WAVE_IRQ)
    jmp(not_osre, "bitloop")
    wrap()

square_sm = rp2.StateMachine(0, nec_square, NEC_SQUARE_FREQ, set_base=Pin(0))
data_sm = rp2.StateMachine(1, nec_data, NEC_DATA_FREQ, out_shiftdir=rp2.PIO.SHIFT_LEFT)

square_sm.active(1)
data_sm.active(1)


LED_ON = 0xE2
LED_OFF = 0x21 

def led_command(command):
    data = 0x00FF0000
    data = data | (command << 8)
    data = data | (command ^ 0xFF)
    data_sm.put(data)

def led_on():
    led_command(LED_ON)

def led_off():
    led_command(LED_OFF)

async def dot():
    led_on()
    await asyncio.sleep(0.25)
    led_off()
    await asyncio.sleep(0.5)

async def dash():
    led_on()
    await asyncio.sleep(1)
    led_off()
    await asyncio.sleep(0.5)

async def morse_code(string):
    for char in string.upper():
        if char == 'A':
            await dot()
            await dash()
        elif char == 'B':
            await dash()
            await dot()
            await dot()
            await dot()
        elif char == 'C':
            await dash()
            await dot()
            await dash()
            await dot()
        elif char == 'D':
            await dash()
            await dot()
            await dot()
        elif char == 'E':
            await dot()
        elif char == 'F':
            await dot()
            await dot()
            await dash()
            await dot()
        elif char == 'G':
            await dash()
            await dash()
            await dot()
        elif char == 'H':
            await dot()
            await dot()
            await dot()
            await dot()
        elif char == 'I':
            await dot()
            await dot()
        elif char == 'J':
            await dot()
            await dash()
            await dash()
            await dash()
        elif char == 'K':
            await dash()
            await dot()
            await dash()
        elif char == 'L':
            await dot()
            await dash()
            await dot()
            await dot()
        elif char == 'M':
            await dash()
            await dash()
        elif char == 'N':
            await dash()
            await dot()
        elif char == 'O':
            await dash()
            await dash()
            await dash()
        elif char == 'P':
            await dot()
            await dash()
            await dash()
            await dot()
        elif char == 'Q':
            await dash()
            await dash()
            await dot()
            await dash()
        elif char == 'R':
            await dot()
            await dash()
            await dot()
        elif char == 'S':
            await dot()
            await dot()
            await dot()
        elif char == 'T':
            await dash()
        elif char == 'U':
            await dot()
            await dot()
            await dash()
        elif char == 'V':
            await dot()
            await dot()
            await dot()
            await dash()
        elif char == 'W':
            await dot()
            await dash()
            await dash()
        elif char == 'X':
            await dash()
            await dot()
            await dot()
            await dash()
        elif char == 'Y':
            await dash()
            await dot()
            await dash()
            await dash()
        elif char == 'Z':
            await dash()
            await dash()
            await dot()
            await dot()
        await asyncio.sleep(0.5)

ssid = ''
password = ''

html = """<!DOCTYPE html>
<html>
    <head> <title>Prank Tyler</title> </head>
    <body> <h1>Prank Tyler</h1>
        <p>{}</p>
        <form action="/morse_code">
            <label for="prank"> Morse Code:</label>
            <input type="text" id="prank" name="prank"><br><br>
            <input type="submit" value="Submit">
    </body>
</html>
"""
wlan = network.WLAN(network.STA_IF)

def connect_to_network():
    wlan.active(True)
    wlan.config(pm = 0xa11140)  # Disable power-save mode
    wlan.connect(ssid, password)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        time.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()
        print('ip = ' + status[0])


current_morse_code = ""

async def serve_client(reader, writer):
    global current_morse_code
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line)

    prank_req_str = "/morse_code?prank="

    prank_index = request.find(prank_req_str)
    print("prank = " + str(prank_index))
    
    if(prank_index >= 0):
        new_morse_code = ""
        i = prank_index + len(prank_req_str)
        while i < len(request):
            char = request[i]
            if char == ' ':
                break
            elif char == '+':
                new_morse_code += ' '
            else:
                new_morse_code += char
            i += 1

        current_morse_code = new_morse_code

    response = html.format("Current morse code: " + str(current_morse_code))
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)

    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")


async def main():
    print('Connecting to Network...')
    connect_to_network()

    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    while True:
        await morse_code(current_morse_code)
        await asyncio.sleep(1)
        
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()