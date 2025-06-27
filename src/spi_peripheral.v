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

    reg ncs1, ncs2;
    reg sclk1, sclk2;
    reg sdi1, sdi2;
    wire sclk_rise = sclk2 & ~sclk1;
    reg [15:0] shift_reg = 16'h0; // 16 bits SPI word (1 R/W + 7 Address + 8 Data)
    reg [4:0] bit_count = 5'd0;   // Count bits received
    reg msg_complete = 1'b0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Reset all registers
            ncs1 <= 1'b1;
            ncs2 <= 1'b1;
            sclk1 <= 1'b0;  
            sclk2 <= 1'b0;
            sdi1 <= 1'b0;  
            sdi2 <= 1'b0;
            msg_complete <= 1'b0;
            shift_reg <= 16'h0;
            bit_count <= 5'd0;
            en_reg_out_7_0 <= 8'h00;
            en_reg_out_15_8 <= 8'h00;
            en_reg_pwm_7_0 <= 8'h00;
            en_reg_pwm_15_8 <= 8'h00;
            pwm_duty_cycle <= 8'h00;
        end else begin
            // Synchronize ncs, sclk and sdi using two FF
            ncs1 <= ncs;
            sclk1 <= sclk;
            sdi1 <= sdi;
            ncs2 <= ncs1;
            sclk2 <= sclk1;
            sdi2 <= sdi1;
            
            // Bit shifting and increment bit counter
            if (!ncs2) begin
                if (sclk_rise && bit_count < 16) begin
                    shift_reg <= {shift_reg[14:0], sdi2};
                    bit_count <= bit_count + 1;
                    if (bit_count == 15) begin
                        msg_complete <= 1'b1;
                    end
                end
            end else if (!ncs1 && ncs2) begin
                if (msg_complete) begin
                    if (shift_reg[15]) begin
                        case (shift_reg[14:8])
                            7'h00: en_reg_out_7_0 <= shift_reg[7:0];
                            7'h01: en_reg_out_15_8 <= shift_reg[7:0];
                            7'h02: en_reg_pwm_7_0 <= shift_reg[7:0];
                            7'h03: en_reg_pwm_15_8 <= shift_reg[7:0];
                            7'h04: pwm_duty_cycle <= shift_reg[7:0];
                            default: ; 
                        endcase
                    end
                    msg_complete <= 1'b0;
                end
                // Reset
                bit_count <= 5'd0; 
                shift_reg <= 16'h0;
            end 
        end
    end
endmodule