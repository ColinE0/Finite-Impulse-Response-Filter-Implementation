"""
FIR Design Tool - Core Filter Design Functions
Replaces MATLAB with Python implementation
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import warnings
warnings.filterwarnings('ignore')
import os

def design_fir_filter(order, cutoff_freq, fs=1.0, filter_type='lowpass', method='window'):
    """
    Design FIR filter coefficients using Python (replaces MATLAB's firpm/fir1)
    """
    # Normalize frequencies and ensure they're valid
    nyquist = fs / 2
    
    if isinstance(cutoff_freq, (int, float)):
        cutoff_freq = [cutoff_freq]
    
    # Ensure cutoff frequencies are valid
    for i, freq in enumerate(cutoff_freq):
        if freq >= nyquist:
            print(f"    Warning: Cutoff frequency {freq}Hz >= Nyquist ({nyquist}Hz)")
            print(f"   Clipping to {nyquist * 0.9}Hz")
            cutoff_freq[i] = nyquist * 0.9
    
    normalized_cutoff = [f / nyquist for f in cutoff_freq]
    
    # Always use window method for reliability
    if filter_type == 'lowpass':
        coefficients = signal.firwin(order + 1, normalized_cutoff[0], 
                                    window='hamming', fs=2)
    elif filter_type == 'highpass':
        coefficients = signal.firwin(order + 1, normalized_cutoff[0],
                                    window='hamming', pass_zero=False, fs=2)
    elif filter_type == 'bandpass':
        coefficients = signal.firwin(order + 1, normalized_cutoff,
                                    window='hamming', pass_zero=False, fs=2)
    else:  # bandstop
        coefficients = signal.firwin(order + 1, normalized_cutoff,
                                    window='hamming', pass_zero=True, fs=2)
    
    return coefficients

def calculate_snr(original, filtered):
    """
    Calculate SNR between original and filtered signals
    """
    error = original - filtered
    signal_power = np.mean(original**2)
    noise_power = np.mean(error**2)
    
    if noise_power == 0:
        return float('inf'), 0.0
    
    snr_db = 10 * np.log10(signal_power / noise_power)
    mse = np.mean(error**2)
    
    return snr_db, mse

def sweep_filter_parameter(param_name, param_values, test_signal, fs=1000, save_plots=True):
    """
    Sweep a filter parameter and compute performance metrics
    """
    results = {
        'parameters': param_values,
        'snr_values': [],
        'mse_values': [],
        'coefficients': [],
        'filtered_signals': []
    }
    
    for param in param_values:
        if param_name == 'order':
            coefficients = design_fir_filter(param, 0.2, fs)
        elif param_name == 'cutoff':
            coefficients = design_fir_filter(30, param, fs)
        else:
            coefficients = design_fir_filter(30, 0.2, fs)
        
        filtered = signal.lfilter(coefficients, 1.0, test_signal)
        snr_db, mse = calculate_snr(test_signal, filtered)
        
        results['snr_values'].append(snr_db)
        results['mse_values'].append(mse)
        results['coefficients'].append(coefficients)
        results['filtered_signals'].append(filtered)
    
    if save_plots:
        plot_parameter_sweep(results, param_name, param_values)
    
    return results

def plot_parameter_sweep(results, param_name, param_values, save_dir='results'):
    """
    Create and save parameter sweep plots
    """
    # Create results directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    plt.figure(figsize=(12, 5))
    
    # Plot SNR
    plt.subplot(1, 2, 1)
    plt.plot(param_values, results['snr_values'], 'bo-', linewidth=2, markersize=8)
    plt.xlabel(f'Filter {param_name.capitalize()}')
    plt.ylabel('SNR (dB)')
    plt.title(f'SNR vs Filter {param_name.capitalize()}')
    plt.grid(True, alpha=0.3)
    
    # Plot MSE (log scale)
    plt.subplot(1, 2, 2)
    plt.plot(param_values, results['mse_values'], 'ro-', linewidth=2, markersize=8)
    plt.xlabel(f'Filter {param_name.capitalize()}')
    plt.ylabel('MSE (log scale)')
    plt.title(f'MSE vs Filter {param_name.capitalize()}')
    plt.grid(True, alpha=0.3)
    plt.yscale('log')
    
    plt.tight_layout()
    plt.savefig(f'{save_dir}/parameter_sweep_{param_name}.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved parameter sweep plot: results/parameter_sweep_{param_name}.png")

def plot_frequency_response(coefficients, fs=1000, save_dir='results'):
    """
    Plot and save filter frequency response
    """
    os.makedirs(save_dir, exist_ok=True)
    
    w, h = signal.freqz(coefficients, worN=1024)
    freq_hz = w * fs / (2 * np.pi)
    
    plt.figure(figsize=(10, 6))
    
    # Magnitude response
    plt.subplot(2, 1, 1)
    plt.plot(freq_hz, 20*np.log10(np.abs(h) + 1e-10))
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude (dB)')
    plt.title(f'Filter Frequency Response ({len(coefficients)}-tap FIR)')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, fs/2)
    
    # Phase response
    plt.subplot(2, 1, 2)
    plt.plot(freq_hz, np.unwrap(np.angle(h)))
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Phase (radians)')
    plt.title('Phase Response')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, fs/2)
    
    plt.tight_layout()
    plt.savefig(f'{save_dir}/filter_response.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved frequency response plot: results/filter_response.png")

def create_homework_style_plot(fs=1000, save_dir='results'):
    """
    Create a plot that directly references EE 4377 homework style
    with zero-padding FFT analysis
    """
    os.makedirs(save_dir, exist_ok=True)
    
    # Create test signal similar to homework
    duration = 0.5
    t = np.arange(0, duration, 1/fs)
    f1, f2 = 50, 120
    test_signal = np.sin(2*np.pi*f1*t) + 0.5*np.sin(2*np.pi*f2*t)
    
    # Compute spectra with different zero-padding (like homework)
    N = len(test_signal)
    
    # No zero-padding
    spectrum1 = np.fft.fft(test_signal, N)
    freq1 = np.fft.fftfreq(N, 1/fs)
    mag1 = np.abs(spectrum1)[:N//2] * 2 / N
    
    # 2x zero-padding
    nfft2 = 2 * N
    spectrum2 = np.fft.fft(test_signal, nfft2)
    freq2 = np.fft.fftfreq(nfft2, 1/fs)
    mag2 = np.abs(spectrum2)[:nfft2//2] * 2 / N
    
    # 8x zero-padding
    nfft3 = 8 * N
    spectrum3 = np.fft.fft(test_signal, nfft3)
    freq3 = np.fft.fftfreq(nfft3, 1/fs)
    mag3 = np.abs(spectrum3)[:nfft3//2] * 2 / N
    
    # Create the plot (homework style)
    plt.figure(figsize=(12, 8))
    
    # Time domain
    plt.subplot(2, 1, 1)
    plt.plot(t, test_signal, 'b-', linewidth=1.5, alpha=0.7)
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.title('Time Domain: Two Sinusoids (EE 4377 Homework Style)')
    plt.grid(True, alpha=0.3)
    
    # Frequency domain with different zero-padding
    plt.subplot(2, 1, 2)
    plt.plot(freq1[:N//2], mag1, 'ro-', markersize=4, alpha=0.7, label='No zero-padding')
    plt.plot(freq2[:nfft2//2], mag2, 'g-', linewidth=1.5, alpha=0.8, label='2x zero-padding')
    plt.plot(freq3[:nfft3//2], mag3, 'b-', linewidth=1, alpha=0.9, label='8x zero-padding')
    
    # Mark expected frequencies (like homework)
    plt.axvline(x=f1, color='red', linestyle='--', alpha=0.5, label=f'f1={f1}Hz')
    plt.axvline(x=f2, color='blue', linestyle='--', alpha=0.5, label=f'f2={f2}Hz')
    
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.title('Spectrum with Different Zero-Padding Levels (Homework Reference)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 200)
    
    plt.tight_layout()
    plt.savefig(f'{save_dir}/zero_padding_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved homework-style plot: results/zero_padding_comparison.png")
    
    return test_signal

class SpectrumAnalyzer:
    """
    Spectrum analyzer with zero-padding and filter visualization
    """
    
    def __init__(self, signal_data, fs):
        self.signal = signal_data
        self.fs = fs
        self.N = len(signal_data)
        
    def compute_spectrum(self, nfft=None, zero_padding=0):
        """
        Compute spectrum with optional zero-padding
        """
        if nfft is None:
            nfft = self.N
        
        if zero_padding > 0:
            padded_signal = np.pad(self.signal, (0, zero_padding), 'constant')
            nfft = len(padded_signal)
        else:
            padded_signal = self.signal
        
        spectrum = np.fft.fft(padded_signal, nfft)
        magnitude = np.abs(spectrum)
        freq = np.fft.fftfreq(nfft, 1/self.fs)
        
        positive_idx = nfft // 2
        positive_freq = freq[:positive_idx]
        positive_magnitude = magnitude[:positive_idx] * 2 / self.N
        
        return positive_freq, positive_magnitude
    
    def analyze_filter_effect(self, coefficients, title="Filter Effect", save_plot=True):
        """
        Show how filtering affects the signal spectrum
        """
        filtered = signal.lfilter(coefficients, 1.0, self.signal)
        
        freq_orig, mag_orig = self.compute_spectrum(zero_padding=1024)
        analyzer_filt = SpectrumAnalyzer(filtered, self.fs)
        freq_filt, mag_filt = analyzer_filt.compute_spectrum(zero_padding=1024)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        t = np.arange(len(self.signal)) / self.fs
        axes[0,0].plot(t, self.signal, 'b-', alpha=0.7, label='Original')
        axes[0,0].plot(t, filtered, 'r-', alpha=0.7, label='Filtered')
        axes[0,0].set_xlabel('Time (s)')
        axes[0,0].set_ylabel('Amplitude')
        axes[0,0].set_title('Time Domain: Original vs Filtered')
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)
        
        w, h = signal.freqz(coefficients, worN=1024)
        freq_hz = w * self.fs / (2 * np.pi)
        axes[0,1].plot(freq_hz, 20*np.log10(np.abs(h) + 1e-10), 'g-', linewidth=2)
        axes[0,1].set_xlabel('Frequency (Hz)')
        axes[0,1].set_ylabel('Magnitude (dB)')
        axes[0,1].set_title('Filter Frequency Response')
        axes[0,1].grid(True, alpha=0.3)
        
        axes[1,0].plot(freq_orig, mag_orig, 'b-', alpha=0.7, label='Original')
        axes[1,0].plot(freq_filt, mag_filt, 'r-', alpha=0.6, label='Filtered')
        axes[1,0].set_xlabel('Frequency (Hz)')
        axes[1,0].set_ylabel('Magnitude')
        axes[1,0].set_title('Spectrum Comparison (with zero-padding)')
        axes[1,0].legend()
        axes[1,0].grid(True, alpha=0.3)
        
        spectral_diff = mag_orig - mag_filt
        axes[1,1].plot(freq_orig, spectral_diff, 'purple', alpha=0.8)
        axes[1,1].fill_between(freq_orig, 0, spectral_diff, alpha=0.3, color='purple')
        axes[1,1].set_xlabel('Frequency (Hz)')
        axes[1,1].set_ylabel('Spectral Difference')
        axes[1,1].set_title('What the Filter Removed')
        axes[1,1].grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14)
        plt.tight_layout()
        
        if save_plot:
            os.makedirs('results', exist_ok=True)
            plt.savefig('results/spectrum_analysis.png', dpi=150, bbox_inches='tight')
            plt.close()
            print(f"Saved spectrum analysis plot: results/spectrum_analysis.png")
        else:
            plt.show()
        
        snr_db, mse = calculate_snr(self.signal, filtered)
        print(f"Filter Performance: SNR={snr_db:.2f} dB, MSE={mse:.6f}")
        
        return filtered