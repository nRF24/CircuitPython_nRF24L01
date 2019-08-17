import time, struct, board, digitalio as dio
from circuitpython_nrf24l01.fake_ble import FakeBLE

# change these (digital output) pins accordingly
ce = dio.DigitalInOut(board.D7)
csn = dio.DigitalInOut(board.D5)

# using board.SPI() automatically selects the MCU's
# available SPI pins, board.SCK, board.MOSI, board.MISO
spi = board.SPI() # init spi bus object

# initialize the nRF24L01 on the spi bus object as a BLE radio using
rf2ble = FakeBLE(spi, csn, ce, name=b'nRF24')
# the name parameter is going to be its braodcasted BLE name
# this can be changed at any time using the attribute
rf2ble.name = b'RFtest'

def master(count=15):
    rf2ble.open_tx_pipe() # endure the tx pip is properly addressed
    for i in range(count): # advertise data this many times
        # pack into bytearray using struct.pack()
        rf2ble.send(struct.pack('i', count)) # 'i' = 4 byte integer
        # channel is automatically managed by send() per BLE specs
        time.sleep(1) # wait till next broadcast
        if (count - i) % 5 == 0 or (count - i) < 5:
            print(count - i, 'advertisments left to go!')
