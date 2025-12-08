"""
Main Script: Complete FIR Filter Project
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy import signal


# Import our modules
from fir_design_tool import (
    design_fir_filter, calculate_snr, sweep_filter_parameter, 
    SpectrumAnalyzer, plot_frequency_response, plot_parameter_sweep,
)
from hardware_integration import update_verilog_file, generate_test_vectors

def find_project_root():
    """Find the project root directory"""
    current = os.path.dirname(os.path.abspath(__file__))
    
    # Look for rtl/ or verilog/ directories
    for _ in range(3):
        if os.path.exists(os.path.join(current, 'rtl')):
            return current
        if os.path.exists(os.path.join(current, 'verilog')):
            return current
        current = os.path.dirname(current)
    
    return os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = find_project_root()
VERILOG_PATH = os.path.join(PROJECT_ROOT, 'rtl', 'fir_filter_folded.v')

def create_all_plots():
    """
    Complete demonstration using SpectrumAnalyzer
    """
    print("FIR Filter Design & Analysis Tool")
    print("="*35)
    
    fs = 1000
    
    # 1. Create test signal
    print("\n1. Creating test signal")
    t = np.linspace(0, 0.5, fs//2)
    f1, f2 = 50, 120
    test_signal = np.sin(2*np.pi*f1*t) + 0.5*np.sin(2*np.pi*f2*t)
    
    # Create SpectrumAnalyzer instance
    analyzer = SpectrumAnalyzer(test_signal, fs)
    print(f"   Created SpectrumAnalyzer with {len(test_signal)} samples")
    
    # 2. Design filter
    print("\n2. Designing FIR filter")
    coefficients = design_fir_filter(
        order=30, 
        cutoff_freq=100,
        fs=fs, 
        filter_type='lowpass',
        method='window'
    )
    
    print(f"    Designed {len(coefficients)}-tap FIR filter")
    print(f"    Cutoff: 100Hz, Sampling: {fs}Hz")
    print(f"    DC Gain: {np.sum(coefficients):.4f}")
    print(f"    First 5 coefficients: {coefficients[:5].round(4)}")
    print(f"    Last 5 coefficients: {coefficients[-5:].round(4)}")
    print(f"    Symmetric: {np.allclose(coefficients, coefficients[::-1])}")
    print(f"    Linear phase: {'Yes' if np.allclose(coefficients, coefficients[::-1]) else 'No'}")
    
    
    # 3. Use SpectrumAnalyzer to analyze filter effect
    print("\n3. Analyzing filter effect with SpectrumAnalyzer")
    filtered_signal = analyzer.analyze_filter_effect(
        coefficients, 
        title="Lowpass Filter: Removing High-Frequency Noise",
        save_plot=True
    )
    
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
    print("\n6. Implementation verification using SpectrumAnalyzer")
    # Create a more complex test signal
    t = np.linspace(0, 0.5, fs//2)
    test_complex = (
        np.sin(2*np.pi*50*t) +                    # Desired signal 1
        0.5*np.sin(2*np.pi*120*t) +               # Desired signal 2  
        0.3*np.sin(2*np.pi*250*t) +               # Noise to be filtered
        0.1*np.random.randn(len(t))               # Random noise
    )

    analyzer = SpectrumAnalyzer(test_complex, fs)
    filtered = analyzer.analyze_filter_effect(
        coefficients,
        title="Lowpass Filter: Python Design Verification",
        save_plot=True
    )

    # Quantization effects (hardware verification)
    from hardware_integration import quantize_coefficients
    quantized, hw_float, q_error = quantize_coefficients(coefficients[:6])
    print(f"   Quantization error: {q_error:.6f}")
    print(f"   Hardware coefficients ready for Verilog")
    
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
    print("1. zero_padding_comparison.png - FFT analysis")
    print("2. filter_response.png - Filter frequency & phase response")
    print("3. parameter_sweep_order.png - SNR/MSE vs filter order")
    print("4. parameter_sweep_cutoff.png - SNR/MSE vs cutoff frequency")
    print("5. spectrum_analysis.png - Complete filter effect analysis")
    print("6. implementation_verification.png - Python vs Hardware comparison")
    
    return coefficients, hw_coeffs

if __name__ == "__main__":
    # Generate all plots
    coefficients, hw_coeffs = create_all_plots()
    
    # Print summary
    print(f"\nSummary:")
    print(f"• Python filter: {len(coefficients)} taps")
    print(f"• Hardware coefficients: {len(hw_coeffs)} folded values")
    print(f"• All plots saved to 'results/' directory")
    print("\nSee README.md for project documentation and analysis.")