`default_nettype none

module spi_peripheral (
    input  wire         clk,              // System clock
    input  wire         rst_n,            // Active low reset
    input  wire         sclk,             // Serial clock
    input  wire         ncs,              // Chip select (active low)
    input  wire         sdi,              // Master Out, Slave In
    output reg  [7:0]   en_reg_out_7_0,   // Enable outputs (bits 7:0)
    output reg  [7:0]   en_reg_out_15_8,  // Enable outputs (bits 15:8)
    output reg  [7:0]   en_reg_pwm_7_0,   // Enable PWM (bits 7:0)
    output reg  [7:0]   en_reg_pwm_15_8,  // Enable PWM (bits 15:8)
    output reg  [7:0]   pwm_duty_cycle    // PWM duty cycle (0x00=0%, 0xFF=100%)
);

    // Synchronization registers
    reg ncs1, ncs2;
    reg sdi1, sdi2;
    reg sclk1, sclk2;
    wire sclk_rise = sclk2 & ~sclk1; // Detect rising edge of sclk

    // SPI payload and bit counter
    reg [15:0] shift_reg;           // 16-bit payload (1 R/W + 7 address + 8 data)
    reg [4:0]  bit_count;           // Count received bits (0 to 15)

    // Temporary registers for one-cycle delay
    reg [7:0]  temp_data;           // Hold data for delayed update
    reg [6:0]  temp_addr;           // Hold address for delayed update
    reg        temp_valid;          // Flag for valid data/address

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Reset all registers
            ncs1 <= 1'b1;
            ncs2 <= 1'b1;
            sdi1 <= 1'b0;
            sdi2 <= 1'b0;
            sclk1 <= 1'b0;
            sclk2 <= 1'b0;
            shift_reg <= 16'd0;
            bit_count <= 5'd0;
            temp_data <= 8'd0;
            temp_addr <= 7'd0;
            temp_valid <= 1'b0;
            en_reg_out_7_0 <= 8'd0;
            en_reg_out_15_8 <= 8'd0;
            en_reg_pwm_7_0 <= 8'd0;
            en_reg_pwm_15_8 <= 8'd0;
            pwm_duty_cycle <= 8'd0;
        end else begin
            // Synchronize inputs
            ncs1 <= ncs;
            ncs2 <= ncs1;
            sdi1 <= sdi;
            sdi2 <= sdi1;
            sclk1 <= sclk;
            sclk2 <= sclk1;

            // Handle SPI transaction
            if (!ncs2) begin
                // Active transaction: receive data on sclk rising edge
                if (sclk_rise && bit_count != 16) begin
                    shift_reg <= {shift_reg[14:0], sdi2};
                    bit_count <= bit_count + 1;
                end
            end else begin
                // Chip select deasserted: reset bit counter and capture data
                if (bit_count == 16) begin
                    if (shift_reg[15]) begin // Write command
                        temp_data <= shift_reg[7:0];
                        temp_addr <= shift_reg[14:8];
                        temp_valid <= 1'b1;
                    end
                    bit_count <= 5'd0;
                    shift_reg <= 16'd0;
                end else begin
                    bit_count <= 5'd0; // Reset for partial transactions
                    shift_reg <= 16'd0;
                end
            end

            // Update output registers one cycle after valid write transaction
            if (temp_valid) begin
                case (temp_addr)
                    7'h00: en_reg_out_7_0 <= temp_data;
                    7'h01: en_reg_out_15_8 <= temp_data;
                    7'h02: en_reg_pwm_7_0 <= temp_data;
                    7'h03: en_reg_pwm_15_8 <= temp_data;
                    7'h04: pwm_duty_cycle <= temp_data;
                    default: ; // Ignore unknown addresses
                endcase
                temp_valid <= 1'b0; // Clear after update
            end
        end
    end

endmodule