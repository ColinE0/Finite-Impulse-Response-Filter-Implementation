// fir_filter_folded.v
// 11-tap symmetric low-pass FIR using a folded architecture (HALF+1 = 6 multipliers
// instead of 11). Coefficients are Q8.8; the full impulse response sums to 256 (1.0),
// so the filter has unity DC gain. Single-cycle: a combinational folded multiply-
// accumulate over the delay line, registered once per clock.

module fir_filter_folded #(
    parameter DATA_WIDTH  = 16,   // Q8.8 samples
    parameter COEFF_WIDTH = 16,   // Q8.8 coefficients
    parameter TAPS        = 11,   // odd, symmetric
    parameter FRAC        = 8     // fractional bits (Q8.8)
)(
    input  wire                          clk,
    input  wire                          reset,    // synchronous, active high
    input  wire signed [DATA_WIDTH-1:0]  data_in,
    output reg  signed [DATA_WIDTH-1:0]  data_out
);
    localparam HALF = (TAPS-1)/2;     // 5 outer pairs + 1 center tap

    // Symmetric coefficients c[0..HALF], c[HALF] is the center. Q8.8.
    // Full 11-tap response = {c0,c1,c2,c3,c4,c5,c4,c3,c2,c1,c0}, sum = 256 -> unity DC gain.
    wire signed [COEFF_WIDTH-1:0] c [0:HALF];
    assign c[0] = 16'hFFFF;   //  -1
    assign c[1] = 16'hFFFE;   //  -2
    assign c[2] = 16'h0003;   //   3
    assign c[3] = 16'h001B;   //  27
    assign c[4] = 16'h003E;   //  62
    assign c[5] = 16'h004E;   //  78  (center)

    // Full delay line: x[0] = newest sample ... x[TAPS-1] = oldest.
    reg signed [DATA_WIDTH-1:0] x [0:TAPS-1];

    // Folded multiply-accumulate over the current delay line (combinational, blocking).
    // Pairing x[k] with x[TAPS-1-k] lets the symmetric taps share one multiplier.
    localparam ACC_WIDTH = DATA_WIDTH + COEFF_WIDTH + 4;   // headroom for the summed products
    reg signed [ACC_WIDTH-1:0] acc;
    integer k;
    always @(*) begin
        acc = $signed(c[HALF]) * $signed(x[HALF]);                          // center tap
        for (k = 0; k < HALF; k = k + 1)
            acc = acc + $signed(c[k]) * ($signed(x[k]) + $signed(x[TAPS-1-k]));
    end

    // Register the delay line and the scaled output once per clock.
    integer i;
    always @(posedge clk) begin
        if (reset) begin
            for (i = 0; i < TAPS; i = i + 1)
                x[i] <= {DATA_WIDTH{1'b0}};
            data_out <= {DATA_WIDTH{1'b0}};
        end else begin
            for (i = TAPS-1; i > 0; i = i - 1)
                x[i] <= x[i-1];
            x[0] <= data_in;
            data_out <= acc >>> FRAC;     // Q16.16 product-sum back to Q8.8
        end
    end
endmodule
