# Algorithm comparison: Counting Sort vs Merge Sort

> **Task:** sort integers from a bounded range  ·  **Family:** sorting


> ⚠️ **Not strictly comparable** — see warnings below.


**Warnings**

- Different tasks: Counting Sort solves "sort integers from a bounded range" while Merge Sort solves "sort a list of comparable items". The comparison below is only meaningful if you consider these tasks equivalent.
- space/best is not declared for Counting Sort; its worst-case bound (O(n+k)) is used as a conservative stand-in.
- space/average is not declared for Counting Sort; its worst-case bound (O(n+k)) is used as a conservative stand-in.
- The two bounds use different parameters (Counting Sort: ['k', 'n'], Merge Sort: ['n']). Numeric samples below assume every non-`n` parameter equals n, so read them as shape comparisons, not exact values.


## Conclusion

These two do not solve the same task (Counting Sort: sort integers from a bounded range; Merge Sort: sort a list of comparable items), so read this as a reference comparison rather than a like-for-like verdict. For average-case time, Counting Sort (O(n+k)) beats Merge Sort (O(n log n)). The advantage only materialises above n ≈ 4: for smaller inputs the theoretically worse algorithm can still win on constant factors. Memory favours Merge Sort (O(n+k) vs O(n)).

**Overall winner: Counting Sort** (weighted score A=5.5 vs B=3)


## Complexity profiles

| | Counting Sort | Merge Sort |
|---|---|---|
| **category** | sorting | sorting |
| **task** | sort integers from a bounded range | sort a list of comparable items |
| **time best** | O(n+k) | O(n log n) |
| **time average** | O(n+k) | O(n log n) |
| **time worst** | O(n+k) | O(n log n) |
| **space worst** | O(n+k) | O(n) |
| **stable** | yes | yes |
| **in place** | no | no |
| **space best** | — | O(n) |
| **space average** | — | O(n) |

## Case-by-case verdict

| dimension | case | Counting Sort | Merge Sort | winner | A÷B as n→∞ | crossover n |
|---|---|---|---|---|---|---|
| time | best | `O(n+k)` | `O(n log n)` | **Counting Sort** | A/B → 0 (≈ n^0.06) | — |
| time | average | `O(n+k)` | `O(n log n)` | **Counting Sort** | A/B → 0 (≈ n^0.06) | — |
| time | worst | `O(n+k)` | `O(n log n)` | **Counting Sort** | A/B → 0 (≈ n^0.06) | — |
| space | best | `O(n+k)` | `O(n)` | **Merge Sort** | → 2× | — |
| space | average | `O(n+k)` | `O(n)` | **Merge Sort** | → 2× | — |
| space | worst | `O(n+k)` | `O(n)` | **Merge Sort** | → 2× | — |

## Growth of the operation count (time/average case)

| n | Counting Sort `O(n+k)` | Merge Sort `O(n log n)` | A ÷ B | cheaper |
|---|---|---|---|---|
| 10 | 20 | 33.2 | 0.602 | A |
| 100 | 200 | 664 | 0.301 | A |
| 1,000 | 2e+03 | 9.97e+03 | 0.201 | A |
| 10,000 | 2e+04 | 1.33e+05 | 0.151 | A |
| 100,000 | 2e+05 | 1.66e+06 | 0.12 | A |
| 1,000,000 | 2e+06 | 1.99e+07 | 0.1 | A |
| 10,000,000 | 2e+07 | 2.33e+08 | 0.086 | A |
| 1,000,000,000 | 2e+09 | 2.99e+10 | 0.0669 | A |

*Values are the declared growth functions evaluated at n — they count abstract operations, not seconds.*


## Reasoning

- time/best: Counting Sort O(n+k) vs Merge Sort O(n log n) → Counting Sort is asymptotically better. the curves touch only near n ≈ 4 (too small to matter), so Counting Sort is effectively ahead everywhere.
- time/average: Counting Sort O(n+k) vs Merge Sort O(n log n) → Counting Sort is asymptotically better. the curves touch only near n ≈ 4 (too small to matter), so Counting Sort is effectively ahead everywhere.
- time/worst: Counting Sort O(n+k) vs Merge Sort O(n log n) → Counting Sort is asymptotically better. the curves touch only near n ≈ 4 (too small to matter), so Counting Sort is effectively ahead everywhere.
- space/best: Counting Sort O(n+k) vs Merge Sort O(n) → Merge Sort is asymptotically better. same growth class — a constant factor of about 2 separates them, which Big-O hides.
- space/average: Counting Sort O(n+k) vs Merge Sort O(n) → Merge Sort is asymptotically better. same growth class — a constant factor of about 2 separates them, which Big-O hides.
- space/worst: Counting Sort O(n+k) vs Merge Sort O(n) → Merge Sort is asymptotically better. same growth class — a constant factor of about 2 separates them, which Big-O hides.

## Growth classes

| case | Counting Sort | class | growth exponent | Merge Sort | class | growth exponent |
|---|---|---|---|---|---|---|
| time/best | `O(n+k)` | linear | 1 | `O(n log n)` | linearithmic | 1.06 |
| time/average | `O(n+k)` | linear | 1 | `O(n log n)` | linearithmic | 1.06 |
| time/worst | `O(n+k)` | linear | 1 | `O(n log n)` | linearithmic | 1.06 |
| space/best | `O(n+k)` | linear | 1 | `O(n)` | linear | 1 |
| space/average | `O(n+k)` | linear | 1 | `O(n)` | linear | 1 |
| space/worst | `O(n+k)` | linear | 1 | `O(n)` | linear | 1 |

*Growth exponent = slope of log g(n) vs log n measured between n=10⁴ and 10⁷: ≈1 linear, ≈2 quadratic, ≈1.0x linearithmic, 0 logarithmic, ≫2 exponential/factorial.*


## Growth chart (log-log, ASCII)

```text
  1.6e+11 │                                                                            
          │                                                                          BB
          │                                                                    BBBBBB  
          │                                                              BBBBBBB    AAA
  5.1e+08 │                                                         BBBBBB    AAAAAA   
          │                                                   BBBBBB    AAAAAA         
          │                                              BBBBBB   AAAAAA               
          │                                        BBBBBB   AAAAAA                     
  1.6e+06 │                                   BBBBBB  AAAAAAA                          
          │                              BBBBBB  AAAAAA                                
          │                        BBBBBB  AAAAAA                                      
          │                   BBBBBB AAAAAA                                            
  5.0e+03 │              BBBBBBAAAAAA                                                  
          │         BBBBBXAAAAA                                                        
          │    BBBBXXAAAA                                                              
          │BBXXXAAA                                                                    
  1.6e+01 │AA                                                                          
          │                                                                            
          └────────────────────────────────────────────────────────────────────────────
           10       100       1,000    10,000    100,000           10,000,000   ← n
  A = O(n+k)   B = O(n log n)   X = the two curves cross/coincide here
  (time/average case · both axes log-scaled · y = operations)
```

## Caveats & constant factors

- **Counting Sort:** k = size of the value range. Linear only when k = O(n); otherwise the range dominates. Not a comparison sort — bypasses the Ω(n log n) bound.
- **Merge Sort:** Guaranteed O(n log n) in every case; needs O(n) aux memory for arrays (O(log n) on linked lists). Excellent for external / streaming sort.

---

*Theoretical comparison generated by `algo-compare`. Big-O notation hides constant factors, memory-hierarchy effects and allocation cost — always confirm with an empirical benchmark (`algo-compare verify`) before making a production decision.*
