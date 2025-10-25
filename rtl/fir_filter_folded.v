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

  // Coefficient storage for folded symmetric FIR (Q8.8 format)
  // Generated from MATLAB design with unity gain compensation
  wire signed [COEFFICIENTS_WIDTH-1:0] coefficients [0:ORDER/2];
  assign coefficients[0] = 16'hFEDB;
  assign coefficients[1] = 16'h0008;
  assign coefficients[2] = 16'h0015;
  assign coefficients[3] = 16'h0026;
  assign coefficients[4] = 16'h0033;
  assign coefficients[5] = 16'h0038;  // center

  // Shift register (stores ORDER/2 + 1 samples for folded operation)
  reg signed [DATA_WIDTH-1:0] shift_reg [0:ORDER/2];
  integer i;
  
  // Folded MAC operation
  reg signed [DATA_WIDTH+COEFFICIENTS_WIDTH:0] acc;  // Extended precision accumulator
  reg signed [DATA_WIDTH-1:0] sum_symmetric [0:ORDER/2-1];
  
  always @(posedge clk) begin
    if (reset) begin
      // Initialize all registers
      for (i = 0; i <= ORDER/2; i = i + 1) 
        shift_reg[i] <= 0;
      acc <= 0;
      data_out <= 0;
      for (i = 0; i < ORDER/2; i = i + 1)
        sum_symmetric[i] <= 0;
    end else begin
      // Shift data through register (folded delay line)
      shift_reg[0] <= data_in;
      for (i = 1; i <= ORDER/2; i = i + 1)
        shift_reg[i] <= shift_reg[i-1];
      
      // Pre-calculate symmetric pairs for folded multiplication
      for (i = 0; i < ORDER/2; i = i + 1)
        sum_symmetric[i] <= shift_reg[i] + shift_reg[ORDER/2 - i];
      
      // Initialize accumulator with center tap (non-symmetric)
      acc <= $signed(coefficients[ORDER/2]) * $signed(shift_reg[ORDER/2]);
      
      // Accumulate symmetric tap pairs
      for (i = 0; i < ORDER/2; i = i + 1)
        acc <= acc + ($signed(coefficients[i]) * $signed(sum_symmetric[i]));
      
      // Output with proper scaling (Q8.8 -> Q16.0)
      data_out <= acc[23:8];  // Fixed-point scaling adjustment
    end
  end
endmodule