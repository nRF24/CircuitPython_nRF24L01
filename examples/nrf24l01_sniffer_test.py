"""
This is only an example of how to use the Sniffer class.
Only channel sniffing is done as address sniffing takes a VERY LONG time.
"""
import board
from digitalio import DigitalInOut
from circuitpython_nrf24l01.rf24 import RF24
from circuitpython_nrf24l01.sniffer import Sniffer

csn = DigitalInOut(board.D7)
ce = DigitalInOut(board.D9)
SPI = board.SPI()
nrf = RF24(SPI, csn, ce) # data_rate defaults to 2 Mbps
snif = Sniffer(nrf)

snif.find_channel(1.5) # snif for 1.5 seconds per channel
nrf.data_rate = 250 # change the data rate
snif.find_channel(1.5) # snif for packets at 250Kbps

# to determine an RF address via sniffing, uncomment the next line
# NOTE this next function will take a VERY LONG time
# snif.find_address()
