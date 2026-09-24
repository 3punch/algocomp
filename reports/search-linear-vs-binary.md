# Algorithm comparison: Linear Search vs Binary Search

> **Task:** find a key in an unsorted array  ·  **Family:** search / retrieval


> ⚠️ **Not strictly comparable** — see warnings below.


**Warnings**

- Different tasks: Linear Search solves "find a key in an unsorted array" while Binary Search solves "find a key in a sorted array". The comparison below is only meaningful if you consider these tasks equivalent.
- space/average is not declared for Linear Search; its worst-case bound (O(1)) is used as a conservative stand-in.


## Conclusion

These two do not solve the same task (Linear Search: find a key in an unsorted array; Binary Search: find a key in a sorted array), so read this as a reference comparison rather than a like-for-like verdict. For average-case time, Binary Search (O(log n)) beats Linear Search (O(n)). Binary Search is better at every input size, not just asymptotically.

**Overall winner: Binary Search** (weighted score A=1 vs B=5)


## Complexity profiles

| | Linear Search | Binary Search |
|---|---|---|
| **category** | search / retrieval | search / retrieval |
| **task** | find a key in an unsorted array | find a key in a sorted array |
| **time best** | O(1) | O(1) |
| **time average** | O(n) | O(log n) |
| **time worst** | O(n) | O(log n) |
| **space worst** | O(1) | O(1) |
| **input sensitive** | yes — best/average/worst differ | yes — best/average/worst differ |
| **space average** | — | O(log n) |

## Case-by-case verdict

| dimension | case | Linear Search | Binary Search | winner | A÷B as n→∞ | crossover n |
|---|---|---|---|---|---|---|
| time | best | `O(1)` | `O(1)` | **tie** | equal | — |
| time | average | `O(n)` | `O(log n)` | **Binary Search** | A/B → ∞ (≈ n^1.00) | — |
| time | worst | `O(n)` | `O(log n)` | **Binary Search** | A/B → ∞ (≈ n^1.00) | — |
| space | average | `O(1)` | `O(log n)` | **Linear Search** | A/B → 0 (≈ n^0.00) | — |
| space | worst | `O(1)` | `O(1)` | **tie** | equal | — |

## Growth of the operation count (time/average case)

| n | Linear Search `O(n)` | Binary Search `O(log n)` | A ÷ B | cheaper |
|---|---|---|---|---|
| 10 | 10 | 3.32 | 3.01 | B |
| 100 | 100 | 6.64 | 15.1 | B |
| 1,000 | 1e+03 | 9.97 | 100 | B |
| 10,000 | 1e+04 | 13.3 | 753 | B |
| 100,000 | 1e+05 | 16.6 | 6,021 | B |
| 1,000,000 | 1e+06 | 19.9 | 50,172 | B |
| 10,000,000 | 1e+07 | 23.3 | 430,043 | B |
| 1,000,000,000 | 1e+09 | 29.9 | 33,447,777 | B |

*Values are the declared growth functions evaluated at n — they count abstract operations, not seconds.*


## Reasoning

- time/best: Linear Search O(1) vs Binary Search O(1) → asymptotically equivalent (same growth class).
- time/average: Linear Search O(n) vs Binary Search O(log n) → Binary Search is asymptotically better. the cost ratio grows like n^1.00, so the advantage widens without bound as n grows.
- time/worst: Linear Search O(n) vs Binary Search O(log n) → Binary Search is asymptotically better. the cost ratio grows like n^1.00, so the advantage widens without bound as n grows.
- space/average: Linear Search O(1) vs Binary Search O(log n) → Linear Search is asymptotically better. the cost ratio grows like n^0.00, so the advantage widens without bound as n grows.
- space/worst: Linear Search O(1) vs Binary Search O(1) → asymptotically equivalent (same growth class).

## Growth classes

| case | Linear Search | class | growth exponent | Binary Search | class | growth exponent |
|---|---|---|---|---|---|---|
| time/best | `O(1)` | constant | 0 | `O(1)` | constant | 0 |
| time/average | `O(n)` | linear | 1 | `O(log n)` | logarithmic | 0 |
| time/worst | `O(n)` | linear | 1 | `O(log n)` | logarithmic | 0 |
| space/average | `O(1)` | constant | 0 | `O(log n)` | logarithmic | 0 |
| space/worst | `O(1)` | constant | 0 | `O(1)` | constant | 0 |

*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and 10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, ≫2 exponential/factorial.*


## Growth chart (log-log, ASCII)

```text
  4.8e+09 │                                                                            
          │                                                                          AA
          │                                                                    AAAAAA  
          │                                                               AAAAAA       
  2.3e+07 │                                                         AAAAAA             
          │                                                    AAAAAA                  
          │                                              AAAAAA                        
          │                                         AAAAAA                             
  1.1e+05 │                                    AAAAA                                   
          │                              AAAAAA                                        
          │                         AAAAAA                                             
          │                   AAAAAA                                                   
  5.4e+02 │              AAAAAA                                                        
          │        AAAAAA                                                              
          │   AAAAAA                                     BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
          │AAA   BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB                              
  2.6e+00 │BBBBBB                                                                      
          │                                                                            
          └────────────────────────────────────────────────────────────────────────────
           10       100       1,000    10,000    100,000           10,000,000   ← n
  A = O(n)   B = O(log n)   X = the two curves cross/coincide here
  (time/average case · both axes log-scaled · y = operations)
```

## Caveats & constant factors

- **Linear Search:** No preprocessing, works on unsorted data and on streams. Average n/2 probes.
- **Binary Search:** Requires sorted, random-access data. Iterative version is O(1) space; recursive is O(log n) stack. Cache-unfriendly on huge arrays (random jumps).

---

*Theoretical comparison generated by `algo-compare`. Big-O notation hides constant factors, memory-hierarchy effects and allocation cost — always confirm with an empirical benchmark (`algo-compare verify`) before making a production decision.*
