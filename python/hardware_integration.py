"""
Hardware Integration - Connects Python design to Verilog hardware
"""

import re
import numpy as np
import matplotlib.pyplot as plt
import os
from scipy import signal

def quantize_coefficients(coefficients, bits=16, format='q8.8'):
    """
    Quantize coefficients for hardware implementation
    """
    if format == 'q8.8':
        scale = 2**8
    elif format == 'q4.12':
        scale = 2**12
    else:
        scale = 2**(bits//2)
    
    scaled = coefficients * scale
    quantized = np.round(scaled).astype(np.int32)
    
    max_val = 2**(bits-1) - 1
    min_val = -2**(bits-1)
    quantized = np.clip(quantized, min_val, max_val)
    
    float_coeffs = quantized / scale
    quantization_error = np.mean((coefficients - float_coeffs)**2)
    
    return quantized, float_coeffs, quantization_error

def plot_quantization_effects(coefficients, save_dir='results'):
    """
    Plot the effects of coefficient quantization
    """
    os.makedirs(save_dir, exist_ok=True)
    
    # Quantize coefficients with different bit widths
    bit_widths = [8, 12, 16, 24]
    quantization_errors = []
    
    for bits in bit_widths:
        quantized, hw_float, error = quantize_coefficients(coefficients, bits=bits)
        quantization_errors.append(error)
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    
    # Plot quantization error vs bit width
    plt.subplot(1, 2, 1)
    plt.plot(bit_widths, quantization_errors, 'bo-', linewidth=2, markersize=8)
    plt.xlabel('Bit Width')
    plt.ylabel('Quantization Error')
    plt.title('Quantization Error vs Bit Width')
    plt.grid(True, alpha=0.3)
    plt.yscale('log')
    
    # Plot original vs quantized coefficients
    plt.subplot(1, 2, 2)
    x = np.arange(len(coefficients))
    quantized_16, hw_float_16, _ = quantize_coefficients(coefficients, bits=16)
    
    plt.stem(x, coefficients, linefmt='b-', markerfmt='bo', basefmt=' ', label='Original')
    plt.stem(x, hw_float_16, linefmt='r--', markerfmt='rx', basefmt=' ', label='Quantized (16-bit)')
    plt.xlabel('Coefficient Index')
    plt.ylabel('Value')
    plt.title('Original vs Quantized Coefficients')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{save_dir}/quantization_effects.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved quantization effects plot: results/quantization_effects.png")
    
    return quantization_errors

def update_verilog_file(python_coefficients, verilog_path='fir_filter_folded.v'):
    """
    Automatically update Verilog file with new coefficients
    """
    # Get only first 6 coefficients for folded architecture
    folded_coeffs = python_coefficients[:6] if len(python_coefficients) >= 6 else python_coefficients
    
    quantized_coeffs, _, _ = quantize_coefficients(folded_coeffs)
    
    # Read existing Verilog file
    with open(verilog_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    coeff_index = 0
    
    for line in lines:
        if 'assign coefficients[' in line and '16' in line:
            if coeff_index < len(quantized_coeffs):
                coeff = quantized_coeffs[coeff_index]
                if coeff < 0:
                    hex_val = coeff & 0xFFFF
                else:
                    hex_val = coeff
                
                new_line = f"assign coefficients[{coeff_index}] = 16'h{hex_val:04X};"
                new_lines.append(new_line + '\n')
                coeff_index += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    with open(verilog_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"Updated {coeff_index} coefficients in {verilog_path}")
    return quantized_coeffs

def generate_test_vectors(coefficients, fs=1000, output_dir='test_vectors'):
    """
    Generate test vectors for Verilog testbench
    """
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    t = np.linspace(0, 1, 100)
    test_signals = {
        'dc': np.ones(50),
        'sine_low': 0.5 * np.sin(2 * np.pi * 50 * t[:50]),
        'step': np.concatenate([np.zeros(25), np.ones(25)])
    }
    
    for name, signal_data in test_signals.items():
        filtered = signal.lfilter(coefficients, 1.0, signal_data)
        np.savetxt(f'{output_dir}/{name}_input.csv', signal_data, fmt='%.6f')
        np.savetxt(f'{output_dir}/{name}_expected.csv', filtered, fmt='%.6f')
    
    print(f"Generated test vectors in {output_dir}/ directory")