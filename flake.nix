{
  description = "Job Scraper Dev Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonEnv = pkgs.python3.withPackages (
            ps: with ps; [
              requests
              beautifulsoup4
              pandas
              xlsxwriter
              openpyxl
              pip
              google-generativeai
              tabulate
              lmstudio
            ]
          );
        in
        {
          default = pkgs.mkShell {
            buildInputs = [ pythonEnv ];

            shellHook = ''
              echo "--- Job Scraper Dev Environment ---"
              echo "Python version: $(python --version)"
              echo "Libraries available: requests, bs4, pandas, xlsxwriter"
              echo "Usage: python job_scraper.py"
              echo "-----------------------------------"
            '';
          };
        }
      );
    };
}
