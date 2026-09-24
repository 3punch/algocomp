# Algorithm comparison: Jump Search vs Binary Search

> **Task:** find a key in a sorted array  ·  **Family:** search / retrieval


**Warnings**

- space/average is not declared for Jump Search; its worst-case bound (O(1)) is used as a conservative stand-in.


## Conclusion

For average-case time, Binary Search (O(log n)) beats Jump Search (O(√n)). The advantage only materialises above n ≈ 16: for smaller inputs the theoretically worse algorithm can still win on constant factors.

**Overall winner: Binary Search** (weighted score A=1 vs B=5)


## Complexity profiles

| | Jump Search | Binary Search |
|---|---|---|
| **category** | search / retrieval | search / retrieval |
| **task** | find a key in a sorted array | find a key in a sorted array |
| **time best** | O(1) | O(1) |
| **time average** | O(√n) | O(log n) |
| **time worst** | O(√n) | O(log n) |
| **space worst** | O(1) | O(1) |
| **input sensitive** | yes — best/average/worst differ | yes — best/average/worst differ |
| **space average** | — | O(log n) |

## Case-by-case verdict

| dimension | case | Jump Search | Binary Search | winner | A÷B as n→∞ | crossover n |
|---|---|---|---|---|---|---|
| time | best | `O(1)` | `O(1)` | **tie** | equal | — |
| time | average | `O(√n)` | `O(log n)` | **Binary Search** | A/B → ∞ (≈ n^0.50) | 16 |
| time | worst | `O(√n)` | `O(log n)` | **Binary Search** | A/B → ∞ (≈ n^0.50) | 16 |
| space | average | `O(1)` | `O(log n)` | **Jump Search** | A/B → 0 (≈ n^0.00) | — |
| space | worst | `O(1)` | `O(1)` | **tie** | equal | — |

## Growth of the operation count (time/average case)

| n | Jump Search `O(√n)` | Binary Search `O(log n)` | A ÷ B | cheaper |
|---|---|---|---|---|
| 10 | 3.16 | 3.32 | 0.952 | A |
| 100 | 10 | 6.64 | 1.51 | B |
| 1,000 | 31.6 | 9.97 | 3.17 | B |
| 10,000 | 100 | 13.3 | 7.53 | B |
| 100,000 | 316 | 16.6 | 19 | B |
| 1,000,000 | 1e+03 | 19.9 | 50.2 | B |
| 10,000,000 | 3.16e+03 | 23.3 | 136 | B |
| 1,000,000,000 | 3.16e+04 | 29.9 | 1,058 | B |

*Values are the declared growth functions evaluated at n — they count abstract operations, not seconds.*


## Reasoning

- time/best: Jump Search O(1) vs Binary Search O(1) → asymptotically equivalent (same growth class).
- time/average: Jump Search O(√n) vs Binary Search O(log n) → Binary Search is asymptotically better. the ordering flips at n ≈ 16: below it Jump Search is cheaper, above it Binary Search takes over and stays ahead.
- time/worst: Jump Search O(√n) vs Binary Search O(log n) → Binary Search is asymptotically better. the ordering flips at n ≈ 16: below it Jump Search is cheaper, above it Binary Search takes over and stays ahead.
- space/average: Jump Search O(1) vs Binary Search O(log n) → Jump Search is asymptotically better. the cost ratio grows like n^0.00, so the advantage widens without bound as n grows.
- space/worst: Jump Search O(1) vs Binary Search O(1) → asymptotically equivalent (same growth class).

## Growth classes

| case | Jump Search | class | growth exponent | Binary Search | class | growth exponent |
|---|---|---|---|---|---|---|
| time/best | `O(1)` | constant | 0 | `O(1)` | constant | 0 |
| time/average | `O(√n)` | sublinear polynomial | 0.5 | `O(log n)` | logarithmic | 0 |
| time/worst | `O(√n)` | sublinear polynomial | 0.5 | `O(log n)` | logarithmic | 0 |
| space/average | `O(1)` | constant | 0 | `O(log n)` | logarithmic | 0 |
| space/worst | `O(1)` | constant | 0 | `O(1)` | constant | 0 |

*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and 10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, ≫2 exponential/factorial.*


## Growth chart (log-log, ASCII)

```text
  6.6e+04 │                                                                            
          │                                                                          AA
          │                                                                     AAAAA  
          │                                                               AAAAAA       
  5.3e+03 │                                                          AAAAAA            
          │                                                     AAAAAA                 
          │                                                AAAAAA                      
          │                                           AAAAA                            
  4.3e+02 │                                      AAAAA                                 
          │                                 AAAAAA                                     
          │                            AAAAA                                           
          │                      AAAAAA                                                
  3.5e+01 │                 AAAAAA                                         BBBBBBBBBBBB
          │            AAAAAA            BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB            
          │       AAAAAXBBBBBBBBBBBBBBBBB                                              
          │  XXXXXBBBBB                                                                
  2.8e+00 │XXB                                                                         
          │                                                                            
          └────────────────────────────────────────────────────────────────────────────
           10       100       1,000    10,000    100,000           10,000,000   ← n
  A = O(√n)   B = O(log n)   X = the two curves cross/coincide here
  (time/average case · both axes log-scaled · y = operations)
```

## Caveats & constant factors

- **Jump Search:** Block jumps of √n then linear scan. Better than binary search on media where seeking backwards is expensive (tapes, some databases).
- **Binary Search:** Requires sorted, random-access data. Iterative version is O(1) space; recursive is O(log n) stack. Cache-unfriendly on huge arrays (random jumps).

---

*Theoretical comparison generated by `algo-compare`. Big-O notation hides constant factors, memory-hierarchy effects and allocation cost — always confirm with an empirical benchmark (`algo-compare verify`) before making a production decision.*
