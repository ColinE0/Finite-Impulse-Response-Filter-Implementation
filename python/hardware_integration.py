"""
Hardware Integration - Connects Python design to Verilog hardware
"""

import re
import numpy as np
import matplotlib.pyplot as plt
import os
import subprocess

def quantize_coefficients(coefficients, bits=16, format='q8.8', unity_gain=False):
    """
    Quantize coefficients for hardware implementation
    """
    if format == 'q8.8':
        scale = 2**8
    elif format == 'q4.12':
        scale = 2**12
    else:
        scale = 2**(bits//2)
    
    coefficients = np.asarray(coefficients, dtype=float)
    if coefficients.ndim != 1 or len(coefficients) == 0 or not np.all(np.isfinite(coefficients)):
        raise ValueError("Coefficients must be a nonempty array of finite values")
    if bits < 2 or bits > 32:
        raise ValueError("Coefficient width must be between 2 and 32 bits")

    scaled = coefficients * scale
    
    max_val = 2**(bits-1) - 1
    min_val = -2**(bits-1)
    quantized = np.clip(np.round(scaled), min_val, max_val).astype(np.int64)

    # Correct the center tap so an odd, symmetric lowpass keeps unity DC gain.
    if unity_gain:
        if len(coefficients) % 2 != 1 or not np.allclose(coefficients, coefficients[::-1], rtol=0, atol=1e-12):
            raise ValueError("Unity gain compensation requires an odd, symmetric filter")
        if not np.isclose(np.sum(coefficients), 1.0, rtol=0, atol=1e-9):
            raise ValueError("The floating-point filter must have unity DC gain")
        if np.any(scaled < min_val) or np.any(scaled > max_val):
            raise ValueError("Coefficients do not fit the selected width")
        half = len(coefficients) // 2
        quantized[half+1:] = quantized[:half][::-1]
        quantized[half] = scale - 2 * int(np.sum(quantized[:half]))
        if not min_val <= quantized[half] <= max_val:
            raise ValueError("Compensated center tap does not fit the selected width")
    
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
        quantized, hw_float, error = quantize_coefficients(coefficients, bits=bits, format='balanced')
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
    # Validate the complete response before folding or changing the file.
    coefficients = np.asarray(python_coefficients, dtype=float)
    with open(verilog_path, 'r') as f:
        source = f.read()

    parameters = {}
    for name in ('TAPS', 'FRAC', 'COEFF_WIDTH'):
        match = re.search(r'\bparameter\s+' + name + r'\s*=\s*(\d+)\b(?=\s*(?:,|//|\)))', source)
        if match is None:
            raise ValueError(f"Could not read RTL parameter {name}")
        parameters[name] = int(match.group(1))
    if parameters['TAPS'] != 11 or parameters['FRAC'] != 8 or parameters['COEFF_WIDTH'] < 16:
        raise ValueError("This coefficient bank requires 11 taps, Q8.8, and at least 16 coefficient bits")
    if coefficients.ndim != 1 or len(coefficients) != parameters['TAPS']:
        raise ValueError(f"Expected {parameters['TAPS']} full coefficients, not a folded or truncated response")

    quantized, _, _ = quantize_coefficients(coefficients, unity_gain=True)
    folded_coeffs = quantized[:len(coefficients)//2 + 1]
    pattern = re.compile(r'^([ \t]*)assign\s+c\[(\d+)\]\s*=\s*[^;]+;[^\n]*', re.MULTILINE)
    indices = [int(match.group(2)) for match in pattern.finditer(source)]
    if sorted(indices) != list(range(len(folded_coeffs))):
        raise ValueError("RTL coefficient assignments are missing, duplicated, or out of range")

    def replace_coefficient(match):
        index = int(match.group(2))
        coeff = int(folded_coeffs[index])
        center = ' (center)' if index == len(folded_coeffs)-1 else ''
        return f"{match.group(1)}assign c[{index}] = 16'sh{coeff & 0xFFFF:04X};   // {coeff}{center}"

    updated = pattern.sub(replace_coefficient, source)
    with open(verilog_path, 'w') as f:
        f.write(updated)

    print(f"Updated {len(folded_coeffs)} coefficients in {verilog_path}")
    return folded_coeffs

def fixed_point_filter(samples, coefficients, frac=8, data_width=16):
    """Unfolded integer reference, including the output register and wraparound."""
    history = [0] * len(coefficients)
    output = []
    mask = (1 << data_width) - 1
    for sample in samples:
        acc = sum(int(c) * x for c, x in zip(coefficients, history))
        value = (acc >> frac) & mask
        if value >= 1 << (data_width-1):
            value -= 1 << data_width
        output.append(value)
        history = [int(sample)] + history[:-1]
    return np.asarray(output, dtype=np.int64)

def generate_test_vectors(coefficients, fs=1000, output_dir='test_vectors'):
    """
    Generate Q8.8 vectors and bit-true expected outputs for the Verilog testbench
    """
    if fs <= 100:
        raise ValueError("Sampling frequency must be above 100 Hz for the 50 Hz test signal")
    quantized, _, _ = quantize_coefficients(coefficients, unity_gain=True)
    os.makedirs(output_dir, exist_ok=True)

    t = np.arange(128) / fs
    rng = np.random.default_rng(0)
    test_signals = {
        'dc': np.ones(128),
        'dc_small': np.full(128, 1/256),
        'dc_negative': -np.ones(128),
        'impulse': np.concatenate([np.ones(1), np.zeros(127)]),
        'sine_low': 0.5 * np.sin(2 * np.pi * 50 * t),
        'step': np.concatenate([np.zeros(64), np.ones(64)]),
        'extremes': np.concatenate([np.full(32, 32767), np.full(32, -32768),
                                    np.tile([32767, -32768], 32)]) / 256,
        'random': rng.integers(-32768, 32768, 2048) / 256
    }

    all_inputs, all_expected = [], []
    for name, signal_data in test_signals.items():
        # Drain the delay line between cases and include the registered tail.
        samples = np.clip(np.round(signal_data * 256), -32768, 32767).astype(np.int64)
        samples = np.concatenate([samples, np.zeros(len(coefficients)+1, dtype=np.int64)])
        expected = fixed_point_filter(samples, quantized)
        np.savetxt(f'{output_dir}/{name}_input.csv', samples / 256, fmt='%.8f')
        np.savetxt(f'{output_dir}/{name}_expected.csv', expected / 256, fmt='%.8f')
        all_inputs.extend(samples)
        all_expected.extend(expected)

    for name, values in (('input', all_inputs), ('expected', all_expected)):
        with open(os.path.join(output_dir, f'{name}.hex'), 'w') as f:
            for value in values:
                f.write(f'{int(value) & 0xFFFF:04X}\n')
    print(f"Generated {len(all_inputs)} test vectors in {output_dir}/ directory")
    return len(all_inputs)

def verify_hardware(verilog_path, vector_dir, sample_count, coeff_width=16, save_dir='results'):
    """Compile the RTL and compare every sample against the integer reference."""
    vector_dir = os.path.abspath(vector_dir)
    testbench = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'testbench',
                                           'fir_filter_vectors_tb.v'))
    sim_path = os.path.join(vector_dir, f'fir_sim_{coeff_width}')
    subprocess.run(['iverilog', '-g2012', '-s', 'fir_filter_vectors_tb',
                    f'-Pfir_filter_vectors_tb.SAMPLES={sample_count}',
                    f'-Pfir_filter_vectors_tb.COEFF_WIDTH={coeff_width}',
                    '-o', sim_path, os.path.abspath(verilog_path), testbench], check=True, timeout=30)
    subprocess.run(['vvp', sim_path], cwd=vector_dir, check=True, timeout=30)

    def read_samples(name):
        with open(os.path.join(vector_dir, name), 'r') as f:
            values = [int(line.strip(), 16) for line in f if line.strip()]
        return np.asarray([v if v < 32768 else v-65536 for v in values])

    expected = read_samples('expected.hex')
    actual = read_samples('actual.hex')
    if len(actual) != sample_count or not np.array_equal(actual, expected):
        raise RuntimeError("RTL output did not match the fixed-point reference")
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        fig, axes = plt.subplots(2, 1, figsize=(12, 6))
        axes[0].plot(expected / 256, label='Fixed-point reference')
        axes[0].plot(actual / 256, '--', label='Verilog output')
        axes[0].set_ylabel('Amplitude')
        axes[0].legend()
        axes[1].plot(actual - expected)
        axes[1].set_xlabel('Sample')
        axes[1].set_ylabel('Error (LSBs)')
        fig.suptitle(f'Implementation Verification ({sample_count} samples)')
        fig.tight_layout()
        fig.savefig(os.path.join(save_dir, 'implementation_verification.png'), dpi=150)
        plt.close(fig)
    return actual
