"""
Regression tests for coefficient export and Python/Verilog agreement.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
import numpy as np

from fir_design_tool import design_fir_filter, sweep_filter_parameter
from hardware_integration import (
    quantize_coefficients, update_verilog_file, fixed_point_filter,
    generate_test_vectors, verify_hardware,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERILOG_PATH = os.path.join(PROJECT_ROOT, 'rtl', 'fir_filter_folded.v')

class HardwareIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.verilog_path = os.path.join(self.temp_dir.name, 'fir_filter_folded.v')
        shutil.copyfile(VERILOG_PATH, self.verilog_path)
        self.coefficients = design_fir_filter(10, 150, 1000)

    def read_verilog(self):
        with open(self.verilog_path) as f:
            return f.read()

    def test_export_preserves_the_existing_filter(self):
        folded = update_verilog_file(self.coefficients, self.verilog_path)
        np.testing.assert_array_equal(folded, [-1, -2, 3, 27, 62, 78])
        self.assertEqual(2 * sum(folded[:-1]) + folded[-1], 256)
        self.assertIn("assign c[0] = 16'shFFFF;", self.read_verilog())
        self.assertIn("assign c[5] = 16'sh004E;", self.read_verilog())

    def test_export_rejects_the_wrong_tap_count(self):
        before = self.read_verilog()
        for coefficients in (self.coefficients[:6], design_fir_filter(30, 100, 1000)):
            with self.subTest(taps=len(coefficients)):
                with self.assertRaises(ValueError):
                    update_verilog_file(coefficients, self.verilog_path)
                self.assertEqual(self.read_verilog(), before)

    def test_export_rejects_missing_or_duplicate_assignments(self):
        original = self.read_verilog()
        for source in (original.replace('assign c[', 'assign coefficients['),
                       original.replace('assign c[1]', 'assign c[0]')):
            with self.subTest():
                with open(self.verilog_path, 'w') as f:
                    f.write(source)
                with self.assertRaises(ValueError):
                    update_verilog_file(self.coefficients, self.verilog_path)
                self.assertEqual(self.read_verilog(), source)

    def test_export_rejects_invalid_coefficients(self):
        asymmetric = self.coefficients.copy()
        asymmetric[0] += 0.1
        before = self.read_verilog()
        for coefficients in (asymmetric, self.coefficients * 2, np.full(11, np.nan)):
            with self.subTest():
                with self.assertRaises(ValueError):
                    update_verilog_file(coefficients, self.verilog_path)
                self.assertEqual(self.read_verilog(), before)

    def test_center_compensation_does_not_break_symmetry(self):
        quantized, hw_float, _ = quantize_coefficients(self.coefficients, unity_gain=True)
        np.testing.assert_array_equal(quantized, quantized[::-1])
        self.assertEqual(sum(quantized), 256)
        self.assertEqual(sum(hw_float), 1.0)

    def test_integer_reference_includes_latency_and_wraparound(self):
        # A gain of 2 overflows both positive and negative 16-bit samples.
        actual = fixed_point_filter([32767, -32768, -1, 0], [512])
        np.testing.assert_array_equal(actual, [0, -2, 0, -2])
        # Arithmetic right shift rounds a negative fractional output down.
        np.testing.assert_array_equal(fixed_point_filter([-1, 0], [1]), [0, -1])

    def test_order_sweep_holds_the_cutoff_in_hertz(self):
        results = sweep_filter_parameter('order', [10, 30], np.ones(64), fs=1000,
                                         save_plots=False, cutoff_freq=150)
        for order, coefficients in zip([10, 30], results['coefficients']):
            np.testing.assert_allclose(coefficients, design_fir_filter(order, 150, 1000))

    def test_sine_vectors_follow_the_sampling_frequency(self):
        for fs in (1000, 2000):
            generate_test_vectors(self.coefficients, fs, self.temp_dir.name)
            samples = np.loadtxt(os.path.join(self.temp_dir.name, 'sine_low_input.csv'))
            expected = np.round(128 * np.sin(2 * np.pi * 50 * np.arange(128) / fs)) / 256
            np.testing.assert_array_equal(samples[:128], expected)

    def test_exported_filters_match_verilog_at_both_widths(self):
        # Check the existing filter and a changed cutoff to prove export takes effect.
        for cutoff in (150, 100):
            coefficients = design_fir_filter(10, cutoff, 1000)
            update_verilog_file(coefficients, self.verilog_path)
            count = generate_test_vectors(coefficients, output_dir=self.temp_dir.name)
            for width in (16, 24):
                with self.subTest(cutoff=cutoff, width=width):
                    verify_hardware(self.verilog_path, self.temp_dir.name, count,
                                    coeff_width=width, save_dir=None)

    def test_unsupported_rtl_parameters_fail(self):
        bench = os.path.join(self.temp_dir.name, 'parameter_tb.v')
        sim = os.path.join(self.temp_dir.name, 'parameter_sim')
        for parameter, value in (('TAPS', 13), ('FRAC', 9), ('COEFF_WIDTH', 8)):
            with self.subTest(parameter=parameter):
                with open(bench, 'w') as f:
                    f.write(f"""module parameter_tb;
fir_filter_folded #(.{parameter}({value})) dut (
    .clk(1'b0), .reset(1'b0), .data_in(16'sd0), .data_out()
);
initial #1 $finish;
endmodule
""")
                subprocess.run(['iverilog', '-g2012', '-s', 'parameter_tb', '-o', sim,
                                self.verilog_path, bench], check=True, capture_output=True, timeout=30)
                result = subprocess.run(['vvp', sim], capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Use TAPS=11, FRAC=8, COEFF_WIDTH>=16', result.stdout)

if __name__ == '__main__':
    unittest.main()
