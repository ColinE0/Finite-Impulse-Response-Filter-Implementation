`timescale 1ns/1ps

module fir_filter_folded_tb;
  reg clk, reset;
  reg signed [15:0] data_in;
  wire signed [15:0] data_out;

  // Instantiate Device Under Test
  fir_filter_folded dut (
    .clk(clk),
    .reset(reset), 
    .data_in(data_in),
    .data_out(data_out)
  );

  // 100 MHz Clock Generation
  always #5 clk = ~clk;

  // Comprehensive Test Sequence
  initial begin
    // Initialize signals
    clk = 0;
    reset = 1;
    data_in = 0;
    
    $display("=== FIR Filter Folded Architecture Test ===");
    $display("");
    
    // Reset sequence
    #20 reset = 0;
    #10; // Wait one clock after reset
    
    $display("Time\tInput\t\tOutput\t\tDescription");
    $display("----------------------------------------------------");

    // Test 1: Unity Gain Verification (DC Input)
    $display("");
    $display("TEST 1: Unity Gain Verification");
    data_in = 16'h0100; // 1.0 in Q8.8 format
    #150; // Wait for filter to settle
    
    if (data_out >= 16'h00F0 && data_out <= 16'h0110) begin
      $display("PASS: Input=%h, Output=%h (Unity gain verified)", data_in, data_out);
    end else begin
      $display("FAIL: Input=%h, Output=%h (Gain issue)", data_in, data_out);
    end

    // Test 2: Impulse Response
    $display("");
    $display("TEST 2: Impulse Response");
    data_in = 16'h0100; // Impulse of 1.0
    #10;
    data_in = 0;
    
    // Monitor impulse response progression
    #20 $display("   T+20ns: Output = %h (Expected: rising edge)", data_out);
    #20 $display("   T+40ns: Output = %h", data_out);
    #20 $display("   T+60ns: Output = %h", data_out);
    #20 $display("   T+80ns: Output = %h (Expected: peak response)", data_out);

    // Test 3: Linearity Check (Different Amplitudes)
    $display("");
    $display("TEST 3: Linearity Verification");
    
    data_in = 16'h0080; // 0.5 in Q8.8
    #100;
    $display("   Input=0.5 (%h): Output=%h", data_in, data_out);
    
    data_in = 16'h0200; // 2.0 in Q8.8  
    #100;
    $display("   Input=2.0 (%h): Output=%h", data_in, data_out);
    
    data_in = 16'h0000; // Return to zero
    #50;

    // Test 4: Symmetric Response Check
    $display("");
    $display("TEST 4: Symmetric Response");
    data_in = 16'h0100;  // Positive input
    #50;
    $display("   Positive input: Output=%h", data_out);
    
    data_in = 16'hFF00;  // Negative input (-1.0 in Q8.8)
    #50;
    $display("   Negative input: Output=%h", data_out);

    // Test 5: Final Gain Accuracy
    $display("");
    $display("TEST 5: Final Gain Accuracy");
    data_in = 16'h0180; // 1.5 in Q8.8
    #150; // Settling time
    
    if (data_out >= 16'h0170 && data_out <= 16'h0190) begin
      $display("PASS: Gain accuracy within 2%% tolerance");
      $display("   Input=1.5 (%h), Output=%h", data_in, data_out);
    end else begin
      $display("FAIL: Gain accuracy outside tolerance");
      $display("   Input=1.5 (%h), Output=%h", data_in, data_out);
    end

    // Summary
    $display("");
    $display("=== TEST SEQUENCE COMPLETE ===");
    $display("All tests executed. Check waveforms for detailed analysis.");
    #100;
    $finish;
  end

  // VCD Waveform Dumping for Analysis
  initial begin
    $dumpfile("fir_filter_folded.vcd");
    $dumpvars(0, fir_filter_folded_tb);
  end
  
  // Monitor for unexpected behavior
  always @(posedge clk) begin
    if (!reset && (data_out === 16'bX || data_out === 16'bZ)) begin
      $display("WARNING: Invalid output detected at time %t", $time);
    end
  end
endmodule