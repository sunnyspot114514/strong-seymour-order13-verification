#include "cadical.hpp"

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc < 4) {
    std::cerr
        << "usage: generate_cadical_cubes INPUT.cnf DEPTH OUTPUT.cubes"
           " [ASSUMPTION ...]\n";
    return 2;
  }
  const int depth = std::atoi(argv[2]);
  if (depth < 1 || depth > 30) {
    std::cerr << "depth must lie between 1 and 30\n";
    return 2;
  }

  CaDiCaL::Solver solver;
  (void)solver.set("quiet", 1);
  (void)solver.set("verbose", 0);
  (void)solver.set("log", 0);
  int variables = 0;
  if (const char *error = solver.read_dimacs(argv[1], variables)) {
    std::cerr << error << '\n';
    return 2;
  }
  for (int index = 4; index < argc; ++index) {
    const int literal = std::atoi(argv[index]);
    if (!literal || std::abs(literal) > variables) {
      std::cerr << "invalid assumption literal\n";
      return 2;
    }
    solver.assume(literal);
  }
  const auto result = solver.generate_cubes(depth);
  std::ofstream output(argv[3]);
  if (!output) {
    std::cerr << "cannot open cube output\n";
    return 2;
  }
  output << "c cadical_status " << result.status << '\n';
  output << "c requested_depth " << depth << '\n';
  output << "c variables " << variables << '\n';
  output << "c assumptions " << argc - 4 << '\n';
  for (const auto &cube : result.cubes) {
    output << 'a';
    for (const int literal : cube)
      output << ' ' << literal;
    output << " 0\n";
  }
  std::cout << "status=" << result.status
            << " cubes=" << result.cubes.size() << '\n';
  return 0;
}
