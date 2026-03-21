# APB UART Design Specification
**Block Name:** APB_UART
**Version:** 1.0
**Date:** 2026-01-10

---

## 1. Overview
The APB_UART is a Universal Asynchronous Receiver/Transmitter (UART) block with an APB slave interface for register access. It is used to provide a serial communication channel in SoC designs. The block supports full-duplex UART communication, programmable baud rate, configurable data frame format, and hardware flow control.

The block is used in applications requiring low-speed serial data communication with external peripherals such as GPS modules, Bluetooth chips, and debug consoles.

---

## 2. Features

### 2.1 APB Slave Interface
- Compliant with AMBA APB Protocol Specification v2.0
- 32-bit data bus
- Supports read and write register access
- No wait states on register reads

### 2.2 UART Transmitter
- 8-entry deep TX FIFO
- Configurable data bits: 5, 6, 7, or 8
- Configurable stop bits: 1 or 2
- Optional parity: even, odd, or none
- TX interrupt on FIFO empty or threshold

### 2.3 UART Receiver
- 8-entry deep RX FIFO
- Overrun, framing, and parity error detection
- RX interrupt on FIFO full or threshold
- Break condition detection

### 2.4 Baud Rate Generator
- Programmable baud rate via 16-bit divisor register
- Supports standard baud rates: 9600, 19200, 38400, 57600, 115200
- Clock source: system clock (pclk)

### 2.5 Hardware Flow Control
- RTS (Request to Send) output
- CTS (Clear to Send) input
- Auto-RTS/CTS mode supported

### 2.6 Interrupts
- TX FIFO empty interrupt
- RX FIFO threshold interrupt
- Error interrupt (framing, parity, overrun)
- Combined interrupt output (OR of all interrupts)

---

## 3. Interfaces

### 3.1 APB Interface (Slave)
| Signal     | Direction | Width | Description                          |
|------------|-----------|-------|--------------------------------------|
| pclk       | Input     | 1     | APB clock                            |
| presetn    | Input     | 1     | Active-low synchronous reset         |
| psel       | Input     | 1     | Peripheral select                    |
| penable    | Input     | 1     | Enable strobe                        |
| pwrite     | Input     | 1     | Write/Read select (1=write)          |
| paddr      | Input     | 8     | Register address                     |
| pwdata     | Input     | 32    | Write data                           |
| prdata     | Output    | 32    | Read data                            |
| pready     | Output    | 1     | Transfer ready                       |
| pslverr    | Output    | 1     | Slave error response                 |

### 3.2 UART Interface
| Signal     | Direction | Width | Description                          |
|------------|-----------|-------|--------------------------------------|
| uart_txd   | Output    | 1     | UART transmit data                   |
| uart_rxd   | Input     | 1     | UART receive data                    |
| uart_rts   | Output    | 1     | Request to send (active-low)         |
| uart_cts   | Input     | 1     | Clear to send (active-low)           |

### 3.3 Interrupt Interface
| Signal     | Direction | Width | Description                          |
|------------|-----------|-------|--------------------------------------|
| uart_intr  | Output    | 1     | Combined interrupt output            |
| tx_intr    | Output    | 1     | TX FIFO interrupt                    |
| rx_intr    | Output    | 1     | RX FIFO interrupt                    |
| err_intr   | Output    | 1     | Error interrupt                      |

---

## 4. Parameters

| Parameter       | Default | Description                              |
|-----------------|---------|------------------------------------------|
| DATA_WIDTH      | 32      | APB data bus width                       |
| ADDR_WIDTH      | 8       | APB address bus width                    |
| FIFO_DEPTH      | 8       | TX and RX FIFO depth (number of entries) |
| BAUD_DIVISOR_W  | 16      | Width of baud rate divisor register      |

---

## 5. Clock and Reset

### 5.1 Clock Domains
| Clock  | Source       | Frequency        | Affected Logic              |
|--------|--------------|------------------|-----------------------------|
| pclk   | SoC APB bus  | 50–100 MHz       | All logic (single domain)   |

### 5.2 Reset
| Reset   | Type        | Polarity    | Affected Domains |
|---------|-------------|-------------|------------------|
| presetn | Synchronous | Active-low  | All logic        |

---

## 6. Operating Modes

| Mode               | Description                                              |
|--------------------|----------------------------------------------------------|
| Normal Mode        | Full-duplex UART TX and RX with FIFO                    |
| Loopback Mode      | Internal loopback — TX connected to RX internally       |
| Flow Control Mode  | Hardware RTS/CTS handshaking enabled                    |
| Interrupt Mode     | Interrupts enabled, CPU notified on TX/RX events        |
| Polling Mode       | Interrupts disabled, software polls status registers    |

---

## 7. Compliance Standards
- AMBA APB Protocol Specification v2.0 (ARM IHI0024)
- RS-232 serial communication standard (framing, baud rates)

---

## 8. Known Constraints
- Maximum supported baud rate is 115200 bps when pclk = 50 MHz
- TX and RX FIFOs share the same depth parameter (FIFO_DEPTH)
- No DMA interface supported in this version
- pslverr is always driven low (no error response in v1.0)
