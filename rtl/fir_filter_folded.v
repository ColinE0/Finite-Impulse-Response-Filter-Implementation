module fir_filter_folded #(
  parameter ORDER = 10,          // 11-tap filter
  parameter COEFFICIENTS_WIDTH = 16,
  parameter DATA_WIDTH = 16
)(
  input wire clk,
  input wire reset,
  input wire signed [DATA_WIDTH-1:0] data_in,
  output reg signed [DATA_WIDTH-1:0] data_out
);

  // Coefficient storage (only need half + center due to folded structure)
  wire signed [COEFFICIENTS_WIDTH-1:0] coefficients [0:ORDER/2];
  assign coefficients[0] = 16'hFFEA;
  assign coefficients[1] = 16'h0009;
  assign coefficients[2] = 16'h0019;
  assign coefficients[3] = 16'h002D;
  assign coefficients[4] = 16'h003D;
  assign coefficients[5] = 16'h0043;  // The center coefficient (h[5])

  // Shift register (stores ORDER/2 + 1 samples)
  reg signed [DATA_WIDTH-1:0] shift_reg [0:ORDER/2];
  integer i;
  
  always @(posedge clk) begin
    if (reset) begin
      for (i=0; i<=ORDER/2; i=i+1) 
        shift_reg[i] <= 0;
    end else begin
      // Shift data through register
      shift_reg[0] <= data_in;
      for (i=1; i<=ORDER/2; i=i+1)
        shift_reg[i] <= shift_reg[i-1];
    end
  end

  // Folded MAC operation with proper accumulation
  reg signed [DATA_WIDTH+COEFFICIENTS_WIDTH:0] acc;  // Extra bit for an overflow
  reg signed [DATA_WIDTH-1:0] sum_symmetric [0:ORDER/2-1];
  
  always @(posedge clk) begin
    if (reset) begin
      acc <= 0;
      data_out <= 0;
      for (i=0; i<ORDER/2; i=i+1)
        sum_symmetric[i] <= 0;
    end else begin
      // Pre-calculate symmetric pairs
      for (i=0; i<ORDER/2; i=i+1)
        sum_symmetric[i] <= shift_reg[i] + shift_reg[ORDER/2 - i];
      
      // Initialize with the center tap
      acc <= $signed(coefficients[ORDER/2]) * $signed(shift_reg[ORDER/2]);
      
      // Accumulate symmetric taps
      for (i=0; i<ORDER/2; i=i+1)
        acc <= acc + ($signed(coefficients[i]) * $signed(sum_symmetric[i]));
      
      // Output with rounding
      data_out <= acc[23:8];  // Q8.8 output
    end
  end
endmodule