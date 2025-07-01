`default_nettype none

module spi_peripheral (
    input  wire         clk,              // System clock
    input  wire         rst_n,            // Active low reset
    input  wire         sclk,             // Serial clock
    input  wire         ncs,              // Chip select
    input  wire         sdi,              // Master Out, Slave In
    output  reg [7:0]   en_reg_out_7_0,   
    output  reg [7:0]   en_reg_out_15_8,  
    output  reg [7:0]   en_reg_pwm_7_0,  
    output  reg [7:0]   en_reg_pwm_15_8,  
    output  reg [7:0]   pwm_duty_cycle,   
);

reg [15:0] shift_reg;
reg [4:0] bit_count;
reg received = 0;
reg processed = 0;
reg ncs1, ncs2;
reg sdi1, sdi2;
reg sclk1, sclk2;
wire sclk_rise = sclk2 & ~sclk1;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        ncs1 <= 1'b1;
        ncs2 <= 1'b1;
        sdi1 <= 1'b0;
        sdi2 <= 1'b0;
        sclk1 <= 0;
        sclk2 <= 0;
        shift_reg <= 16'd0;
        bit_count <= 5'd0;
        received <= 1'b0;
        processed <= 1'b0;
        en_reg_out_7_0 <= 8'b0;
        en_reg_out_15_8 <= 8'b0;
        en_reg_pwm_7_0 <= 8'b0;
        en_reg_pwm_15_8 <= 8'b0;
        pwm_duty_cycle <= 8'b0;

    end else begin
        // Synchornization
        ncs1 <= ncs; 
        ncs2 <= ncs1;
        sdi1 <= sdi;
        sdi2 <= sdi1;
        sclk1 <= sclk;
        sclk2 <= sclk1;

        // Default assignments to prevent inferred latches
        received <= received; // hold value unless changed
        processed <= processed;

        if (ncs2 == 1'b0) begin
            // Receiving mode
            if (sclk_rise && bit_count != 16) begin
                shift_reg <= {shift_reg[14:0], sdi2};
                bit_count <= bit_count + 1;
            end
        end else begin
            // Chip select deasserted
            if (bit_count == 16) begin
                received <= 1'b1;
                bit_count <= 5'd0;
            end else if (processed == 1'b1) begin
                received <= 1'b0;
            end
        end

        // Process shift_reg if received and not yet processed
        if (received && !processed) begin
            if (shift_reg[15]) begin
                case (shift_reg[14:8])
                    7'h00: en_reg_out_7_0 <= shift_reg[7:0];
                    7'h01: en_reg_out_15_8 <= shift_reg[7:0];
                    7'h02: en_reg_pwm_7_0 <= shift_reg[7:0];
                    7'h03: en_reg_pwm_15_8 <= shift_reg[7:0];
                    7'h04: pwm_duty_cycle <= shift_reg[7:0];
                    default: ; // ignore unknown addresses
                endcase
            end
            processed <= 1'b1;
        end else if (processed) begin
            processed <= 1'b0;
        end
    end
end

endmodule