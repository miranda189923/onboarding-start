`default_nettype none

module spi_peripheral (
    input  wire         clk,              // System clock
    input  wire         rst_n,            // Reset
    input  wire         sclk,             // Serial clock
    input  wire         ncs,              // Chip select
    input  wire         sdi,              // Master out, slave in
    output  reg [7:0]   en_reg_out_7_0,   
    output  reg [7:0]   en_reg_out_15_8,  
    output  reg [7:0]   en_reg_pwm_7_0,  
    output  reg [7:0]   en_reg_pwm_15_8,  
    output  reg [7:0]   pwm_duty_cycle,   
);

    reg ncs1, ncs2; // Synchronization registers
    reg sdi1, sdi2;
    reg sclk1, sclk2;    
    wire sclk_rise = sclk2 & ~sclk1;             // Detect rising edge of sclk
    reg [15:0] shift_reg;                        // Received message (1 R/W bit + 7 address bits + 8 data bits)
    reg [4:0]  bit_count;                        // Number of received bits
    reg [7:0]  temp_data;                        // Temporarily hold data for delayed update
    reg [6:0]  temp_addr;                        // Temporarily hold address for delayed update
    reg        temp_valid;                       // Trigger output registers update

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin 
            // Reset
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
            // Synchronize inputs with 2 stage flip flops
            ncs1 <= ncs;
            ncs2 <= ncs1;
            sdi1 <= sdi;
            sdi2 <= sdi1;
            sclk1 <= sclk;
            sclk2 <= sclk1;

            if (!ncs2) begin
                if (sclk_rise && bit_count != 16) begin
                    shift_reg <= {shift_reg[14:0], sdi2};     // Shift in new bits during active transaction
                    bit_count <= bit_count + 1;               // Increment bit counter
                end
            end else begin
                if (bit_count == 16) begin
                    if (shift_reg[15]) begin                  // Write command
                        temp_data <= shift_reg[7:0];          // Store data
                        temp_addr <= shift_reg[14:8];         // Store address
                        temp_valid <= 1'b1;                   // Set flag for update in next cycle
                    end
                    bit_count <= 5'd0;
                    shift_reg <= 16'd0;
                end else begin
                    bit_count <= 5'd0; 
                    shift_reg <= 16'd0;
                end
            end

            if (temp_valid) begin                              // Update output register based on stored address
                case (temp_addr)
                    7'h00: en_reg_out_7_0 <= temp_data;
                    7'h01: en_reg_out_15_8 <= temp_data;
                    7'h02: en_reg_pwm_7_0 <= temp_data;
                    7'h03: en_reg_pwm_15_8 <= temp_data;
                    7'h04: pwm_duty_cycle <= temp_data;
                    default: ; // Ignore unknown addresses
                endcase
                temp_valid <= 1'b0;
            end
        end
    end

endmodule