{ pkgs ? import <nixpkgs> {} }:

let
  # Define the python version and the specific packages needed
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    requests          # For fetching the web pages
    beautifulsoup4    # For parsing HTML
    pandas            # For data manipulation
    xlsxwriter        # For creating Excel dropdowns and colors
    openpyxl          # For reading/writing Excel files
  ]);
in

pkgs.mkShell {
  buildInputs = [
    pythonEnv
  ];

  # Optional: Environmental variables or shell aliases
  shellHook = ''
    echo "--- Job Scraper Dev Environment ---"
    echo "Python version: $(python --version)"
    echo "Libraries available: requests, bs4, pandas, xlsxwriter"
    echo "Usage: python job_scraper.py"
    echo "-----------------------------------"
  '';
}
