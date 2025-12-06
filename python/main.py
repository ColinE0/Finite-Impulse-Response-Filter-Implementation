#!/usr/bin/env python3
"""
Main Script: Complete FIR Filter Project
Creates all plots for README.md automatically
"""

import numpy as np
import os
import matplotlib.pyplot as plt
from scipy import signal
import sys


# Import our modules
from fir_design_tool import (
    design_fir_filter, calculate_snr, sweep_filter_parameter, 
    SpectrumAnalyzer, plot_frequency_response, plot_parameter_sweep,
    create_homework_style_plot
)
from hardware_integration import update_verilog_file, generate_test_vectors

def find_project_root():
    """Find the project root directory"""
    # Try to find by looking for common directories
    current = os.path.dirname(os.path.abspath(__file__))
    
    # Look for rtl/ or verilog/ directories
    for _ in range(3):  # Check up to 3 levels up
        if os.path.exists(os.path.join(current, 'rtl')):
            return current
        if os.path.exists(os.path.join(current, 'verilog')):
            return current
        current = os.path.dirname(current)
    
    return os.path.dirname(os.path.abspath(__file__))

# Then use it:
PROJECT_ROOT = find_project_root()
VERILOG_PATH = os.path.join(PROJECT_ROOT, 'rtl', 'fir_filter_folded.v')

def create_all_plots():
    """
    Create all the plots needed for the README.md documentation
    """
    print("="*70)
    print("GENERATING ALL PLOTS FOR README.md")
    print("="*70)
    
    fs = 1000
    
    # 1. Create homework-style zero-padding plot
    print("\n1. Creating homework-style zero-padding plot")
    test_signal = create_homework_style_plot(fs=fs)
    
    # 2. Design a filter
    print("\n2. Designing FIR filter")
    coefficients = design_fir_filter(
        order=30, 
        cutoff_freq=100, 
        fs=fs, 
        filter_type='lowpass',
        method='window'
    )
    
    # 3. Create frequency response plot
    print("\n3. Creating frequency response plot")
    plot_frequency_response(coefficients, fs=fs)
    
    # 4. Create parameter sweep plots
    print("\n4. Creating parameter sweep plots")
    
    # Create a more complex test signal for parameter sweeping
    t = np.linspace(0, 1, fs)
    f1, f2, f_noise = 50, 120, 250
    complex_signal = (
        np.sin(2*np.pi*f1*t) + 
        0.5*np.sin(2*np.pi*f2*t) + 
        0.3*np.sin(2*np.pi*f_noise*t) + 
        0.1*np.random.randn(len(t))
    )
    
    # Sweep filter orders
    orders = [10, 20, 30, 40, 50, 60]
    order_results = sweep_filter_parameter('order', orders, complex_signal, fs, save_plots=True)
    
    # Sweep cutoff frequencies
    cutoffs = [50, 100, 150, 200, 250]
    cutoff_results = sweep_filter_parameter('cutoff', cutoffs, complex_signal, fs, save_plots=True)
    
    # 5. Create spectrum analysis plot
    print("\n5. Creating spectrum analysis plot")
    analyzer = SpectrumAnalyzer(complex_signal, fs)
    analyzer.analyze_filter_effect(coefficients, "Lowpass Filter Effect", save_plot=True)
    
    # 6. Create implementation verification plot
    print("\n6. Creating implementation verification plot")
    create_implementation_verification_plot(coefficients)
    
    # 7. Update hardware with new coefficients
    print("\n7. Updating Verilog hardware")
    hw_coeffs = update_verilog_file(coefficients[:6], VERILOG_PATH)
    
    # 8. Generate test vectors
    print("\n8. Generating test vectors")
    generate_test_vectors(coefficients, fs, output_dir='test_vectors')
    
    print("\n" + "="*30)
    print("Plots Generated Successfully")
    print("="*30)
    print("\nGenerated files in 'results/' directory:")
    print("1. zero_padding_comparison.png - Homework-style FFT analysis")
    print("2. filter_response.png - Filter frequency & phase response")
    print("3. parameter_sweep_order.png - SNR/MSE vs filter order")
    print("4. parameter_sweep_cutoff.png - SNR/MSE vs cutoff frequency")
    print("5. spectrum_analysis.png - Complete filter effect analysis")
    print("6. implementation_verification.png - Python vs Hardware comparison")
    
    return coefficients, hw_coeffs

def create_implementation_verification_plot(coefficients, fs=1000):
    """
    Create a plot showing Python design vs Hardware implementation
    """
    import os
    os.makedirs('results', exist_ok=True)
    
    # Create a simple test signal
    t = np.linspace(0, 0.5, 500)
    test_signal = np.sin(2*np.pi*50*t) + 0.5*np.sin(2*np.pi*120*t)
    
    # Python filtered signal
    python_filtered = signal.lfilter(coefficients, 1.0, test_signal)
    
    # Create hardware-filtered signal (simplified - would come from actual Verilog)
    # For demonstration, we'll simulate quantization effects
    from hardware_integration import quantize_coefficients
    quantized, hw_float, error = quantize_coefficients(coefficients[:6])
    
    # Create full symmetric coefficients from folded hardware coefficients
    hw_coeffs_full = np.array([
        hw_float[0], hw_float[1], hw_float[2],
        hw_float[3], hw_float[4], hw_float[5],
        hw_float[4], hw_float[3], hw_float[2],
        hw_float[1], hw_float[0]
    ])
    
    hardware_filtered = signal.lfilter(hw_coeffs_full, 1.0, test_signal)
    
    # Calculate error metrics
    snr_python, mse_python = calculate_snr(test_signal, python_filtered)
    snr_hw, mse_hw = calculate_snr(test_signal, hardware_filtered)
    implementation_error = np.mean((python_filtered - hardware_filtered)**2)
    
    # Create the verification plot
    plt.figure(figsize=(14, 10))
    
    # Plot 1: Time domain comparison
    plt.subplot(3, 2, 1)
    plt.plot(t, test_signal, 'gray', alpha=0.5, label='Original')
    plt.plot(t, python_filtered, 'b-', alpha=0.7, label='Python Design')
    plt.plot(t, hardware_filtered, 'r--', alpha=0.7, label='Hardware (Quantized)')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.title('Time Domain: Implementation Comparison')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Frequency response comparison
    w, h_python = signal.freqz(coefficients, worN=1024)
    w, h_hardware = signal.freqz(hw_coeffs_full, worN=1024)
    freq_hz = w * fs / (2 * np.pi)
    
    plt.subplot(3, 2, 2)
    plt.plot(freq_hz, 20*np.log10(np.abs(h_python) + 1e-10), 'b-', label='Python')
    plt.plot(freq_hz, 20*np.log10(np.abs(h_hardware) + 1e-10), 'r--', label='Hardware')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (dB)')
    plt.title('Frequency Response Comparison')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim(0, fs/2)
    
    # Plot 3: Implementation error
    plt.subplot(3, 2, 3)
    error_signal = python_filtered - hardware_filtered
    plt.plot(t, error_signal, 'purple')
    plt.fill_between(t, 0, error_signal, alpha=0.3, color='purple')
    plt.xlabel('Time (s)')
    plt.ylabel('Error')
    plt.title(f'Implementation Error (MSE: {implementation_error:.2e})')
    plt.grid(True, alpha=0.3)
    
    # Plot 4: SNR comparison
    plt.subplot(3, 2, 4)
    categories = ['Python Design', 'Hardware']
    snr_values = [snr_python, snr_hw]
    colors = ['blue', 'red']
    
    bars = plt.bar(categories, snr_values, color=colors, alpha=0.7)
    plt.ylabel('SNR (dB)')
    plt.title('Signal-to-Noise Ratio Comparison')
    plt.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, value in zip(bars, snr_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{value:.2f} dB', ha='center', va='bottom')
    
    # Plot 5: Coefficients comparison
    plt.subplot(3, 2, 5)
    x = np.arange(len(coefficients[:11]))
    plt.stem(x, coefficients[:11], linefmt='b-', markerfmt='bo', basefmt=' ', label='Python')
    plt.stem(x, hw_coeffs_full, linefmt='r--', markerfmt='rx', basefmt=' ', label='Hardware')
    plt.xlabel('Coefficient Index')
    plt.ylabel('Value')
    plt.title('Coefficient Values (Floating vs Fixed-point)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 6: Performance summary
    plt.subplot(3, 2, 6)
    metrics = ['MSE', 'Quant Error', 'DC Gain']
    python_vals = [mse_python, error, np.sum(coefficients)]
    hw_vals = [mse_hw, 0, np.sum(hw_coeffs_full)]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    plt.bar(x - width/2, python_vals, width, label='Python', alpha=0.7, color='blue')
    plt.bar(x + width/2, hw_vals, width, label='Hardware', alpha=0.7, color='red')
    
    plt.xlabel('Metric')
    plt.ylabel('Value')
    plt.title('Performance Metrics Comparison')
    plt.xticks(x, metrics)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.yscale('log')
    
    plt.suptitle('Implementation Verification: Python Design vs Hardware', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('results/implementation_verification.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved implementation verification plot: results/implementation_verification.png")

if __name__ == "__main__":
    # Generate all plots
    coefficients, hw_coeffs = create_all_plots()
    
    # Print summary
    print(f"\nSummary:")
    print(f"• Python filter: {len(coefficients)} taps")
    print(f"• Hardware coefficients: {len(hw_coeffs)} folded values")
    print(f"• All plots saved to 'results/' directory")
    print(f"• Ready to include in README.md")