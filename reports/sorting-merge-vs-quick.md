# Algorithm comparison: Merge Sort vs Quick Sort

> **Task:** sort a list of comparable items  ·  **Family:** sorting


## Conclusion

Merge Sort and Quick Sort are in the same asymptotic class for average-case time (O(n log n)). Any real difference comes from constant factors, cache behaviour and allocation — measure before choosing. Worst case favours Merge Sort (O(n log n) vs O(n^2)); stability differs (Merge Sort: stable, Quick Sort: unstable); in-place-ness differs (Merge Sort: extra memory, Quick Sort: in-place).

**Overall winner: Merge Sort** (weighted score A=2 vs B=1.5)


## Complexity profiles

| | Merge Sort | Quick Sort |
|---|---|---|
| **category** | sorting | sorting |
| **task** | sort a list of comparable items | sort a list of comparable items |
| **time best** | O(n log n) | O(n log n) |
| **time average** | O(n log n) | O(n log n) |
| **time worst** | O(n log n) | O(n^2) |
| **space best** | O(n) | O(log n) |
| **space average** | O(n) | O(log n) |
| **space worst** | O(n) | O(n) |
| **stable** | yes | no |
| **in place** | no | yes |
| **input sensitive** | — | yes — best/average/worst differ |

## Case-by-case verdict

| dimension | case | Merge Sort | Quick Sort | winner | A÷B as n→∞ | crossover n |
|---|---|---|---|---|---|---|
| time | best | `O(n log n)` | `O(n log n)` | **tie** | equal | — |
| time | average | `O(n log n)` | `O(n log n)` | **tie** | equal | — |
| time | worst | `O(n log n)` | `O(n^2)` | **Merge Sort** | A/B → 0 (≈ n^0.94) | — |
| space | best | `O(n)` | `O(log n)` | **Quick Sort** | A/B → ∞ (≈ n^1.00) | — |
| space | average | `O(n)` | `O(log n)` | **Quick Sort** | A/B → ∞ (≈ n^1.00) | — |
| space | worst | `O(n)` | `O(n)` | **tie** | equal | — |

## Growth of the operation count (time/average case)

| n | Merge Sort `O(n log n)` | Quick Sort `O(n log n)` | A ÷ B | cheaper |
|---|---|---|---|---|
| 10 | 33.2 | 33.2 | 1 | = |
| 100 | 664 | 664 | 1 | = |
| 1,000 | 9.97e+03 | 9.97e+03 | 1 | = |
| 10,000 | 1.33e+05 | 1.33e+05 | 1 | = |
| 100,000 | 1.66e+06 | 1.66e+06 | 1 | = |
| 1,000,000 | 1.99e+07 | 1.99e+07 | 1 | = |
| 10,000,000 | 2.33e+08 | 2.33e+08 | 1 | = |
| 1,000,000,000 | 2.99e+10 | 2.99e+10 | 1 | = |

*Values are the declared growth functions evaluated at n — they count abstract operations, not seconds.*


## Reasoning

- time/best: Merge Sort O(n log n) vs Quick Sort O(n log n) → asymptotically equivalent (same growth class).
- time/average: Merge Sort O(n log n) vs Quick Sort O(n log n) → asymptotically equivalent (same growth class).
- time/worst: Merge Sort O(n log n) vs Quick Sort O(n^2) → Merge Sort is asymptotically better. the cost ratio grows like n^0.94, so the advantage widens without bound as n grows.
- space/best: Merge Sort O(n) vs Quick Sort O(log n) → Quick Sort is asymptotically better. the cost ratio grows like n^1.00, so the advantage widens without bound as n grows.
- space/average: Merge Sort O(n) vs Quick Sort O(log n) → Quick Sort is asymptotically better. the cost ratio grows like n^1.00, so the advantage widens without bound as n grows.
- space/worst: Merge Sort O(n) vs Quick Sort O(n) → asymptotically equivalent (same growth class).

## Growth classes

| case | Merge Sort | class | growth exponent | Quick Sort | class | growth exponent |
|---|---|---|---|---|---|---|
| time/best | `O(n log n)` | linearithmic | 1.06 | `O(n log n)` | linearithmic | 1.06 |
| time/average | `O(n log n)` | linearithmic | 1.06 | `O(n log n)` | linearithmic | 1.06 |
| time/worst | `O(n log n)` | linearithmic | 1.06 | `O(n^2)` | polynomial (degree ≈ 2.00) | 2 |
| space/best | `O(n)` | linear | 1 | `O(log n)` | logarithmic | 0 |
| space/average | `O(n)` | linear | 1 | `O(log n)` | logarithmic | 0 |
| space/worst | `O(n)` | linear | 1 | `O(n)` | linear | 1 |

*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and 10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, ≫2 exponential/factorial.*


## Growth chart (log-log, ASCII)

```text
  1.6e+11 │                                                                            
          │                                                                          XX
          │                                                                    XXXXXX  
          │                                                               XXXXXX       
  5.6e+08 │                                                         XXXXXX             
          │                                                    XXXXXX                  
          │                                              XXXXXX                        
          │                                         XXXXXX                             
  2.0e+06 │                                    XXXXX                                   
          │                               XXXXXX                                       
          │                          XXXXX                                             
          │                    XXXXXX                                                  
  7.2e+03 │               XXXXXX                                                       
          │          XXXXXX                                                            
          │      XXXXX                                                                 
          │ XXXXX                                                                      
  2.6e+01 │XX                                                                          
          │                                                                            
          └────────────────────────────────────────────────────────────────────────────
           10       100       1,000    10,000    100,000           10,000,000   ← n
  A = O(n log n)   B = O(n log n)   X = the two curves cross/coincide here
  (time/average case · both axes log-scaled · y = operations)
```

## Caveats & constant factors

- **Merge Sort:** Guaranteed O(n log n) in every case; needs O(n) aux memory for arrays (O(log n) on linked lists). Excellent for external / streaming sort.
- **Quick Sort:** Worst case O(n²) with a bad pivot (sorted input + first-element pivot); randomised or median-of-three pivots make it O(n log n) with high probability. Fastest general sort in practice: tiny constants, cache friendly.

---

*Theoretical comparison generated by `algo-compare`. Big-O notation hides constant factors, memory-hierarchy effects and allocation cost — always confirm with an empirical benchmark (`algo-compare verify`) before making a production decision.*
