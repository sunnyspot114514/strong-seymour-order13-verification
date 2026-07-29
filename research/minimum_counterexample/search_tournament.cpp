#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int required_minimum_outdegree = 6;

struct Evaluation {
  int strong = 0;
  int total_gap = 0;
  int strong_cover_distance = 0;
  int degree_penalty = 0;
  std::vector<int> matching;
  std::vector<int> outdegree;

  long long energy() const {
    return 100000000LL * degree_penalty + 1000000LL * strong +
           1000LL * strong_cover_distance - total_gap;
  }
};

struct Tournament {
  int n = 0;
  std::vector<std::uint32_t> out;
};

bool augment(int left_vertex, std::uint32_t right_mask,
             const std::vector<std::uint32_t>& out, std::vector<int>& match,
             std::uint32_t& seen) {
  std::uint32_t available = out[left_vertex] & right_mask & ~seen;
  while (available != 0) {
    const int right_vertex = __builtin_ctz(available);
    available &= available - 1;
    seen |= std::uint32_t{1} << right_vertex;
    if (match[right_vertex] < 0 ||
        augment(match[right_vertex], right_mask, out, match, seen)) {
      match[right_vertex] = left_vertex;
      return true;
    }
  }
  return false;
}

int cover_distance(const std::vector<std::uint32_t>& rows,
                   std::uint32_t right_mask) {
  const int left_count = static_cast<int>(rows.size());
  const int budget = left_count - 1;
  int best = std::numeric_limits<int>::max();
  const std::uint32_t subset_count = std::uint32_t{1} << left_count;
  for (std::uint32_t left_cover = 0; left_cover < subset_count;
       ++left_cover) {
    const int left_size = __builtin_popcount(left_cover);
    const int right_budget = budget - left_size;
    if (right_budget < 0) {
      continue;
    }
    std::array<int, 32> column_degrees{};
    int uncovered_edges = 0;
    for (int source = 0; source < left_count; ++source) {
      if ((left_cover >> source) & 1U) {
        continue;
      }
      std::uint32_t targets = rows[source] & right_mask;
      uncovered_edges += __builtin_popcount(targets);
      while (targets != 0) {
        const int target = __builtin_ctz(targets);
        targets &= targets - 1;
        ++column_degrees[target];
      }
    }
    std::sort(column_degrees.begin(), column_degrees.end(),
              std::greater<int>());
    for (int index = 0; index < right_budget; ++index) {
      uncovered_edges -= column_degrees[index];
    }
    best = std::min(best, uncovered_edges);
  }
  return best;
}

Evaluation evaluate(const Tournament& tournament) {
  const int n = tournament.n;
  const std::uint32_t all =
      n == 32 ? std::numeric_limits<std::uint32_t>::max()
              : ((std::uint32_t{1} << n) - 1);
  Evaluation result;
  result.matching.reserve(n);
  result.outdegree.reserve(n);
  for (int root = 0; root < n; ++root) {
    const std::uint32_t first = tournament.out[root];
    std::uint32_t second = 0;
    std::uint32_t pending = first;
    while (pending != 0) {
      const int vertex = __builtin_ctz(pending);
      pending &= pending - 1;
      second |= tournament.out[vertex];
    }
    second &= ~first;
    second &= ~(std::uint32_t{1} << root);
    second &= all;

    std::vector<int> match(n, -1);
    std::vector<std::uint32_t> matching_rows;
    int matching_size = 0;
    int bipartite_edges = 0;
    pending = first;
    while (pending != 0) {
      const int left_vertex = __builtin_ctz(pending);
      pending &= pending - 1;
      matching_rows.push_back(tournament.out[left_vertex] & second);
      bipartite_edges += __builtin_popcount(matching_rows.back());
      std::uint32_t seen = 0;
      if (augment(left_vertex, second, tournament.out, match, seen)) {
        ++matching_size;
      }
    }
    const int degree = __builtin_popcount(first);
    const int gap = degree - matching_size;
    result.matching.push_back(matching_size);
    result.outdegree.push_back(degree);
    result.total_gap += gap;
    result.degree_penalty +=
        std::max(0, required_minimum_outdegree - degree);
    if (gap == 0) {
      ++result.strong;
      result.strong_cover_distance +=
          degree <= 7 ? cover_distance(matching_rows, second)
                      : bipartite_edges - degree;
    }
  }
  return result;
}

void flip_edge(Tournament& tournament, int u, int v) {
  if (u == v) {
    throw std::runtime_error("cannot flip a loop");
  }
  if ((tournament.out[u] >> v) & 1U) {
    tournament.out[u] &= ~(std::uint32_t{1} << v);
    tournament.out[v] |= std::uint32_t{1} << u;
  } else {
    tournament.out[v] &= ~(std::uint32_t{1} << u);
    tournament.out[u] |= std::uint32_t{1} << v;
  }
}

bool is_directed_triangle(const Tournament& tournament, int u, int v, int w) {
  const bool uv = (tournament.out[u] >> v) & 1U;
  const bool vw = (tournament.out[v] >> w) & 1U;
  const bool wu = (tournament.out[w] >> u) & 1U;
  return (uv && vw && wu) || (!uv && !vw && !wu);
}

void reverse_directed_triangle(Tournament& tournament, int u, int v, int w) {
  flip_edge(tournament, u, v);
  flip_edge(tournament, v, w);
  flip_edge(tournament, w, u);
}

Tournament read_matrix(const std::string& path) {
  std::ifstream input(path);
  if (!input) {
    throw std::runtime_error("cannot open matrix: " + path);
  }
  std::vector<std::string> rows;
  std::string line;
  while (std::getline(input, line)) {
    if (!line.empty() && line.back() == '\r') {
      line.pop_back();
    }
    if (!line.empty()) {
      rows.push_back(line);
    }
  }
  Tournament result;
  result.n = static_cast<int>(rows.size());
  if (result.n <= 0 || result.n > 31) {
    throw std::runtime_error("unsupported matrix order");
  }
  result.out.assign(result.n, 0);
  for (int u = 0; u < result.n; ++u) {
    if (static_cast<int>(rows[u].size()) != result.n) {
      throw std::runtime_error("matrix is not square");
    }
    for (int v = 0; v < result.n; ++v) {
      if (rows[u][v] == '1') {
        result.out[u] |= std::uint32_t{1} << v;
      } else if (rows[u][v] != '0') {
        throw std::runtime_error("matrix is not binary");
      }
    }
  }
  for (int u = 0; u < result.n; ++u) {
    if ((result.out[u] >> u) & 1U) {
      throw std::runtime_error("matrix has a loop");
    }
    for (int v = u + 1; v < result.n; ++v) {
      const int arcs = ((result.out[u] >> v) & 1U) +
                       ((result.out[v] >> u) & 1U);
      if (arcs != 1) {
        throw std::runtime_error("matrix is not a tournament");
      }
    }
  }
  return result;
}

Tournament delete_vertex(const Tournament& source, int deleted) {
  Tournament result;
  result.n = source.n - 1;
  result.out.assign(result.n, 0);
  std::vector<int> kept;
  for (int vertex = 0; vertex < source.n; ++vertex) {
    if (vertex != deleted) {
      kept.push_back(vertex);
    }
  }
  for (int u = 0; u < result.n; ++u) {
    for (int v = 0; v < result.n; ++v) {
      if ((source.out[kept[u]] >> kept[v]) & 1U) {
        result.out[u] |= std::uint32_t{1} << v;
      }
    }
  }
  return result;
}

std::string matrix_text(const Tournament& tournament) {
  std::ostringstream output;
  for (int u = 0; u < tournament.n; ++u) {
    for (int v = 0; v < tournament.n; ++v) {
      output << (((tournament.out[u] >> v) & 1U) ? '1' : '0');
    }
    output << '\n';
  }
  return output.str();
}

void report_best(const Tournament& tournament, const Evaluation& evaluation,
                 int restart, long long iteration) {
  std::cerr << "best strong=" << evaluation.strong
            << " energy=" << evaluation.energy()
            << " degree_penalty=" << evaluation.degree_penalty
            << " total_gap=" << evaluation.total_gap
            << " cover_distance=" << evaluation.strong_cover_distance
            << " restart=" << restart << " iteration=" << iteration << '\n';
    if (evaluation.strong == 0 && evaluation.degree_penalty == 0) {
      std::cout << matrix_text(tournament);
  }
}

bool exhaustive_repair(Tournament& tournament, int radius) {
  std::vector<std::pair<int, int>> edges;
  for (int u = 0; u < tournament.n; ++u) {
    for (int v = u + 1; v < tournament.n; ++v) {
      edges.emplace_back(u, v);
    }
  }
  long long checked = 0;
  for (int first = 0; first < static_cast<int>(edges.size()); ++first) {
    flip_edge(tournament, edges[first].first, edges[first].second);
    Evaluation evaluation = evaluate(tournament);
    ++checked;
    if (evaluation.strong == 0 && evaluation.degree_penalty == 0) {
      std::cerr << "exhaustive repair found at radius=1 checked=" << checked
                << '\n';
      std::cout << matrix_text(tournament);
      return true;
    }
    if (radius >= 2) {
      for (int second = first + 1;
           second < static_cast<int>(edges.size()); ++second) {
        flip_edge(tournament, edges[second].first, edges[second].second);
        evaluation = evaluate(tournament);
        ++checked;
        if (evaluation.strong == 0 && evaluation.degree_penalty == 0) {
          std::cerr << "exhaustive repair found at radius=2 checked="
                    << checked << '\n';
          std::cout << matrix_text(tournament);
          return true;
        }
        if (radius >= 3) {
          for (int third = second + 1;
               third < static_cast<int>(edges.size()); ++third) {
            flip_edge(tournament, edges[third].first, edges[third].second);
            evaluation = evaluate(tournament);
            ++checked;
            if (evaluation.strong == 0 && evaluation.degree_penalty == 0) {
              std::cerr << "exhaustive repair found at radius=3 checked="
                        << checked << '\n';
              std::cout << matrix_text(tournament);
              return true;
            }
            flip_edge(tournament, edges[third].first, edges[third].second);
          }
        }
        flip_edge(tournament, edges[second].first, edges[second].second);
      }
    }
    flip_edge(tournament, edges[first].first, edges[first].second);
  }
  std::cerr << "exhaustive repair found none radius=" << radius
            << " checked=" << checked << '\n';
  return false;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 2 || argc > 10) {
    std::cerr << "usage: search_tournament MATRIX [RESTARTS] [ITERATIONS] "
                 "[SEED] [PERTURB] [REPAIR_RADIUS] [MIN_OUTDEGREE] "
                 "[BEST_MATRIX] [KEEP_ORDER]\n";
    return 2;
  }
  const Tournament source = read_matrix(argv[1]);
  const int restarts = argc >= 3 ? std::stoi(argv[2]) : 200;
  const long long iterations = argc >= 4 ? std::stoll(argv[3]) : 200000;
  const std::uint64_t seed =
      argc >= 5
          ? std::stoull(argv[4])
          : static_cast<std::uint64_t>(
                std::chrono::high_resolution_clock::now()
                    .time_since_epoch()
                    .count());
  const int perturb = argc >= 6 ? std::stoi(argv[5]) : 12;
  const int repair_radius = argc >= 7 ? std::stoi(argv[6]) : 2;
  required_minimum_outdegree = argc >= 8 ? std::stoi(argv[7]) : 6;
  const std::string best_matrix_path = argc >= 9 ? argv[8] : "";
  const bool keep_order = argc >= 10 ? std::stoi(argv[9]) != 0 : false;
  std::mt19937_64 random(seed);
  std::uniform_real_distribution<double> unit(0.0, 1.0);

  Tournament global_best;
  Evaluation global_evaluation;
  global_evaluation.strong = std::numeric_limits<int>::max();

  for (int restart = 0; restart < restarts; ++restart) {
    const int deleted = restart % source.n;
    Tournament current =
        keep_order ? source : delete_vertex(source, deleted);
    std::uniform_int_distribution<int> vertex(0, current.n - 1);
    for (int step = 0; step < perturb; ++step) {
      int u = vertex(random);
      int v = vertex(random);
      if (u == v) {
        --step;
        continue;
      }
      flip_edge(current, u, v);
    }
    Evaluation current_evaluation = evaluate(current);
    double temperature = 5000.0;

    for (long long iteration = 0; iteration < iterations; ++iteration) {
      if (current_evaluation.energy() < global_evaluation.energy()) {
        global_best = current;
        global_evaluation = current_evaluation;
        report_best(global_best, global_evaluation, restart, iteration);
        if (!best_matrix_path.empty()) {
          std::ofstream best_output(best_matrix_path);
          if (!best_output) {
            throw std::runtime_error("cannot write best matrix: " +
                                     best_matrix_path);
          }
          best_output << matrix_text(global_best);
        }
        if (global_evaluation.strong == 0 &&
            global_evaluation.degree_penalty == 0) {
          return 0;
        }
      }

      int u = vertex(random);
      int v = vertex(random);
      int w = -1;
      bool triangle_move = unit(random) < 0.5;
      if (u == v) {
        continue;
      }
      if (triangle_move) {
        w = vertex(random);
        if (w == u || w == v || !is_directed_triangle(current, u, v, w)) {
          continue;
        }
        reverse_directed_triangle(current, u, v, w);
      } else {
        flip_edge(current, u, v);
      }
      Evaluation candidate = evaluate(current);
      const long long delta =
          candidate.energy() - current_evaluation.energy();
      const bool accept =
          delta <= 0 ||
          unit(random) < std::exp(-static_cast<double>(delta) / temperature);
      if (accept) {
        current_evaluation = std::move(candidate);
      } else if (triangle_move) {
        reverse_directed_triangle(current, u, v, w);
      } else {
        flip_edge(current, u, v);
      }
      temperature *= 0.99995;
      if (temperature < 0.05) {
        temperature = 5000.0;
      }
    }
  }
  std::cerr << "no counterexample found; best strong="
            << global_evaluation.strong << " seed=" << seed << '\n';
  if (repair_radius > 0 &&
      exhaustive_repair(global_best, std::min(repair_radius, 3))) {
    return 0;
  }
  std::cout << matrix_text(global_best);
  return 1;
}
