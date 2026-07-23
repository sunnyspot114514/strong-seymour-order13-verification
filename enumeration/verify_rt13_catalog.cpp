#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

constexpr int N = 13;
constexpr int SIDE = 6;
constexpr std::uint64_t EXPECTED_RECORDS = 1495297;

struct VertexResult {
  bool strong = false;
  int matching_size = 0;
  std::uint8_t defect_left_subset = 0;
  std::uint8_t defect_neighbors = 0;
  std::array<int, SIDE> left{};
  std::array<int, SIDE> right{};
  std::array<int, SIDE> match_left_to_right{};
};

struct Witness {
  std::uint64_t catalog_index = 0;
  std::string upper_triangle;
  std::array<std::uint16_t, N> out{};
  std::array<VertexResult, N> vertices{};
  int strong_count = N;
};

[[noreturn]] void fail(const std::string& message) {
  std::cerr << "ERROR: " << message << '\n';
  std::exit(1);
}

std::array<std::uint16_t, N> parse_tournament(
    const std::string& encoding, std::uint64_t index) {
  if (encoding.size() != N * (N - 1) / 2) {
    fail("record " + std::to_string(index) + " has length " +
         std::to_string(encoding.size()) + ", expected 78");
  }

  std::array<std::uint16_t, N> out{};
  std::size_t pos = 0;
  for (int i = 0; i < N; ++i) {
    for (int j = i + 1; j < N; ++j) {
      const char bit = encoding[pos++];
      if (bit == '1') {
        out[i] |= static_cast<std::uint16_t>(1u << j);
      } else if (bit == '0') {
        out[j] |= static_cast<std::uint16_t>(1u << i);
      } else {
        fail("record " + std::to_string(index) +
             " contains a character other than 0 or 1");
      }
    }
  }

  for (int v = 0; v < N; ++v) {
    if (__builtin_popcount(out[v]) != SIDE) {
      fail("record " + std::to_string(index) + " is not 6-regular");
    }
  }
  return out;
}

std::array<std::uint8_t, SIDE> build_bipartite_rows(
    const std::array<std::uint16_t, N>& out, int root,
    std::array<int, SIDE>& left, std::array<int, SIDE>& right) {
  int nl = 0;
  int nr = 0;
  for (int v = 0; v < N; ++v) {
    if (v == root) continue;
    if (out[root] & (1u << v)) {
      if (nl >= SIDE) fail("out-neighborhood overflow");
      left[nl++] = v;
    } else {
      if (nr >= SIDE) fail("in-neighborhood overflow");
      right[nr++] = v;
    }
  }
  if (nl != SIDE || nr != SIDE) fail("unexpected neighborhood size");

  std::array<std::uint8_t, SIDE> rows{};
  for (int i = 0; i < SIDE; ++i) {
    for (int j = 0; j < SIDE; ++j) {
      if (out[left[i]] & (1u << right[j])) {
        rows[i] |= static_cast<std::uint8_t>(1u << j);
      }
    }
  }
  return rows;
}

// Hall's theorem: a perfect matching exists exactly when every subset of
// the left side has at least as many neighbors as vertices.
bool hall_has_perfect_matching(
    const std::array<std::uint8_t, SIDE>& rows,
    std::uint8_t& defect_subset, std::uint8_t& defect_neighbors) {
  std::array<std::uint8_t, 1 << SIDE> neighbor_union{};
  for (int subset = 1; subset < (1 << SIDE); ++subset) {
    const int bit = __builtin_ctz(subset);
    const int previous = subset & (subset - 1);
    neighbor_union[subset] =
        static_cast<std::uint8_t>(neighbor_union[previous] | rows[bit]);
    if (__builtin_popcount(neighbor_union[subset]) <
        __builtin_popcount(static_cast<unsigned>(subset))) {
      defect_subset = static_cast<std::uint8_t>(subset);
      defect_neighbors = neighbor_union[subset];
      return false;
    }
  }
  defect_subset = 0;
  defect_neighbors = 0;
  return true;
}

// Separately implemented Kuhn augmenting-path matching, evaluated for every
// root and checked against the Hall-subset result.
bool augment(int u, const std::array<std::uint8_t, SIDE>& rows,
             std::array<int, SIDE>& match_right, std::uint8_t& seen) {
  std::uint8_t available = rows[u];
  while (available) {
    const int v = __builtin_ctz(available);
    available &= static_cast<std::uint8_t>(available - 1);
    if (seen & (1u << v)) continue;
    seen |= static_cast<std::uint8_t>(1u << v);
    if (match_right[v] == -1 ||
        augment(match_right[v], rows, match_right, seen)) {
      match_right[v] = u;
      return true;
    }
  }
  return false;
}

int maximum_matching_size(
    const std::array<std::uint8_t, SIDE>& rows,
    std::array<int, SIDE>& match_left_to_right) {
  std::array<int, SIDE> match_right{};
  match_right.fill(-1);
  match_left_to_right.fill(-1);
  int size = 0;
  for (int u = 0; u < SIDE; ++u) {
    std::uint8_t seen = 0;
    if (augment(u, rows, match_right, seen)) ++size;
  }
  for (int v = 0; v < SIDE; ++v) {
    if (match_right[v] != -1) {
      match_left_to_right[match_right[v]] = v;
    }
  }
  return size;
}

VertexResult check_vertex(const std::array<std::uint16_t, N>& out,
                          int root) {
  VertexResult result;
  const auto rows =
      build_bipartite_rows(out, root, result.left, result.right);
  result.strong = hall_has_perfect_matching(
      rows, result.defect_left_subset, result.defect_neighbors);
  result.matching_size =
      maximum_matching_size(rows, result.match_left_to_right);
  if (result.strong != (result.matching_size == SIDE)) {
    fail("Hall and augmenting-path implementations disagree");
  }
  return result;
}

std::string adjacency_row(const std::array<std::uint16_t, N>& out, int v) {
  std::string row;
  row.reserve(N);
  for (int w = 0; w < N; ++w) {
    row.push_back((out[v] & (1u << w)) ? '1' : '0');
  }
  return row;
}

void print_int_array(std::ostream& output, const std::vector<int>& values) {
  output << '[';
  for (std::size_t i = 0; i < values.size(); ++i) {
    if (i) output << ',';
    output << values[i];
  }
  output << ']';
}

void print_witness(const Witness& witness) {
  std::cout << "  \"first_minimum_witness\": {\n";
  std::cout << "    \"catalog_index_1_based\": " << witness.catalog_index
            << ",\n";
  std::cout << "    \"upper_triangle\": \"" << witness.upper_triangle
            << "\",\n";
  std::cout << "    \"strong_count\": " << witness.strong_count << ",\n";

  std::vector<int> non_strong;
  std::vector<int> matching_sizes;
  for (int v = 0; v < N; ++v) {
    if (!witness.vertices[v].strong) non_strong.push_back(v);
    matching_sizes.push_back(witness.vertices[v].matching_size);
  }
  std::cout << "    \"non_strong_vertices\": ";
  print_int_array(std::cout, non_strong);
  std::cout << ",\n    \"matching_sizes\": ";
  print_int_array(std::cout, matching_sizes);
  std::cout << ",\n";

  std::cout << "    \"adjacency_matrix\": [\n";
  for (int v = 0; v < N; ++v) {
    std::cout << "      \"" << adjacency_row(witness.out, v) << "\""
              << (v + 1 == N ? "\n" : ",\n");
  }
  std::cout << "    ],\n";

  std::cout << "    \"hall_defects\": [\n";
  bool first_defect = true;
  for (int v = 0; v < N; ++v) {
    const auto& result = witness.vertices[v];
    if (result.strong) continue;
    if (!first_defect) std::cout << ",\n";
    first_defect = false;
    std::vector<int> subset;
    std::vector<int> neighbors;
    for (int i = 0; i < SIDE; ++i) {
      if (result.defect_left_subset & (1u << i)) {
        subset.push_back(result.left[i]);
      }
      if (result.defect_neighbors & (1u << i)) {
        neighbors.push_back(result.right[i]);
      }
    }
    std::cout << "      {\"vertex\":" << v << ",\"S\":";
    print_int_array(std::cout, subset);
    std::cout << ",\"GammaS\":";
    print_int_array(std::cout, neighbors);
    std::cout << '}';
  }
  std::cout << "\n    ]\n  }\n";
}

void print_exception_record(
    std::ostream& output, std::uint64_t catalog_index,
    const std::string& upper_triangle,
    const std::array<VertexResult, N>& vertices, int strong_count) {
  std::vector<int> non_strong;
  std::vector<int> matching_sizes;
  for (int v = 0; v < N; ++v) {
    if (!vertices[v].strong) non_strong.push_back(v);
    matching_sizes.push_back(vertices[v].matching_size);
  }

  output << "{\"catalog_index_1_based\":" << catalog_index
         << ",\"upper_triangle\":\"" << upper_triangle
         << "\",\"strong_count\":" << strong_count
         << ",\"non_strong_vertices\":";
  print_int_array(output, non_strong);
  output << ",\"matching_sizes\":";
  print_int_array(output, matching_sizes);

  output << ",\"hall_defects\":[";
  bool first_defect = true;
  for (int v = 0; v < N; ++v) {
    const auto& result = vertices[v];
    if (result.strong) continue;
    if (!first_defect) output << ',';
    first_defect = false;
    std::vector<int> subset;
    std::vector<int> neighbors;
    for (int i = 0; i < SIDE; ++i) {
      if (result.defect_left_subset & (1u << i)) {
        subset.push_back(result.left[i]);
      }
      if (result.defect_neighbors & (1u << i)) {
        neighbors.push_back(result.right[i]);
      }
    }
    output << "{\"vertex\":" << v << ",\"S\":";
    print_int_array(output, subset);
    output << ",\"GammaS\":";
    print_int_array(output, neighbors);
    output << '}';
  }

  output << "],\"perfect_matchings\":[";
  bool first_matching = true;
  for (int v = 0; v < N; ++v) {
    const auto& result = vertices[v];
    if (!result.strong) continue;
    if (!first_matching) output << ',';
    first_matching = false;
    output << "{\"vertex\":" << v << ",\"edges\":[";
    for (int i = 0; i < SIDE; ++i) {
      const int matched_right = result.match_left_to_right[i];
      if (matched_right < 0 || matched_right >= SIDE) {
        fail("strong vertex is missing a perfect-matching edge");
      }
      if (i) output << ',';
      output << '[' << result.left[i] << ','
             << result.right[matched_right] << ']';
    }
    output << "]}";
  }
  output << "]}\n";
}

}  // namespace

int main(int argc, char** argv) {
  std::uint64_t expected_records = EXPECTED_RECORDS;
  std::string exceptions_file;
  for (int i = 1; i < argc; ++i) {
    const std::string option = argv[i];
    if (option == "--expected-records") {
      if (++i >= argc) fail("--expected-records requires a value");
      try {
        expected_records = std::stoull(argv[i]);
      } catch (...) {
        fail("invalid value for --expected-records");
      }
      if (expected_records == 0) {
        fail("expected record count must be positive");
      }
    } else if (option == "--exceptions-file") {
      if (++i >= argc) fail("--exceptions-file requires a path");
      exceptions_file = argv[i];
      if (exceptions_file.empty()) fail("exceptions path must not be empty");
    } else {
      fail("usage: verify_rt13_catalog [--expected-records N] "
           "[--exceptions-file PATH]");
    }
  }

  std::ios::sync_with_stdio(false);
  std::cin.tie(nullptr);

  std::ofstream exceptions_output;
  if (!exceptions_file.empty()) {
    exceptions_output.open(exceptions_file, std::ios::out | std::ios::trunc);
    if (!exceptions_output) {
      fail("cannot open exceptions file: " + exceptions_file);
    }
  }

  std::array<std::uint64_t, N + 1> distribution{};
  std::uint64_t records = 0;
  std::uint64_t minimum_count = 0;
  int minimum_strong = N + 1;
  Witness first_minimum;
  std::string line;
  const auto start = std::chrono::steady_clock::now();

  while (std::getline(std::cin, line)) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (line.empty()) fail("empty catalog record");
    ++records;
    const auto out = parse_tournament(line, records);

    std::array<VertexResult, N> vertex_results{};
    int strong_count = 0;
    for (int v = 0; v < N; ++v) {
      vertex_results[v] = check_vertex(out, v);
      if (vertex_results[v].strong) ++strong_count;
    }
    ++distribution[strong_count];
    if (exceptions_output && strong_count < N) {
      print_exception_record(exceptions_output, records, line, vertex_results,
                             strong_count);
    }

    if (strong_count < minimum_strong) {
      minimum_strong = strong_count;
      minimum_count = 1;
      first_minimum = Witness{records, line, out, vertex_results,
                              strong_count};
    } else if (strong_count == minimum_strong) {
      ++minimum_count;
    }

    if (records % 100000 == 0) {
      const auto now = std::chrono::steady_clock::now();
      const double seconds =
          std::chrono::duration<double>(now - start).count();
      std::cerr << "processed=" << records << " elapsed_seconds=" << seconds
                << " current_minimum=" << minimum_strong << '\n';
    }
  }

  if (records != expected_records) {
    fail("catalog contains " + std::to_string(records) +
         " records, expected " + std::to_string(expected_records));
  }

  const auto end = std::chrono::steady_clock::now();
  const double elapsed = std::chrono::duration<double>(end - start).count();
  std::cerr << "complete records=" << records << " elapsed_seconds="
            << elapsed << " minimum_strong=" << minimum_strong
            << " minimum_count=" << minimum_count << '\n';

  std::cout << "{\n";
  std::cout << "  \"catalog_records\": " << records << ",\n";
  std::cout << "  \"vertex_checks\": " << records * N << ",\n";
  std::cout << "  \"all_records_valid_6_regular_tournaments\": true,\n";
  std::cout << "  \"hall_and_augmenting_path_agree_everywhere\": true,\n";
  std::cout << "  \"minimum_strong_vertices\": " << minimum_strong << ",\n";
  std::cout << "  \"maximum_non_strong_vertices\": " << N - minimum_strong
            << ",\n";
  std::cout << "  \"minimum_isomorphism_class_count\": " << minimum_count
            << ",\n";
  std::cout << "  \"strong_count_distribution_unlabelled\": {\n";
  bool first = true;
  for (int count = 0; count <= N; ++count) {
    if (!distribution[count]) continue;
    if (!first) std::cout << ",\n";
    first = false;
    std::cout << "    \"" << count << "\": " << distribution[count];
  }
  std::cout << "\n  },\n";
  print_witness(first_minimum);
  std::cout << "}\n";
  return 0;
}
