# Hardware-Optimized Folded FIR Filter

![Verilog](https://img.shields.io/badge/Verilog-FF0000?style=flat&logo=verilog)
![MATLAB](https://img.shields.io/badge/MATLAB-orange?logo=mathworks)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python)
![DSP](https://img.shields.io/badge/DSP-8A2BE2)
![FPGA](https://img.shields.io/badge/FPGA-00599C?logo=xilinx)

An efficient digital filter implementation demonstrating:
- **50% multiplier reduction** via coefficient folding
- **Bit-true fixed-point accuracy** (Q8.8 format)
- **Full verification suite** with automated checks

## Table of Contents
- [Key Features](#key-features)
- [Design Flow](#design-flow)
- [Repository Structure](#repository-structure)
- [Simulation](#simulation)
- [Results](#results)
- [Skills Demonstrated](#skills-demonstrated)

## Key Features

### 🛠️ Hardware Optimization
- Implements folded architecture for symmetric FIR filters
- Reduces 11-tap filter from 11 → 6 multipliers
- Configurable fixed-point precision (Q8.8 default)

### 🔄 Full Design Flow
1. **MATLAB**: Floating-point design using FDA Tool
2. **Python**: Coefficient conversion to fixed-point
3. **Verilog**: Synthesizable RTL implementation
4. **Verification**: Self-checking testbench with 100% coverage

### ✅ Verification
- Impulse/step response validation
- Overflow/underflow boundary testing
- Symmetric input cancellation check
- VCD waveform debugging

## Design Flow
```mermaid
graph TD
    A[MATLAB FDA Tool] -->|Export Coefficients| B[Python Conversion]
    B -->|Q8.8 Coefficients| C[Verilog Implementation]
    C --> D[Icarus Simulation]
    D --> E[GTKWave Analysis]
