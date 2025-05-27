import numpy as np

# Load coefficients
coeffs_float = np.loadtxt('fir_coefficients.csv')
coeffs_fixed = np.round(coeffs_float * 256).astype(np.int16)  # Q8.8

# Print Verilog hex (force unsigned handling)
for i, coeff in enumerate(coeffs_fixed):
    hex_val = np.uint16(coeff) & 0xFFFF  # Treat as unsigned
    print(f"assign coefficients[{i}] = 16'h{hex_val:04X};")