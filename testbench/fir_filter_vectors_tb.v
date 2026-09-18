// fir_filter_vectors_tb.v
// Checks every output against the Python fixed-point reference.
// Input and expected vectors include the one-clock output delay and drain samples.

`timescale 1ns/1ps

module fir_filter_vectors_tb;
    parameter SAMPLES = 3040;
    parameter COEFF_WIDTH = 16;

    reg                clk = 0;
    reg                reset = 1;
    reg  signed [15:0] data_in = 0;
    wire signed [15:0] data_out;

    reg [15:0] samples [0:SAMPLES-1];
    reg [15:0] expected [0:SAMPLES-1];
    integer i, output_file;

    fir_filter_folded #(.COEFF_WIDTH(COEFF_WIDTH)) dut (
        .clk(clk), .reset(reset), .data_in(data_in), .data_out(data_out)
    );

    always #5 clk = ~clk;

    initial begin
        $readmemh("input.hex", samples);
        $readmemh("expected.hex", expected);
        output_file = $fopen("actual.hex", "w");
        if (output_file == 0) $fatal(1, "Could not open actual.hex");

        repeat (2) @(negedge clk);
        reset = 0;
        for (i = 0; i < SAMPLES; i = i + 1) begin
            data_in = samples[i];
            @(negedge clk);
            $fdisplay(output_file, "%04h", data_out);
            if (data_out !== expected[i])
                $fatal(1, "Sample %0d: got %0d, expected %0d", i, data_out, $signed(expected[i]));
        end

        $fclose(output_file);
        $display("PASS: %0d samples matched (COEFF_WIDTH=%0d)", SAMPLES, COEFF_WIDTH);
        $finish;
    end
endmodule
