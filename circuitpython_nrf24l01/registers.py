"""nRF24L01(+) registers"""

REGISTERS = {
    'CONFIG'     : 0x00,# register for configuring IRQ, CRC, PWR & RX/TX roles
    'EN_AA'      : 0x01,# register for auto-ACK feature. Each bit represents this feature per pipe
    'EN_RX'      : 0x02,# register to open/close pipes. Each bit represents this feature per pipe
    'SETUP_AW'   : 0x03,# address width register
    'SETUP_RETR' : 0x04,# auto-retry count and delay register
    'RF_CH'      : 0x05,# channel register
    'RF_SETUP'   : 0x06,# RF Power Amplifier & Data Rate
    'RX_ADDR'    : 0x0a,# RX pipe addresses rangeing [0,5]:[0xA:0xF]
    'RX_PW'      : 0x11,# RX payload widths on pipes ranging [0,5]:[0x11,0x16]
    'FIFO'       : 0x17,# register containing info on both RX/TX FIFOs + re-use payload flag
    'DYNPD'      : 0x1c,# dynamic payloads feature. Each bit represents this feature per pipe
    'FEATURE'    : 0x1d # global toggles for dynamic payloads, auto-ACK, and custom ACK features
}
