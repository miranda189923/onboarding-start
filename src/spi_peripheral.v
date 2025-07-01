module spi_peripheral (
    input wire ncs,
    input wire clk,
    input wire rst_n,
    input wire sclk,
    input wire sdi,
    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);

reg [15:0] message;
reg [4:0] bit_cnt;
reg text_received = 0;
reg text_processed = 0;

// Synchronized signals
reg ncs_sync1, ncs_sync2;
reg sdi_sync1, sdi_sync2;
reg sclk_sync1, sclk_sync2;

wire pos_sclk = sclk_sync2 & ~sclk_sync1;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        // Reset everything
        ncs_sync1 <= 1'b1;
        ncs_sync2 <= 1'b1;
        sdi_sync1 <= 1'b0;
        sdi_sync2 <= 1'b0;
        sclk_sync1 <= 0;
        sclk_sync2 <= 0;

        message <= 16'd0;
        bit_cnt <= 5'd0;
        text_received <= 1'b0;
        text_processed <= 1'b0;

        en_reg_out_7_0 <= 8'b0;
        en_reg_out_15_8 <= 8'b0;
        en_reg_pwm_7_0 <= 8'b0;
        en_reg_pwm_15_8 <= 8'b0;
        pwm_duty_cycle <= 8'b0;

    end else begin
        // Synchronize inputs
        ncs_sync1 <= ncs;
        ncs_sync2 <= ncs_sync1;
        sdi_sync1 <= sdi;
        sdi_sync2 <= sdi_sync1;
        sclk_sync1 <= sclk;
        sclk_sync2 <= sclk_sync1;

        // Default assignments to prevent inferred latches
        text_received <= text_received; // hold value unless changed
        text_processed <= text_processed;

        if (ncs_sync2 == 1'b0) begin
            // Receiving mode
            if (pos_sclk && bit_cnt != 16) begin
                message <= {message[14:0], sdi_sync2};
                bit_cnt <= bit_cnt + 1;
            end
        end else begin
            // Chip select deasserted
            if (bit_cnt == 16) begin
                text_received <= 1'b1;
                bit_cnt <= 5'd0;
            end else if (text_processed == 1'b1) begin
                text_received <= 1'b0;
            end
        end

        // Process message if received and not yet processed
        if (text_received && !text_processed) begin
            if (message[15]) begin
                case (message[14:8])
                    7'h00: en_reg_out_7_0 <= message[7:0];
                    7'h01: en_reg_out_15_8 <= message[7:0];
                    7'h02: en_reg_pwm_7_0 <= message[7:0];
                    7'h03: en_reg_pwm_15_8 <= message[7:0];
                    7'h04: pwm_duty_cycle <= message[7:0];
                    default: ; // ignore unknown addresses
                endcase
            end
            text_processed <= 1'b1;
        end else if (text_processed) begin
            text_processed <= 1'b0;
        end
    end
end

endmodule