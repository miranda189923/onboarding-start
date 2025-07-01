# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

async def await_half_sclk(dut):
    """Wait for half an SCLK period (5 µs, assuming 100 kHz SPI clock)."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        if (start_time + 100 * 100 * 0.5) < cocotb.utils.get_sim_time(units="ns"):
            break

def ui_in_logicarray(ncs, bit, sclk):
    """Create LogicArray for ui_in with ncs, sdi, and sclk."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send a 16-bit SPI transaction: 1-bit R/W, 7-bit address, 8-bit data.
    Parameters:
    - r_w: True for write, False for read
    - address: 7-bit address (0-127)
    - data: 8-bit data (0-255)
    """
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    first_byte = (int(r_w) << 7) | address
    sclk, ncs, bit = 0, 0, 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    for i in range(8):
        bit = (first_byte >> (7 - i)) & 0x1
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    for i in range(8):
        bit = (data_int >> (7 - i)) & 0x1
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    sclk, ncs, bit = 0, 1, 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

async def setup_pwm(dut, output_bit=0):
    """Configure DUT for PWM testing on specified output bit."""
    dut._log.info(f"Enabling output and PWM for uo_out[{output_bit}]")
    await send_spi_transaction(dut, 1, 0x00, 1 << output_bit)  # Enable output
    await send_spi_transaction(dut, 1, 0x02, 1 << output_bit)  # Enable PWM
    await ClockCycles(dut.clk, 100)  # Wait for stable state

async def wait_for_value(dut, signal, bit_index, target_value, timeout_cycles=5000):
    """
    Poll specified signal bit until it equals target_value or times out.
    Parameters:
    - signal: Signal to monitor (e.g., dut.uo_out)
    - bit_index: Bit to check (0-7)
    - target_value: Expected value (0 or 1)
    - timeout_cycles: Maximum clock cycles to wait
    Returns: Simulation time (ns) when target value is detected
    """
    for _ in range(timeout_cycles):
        bit_value = (int(signal.value) >> bit_index) & 1
        if bit_value == target_value:
            return cocotb.utils.get_sim_time(units="ns")
        await ClockCycles(dut.clk, 1)
    raise TimeoutError(f"Timed out waiting for {signal._name}[{bit_index}] to become {target_value}")

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    await send_spi_transaction(dut, 1, 0x00, 0xF0)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000)
    dut._log.info("Write transaction, address 0x01, data 0xCC")
    await send_spi_transaction(dut, 1, 0x01, 0xCC)
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)
    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)
    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    await send_spi_transaction(dut, 0, 0x00, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    dut._log.info("Read transaction (invalid), address 0x41, data 0xEF")
    await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)
    dut._log.info("Write transaction, address 0x02, data 0xFF")
    await send_spi_transaction(dut, 1, 0x02, 0xFF)
    await ClockCycles(dut.clk, 100)
    dut._log.info("Write transaction, address 0x04, data 0xCF")
    await send_spi_transaction(dut, 1, 0x04, 0xCF)
    await ClockCycles(dut.clk, 30000)
    dut._log.info("Write transaction, address 0x04, data 0xFF")
    await send_spi_transaction(dut, 1, 0x04, 0xFF)
    await ClockCycles(dut.clk, 30000)
    dut._log.info("Write transaction, address 0x04, data 0x00")
    await send_spi_transaction(dut, 1, 0x04, 0x00)
    await ClockCycles(dut.clk, 30000)
    dut._log.info("Write transaction, address 0x04, data 0x01")
    await send_spi_transaction(dut, 1, 0x04, 0x01)
    await ClockCycles(dut.clk, 30000)
    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Start Frequency test")
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())
    dut._log.info("Reset")
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    dut._log.info("Testing at 50 percent duty cycle")
    await setup_pwm(dut, output_bit=0)
    await send_spi_transaction(dut, 1, 0x04, 0x80)
    await ClockCycles(dut.clk, 20000)
    t0 = await wait_for_value(dut, dut.uo_out, 0, 1, timeout_cycles=5000)
    t1 = await wait_for_value(dut, dut.uo_out, 0, 0, timeout_cycles=5000)
    t2 = await wait_for_value(dut, dut.uo_out, 0, 1, timeout_cycles=5000)
    period_ns = t2 - t0
    freq_hz = 1e9 / period_ns
    dut._log.info(f"Measured period {period_ns} ns ⇒ {freq_hz:.1f} Hz")
    assert 2900 < freq_hz < 3100, f"Got {freq_hz:.1f} Hz, expected ~3000 Hz"
    dut._log.info("PWM Frequency test completed successfully")

@cocotb.test()
async def test_pwm_duty(dut):
    """Test PWM duty cycle on uo_out[0] for 0%, 50%, and 100%."""
    dut._log.info("Start PWM Duty Cycle test")
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset DUT
    dut._log.info("Reset")
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Define test cases: (expected duty cycle %, data value, tolerance %)
    test_cases = [
        (50, 0x80, 5),   # 50% ± 5%
        (0, 0x00, 0.1),  # 0% (check output low)
        (100, 0xFF, 0.1) # 100% (check output high)
    ]

    # Setup PWM for uo_out[0]
    await setup_pwm(dut, output_bit=0)

    # Test each duty cycle
    for expected_duty, data, tolerance in test_cases:
        dut._log.info(f"Testing {expected_duty}% duty cycle (data=0x{data:02X})")
        await send_spi_transaction(dut, 1, 0x04, data)
        await ClockCycles(dut.clk, 10000)  # Wait for stable PWM output

        if expected_duty == 0:
            # Special case: 0% duty cycle should keep output low
            value = (int(dut.uo_out.value) >> 0) & 1
            dut._log.info(f"uo_out[0] = {value}")
            assert value == 0, f"Expected 0% duty cycle (uo_out[0]=0), got {value}"
        elif expected_duty == 100:
            # Special case: 100% duty cycle should keep output high
            value = (int(dut.uo_out.value) >> 0) & 1
            dut._log.info(f"uo_out[0] = {value}")
            assert value == 1, f"Expected 100% duty cycle (uo_out[0]=1), got {value}"
        else:
            # Measure duty cycle for non-edge cases
            t0 = await wait_for_value(dut, dut.uo_out, 0, 1, timeout_cycles=5000)
            t1 = await wait_for_value(dut, dut.uo_out, 0, 0, timeout_cycles=5000)
            t2 = await wait_for_value(dut, dut.uo_out, 0, 1, timeout_cycles=5000)
            period = t2 - t0
            high_time = t1 - t0
            measured_duty = (high_time / period) * 100
            dut._log.info(f"Period: {period} ns, High time: {high_time} ns, Duty Cycle: {measured_duty:.1f}%")
            assert (expected_duty - tolerance) <= measured_duty <= (expected_duty + tolerance), \
                f"Expected {expected_duty}% ± {tolerance}%, got {measured_duty:.1f}%"

    dut._log.info("PWM Duty Cycle test completed successfully")