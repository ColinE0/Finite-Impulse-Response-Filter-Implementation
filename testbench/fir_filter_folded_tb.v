// fir_filter_folded_tb.v
// Self-checking testbench. Verifies:
//   1. unity DC gain: a held 1.0 input settles to a 1.0 output
//   2. impulse response is symmetric and sums to 1.0 (linear-phase, unity gain)
// Prints RESULT: PASS only if every check holds.

`timescale 1ns/1ps

module fir_filter_folded_tb;
    localparam TAPS = 11;

    reg                clk = 0;
    reg                reset = 1;
    reg  signed [15:0] data_in = 0;
    wire signed [15:0] data_out;

    integer i, s, isum, errors = 0;
    reg signed [15:0] resp [0:TAPS-1];

    fir_filter_folded dut (.clk(clk), .reset(reset), .data_in(data_in), .data_out(data_out));

    always #5 clk = ~clk;

    initial begin
        $dumpfile("fir_filter_folded.vcd");
        $dumpvars(0, fir_filter_folded_tb);
        $display("=== FIR Filter (folded) self-checking test ===");

        // Reset
        @(negedge clk); @(negedge clk); reset = 0;

        // Test 1: unity DC gain
        data_in = 16'sh0100;                 // 1.0 in Q8.8
        repeat (TAPS+4) @(negedge clk);
        if (data_out >= 16'sh00FF && data_out <= 16'sh0101)
            $display("PASS Test 1 (unity DC gain): data_out = %0d (expected 256)", data_out);
        else begin
            errors = errors + 1;
            $display("FAIL Test 1 (unity DC gain): data_out = %0d (expected 256)", data_out);
        end

        // Test 2: impulse response symmetry and sum
        reset = 1; @(negedge clk); @(negedge clk); reset = 0;
        data_in = 16'sh0100;                 // one-cycle impulse
        @(negedge clk);
        data_in = 0;
        for (s = 0; s < TAPS; s = s + 1) begin
            @(negedge clk);
            resp[s] = data_out;              // 1-cycle latency captured across TAPS samples
        end
        for (i = 0; i < TAPS; i = i + 1)
            if (resp[i] !== resp[TAPS-1-i]) begin
                errors = errors + 1;
                $display("FAIL Test 2 (symmetry): resp[%0d]=%0d != resp[%0d]=%0d",
                         i, resp[i], TAPS-1-i, resp[TAPS-1-i]);
            end
        isum = 0;
        for (i = 0; i < TAPS; i = i + 1) isum = isum + resp[i];
        if (isum === 256)
            $display("PASS Test 2 (impulse symmetric, sum = %0d)", isum);
        else begin
            errors = errors + 1;
            $display("FAIL Test 2 (impulse sum = %0d, expected 256)", isum);
        end

        if (errors == 0) $display("RESULT: PASS (all checks)");
        else             $display("RESULT: FAIL (%0d errors)", errors);
        #20 $finish;
    end
endmodule
