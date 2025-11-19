% Design FIR coefficients
order = 10;
cutoff = 0.2;
coefficients = firpm(order, [0, cutoff, cutoff+0.1, 1], [1, 1, 0, 0]); % Equiripple design

% Transpose coefficients to column vector (required for writematrix)
coefficients = coefficients'; 

% Export to CSV (correct syntax)
writematrix(coefficients, 'fir_coefficients.csv'); 

disp('Coefficients saved to fir_coefficients.csv');