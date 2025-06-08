`timescale 1ns/1ps

module fir_filter_folded_tb;
  reg clk, reset;
  reg signed [15:0] data_in;
  wire signed [15:0] data_out;

  // Instantiate DUT
  fir_filter_folded dut (clk, reset, data_in, data_out);

  // Clock generation (100 MHz)
  always #5 clk = ~clk;

  // Test sequence
  initial begin
    // Initialize
    clk = 0; reset = 1; data_in = 0;
    #20 reset = 0;
    #10; // Wait one clock after reset

    // Test 1: Impulse Response (just checking first output)
    data_in = 16'h0100; // 1.0 in Q8.8
    #10;
    data_in = 0;
    #100; // Wait for output
    $display("First output: ", data_out);

    // Test 2: Simple step response (visual check)
    repeat (5) begin
      data_in = 16'h0100; // Step input
      #10;
    end
    data_in = 0;
    #100;

    // Test 3: Symmetric check
    data_in = 100;  #20;
    data_in = -100; #20;
    $display("Symmetric test output: ", data_out);

    // Test 4: Display some outputs
    data_in = 16'h2000; #20;
    data_in = 16'h4000; #20;
    data_in = 16'h0000; #20;

    $display("Done. Check waveforms for behavior.");
    #100;
    $finish;
  end

  // Saving waveforms
  initial begin
    $dumpfile("fir_filter_folded.vcd");
    $dumpvars(0, fir_filter_folded_tb);
  end
endmodule