#include <cstdint>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int maximum_matching(const std::vector<std::uint32_t>& rows,
                     int right_count) {
  std::vector<int> matched_right(right_count, -1);
  std::function<bool(int, std::uint32_t&)> augment =
      [&](int left, std::uint32_t& seen) {
        std::uint32_t available = rows[left] & ~seen;
        while (available) {
          const int right = __builtin_ctz(available);
          available &= available - 1;
          seen |= std::uint32_t{1} << right;
          if (matched_right[right] < 0 ||
              augment(matched_right[right], seen)) {
            matched_right[right] = left;
            return true;
          }
        }
        return false;
      };
  int size = 0;
  for (int left = 0; left < static_cast<int>(rows.size()); ++left) {
    std::uint32_t seen = 0;
    if (augment(left, seen))
      ++size;
  }
  return size;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: verify MATRIX\n";
    return 2;
  }
  std::ifstream input(argv[1]);
  if (!input) {
    std::cerr << "cannot open matrix\n";
    return 2;
  }
  std::vector<std::string> matrix;
  for (std::string row; std::getline(input, row);)
    if (!row.empty())
      matrix.push_back(row);
  const int order = static_cast<int>(matrix.size());
  if (order < 1 || order > 31)
    throw std::runtime_error("unsupported order");
  std::vector<std::uint32_t> out(order);
  for (int u = 0; u < order; ++u) {
    if (static_cast<int>(matrix[u].size()) != order)
      throw std::runtime_error("matrix is not square");
    for (int v = 0; v < order; ++v) {
      if (matrix[u][v] == '1')
        out[u] |= std::uint32_t{1} << v;
      else if (matrix[u][v] != '0')
        throw std::runtime_error("matrix is not binary");
    }
  }
  for (int u = 0; u < order; ++u) {
    if (out[u] & (std::uint32_t{1} << u))
      throw std::runtime_error("matrix has a loop");
    for (int v = u + 1; v < order; ++v) {
      const int arcs = ((out[u] >> v) & 1U) + ((out[v] >> u) & 1U);
      if (arcs != 1)
        throw std::runtime_error("matrix is not a tournament");
    }
  }

  int strong_vertices = 0;
  for (int root = 0; root < order; ++root) {
    const std::uint32_t first_mask = out[root];
    std::uint32_t second_mask = 0;
    for (std::uint32_t pending = first_mask; pending;
         pending &= pending - 1)
      second_mask |= out[__builtin_ctz(pending)];
    second_mask &= ~first_mask;
    second_mask &= ~(std::uint32_t{1} << root);

    std::vector<int> left;
    std::vector<int> right;
    for (int vertex = 0; vertex < order; ++vertex) {
      if (first_mask & (std::uint32_t{1} << vertex))
        left.push_back(vertex);
      if (second_mask & (std::uint32_t{1} << vertex))
        right.push_back(vertex);
    }
    std::vector<std::uint32_t> rows(left.size());
    for (int i = 0; i < static_cast<int>(left.size()); ++i)
      for (int j = 0; j < static_cast<int>(right.size()); ++j)
        if (out[left[i]] & (std::uint32_t{1} << right[j]))
          rows[i] |= std::uint32_t{1} << j;

    const int matching =
        maximum_matching(rows, static_cast<int>(right.size()));
    std::uint32_t defect_subset = 0;
    std::uint32_t defect_gamma = 0;
    const std::uint32_t subsets =
        std::uint32_t{1} << static_cast<int>(left.size());
    for (std::uint32_t subset = 1; subset < subsets; ++subset) {
      std::uint32_t gamma = 0;
      for (int i = 0; i < static_cast<int>(left.size()); ++i)
        if (subset & (std::uint32_t{1} << i))
          gamma |= rows[i];
      if (__builtin_popcount(subset) > __builtin_popcount(gamma)) {
        defect_subset = subset;
        defect_gamma = gamma;
        break;
      }
    }
    const bool strong = matching == static_cast<int>(left.size());
    if (strong || !defect_subset)
      ++strong_vertices;
    std::cout << "v=" << root << " d=" << left.size()
              << " n2=" << right.size() << " matching=" << matching
              << " hall=" << __builtin_popcount(defect_subset) << ">"
              << __builtin_popcount(defect_gamma) << '\n';
  }
  std::cout << "order=" << order << " strong_vertices=" << strong_vertices
            << " verified=" << (strong_vertices == 0 ? "true" : "false")
            << '\n';
  return strong_vertices == 0 ? 0 : 1;
}
