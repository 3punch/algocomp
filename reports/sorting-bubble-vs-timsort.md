# Algorithm comparison: Bubble Sort vs Timsort

> **Task:** sort a list of comparable items  ·  **Family:** sorting


## Conclusion

For average-case time, Timsort (O(n log n)) beats Bubble Sort (O(n^2)). Timsort is better at every input size, not just asymptotically. Memory favours Bubble Sort (O(1) vs O(n)); in-place-ness differs (Bubble Sort: in-place, Timsort: extra memory).

**Overall winner: Timsort** (weighted score A=1.5 vs B=5)


## Complexity profiles

| | Bubble Sort | Timsort |
|---|---|---|
| **category** | sorting | sorting |
| **task** | sort a list of comparable items | sort a list of comparable items |
| **time best** | O(n) | O(n) |
| **time average** | O(n^2) | O(n log n) |
| **time worst** | O(n^2) | O(n log n) |
| **space worst** | O(1) | O(n) |
| **stable** | yes | yes |
| **in place** | yes | no |
| **input sensitive** | yes — best/average/worst differ | yes — best/average/worst differ |

## Case-by-case verdict

| dimension | case | Bubble Sort | Timsort | winner | A÷B as n→∞ | crossover n |
|---|---|---|---|---|---|---|
| time | best | `O(n)` | `O(n)` | **tie** | equal | — |
| time | average | `O(n^2)` | `O(n log n)` | **Timsort** | A/B → ∞ (≈ n^0.94) | — |
| time | worst | `O(n^2)` | `O(n log n)` | **Timsort** | A/B → ∞ (≈ n^0.94) | — |
| space | worst | `O(1)` | `O(n)` | **Bubble Sort** | A/B → 0 (≈ n^1.00) | — |

## Growth of the operation count (time/average case)

| n | Bubble Sort `O(n^2)` | Timsort `O(n log n)` | A ÷ B | cheaper |
|---|---|---|---|---|
| 10 | 100 | 33.2 | 3.01 | B |
| 100 | 1e+04 | 664 | 15.1 | B |
| 1,000 | 1e+06 | 9.97e+03 | 100 | B |
| 10,000 | 1e+08 | 1.33e+05 | 753 | B |
| 100,000 | 1e+10 | 1.66e+06 | 6,021 | B |
| 1,000,000 | 1.00e+12 | 1.99e+07 | 50,172 | B |
| 10,000,000 | 1.00e+14 | 2.33e+08 | 430,043 | B |
| 1,000,000,000 | 1.00e+18 | 2.99e+10 | 33,447,777 | B |

*Values are the declared growth functions evaluated at n — they count abstract operations, not seconds.*


## Reasoning

- time/best: Bubble Sort O(n) vs Timsort O(n) → asymptotically equivalent (same growth class).
- time/average: Bubble Sort O(n^2) vs Timsort O(n log n) → Timsort is asymptotically better. the cost ratio grows like n^0.94, so the advantage widens without bound as n grows.
- time/worst: Bubble Sort O(n^2) vs Timsort O(n log n) → Timsort is asymptotically better. the cost ratio grows like n^0.94, so the advantage widens without bound as n grows.
- space/worst: Bubble Sort O(1) vs Timsort O(n) → Bubble Sort is asymptotically better. the cost ratio grows like n^1.00, so the advantage widens without bound as n grows.

## Growth classes

| case | Bubble Sort | class | growth exponent | Timsort | class | growth exponent |
|---|---|---|---|---|---|---|
| time/best | `O(n)` | linear | 1 | `O(n)` | linear | 1 |
| time/average | `O(n^2)` | polynomial (degree ≈ 2.00) | 2 | `O(n log n)` | linearithmic | 1.06 |
| time/worst | `O(n^2)` | polynomial (degree ≈ 2.00) | 2 | `O(n log n)` | linearithmic | 1.06 |
| space/worst | `O(1)` | constant | 0 | `O(n)` | linear | 1 |

*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and 10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, ≫2 exponential/factorial.*


## Growth chart (log-log, ASCII)

```text
  2.1e+19 │                                                                            
          │                                                                          AA
          │                                                                    AAAAAA  
          │                                                               AAAAAA       
  6.6e+14 │                                                          AAAAAA            
          │                                                    AAAAAA                  
          │                                               AAAAAA                       
          │                                          AAAAAA                            
  2.1e+10 │                                     AAAAA                           BBBBBBB
          │                                AAAAA                      BBBBBBBBBBB      
          │                          AAAAAA                 BBBBBBBBBB                 
          │                     AAAAAA            BBBBBBBBBB                           
  6.7e+05 │               AAAAAA         BBBBBBBBB                                     
          │          AAAAAA    BBBBBBBBBB                                              
          │     AAAAAABBBBBBBBBB                                                       
          │AAAXXBBBBBBB                                                                
  2.1e+01 │BBB                                                                         
          │                                                                            
          └────────────────────────────────────────────────────────────────────────────
           10       100       1,000    10,000    100,000           10,000,000   ← n
  A = O(n^2)   B = O(n log n)   X = the two curves cross/coincide here
  (time/average case · both axes log-scaled · y = operations)
```

## Caveats & constant factors

- **Bubble Sort:** Best case O(n) only with an early-exit flag on an already sorted input. Terrible constant factor and cache behaviour; teaching example only.
- **Timsort:** Adaptive merge sort exploiting existing runs. O(n) on already-sorted input. Default in Python (list.sort) and Java (Arrays.sort for objects).

---

*Theoretical comparison generated by `algo-compare`. Big-O notation hides constant factors, memory-hierarchy effects and allocation cost — always confirm with an empirical benchmark (`algo-compare verify`) before making a production decision.*
