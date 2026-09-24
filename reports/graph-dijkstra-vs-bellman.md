# Algorithm comparison: Dijkstra (binary heap) vs Bellman-Ford

> **Task:** single-source shortest path, non-negative weights  ·  **Family:** graph


**Warnings**

- Same problem, different preconditions: "single-source shortest path, non-negative weights" vs "single-source shortest path, possibly negative weights". Check that your workload satisfies both before trusting the verdict.


## Conclusion

For average-case time, Dijkstra (binary heap) (O((V+E)·log(V))) beats Bellman-Ford (O(V·E)). The advantage only materialises above n ≈ 4: for smaller inputs the theoretically worse algorithm can still win on constant factors.

**Overall winner: Dijkstra (binary heap)** (weighted score A=5.5 vs B=0)


## Complexity profiles

| | Dijkstra (binary heap) | Bellman-Ford |
|---|---|---|
| **category** | graph | graph |
| **task** | single-source shortest path, non-negative weights | single-source shortest path, possibly negative weights |
| **time best** | O((V+E)·log(V)) | O(V·E) |
| **time average** | O((V+E)·log(V)) | O(V·E) |
| **time worst** | O((V+E)·log(V)) | O(V·E) |
| **space worst** | O(V) | O(V) |

## Case-by-case verdict

| dimension | case | Dijkstra (binary heap) | Bellman-Ford | winner | A÷B as n→∞ | crossover n |
|---|---|---|---|---|---|---|
| time | best | `O((V+E)·log(V))` | `O(V·E)` | **Dijkstra (binary heap)** | A/B → 0 (≈ n^0.94) | — |
| time | average | `O((V+E)·log(V))` | `O(V·E)` | **Dijkstra (binary heap)** | A/B → 0 (≈ n^0.94) | — |
| time | worst | `O((V+E)·log(V))` | `O(V·E)` | **Dijkstra (binary heap)** | A/B → 0 (≈ n^0.94) | — |
| space | worst | `O(V)` | `O(V)` | **tie** | equal | — |

## Growth of the operation count (time/average case)

| n | Dijkstra (binary heap) `O((V+E)·log(V))` | Bellman-Ford `O(V·E)` | A ÷ B | cheaper |
|---|---|---|---|---|
| 10 | 66.4 | 100 | 0.664 | A |
| 100 | 1.33e+03 | 1e+04 | 0.133 | A |
| 1,000 | 1.99e+04 | 1e+06 | 0.0199 | A |
| 10,000 | 2.66e+05 | 1e+08 | 0.00266 | A |
| 100,000 | 3.32e+06 | 1e+10 | 0.000332 | A |
| 1,000,000 | 3.99e+07 | 1.00e+12 | 3.99e-05 | A |
| 10,000,000 | 4.65e+08 | 1.00e+14 | 4.65e-06 | A |
| 1,000,000,000 | 5.98e+10 | 1.00e+18 | 5.98e-08 | A |

*Values are the declared growth functions evaluated at n — they count abstract operations, not seconds.*


## Reasoning

- time/best: Dijkstra (binary heap) O((V+E)·log(V)) vs Bellman-Ford O(V·E) → Dijkstra (binary heap) is asymptotically better. the cost ratio grows like n^0.94, so the advantage widens without bound as n grows.
- time/average: Dijkstra (binary heap) O((V+E)·log(V)) vs Bellman-Ford O(V·E) → Dijkstra (binary heap) is asymptotically better. the cost ratio grows like n^0.94, so the advantage widens without bound as n grows.
- time/worst: Dijkstra (binary heap) O((V+E)·log(V)) vs Bellman-Ford O(V·E) → Dijkstra (binary heap) is asymptotically better. the cost ratio grows like n^0.94, so the advantage widens without bound as n grows.
- space/worst: Dijkstra (binary heap) O(V) vs Bellman-Ford O(V) → asymptotically equivalent (same growth class).

## Growth classes

| case | Dijkstra (binary heap) | class | growth exponent | Bellman-Ford | class | growth exponent |
|---|---|---|---|---|---|---|
| time/best | `O((V+E)·log(V))` | linearithmic | 1.06 | `O(V·E)` | polynomial (degree ≈ 2.00) | 2 |
| time/average | `O((V+E)·log(V))` | linearithmic | 1.06 | `O(V·E)` | polynomial (degree ≈ 2.00) | 2 |
| time/worst | `O((V+E)·log(V))` | linearithmic | 1.06 | `O(V·E)` | polynomial (degree ≈ 2.00) | 2 |
| space/worst | `O(V)` | linear | 1 | `O(V)` | linear | 1 |

*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and 10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, ≫2 exponential/factorial.*


## Growth chart (log-log, ASCII)

```text
  2.0e+19 │                                                                            
          │                                                                          BB
          │                                                                     BBBBB  
          │                                                               BBBBBB       
  7.6e+14 │                                                          BBBBBB            
          │                                                     BBBBBB                 
          │                                                BBBBB                       
          │                                          BBBBBB                            
  2.9e+10 │                                      BBBBB                         AAAAAAAA
          │                                BBBBBB                    AAAAAAAAAA        
          │                           BBBBBB               AAAAAAAAAA                  
          │                      BBBBBB          AAAAAAAAAA                            
  1.1e+06 │                 BBBBB       AAAAAAAAAA                                     
          │           BBBBBB   AAAAAAAAAA                                              
          │      BBBBBXAAAAAAAA                                                        
          │ BBXXXXAAAA                                                                 
  4.3e+01 │XAA                                                                         
          │                                                                            
          └────────────────────────────────────────────────────────────────────────────
           10       100       1,000    10,000    100,000           10,000,000   ← n
  A = O((V+E)·log(V))   B = O(V·E)   X = the two curves cross/coincide here
  (time/average case · both axes log-scaled · y = operations)
```

## Caveats & constant factors

- **Dijkstra (binary heap):** The standard choice. Cannot handle negative edge weights.
- **Bellman-Ford:** O(VE) — much slower than Dijkstra, but the only simple SSSP algorithm that handles negative edges and detects negative cycles.

---

*Theoretical comparison generated by `algo-compare`. Big-O notation hides constant factors, memory-hierarchy effects and allocation cost — always confirm with an empirical benchmark (`algo-compare verify`) before making a production decision.*
